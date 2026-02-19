"""OutBot CLI - full-featured terminal interface with memory and personality.

Usage:
  python brain/chat.py          # Text chat
  python brain/chat.py --voice  # Voice chat (speak + listen)
"""

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.core.claude_client import ClaudeClient, CHAT_MODEL
from brain.core.config import Config
from brain.core.usage import UsageTracker
from brain.core.db import Database
from brain.core.events import EventBus
from brain.core.models import Message
from brain.memory.recall import is_recall_trigger, search_memory, format_recall_context
from brain.memory.reflection import reflect_on_session
from brain.memory.remember import (
    is_remember_trigger,
    is_forget_trigger,
    extract_memory,
    write_memory,
    forget_memory,
)
from brain.mail.inbox import Inbox, InboundEmail
from brain.mail.outbox import Outbox
from brain.personality.formatter import format_outbound
from brain.personality.loader import PersonalityLoader
from brain.session.archiver import SessionArchiver
from brain.session.context import format_catchup_summary
from brain.session.manager import SessionManager

CLI_JID = "cli@local"
MAX_CONTEXT_MESSAGES = 20

# Email intent detection — word-pair approach for natural phrasing
_EMAIL_NOUNS = {"email", "emails", "mail", "inbox"}
_CHECK_VERBS = {"check", "read", "show", "get", "fetch", "see", "list", "any", "new", "latest", "recent", "look", "open", "view", "pull"}
_SEND_VERBS = {"send", "write", "compose", "draft", "fire"}


