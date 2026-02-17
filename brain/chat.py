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
from brain.personality.formatter import format_outbound
from brain.personality.loader import PersonalityLoader
from brain.session.archiver import SessionArchiver
from brain.session.context import format_catchup_summary
from brain.session.manager import SessionManager

CLI_JID = "cli@local"
MAX_CONTEXT_MESSAGES = 20


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

    async def send(self, text: str) -> str:
        """Send a message to OutBot and get a response."""
        # Store user message
        self._store_message(text, sender="troy", is_from_me=False)
        self._message_count += 1

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
        system_prompt = (
            f"{personality}\n\n"
            "You are chatting with Troy in a terminal. "
            "Follow your personality rules exactly. Keep responses concise."
        )
        if self.voice:
            system_prompt += (
                "\nThis is a VOICE conversation — Troy is speaking to you. "
                "Keep responses SHORT (1-3 sentences). This will be spoken aloud, "
                "so avoid bullet points, formatting, and long lists."
            )

        # Build prompt with conversation context
        if context:
            prompt = f"{context}\n\nTroy's latest message: {text}"
        else:
            prompt = text

        # Add recall context from past conversations
        if recall_context:
            prompt += f"\n\n{recall_context}"

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

        print("\n  ╔═══════════════════════════════════╗")
        if self.voice:
            print("  ║     OutBot Voice Chat             ║")
            print("  ║  ENTER = record, ENTER = stop     ║")
        else:
            print("  ║     OutBot Terminal Chat           ║")
        print(f"  ║  Model: {CHAT_MODEL:<27}║")
        print("  ║  Type 'quit' to exit              ║")
        print("  ╚═══════════════════════════════════╝\n")

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
