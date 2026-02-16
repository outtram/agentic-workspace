/**
 * Typing indicator management.
 * Auto-clears composing state after 25 seconds to avoid stuck indicators.
 */

export class TypingManager {
  private activeTimers = new Map<string, NodeJS.Timeout>();

  constructor(
    private sendPresence: (jid: string, status: 'composing' | 'paused') => Promise<void>,
  ) {}

  /** Set or clear typing indicator for a chat. */
  async setTyping(jid: string, isTyping: boolean): Promise<void> {
    // Clear any existing timer for this chat
    const existing = this.activeTimers.get(jid);
    if (existing) {
      clearTimeout(existing);
      this.activeTimers.delete(jid);
    }

    if (isTyping) {
      await this.sendPresence(jid, 'composing');
      // Auto-clear after 25 seconds to avoid stuck typing indicators
      const timer = setTimeout(async () => {
        this.activeTimers.delete(jid);
        try {
          await this.sendPresence(jid, 'paused');
        } catch {
          // Ignore - connection may have dropped
        }
      }, 25_000);
      this.activeTimers.set(jid, timer);
    } else {
      await this.sendPresence(jid, 'paused');
    }
  }

  /** Clear all active typing indicators. Used during shutdown. */
  clearAll(): void {
    for (const timer of this.activeTimers.values()) {
      clearTimeout(timer);
    }
    this.activeTimers.clear();
  }
}
