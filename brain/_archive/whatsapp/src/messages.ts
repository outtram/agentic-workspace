/**
 * Message extraction utilities for Baileys WAMessage objects.
 */

import type { proto } from '@whiskeysockets/baileys';

export interface IncomingMessage {
  id: string;
  chat_jid: string;
  sender: string;
  sender_name: string;
  content: string;
  timestamp: string;
  is_from_me: boolean;
}

/**
 * Extract a normalised IncomingMessage from a Baileys WAMessage.
 * Returns null for messages we should skip (status broadcasts, empty content).
 */
export function extractMessage(msg: proto.IWebMessageInfo): IncomingMessage | null {
  // Skip status@broadcast messages
  const jid = msg.key.remoteJid;
  if (!jid || jid === 'status@broadcast') return null;

  // Extract text content from various message types
  const message = msg.message;
  if (!message) return null;

  const text =
    message.conversation ??
    message.extendedTextMessage?.text ??
    message.imageMessage?.caption ??
    message.videoMessage?.caption ??
    null;

  if (!text) return null;

  const isFromMe = msg.key.fromMe ?? false;
  const sender = isFromMe
    ? jid
    : msg.key.participant ?? jid;

  const senderName = msg.pushName ?? sender;

  const timestamp = msg.messageTimestamp
    ? new Date(Number(msg.messageTimestamp) * 1000).toISOString()
    : new Date().toISOString();

  return {
    id: msg.key.id ?? '',
    chat_jid: jid,
    sender,
    sender_name: senderName,
    content: text,
    timestamp,
    is_from_me: isFromMe,
  };
}

/** Escape XML/HTML special characters. */
export function escapeXml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}
