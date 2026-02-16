/**
 * UNIX socket JSON-RPC 2.0 server.
 * The Python brain connects as a client. Protocol: newline-delimited JSON.
 *
 * Requests from brain:  {"jsonrpc":"2.0","method":"send_message","params":{...},"id":1}
 * Responses to brain:   {"jsonrpc":"2.0","result":{"ok":true},"id":1}
 * Notifications (no id): {"jsonrpc":"2.0","method":"message_received","params":{...}}
 */

import { createServer, type Server, type Socket } from 'net';
import { existsSync, unlinkSync } from 'fs';
import pino from 'pino';
import { LOG_LEVEL } from './config.js';

interface JsonRpcRequest {
  jsonrpc: '2.0';
  method: string;
  params: Record<string, unknown>;
  id: string | number;
}

type Handler = (params: Record<string, unknown>) => Promise<unknown>;

export class IPCServer {
  private server: Server | null = null;
  private client: Socket | null = null;
  private buffer = '';
  private logger = pino({ name: 'ipc', level: LOG_LEVEL });

  constructor(
    private socketPath: string,
    private handlers: Record<string, Handler>,
  ) {}

  /** Start listening on the UNIX socket. */
  async start(): Promise<void> {
    // Remove stale socket file if it exists
    if (existsSync(this.socketPath)) {
      unlinkSync(this.socketPath);
      this.logger.info('Removed stale socket file');
    }

    return new Promise<void>((resolve, reject) => {
      this.server = createServer((socket) => {
        this.logger.info('Python brain connected');
        this.client = socket;
        this.buffer = '';

        socket.on('data', (data) => {
          this.buffer += data.toString('utf-8');
          this.processBuffer();
        });

        socket.on('close', () => {
          this.logger.info('Python brain disconnected');
          this.client = null;
          this.buffer = '';
        });

        socket.on('error', (err) => {
          this.logger.error({ err }, 'Client socket error');
          this.client = null;
          this.buffer = '';
        });
      });

      this.server.on('error', reject);

      this.server.listen(this.socketPath, () => {
        this.logger.info({ path: this.socketPath }, 'IPC server listening');
        resolve();
      });
    });
  }

  /** Process newline-delimited JSON messages from the buffer. */
  private processBuffer(): void {
    let newlineIdx: number;
    while ((newlineIdx = this.buffer.indexOf('\n')) !== -1) {
      const line = this.buffer.slice(0, newlineIdx).trim();
      this.buffer = this.buffer.slice(newlineIdx + 1);

      if (!line) continue;

      try {
        const msg = JSON.parse(line) as JsonRpcRequest;
        void this.handleMessage(msg);
      } catch (err) {
        this.logger.error({ err, line }, 'Failed to parse JSON-RPC message');
      }
    }
  }

  /** Route a JSON-RPC request to the appropriate handler. */
  private async handleMessage(msg: JsonRpcRequest): Promise<void> {
    const { method, params, id } = msg;
    const handler = this.handlers[method];

    if (!handler) {
      this.logger.warn({ method }, 'Unknown method');
      if (id !== undefined) {
        this.sendResponse(id, null, { code: -32601, message: `Method not found: ${method}` });
      }
      return;
    }

    try {
      const result = await handler(params ?? {});
      if (id !== undefined) {
        this.sendResponse(id, result ?? { ok: true });
      }
    } catch (err) {
      this.logger.error({ err, method }, 'Handler error');
      if (id !== undefined) {
        const message = err instanceof Error ? err.message : 'Internal error';
        this.sendResponse(id, null, { code: -32603, message });
      }
    }
  }

  /** Send a JSON-RPC response back to the Python brain. */
  private sendResponse(
    id: string | number,
    result: unknown,
    error?: { code: number; message: string },
  ): void {
    if (!this.client) return;

    const msg: Record<string, unknown> = { jsonrpc: '2.0', id };
    if (error) {
      msg.error = error;
    } else {
      msg.result = result;
    }

    this.client.write(JSON.stringify(msg) + '\n');
  }

  /** Send a JSON-RPC notification to the Python brain (no id = no response expected). */
  notify(method: string, params: Record<string, unknown>): void {
    if (!this.client) {
      this.logger.debug({ method }, 'No client connected, dropping notification');
      return;
    }

    const msg = { jsonrpc: '2.0', method, params };
    this.client.write(JSON.stringify(msg) + '\n');
  }

  /** Shut down the IPC server and clean up the socket file. */
  async stop(): Promise<void> {
    if (this.client) {
      this.client.destroy();
      this.client = null;
    }

    return new Promise<void>((resolve) => {
      if (this.server) {
        this.server.close(() => {
          if (existsSync(this.socketPath)) {
            unlinkSync(this.socketPath);
          }
          this.logger.info('IPC server stopped');
          resolve();
        });
      } else {
        resolve();
      }
    });
  }
}
