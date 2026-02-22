/**
 * Outgoing message queue with offline buffering.
 * Messages are never lost - queued when disconnected, flushed on reconnect.
 */

import pino from 'pino';
import { LOG_LEVEL } from './config.js';

interface QueuedMessage {
  jid: string;
  text: string;
  timestamp: number;
}

export class MessageQueue {
  private queue: QueuedMessage[] = [];
  private connected = false;
  private sendFn: ((jid: string, text: string) => Promise<void>) | null = null;
  private logger = pino({ name: 'queue', level: LOG_LEVEL });

  /** Register the actual send function (from WhatsAppConnection). */
  setSender(fn: (jid: string, text: string) => Promise<void>): void {
    this.sendFn = fn;
  }

  /** Update connection state. Flushes queue when reconnected. */
  setConnected(connected: boolean): void {
    this.connected = connected;
    if (connected && this.queue.length > 0) {
      this.logger.info({ queued: this.queue.length }, 'Connection restored, flushing queue');
      void this.flush();
    }
  }

  /** Enqueue a message. Sends immediately if connected, otherwise buffers. */
  async enqueue(jid: string, text: string): Promise<void> {
    if (this.connected && this.sendFn) {
      try {
        await this.sendFn(jid, text);
        return;
      } catch (err) {
        this.logger.warn({ err, jid }, 'Send failed, queuing message');
      }
    }

    this.queue.push({ jid, text, timestamp: Date.now() });
    this.logger.info({ jid, queueSize: this.queue.length }, 'Message queued (offline)');
  }

  /** Flush all queued messages in order. */
  private async flush(): Promise<void> {
    if (!this.sendFn) return;

    while (this.queue.length > 0 && this.connected) {
      const msg = this.queue[0];
      try {
        await this.sendFn(msg.jid, msg.text);
        this.queue.shift();
      } catch (err) {
        this.logger.warn({ err, jid: msg.jid }, 'Flush send failed, will retry on next reconnect');
        break;
      }
    }

    if (this.queue.length === 0) {
      this.logger.info('Queue flushed successfully');
    }
  }
}
