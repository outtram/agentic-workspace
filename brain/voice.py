"""OutBot Voice Chat - simple terminal voice interface.

Controls:
  ENTER  = start/stop recording
  q      = quit
"""

import asyncio
import io
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

# Fix macOS corporate SSL certs before any network imports
def _fix_ssl_certs():
    """Combine macOS system certs with certifi so HuggingFace downloads work."""
    if os.environ.get("REQUESTS_CA_BUNDLE"):
        return  # Already set
    combined = Path(tempfile.gettempdir()) / "outbot_certs.pem"
    if combined.exists():
        os.environ["REQUESTS_CA_BUNDLE"] = str(combined)
        return
    try:
        import certifi
        certs = []
        for keychain in [
            "/System/Library/Keychains/SystemRootCertificates.keychain",
            "/Library/Keychains/System.keychain",
        ]:
            result = subprocess.run(
                ["security", "find-certificate", "-a", "-p", keychain],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                certs.append(result.stdout)
        certs.append(Path(certifi.where()).read_text())
        combined.write_text("\n".join(certs))
        os.environ["REQUESTS_CA_BUNDLE"] = str(combined)
    except Exception:
        pass  # Best effort — model may already be cached

_fix_ssl_certs()

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from brain.core.claude_client import ClaudeClient
from brain.personality.loader import PersonalityLoader
from brain.personality.formatter import format_outbound

# ── Config ──────────────────────────────────────────────
VOICE = os.environ.get("OUTBOT_VOICE", "")  # Empty = system default
SPEAK_RATE = int(os.environ.get("OUTBOT_SPEAK_RATE", "190"))
WHISPER_MODEL = os.environ.get("OUTBOT_WHISPER_MODEL", "base")  # tiny/base/small/medium
SAMPLE_RATE = 16000
# ────────────────────────────────────────────────────────

# Lazy-loaded Whisper model
_whisper: WhisperModel | None = None


def _get_whisper() -> WhisperModel:
    global _whisper
    if _whisper is None:
        print(f"  Loading Whisper ({WHISPER_MODEL}) — first time only...", flush=True)
        # Try cached model first (no network), fall back to download
        try:
            _whisper = WhisperModel(
                WHISPER_MODEL, device="cpu", compute_type="int8",
                download_root=None, local_files_only=True,
            )
        except Exception:
            # Model not cached — download it
            _whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _whisper


def speak(text: str) -> None:
    """Speak text using macOS say command."""
    clean = text.replace("*", "").replace("_", "").replace("```", "")
    cmd = ["say", "-r", str(SPEAK_RATE)]
    if VOICE:
        cmd.extend(["-v", VOICE])
    cmd.append(clean)
    subprocess.run(cmd, capture_output=True)


def record() -> np.ndarray | None:
    """Record audio until user presses Enter. Returns numpy array or None."""
    frames: list[np.ndarray] = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            callback=callback,
        )
        stream.start()
        input()  # Block until Enter
        stream.stop()
        stream.close()
    except Exception as e:
        print(f"\n  [Mic error: {e}]")
        print("  Check: System Settings > Privacy > Microphone")
        return None

    if not frames:
        return None

    return np.concatenate(frames)


def audio_to_wav_bytes(audio: np.ndarray) -> bytes:
    """Convert numpy audio array to WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


def transcribe(audio: np.ndarray) -> str | None:
    """Transcribe audio using local Whisper model."""
    model = _get_whisper()

    wav_data = audio_to_wav_bytes(audio)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        tmp.write(wav_data)
        tmp.close()
        segments, _ = model.transcribe(tmp.name, language="en", beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments)
        return text.strip() or None
    except Exception as e:
        print(f"\n  [Whisper error: {e}]")
        return None
    finally:
        os.unlink(tmp.name)


async def main():
    loader = PersonalityLoader(".claude/memory")
    personality = loader.load_personality()
    client = ClaudeClient(model="sonnet")

    system_prompt = (
        f"{personality}\n\n"
        "You are chatting with Troy via voice. Keep responses SHORT and "
        "conversational - 1-3 sentences max. This is spoken aloud, so avoid "
        "bullet points and formatting. Be natural and conversational."
    )

    print("\n  ╔═══════════════════════════════════╗")
    print("  ║       OutBot Voice Chat           ║")
    print("  ║                                   ║")
    print("  ║  ENTER = start recording           ║")
    print("  ║  ENTER = stop recording            ║")
    print("  ║  q     = quit                      ║")
    print("  ╚═══════════════════════════════════╝\n")

    # Pre-load Whisper model
    _get_whisper()
    print()

    while True:
        cmd = input("  Press ENTER to talk (q to quit): ").strip().lower()
        if cmd in ("q", "quit", "exit"):
            break

        print("  🎙️  Recording... press ENTER to stop")
        audio = record()

        if audio is None or len(audio) < SAMPLE_RATE * 0.5:
            print("  [Too short — try again]\n")
            continue

        print("  ⏳ Transcribing...", end="", flush=True)
        text = transcribe(audio)

        if not text:
            print("\r  [Couldn't understand that]     \n")
            continue

        print(f"\r  Troy: {text}                     ")

        print("  ⏳ Thinking...", end="", flush=True)
        try:
            raw = await client.ask(prompt=text, system_prompt=system_prompt)
            reply = format_outbound(raw)
            print(f"\r  OutBot: {reply}                 ")
            print()
            speak(reply)
        except Exception as e:
            print(f"\r  [Error: {e}]                   \n")

    print("\n  Cheers, mate!\n")


if __name__ == "__main__":
    asyncio.run(main())
