# Archived Code

Code archived on 2026-02-22 when replacing WhatsApp with Telegram.

## whatsapp/
Node.js WhatsApp adapter using Baileys (reverse-engineered WhatsApp Web protocol).
Archived because: Deloitte laptop restrictions prevented WhatsApp setup.
Replaced by: `brain/telegram/` using Telegram Bot API.

## ipc/
Python UNIX socket IPC client for communicating with the Node.js WhatsApp subprocess.
Archived because: Telegram adapter runs natively in Python (no subprocess/IPC needed).
The JSON-RPC 2.0 protocol is preserved here for reference if needed.
