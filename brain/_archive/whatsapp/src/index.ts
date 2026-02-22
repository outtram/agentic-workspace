/**
 * OutBot WhatsApp service entry point.
 * Wires together: WhatsApp connection, IPC server, message queue, typing manager.
 *
 * The Python brain connects via UNIX socket and sends JSON-RPC commands.
 * All incoming WhatsApp messages are forwarded to the brain as notifications.
 */

import pino from 'pino';
import { WhatsAppConnection } from './connection.js';
import { MessageQueue } from './queue.js';
import { TypingManager } from './typing.js';
import { IPCServer } from './ipc-server.js';
import { SOCKET_PATH, AUTH_DIR, LOG_LEVEL, PHONE_NUMBER } from './config.js';

const logger = pino({ name: 'outbot-wa', level: LOG_LEVEL });

async function main(): Promise<void> {
  logger.info('OutBot WhatsApp service starting...');

  const queue = new MessageQueue();

  const ipc = new IPCServer(SOCKET_PATH, {
    send_message: async (params) => {
      const { chat_jid, text } = params as { chat_jid: string; text: string };
      await queue.enqueue(chat_jid, text);
      return { ok: true };
    },
    set_typing: async (params) => {
      const { chat_jid, typing } = params as { chat_jid: string; typing: boolean };
      await typingManager.setTyping(chat_jid, typing);
      return { ok: true };
    },
  });

  const connection = new WhatsAppConnection(
    AUTH_DIR,
    (jid, msg) => {
      // Forward all messages to the Python brain
      ipc.notify('message_received', msg as unknown as Record<string, unknown>);
    },
    (connected) => {
      queue.setConnected(connected);
      ipc.notify('connection_status', { connected });
    },
    (qr) => {
      ipc.notify('qr_code', { qr });
    },
    PHONE_NUMBER || undefined,
  );

  const typingManager = new TypingManager(async (jid, status) => {
    await connection.socket?.sendPresenceUpdate(status, jid);
  });

  queue.setSender(async (jid, text) => {
    await connection.sendMessage(jid, text);
  });

  // Start IPC server first so the brain can connect immediately
  await ipc.start();
  logger.info('IPC server ready, connecting to WhatsApp...');

  // Connect to WhatsApp (will show QR if first time)
  await connection.connect();

  // Graceful shutdown
  const shutdown = async (signal: string) => {
    logger.info({ signal }, 'Shutting down...');
    typingManager.clearAll();
    await connection.disconnect();
    await ipc.stop();
    process.exit(0);
  };

  process.on('SIGINT', () => void shutdown('SIGINT'));
  process.on('SIGTERM', () => void shutdown('SIGTERM'));
}

main().catch((err) => {
  logger.fatal({ err }, 'Fatal error');
  process.exit(1);
});
