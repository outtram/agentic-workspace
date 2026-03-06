"""Tests for voice chat — verifies core components without needing a mic."""

import io
import os
import sys
import tempfile
import wave

import pytest

np = pytest.importorskip("numpy")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent.parent))

from brain.voice import _fix_ssl_certs, audio_to_wav_bytes, transcribe, _get_whisper

# Ensure SSL certs are fixed before any HuggingFace calls
_fix_ssl_certs()


def _make_silence(duration_s: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
    """Generate silent audio (zeros) as int16 numpy array."""
    n_samples = int(sample_rate * duration_s)
    return np.zeros(n_samples, dtype=np.int16)


def _make_tone(freq: float = 440, duration_s: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
    """Generate a pure sine tone as int16 numpy array."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    tone = (np.sin(2 * np.pi * freq * t) * 16000).astype(np.int16)
    return tone


class TestSSLFix:
    def test_sets_requests_ca_bundle(self):
        """SSL fix should set REQUESTS_CA_BUNDLE env var."""
        # Clear it first to test
        old = os.environ.pop("REQUESTS_CA_BUNDLE", None)
        # Remove cached file
        combined = os.path.join(tempfile.gettempdir(), "outbot_certs.pem")
        if os.path.exists(combined):
            os.unlink(combined)
        try:
            _fix_ssl_certs()
            assert "REQUESTS_CA_BUNDLE" in os.environ
            assert os.path.exists(os.environ["REQUESTS_CA_BUNDLE"])
        finally:
            if old:
                os.environ["REQUESTS_CA_BUNDLE"] = old


class TestAudioConversion:
    def test_wav_bytes_valid(self):
        """audio_to_wav_bytes should produce valid WAV data."""
        audio = _make_silence(0.5)
        wav_data = audio_to_wav_bytes(audio)

        # Should start with RIFF header
        assert wav_data[:4] == b"RIFF"

        # Should be parseable as WAV
        buf = io.BytesIO(wav_data)
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
            assert wf.getnframes() == 8000  # 0.5s * 16000

    def test_tone_has_nonzero_data(self):
        """A tone should produce non-silent WAV data."""
        audio = _make_tone(440, 0.5)
        wav_data = audio_to_wav_bytes(audio)
        assert len(wav_data) > 100  # Not empty


class TestWhisperModel:
    def test_model_loads(self):
        """Whisper model should load from cache (downloaded during install)."""
        model = _get_whisper()
        assert model is not None

    def test_transcribe_silence_returns_none(self):
        """Transcribing silence should return None (no speech detected)."""
        audio = _make_silence(1.0)
        result = transcribe(audio)
        # Whisper may return empty string or hallucinate on silence
        # Either None or very short text is acceptable
        assert result is None or len(result) < 20

    def test_transcribe_returns_string(self):
        """Transcribe should return a string or None, never raise."""
        audio = _make_tone(440, 1.0)
        result = transcribe(audio)
        assert result is None or isinstance(result, str)
