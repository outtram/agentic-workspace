"""Voice mode handler — toggle, record, transcribe, speak within the TUI.

Imports transcribe/speak from brain.voice. Recording is handled via
sounddevice InputStream controlled by Textual key events (not stdin).
"""

import re

try:
    import numpy as np
    import sounddevice as sd
    from brain.voice import transcribe, speak, _find_input_device, SAMPLE_RATE

    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    SAMPLE_RATE = 16000


def _strip_markup(text: str) -> str:
    """Remove Rich markup tags for TTS."""
    return re.sub(r"\[/?[^\]]*\]", "", text)


class VoiceHandler:
    """Manages voice mode state and recording within the TUI."""

    def __init__(self):
        self.active = False
        self.recording = False
        self._frames: list = []
        self._stream = None

    def toggle(self) -> bool:
        """Toggle voice mode on/off. Returns new state."""
        if not VOICE_AVAILABLE:
            return False
        if self.recording:
            self.stop_recording()
        self.active = not self.active
        return self.active

    def start_recording(self) -> bool:
        """Start recording audio. Returns True if started successfully."""
        if not VOICE_AVAILABLE or self.recording:
            return False

        self._frames = []
        try:
            device = _find_input_device()
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                callback=self._audio_callback,
                device=device,
            )
            self._stream.start()
            self.recording = True
            return True
        except Exception:
            self.recording = False
            return False

    def stop_recording(self):
        """Stop recording and return audio as numpy array."""
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self.recording = False

        if not self._frames:
            return None

        audio = np.concatenate(self._frames)
        # Check minimum duration (0.5s) and volume
        if len(audio) < SAMPLE_RATE * 0.5:
            return None
        peak = np.max(np.abs(audio))
        if peak < 50:
            return None  # Too quiet
        return audio

    def _audio_callback(self, indata, frame_count, time_info, status):
        """Sounddevice callback — accumulates audio chunks."""
        self._frames.append(indata.copy())
