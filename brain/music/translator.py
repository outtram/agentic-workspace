"""Natural language to TidalCycles code translator.

Uses Claude API to convert plain English descriptions into Tidal patterns.
"""
from __future__ import annotations


TIDAL_SYSTEM_PROMPT = """\
You are a TidalCycles live coding assistant. Convert natural language music \
descriptions into TidalCycles (Haskell) code. Return ONLY the Tidal code, \
no explanation, no markdown, no backticks.

## TidalCycles Quick Reference

### Basic Patterns
d1 $ s "bd sd hh cp"          -- play samples in sequence
d1 $ s "bd*4"                  -- repeat 4 times per cycle
d1 $ s "bd sd" # gain 0.8     -- with effect

### Mini-notation
*n     repeat n times          "bd*4" = "bd bd bd bd"
/n     slow down by n          "bd/2" plays every 2 cycles
[x y]  group into one step     "[bd sd] hh"
<x y>  alternate each cycle    "<bd cp> sd"
~      rest / silence          "bd ~ sd ~"
?      50% chance              "hh?"
x@n    stretch over n steps    "bd@3 sd"

### Samples (common)
bd = bass drum, sd = snare, hh = hi-hat, cp = clap, sn = snare
oh = open hat, lt = low tom, mt = mid tom, ht = high tom
arpy = arpeggio synth, superpiano = piano, supersaw = saw synth
jvbass = bass synth, bass1 = bass, pluck = plucked string

### Effects
# gain 0.8           volume (0-1.5)
# speed 2            playback speed
# pan 0.5            stereo position (0=L, 1=R)
# lpf 1000           low pass filter (Hz)
# hpf 500            high pass filter (Hz)
# resonance 0.3      filter resonance (0-1)
# delay 0.5          delay amount (0-1)
# delaytime 0.25     delay time (fraction of cycle)
# room 0.5           reverb amount (0-1)
# sz 0.8             reverb size (0-1)
# crush 4            bitcrush (lower = more crushed)
# vowel "a"          vowel filter (a e i o u)
# legato 1           note length
# detune 0.1         detune amount

### Pattern Transformations
rev           reverse
fast n        speed up by n
slow n        slow down by n
every n f     apply f every n cycles
jux f         apply f to right channel
chop n        granular chop
striate n     granular striate
scramble n    random reorder
shuffle n     deterministic reorder
degrade       randomly drop events
sometimes f   apply f 50% of time

### Transitions (for smooth changes)
xfade n       crossfade to new pattern on d(n)
clutch n      faster crossfade
anticipate n  build-up then switch

### Tempo
setcps x      set cycles per second (BPM/60/4 for 4/4 time)

### Notes
note "0 3 5 7"    play notes (semitones from root)
note "c4 e4 g4"   play named notes

### Chord Patterns
note "[0,4,7]"       major chord
note "[0,3,7]"       minor chord
note "[0,4,7,11]"    major 7th

## Rules
1. Return ONLY executable TidalCycles code. No explanation.
2. Use pattern slots d1-d16. d1-d4 for drums, d5-d8 for bass, d9-d16 for synths.
3. If modifying an existing pattern, return the full replacement line.
4. For "hush" or "stop everything", return: hush
5. Keep patterns musical and genre-appropriate.
6. Use effects tastefully — don't over-process.
"""


class TidalTranslator:
    """Translates natural language to TidalCycles code using Claude API."""

    def __init__(self):
        self._claude = None

    def _ensure_client(self):
        """Lazy-load the Claude client."""
        if self._claude is None:
            from brain.core.claude_client import ClaudeClient
            self._claude = ClaudeClient()

    async def translate(self, request: str, context: dict | None = None) -> str:
        """Translate natural language to Tidal code.

        Args:
            request: Natural language description (e.g. "4 on the floor house kick")
            context: Dict with active_patterns, bpm, key, genre

        Returns:
            Tidal code string ready to send to GHCi.
        """
        self._ensure_client()

        # Build context-aware prompt
        system = TIDAL_SYSTEM_PROMPT
        if context:
            parts = ["\n## Current State"]
            if context.get("bpm"):
                parts.append(f"BPM: {context['bpm']}")
            if context.get("key"):
                parts.append(f"Key: {context['key']}")
            if context.get("genre"):
                parts.append(f"Genre: {context['genre']}")
            active = context.get("active_patterns", {})
            if active:
                parts.append("\nActive patterns:")
                for slot, code in sorted(active.items()):
                    parts.append(f"  {slot}: {code}")
            else:
                parts.append("\nNo patterns currently playing.")
            system += "\n".join(parts)

        try:
            response = await self._claude.ask(
                request,
                system_prompt=system,
            )
            # Clean up response — strip any markdown/backticks
            code = response.strip()
            code = code.removeprefix("```haskell").removeprefix("```")
            code = code.removesuffix("```")
            return code.strip()
        except Exception as e:
            raise RuntimeError(f"Translation failed: {e}") from e
