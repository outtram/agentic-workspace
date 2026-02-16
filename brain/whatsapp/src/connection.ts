/**
 * Baileys WhatsApp connection manager.
 * Handles connection lifecycle, auth persistence, auto-reconnect, and message routing.
 */

import makeWASocket, {
  Browsers,
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  useMultiFileAuthState,
  type WASocket,
} from '@whiskeysockets/baileys';
import pino from 'pino';
import qrTerminal from 'qrcode-terminal';
import { extractMessage, type IncomingMessage } from './messages.js';
import { LOG_LEVEL, RECONNECT_DELAY, MAX_RECONNECT_ATTEMPTS } from './config.js';

export class WhatsAppConnection {
  private sock: WASocket | null = null;
  private reconnectAttempts = 0;
  private logger = pino({ name: 'whatsapp', level: LOG_LEVEL });

  constructor(
    private authDir: string,
    private onMessage: (jid: string, msg: IncomingMessage) => void,
    private onConnectionChange: (connected: boolean) => void,
    private onQR: (qr: string) => void,
    private phoneNumber?: string,
  ) {}

  /** Get the underlying socket (for typing indicators etc). */
  get socket(): WASocket | null {
    return this.sock;
  }

  /** Establish WhatsApp Web connection via Baileys. */
  async connect(): Promise<void> {
    const { state, saveCreds } = await useMultiFileAuthState(this.authDir);

    // Fetch latest WA Web version (required for handshake)
    let version: [number, number, number] | undefined;
    try {
      const versionInfo = await fetchLatestBaileysVersion();
      version = versionInfo.version;
      this.logger.info({ version }, 'Using WA Web version');
    } catch (err) {
      this.logger.warn({ err }, 'Failed to fetch WA version, using default');
    }

    this.sock = makeWASocket({
      auth: {
        creds: state.creds,
        keys: makeCacheableSignalKeyStore(state.keys, this.logger),
      },
      ...(version && { version }),
      logger: this.logger,
      browser: Browsers.macOS('Chrome'),
      connectTimeoutMs: 30_000,
    });

    // Request pairing code after socket creation if phone number provided
    if (this.phoneNumber && !state.creds.registered) {
      // Delay slightly to let the socket establish the WebSocket connection
      setTimeout(async () => {
        try {
          this.logger.info('Requesting pairing code for %s...', this.phoneNumber);
          const code = await this.sock!.requestPairingCode(this.phoneNumber!);
          console.log('\n╔══════════════════════════════════════╗');
          console.log('║  WhatsApp Pairing Code: ' + code.padEnd(13) + '║');
          console.log('║                                      ║');
          console.log('║  On your phone:                      ║');
          console.log('║  Settings > Linked Devices > Link    ║');
          console.log('║  > Link with phone number            ║');
          console.log('║  Enter the code above                ║');
          console.log('╚══════════════════════════════════════╝\n');
          this.onQR(`pairing:${code}`);
        } catch (err) {
          this.logger.error({ err }, 'Failed to request pairing code');
        }
      }, 5000);
    }

    // Handle connection lifecycle
    this.sock.ev.on('connection.update', async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        // Render QR code to terminal (fallback when no phone number)
        qrTerminal.generate(qr, { small: true });
        this.onQR(qr);
      }

      if (connection === 'open') {
        this.reconnectAttempts = 0;
        this.logger.info('WhatsApp connection established');
        this.onConnectionChange(true);
      }

      if (connection === 'close') {
        this.onConnectionChange(false);

        const statusCode = (lastDisconnect?.error as any)?.output?.statusCode;

        if (statusCode === DisconnectReason.loggedOut) {
          this.logger.error('Logged out of WhatsApp - delete auth/ and re-scan QR code');
          process.exit(1);
        }

        this.reconnectAttempts++;
        if (this.reconnectAttempts > MAX_RECONNECT_ATTEMPTS) {
          this.logger.error(
            { attempts: this.reconnectAttempts },
            'Max reconnect attempts exceeded',
          );
          process.exit(1);
        }

        this.logger.info(
          { attempt: this.reconnectAttempts, delay: RECONNECT_DELAY },
          'Reconnecting...',
        );
        setTimeout(() => this.connect(), RECONNECT_DELAY);
      }
    });

    // Persist auth credentials on update
    this.sock.ev.on('creds.update', saveCreds);

    // Route incoming messages to the callback
    this.sock.ev.on('messages.upsert', async ({ messages, type }) => {
      // Only process new messages (not history sync)
      if (type !== 'notify') return;

      for (const raw of messages) {
        const msg = extractMessage(raw);
        if (msg) {
          this.logger.debug({ jid: msg.chat_jid, from: msg.sender_name }, 'Message received');
          this.onMessage(msg.chat_jid, msg);
        }
      }
    });
  }

  /** Send a text message to a JID. */
  async sendMessage(jid: string, text: string): Promise<void> {
    if (!this.sock) {
      throw new Error('WhatsApp not connected');
    }
    await this.sock.sendMessage(jid, { text });
    this.logger.debug({ jid }, 'Message sent');
  }

  /** Set typing presence for a chat. */
  async setTyping(jid: string, isTyping: boolean): Promise<void> {
    if (!this.sock) return;
    await this.sock.sendPresenceUpdate(isTyping ? 'composing' : 'paused', jid);
  }

  /** Gracefully disconnect from WhatsApp. */
  async disconnect(): Promise<void> {
    if (this.sock) {
      this.sock.end(undefined);
      this.sock = null;
      this.logger.info('WhatsApp disconnected');
    }
  }
}