class OutBotCLI:
    """Full OutBot experience via terminal — sessions, memory, personality."""

    def __init__(self, voice: bool = False):
        self.config = Config.load()
        self.db = Database(self.config.db_path)
        self.event_bus = EventBus()
        self.sessions = SessionManager(self.db, self.event_bus)
        self.personality_loader = PersonalityLoader(self.config.memory_dir)
        self.claude = ClaudeClient()
        self.usage = UsageTracker()
        self.claude.set_usage_tracker(self.usage)
        self.voice = voice
        self._message_count = 0

        # Email (lazy — only init if credentials configured)
        self._outbox: Outbox | None = None
        self._inbox: Inbox | None = None
        if self.config.email_address and self.config.email_app_password:
            self._outbox = Outbox.from_config(self.config, event_bus=self.event_bus)
            self._inbox = Inbox.from_config(self.config)

        # Voice components (lazy loaded)
        self._voice_record = None
        self._voice_transcribe = None
        self._voice_speak = None

    def _init_voice(self):
        """Load voice components on first use."""
        if self._voice_record is not None:
            return
        from brain.voice import record, transcribe, speak, _get_whisper, SAMPLE_RATE
        self._voice_record = record
        self._voice_transcribe = transcribe
        self._voice_speak = speak
        self._voice_sample_rate = SAMPLE_RATE
        # Pre-load whisper model
        print("  Loading speech model...", flush=True)
        _get_whisper()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _store_message(self, content: str, sender: str, is_from_me: bool) -> Message:
        """Store a message in the database."""
        msg = Message(
            id=str(uuid.uuid4()),
            chat_jid=CLI_JID,
            sender=sender,
            sender_name="Troy" if not is_from_me else "OutBot",
            content=content,
            timestamp=self._now(),
            is_from_me=is_from_me,
        )
        self.db.store_message(msg)
        return msg

    def _get_context(self) -> str:
        """Get recent conversation history as catch-up context."""
        # Get recent messages for this session
        session = self.sessions.get_or_create_session(CLI_JID)

        # Fetch recent messages (last N)
        recent = self.db.get_messages_since(CLI_JID, "", limit=MAX_CONTEXT_MESSAGES)
        if not recent:
            return ""

        # Skip the very last one (it's the message we just stored)
        return format_catchup_summary(recent)

    @staticmethod
    def _words(text: str) -> set[str]:
        """Extract lowercase words, stripping punctuation."""
        import re
        return set(re.findall(r"[a-z]+", text.lower()))

    def _is_email_check(self, text: str) -> bool:
        """Check if the user wants to check their email."""
        words = self._words(text)
        has_email_noun = bool(words & _EMAIL_NOUNS)
        has_check_verb = bool(words & _CHECK_VERBS)
        # "inbox" alone is enough, others need a verb
        return "inbox" in words or (has_email_noun and has_check_verb)

    def _is_email_send(self, text: str) -> bool:
        """Check if the user wants to send an email."""
        words = self._words(text)
        has_email_noun = bool(words & _EMAIL_NOUNS)
        has_send_verb = bool(words & _SEND_VERBS)
        return has_email_noun and has_send_verb

    async def _fetch_emails(self, limit: int = 10, unread_only: bool = False) -> str:
        """Fetch inbox and format as context for Claude.

        Defaults to ALL recent emails (not just unread) so Troy can always
        see what's in his inbox even if messages were already opened.
        """
        if not self._inbox:
            return "[Email not configured — set credentials in brain/.env]"

        try:
            emails = await self._inbox.check(limit=limit, unread_only=unread_only)
        except Exception as e:
            hint = ""
            if "EOF" in str(e) or "AUTHENTICATIONFAILED" in str(e):
                hint = " (hint: enable IMAP in Gmail Settings)"
            return f"[Email check failed: {e}{hint}]"

        if not emails:
            label = "unread emails" if unread_only else "recent emails"
            return f"[No {label} in inbox]"

        label = "unread" if unread_only else "recent"
        lines = [f"[{len(emails)} {label} email(s) fetched from inbox:]"]
        for i, e in enumerate(emails, 1):
            name = e.sender_name or e.sender
            preview = e.body[:200].replace("\n", " ") if e.body else "(no body)"
            lines.append(f"  {i}. From: {name} <{e.sender}>")
            lines.append(f"     Subject: {e.subject}")
            lines.append(f"     Date: {e.date}")
            lines.append(f"     Preview: {preview}")
        return "\n".join(lines)

    async def _do_email_send(self, text: str) -> str:
        """Extract email details via Claude and send. Returns status note."""
        if not self._outbox:
            return "[Email not configured — set credentials in brain/.env]"

        # Ask Claude to extract email fields from the user's message
        extraction = await self.claude.judge(
            prompt=text,
            system_prompt=(
                "Extract email details from the user's message. "
                "Reply in EXACTLY this format (one field per line):\n"
                "TO: <email address>\n"
                "SUBJECT: <subject line>\n"
                "BODY: <email body>\n\n"
                "If no recipient is specified, use TO: default\n"
                "If details are vague, make reasonable assumptions."
            ),
        )

        # Parse the extraction
        to_addr = ""
        subject = ""
        body = ""
        for line in extraction.strip().splitlines():
            line = line.strip()
            if line.upper().startswith("TO:"):
                to_addr = line[3:].strip()
            elif line.upper().startswith("SUBJECT:"):
                subject = line[8:].strip()
            elif line.upper().startswith("BODY:"):
                body = line[5:].strip()

        if to_addr.lower() == "default" or not to_addr:
            to_addr = self.config.email_default_to
            if not to_addr:
                return "[No recipient specified and OUTBOT_EMAIL_DEFAULT_TO not set]"

        if not subject:
            subject = "(no subject)"
        if not body:
            body = text

        try:
            await self._outbox.send(to=to_addr, subject=subject, body=body)
            return f"[Email SENT to {to_addr} — subject: \"{subject}\"]"
        except Exception as e:
            return f"[Email send FAILED: {e}]"

    async def send(self, text: str) -> str:
        """Send a message to OutBot and get a response."""
        # Store user message
        self._store_message(text, sender="troy", is_from_me=False)
        self._message_count += 1

        # Handle email — fetch/send data, then pass through Claude for natural response
        email_context = ""
        if self._is_email_check(text):
            # Only filter to unread if user specifically asks for "unread" or "new"
            words = self._words(text)
            unread_only = bool(words & {"unread", "new", "unseen"})
            email_context = await self._fetch_emails(limit=10, unread_only=unread_only)
        elif self._is_email_send(text):
            email_context = await self._do_email_send(text)

        # Handle memory triggers before calling Claude
        memory_note = ""
        if is_forget_trigger(text):
            removed = await forget_memory(text, self.config.memory_dir, self.claude)
            if removed:
                self.personality_loader.clear_cache()
                memory_note = "[Memory removed]"
            else:
                memory_note = "[No matching memory found]"
        elif is_remember_trigger(text):
            entry = await extract_memory(text, self.claude)
            summary = write_memory(entry, self.config.memory_dir)
            self.personality_loader.clear_cache()
            memory_note = f'[Memory saved: "{summary}"]'

        # Search past memories if message references history
        recall_context = ""
        if is_recall_trigger(text):
            results = search_memory(text, self.config.memory_dir)
            recall_context = format_recall_context(results)

        # Get conversation context
        context = self._get_context()

        # Load personality (picks up new memories after cache clear)
        personality = self.personality_loader.load_personality()

        # Build system prompt
        email_status = ""
        if self._outbox:
            email_status = (
                f"\nYou CAN send and check email via {self._outbox.from_address}. "
                "If Troy asks you to send an email, tell him to phrase it as "
                "'send email to X about Y' or 'send me a test email'. "
                "If he asks to check email, tell him to say 'check email' or 'inbox'.\n"
                "IMPORTANT: Email is handled by your built-in adapter. "
                "NEVER use browser tools, web tools, or any external tools to access email. "
                "If email data appears in the prompt below, just read it and respond — "
                "do NOT try to fetch, open, or browse email yourself."
            )

        system_prompt = (
            f"{personality}\n\n"
            "You are chatting with Troy in a terminal. "
            "Follow your personality rules exactly. Keep responses concise."
            f"{email_status}"
        )
        if self.voice:
            system_prompt += (
                "\nThis is a VOICE conversation — Troy is speaking to you. "
                "Keep responses SHORT (1-3 sentences). This will be spoken aloud, "
                "so avoid bullet points, formatting, and long lists."
            )
        else:
            system_prompt += (
                "\nYou DO have voice mode. Troy can run 'outbot voice' to "
                "start a voice conversation where he speaks and you reply aloud. "
                "Other options: 'outbot sonnet' (save credits), 'outbot test' (diagnostics), "
                "'outbot debug' (verbose logging). "
                "If he asks about audio/voice, tell him to restart with 'outbot voice'."
            )

        # Build prompt with conversation context
        if context:
            prompt = f"{context}\n\nTroy's latest message: {text}"
        else:
            prompt = text

        # Add recall context from past conversations
        if recall_context:
            prompt += f"\n\n{recall_context}"

        # Add email context (inbox results or send confirmation)
        if email_context:
            prompt += f"\n\n{email_context}"

        # Add memory note so Claude can acknowledge naturally
        if memory_note:
            prompt += f"\n\n{memory_note}"

        # Call Claude
        reply = await self.claude.ask(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        # Format output for the active channel
        channel = "voice" if self.voice else "cli"
        reply = format_outbound(reply, channel=channel)

        # Store OutBot's reply
        self._store_message(reply, sender="outbot", is_from_me=True)
        self._message_count += 1

        return reply

    def _get_voice_input(self) -> str | None:
        """Record and transcribe voice input."""
        print("  🎙️  Recording... press ENTER to stop")
        audio = self._voice_record()

        if audio is None or len(audio) < self._voice_sample_rate * 0.5:
            print("  [Too short — try again]")
            return None

        print("  ⏳ Transcribing...", end="", flush=True)
        text = self._voice_transcribe(audio)

        if not text:
            print("\r  [Couldn't understand that]     ")
            return None

        print(f"\r  Troy: {text}                     ")
        return text

    async def run(self):
        """Main chat loop."""
        if self.voice:
            self._init_voice()

        W = 35  # Interior width between ║ and ║
        def _row(text: str) -> str:
            return f"  ║ {text:<{W-2}} ║"

        print(f"\n  ╔{'═' * W}╗")
        if self.voice:
            print(_row("OutBot Voice Chat"))
            print(_row("ENTER = record, ENTER = stop"))
        else:
            print(_row("OutBot Terminal Chat"))
        print(_row(f"Model: {CHAT_MODEL}"))
        email_addr = self._outbox.from_address if self._outbox else None
        if email_addr:
            print(_row(f"Email: {email_addr}"))
        print(_row("Type 'quit' to exit"))
        print(f"  ╚{'═' * W}╝\n")

        while True:
            try:
                if self.voice:
                    cmd = input("  Press ENTER to talk (q to quit): ").strip().lower()
                    if cmd in ("q", "quit", "exit"):
                        break
                    text = self._get_voice_input()
                    if not text:
                        continue
                else:
                    text = input("  Troy > ").strip()
                    if text.lower() in ("quit", "exit", "q"):
                        break
                    if not text:
                        continue

            except (EOFError, KeyboardInterrupt):
                break

            print("  ⏳ ...", end="", flush=True)

            try:
                reply = await self.send(text)
                print(f"\r  OutBot > {reply}                 ")
                print(f"  [{self.usage.format_status()}]\n")

                if self.voice and self._voice_speak:
                    self._voice_speak(reply)

            except Exception as e:
                print(f"\r  [Error: {e}]                   \n")

        # Archive session if enough messages
        if self._message_count >= 3:
            try:
                messages = self.db.get_messages_since(CLI_JID, "", limit=200)
                summary = await self.claude.judge(
                    prompt="\n".join(m.content for m in messages[-10:]),
                    system_prompt=(
                        "Summarise this conversation in 5-8 words for a filename. "
                        "Reply with ONLY the summary, no quotes or punctuation."
                    ),
                )
                archiver = SessionArchiver()
                path = archiver.archive(CLI_JID, messages, summary.strip())
                print(f"  Session archived ({path.name})")

                # Reflect on the session — observe patterns
                observations = await reflect_on_session(
                    messages, self.config.memory_dir, self.claude,
                )
                if observations:
                    print(f"  Learned {len(observations)} new pattern(s)")
            except Exception as e:
                print(f"  [Archive failed: {e}]")

        # Show usage summary
        if self.usage.session_calls > 0:
            print()
            print(self.usage.format_session_summary())

        print("\n  Cheers, mate!\n")
        self.db.close()


async def _run_diagnostics():
    """Test the Claude CLI connection step by step."""
    import shutil
    import subprocess
    import time
    from brain.core.claude_client import _find_claude, ClaudeClient

    print("\n  === OutBot Diagnostics ===\n")

    # Step 1: Find binary
    path = _find_claude()
    print(f"  1. Claude binary: {path}")
    if not shutil.which("claude") and not os.path.isfile(path):
        print("     FAIL — claude not found. Install Claude Code first.")
        return
    print("     OK")

    # Step 2: Check version (direct subprocess, no async)
    print("  2. Checking version...", end="", flush=True)
    r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
    print(f" {r.stdout.strip()}")

    # Step 3: Raw shell test (no pipes — output goes straight to terminal)
    # Set NODE_EXTRA_CA_CERTS for corporate proxy SSL
    from brain.core.claude_client import _get_ca_certs
    ca_path = _get_ca_certs()
    ca_env = f"NODE_EXTRA_CA_CERTS='{ca_path}' " if ca_path else ""
    print("  3. Raw shell test (output appears below):")
    print(f"     Running: {ca_env}claude -p --model haiku 'say PING'")
    t0 = time.time()
    rc = os.system(f"{ca_env}'{path}' -p --model haiku 'say PING' 2>/dev/null")
    elapsed = time.time() - t0
    print(f"     rc={rc}, {elapsed:.1f}s")
    if rc != 0:
        print("     FAIL — claude --print doesn't work in this terminal.")
        print("     Are you running Claude Code in another terminal?")
        print("     Try: claude auth status")
        return

    # Step 4: subprocess.run with pipe capture
    print("  4. Pipe capture test...", end="", flush=True)
    t0 = time.time()
    step4_env = {**os.environ}
    if ca_path:
        step4_env["NODE_EXTRA_CA_CERTS"] = ca_path
    r = subprocess.run(
        [path, "-p", "--model", "haiku", "Reply with: PONG OK"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=step4_env,
        timeout=60,
    )
    elapsed = time.time() - t0
    print(f" {elapsed:.1f}s rc={r.returncode} — {r.stdout.decode().strip()[:60]}")
    if r.returncode != 0:
        print(f"     FAIL — stderr: {r.stderr.decode().strip()[:200]}")
        return

    # Step 5: Full ClaudeClient test
    print("  5. ClaudeClient (sonnet + system prompt)...", end="", flush=True)
    t0 = time.time()
    try:
        client = ClaudeClient(model="sonnet")
        loader = PersonalityLoader(Config.load().memory_dir)
        personality = loader.load_personality()
        result = await client.ask(
            "Say one sentence to confirm you work.",
            system_prompt=f"{personality}\n\nReply concisely.",
        )
        elapsed = time.time() - t0
        print(f" {elapsed:.1f}s — {result[:80]}")
    except Exception as e:
        print(f"\n     FAIL — {e}")
        return

    print("\n  All checks passed. Chat should work.\n")


if __name__ == "__main__":
    import logging
    import os

    if "--debug" in sys.argv:
        logging.basicConfig(level=logging.DEBUG, format="  [%(name)s] %(message)s")

    if "--test" in sys.argv:
        asyncio.run(_run_diagnostics())
    else:
        voice_mode = "--voice" in sys.argv
        cli = OutBotCLI(voice=voice_mode)
        asyncio.run(cli.run())
