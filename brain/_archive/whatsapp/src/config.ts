/**
 * OutBot WhatsApp service configuration.
 * Loaded from environment variables with sensible defaults.
 */

/** UNIX socket path for IPC with the Python brain. */
export const SOCKET_PATH = process.env.OUTBOT_SOCKET_PATH ?? '/tmp/outbot.sock';

/** Directory for Baileys auth state (session persistence). */
export const AUTH_DIR = './auth';

/** Directory for message store / SQLite. */
export const STORE_DIR = './store';

/** Delay before reconnecting after a non-logout disconnect (ms). */
export const RECONNECT_DELAY = 5000;

/** Maximum reconnection attempts before giving up. */
export const MAX_RECONNECT_ATTEMPTS = 10;

/** How often to poll for messages if needed (ms). */
export const MESSAGE_POLL_INTERVAL = 2000;

/** Idle timeout before marking session inactive (ms). 30 minutes. */
export const IDLE_TIMEOUT = 1_800_000;

/** Pino log level. */
export const LOG_LEVEL = process.env.OUTBOT_LOG_LEVEL ?? 'info';

/** Phone number for pairing code auth (E.164 without +, e.g. "61409978707"). */
export const PHONE_NUMBER = process.env.OUTBOT_PHONE_NUMBER ?? '';
