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

## AVAILABLE SAMPLES (ONLY use these names)

### Drums — Kicks
bd (24)        -- acoustic/electronic kicks (bd:0 to bd:23)
808bd (25)     -- 808 kick variants
hardkick (6)   -- hard techno kicks
clubkick (1)   -- club kick
kicklinn (1)   -- LinnDrum kick
popkick (1)    -- pop kick

### Drums — Snares & Claps
sn (52)        -- snare variants (sn:0 to sn:51)
sd (2)         -- snare drum
808sd (25)     -- 808 snare variants
cp (2)         -- clap
realclaps (1)  -- real clap sample

### Drums — Hi-hats & Cymbals
hh (13)        -- hi-hats (closed)
hh27 (13)      -- alt hi-hats
oh (5)         -- open hat (808 open hats)
808oh (5)      -- 808 open hat
808hc (5)      -- 808 closed hat
cr (6)         -- crash cymbal
808cy (25)     -- 808 cymbal

### Drums — Toms
ht (1)         -- high tom
mt (1)         -- mid tom
lt (1)         -- low tom
808ht (5)      -- 808 high tom
808mt (5)      -- 808 mid tom
808lt (5)      -- 808 low tom

### Drums — Percussion
rm (1)         -- rimshot
rs (1)         -- rim
cb (1)         -- cowbell
perc (6)       -- misc percussion
hand (17)      -- hand drums
tabla (26)     -- tabla hits
tabla2 (46)    -- more tabla

### Electronic & Techno
techno (7)     -- techno percussion loops
tech (13)      -- tech house percussion
stab (23)      -- stab hits
industrial (32) -- industrial noise/hits
rave (8)       -- rave stabs/hits
rave2 (8)      -- more rave hits
gabba (4)      -- gabba kicks
hardcore (12)  -- hardcore hits
noise (1)      -- noise hit
glitch (8)     -- glitch sounds
glitch2 (8)    -- more glitch

### Bass & Synth Samples
jvbass (13)    -- Juno bass (great for techno)
bass (4)       -- basic bass
bass0-bass3    -- bass variants
moog (7)       -- Moog synth
arpy (11)      -- arpeggio synth
pluck (17)     -- plucked string
space (18)     -- space sounds

### 808 Kit (full set)
808 (7)        -- 808 misc

### Breaks & Loops
breaks125 (2)  -- breakbeat 125bpm
breaks152 (1)  -- breakbeat 152bpm
breaks157 (1)  -- breakbeat 157bpm
breaks165 (1)  -- breakbeat 165bpm

### Misc Useful
click (4)      -- click/metronome
sine (1)       -- sine wave
co (4)         -- conga
numbers (9)    -- spoken numbers
padlong (1)    -- long pad
wobble (1)     -- wobble bass

## SYNTHESISED DRUM MACHINES (PREFER these over samples for better sound)

### TR-808 (use for hip-hop, trap, electro, boom bap)
eight0eight    -- 808 kick. Params: decay (0.5-2.0), tone (0-1), freq (40-70). \
THE bass drum. Long boomy decay. Use freq 45 for trap sub-bass kicks
eightsnare     -- 808 snare. Params: tone (0-1), snap (0-1). Tight or loose
eightclap      -- 808 clap. Built-in reverb tail. Classic
eightch        -- 808 closed hat. Metallic, tight
eightoh        -- 808 open hat. Metallic, longer decay
eightcow       -- 808 cowbell. Two detuned squares, classic
eightrim       -- 808 rimshot. Short, sharp click
eighttom       -- 808 tom. Params: freq (80-200). Use freq to pitch: 80=low, 120=mid, 180=high

### TR-909 (use for house, techno, trance, dance)
ninekick       -- 909 kick. Params: drive (1-3). Punchier than 808, more click/attack
ninesnare      -- 909 snare. Params: snap (0-1). Bright, snappy, cuts through mix
nineclap       -- 909 clap. Tight, cracky. House/techno standard
ninech         -- 909 closed hat. Bright, cutting, sizzle
nineoh         -- 909 open hat. Longer sizzle than ninech
nineride       -- 909 ride cymbal. Long metallic shimmer

### IMPORTANT: For drum machines, use synth names directly:
-- d1 $ s "eight0eight*4" # gain 1.1 # decay 1.2
-- d2 $ s "~ ~ ninesnare ~" # gain 0.9 # snap 0.8
-- These sound MUCH better than the default bd/sn/hh samples

## AVAILABLE SYNTHS (custom SuperDirt synths)

### Lead / Melodic
supersaw       -- detuned 5-voice saw stack. Params: detune (0.1-1.0). Great for \
leads, stabs, trance/Justice-style riffs
acid           -- 303-style acid bass with resonant filter. Params: resonance \
(0-1). Classic acid techno
superchip      -- 8-bit chiptune square waves. Retro game sounds
superfm        -- FM synthesis, metallic bells. Params: fmamt (0.5-5). \
Industrial/IDM textures
techstab       -- short sharp techno stab (Ben Klock style). Punchy, minimal

### Bass
subbass        -- pure sine sub bass. Deep, clean low end. Use with note "0"
reese          -- detuned saw pair, deep and menacing. Params: detune (0.1-1.0). \
DnB/techno
jvbass         -- (sample) Juno bass, 13 variants

### Pads & Atmosphere
darkpad        -- evolving dark pad. Params: detune (0.1-0.5). Dub techno, \
ambient. Use with slow patterns
drone          -- long evolving drone with harmonics. Ambient, ritual techno
hooversynth    -- classic mentasm/hoover. Rave, hard techno

### Percussion / FX
metallic       -- metallic percussion (FM hi-hats, industrial). Use for synth hats
noise303       -- filtered noise. Params: resonance (0-1). Risers, sweeps, \
percussion
distsaw        -- hard-clipped distorted saw. Params: drive (1-10). Industrial \
techno leads

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
# coarse 8           downsample

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

## GENRE TIPS

### Techno (Berlin/minimal)
- Kicks: ninekick (drive 1.5-2.5), hardkick
- Snare: ninesnare (snap 0.8-1.0)
- Hats: ninech, nineoh, metallic synth
- Bass: reese, subbass, acid
- Leads: supersaw with crush, techstab, distsaw
- BPM: 125-138

### Acid Techno
- Bass: acid synth with resonance 0.5-0.9
- Kicks: ninekick (drive 2), hardkick
- Hats: ninech, eightch
- Use lots of lpf modulation: lpf (slow 4 $ range 400 4000 sine)
- BPM: 130-140

### Industrial / Hard Techno
- Kicks: ninekick (drive 3), hardkick, gabba
- Perc: industrial samples, metallic synth, noise303
- Bass: distsaw, reese with crush
- BPM: 140-160

### Dub Techno
- Kicks: ninekick (drive 1) with room 0.3
- Pads: darkpad with room 0.8 and delay 0.5
- Bass: subbass, very minimal
- Hats: ninech with delay 0.3, delaytime (1/6)
- Chords: supersaw with lpf 1500, room 0.6, delay 0.4
- BPM: 118-125

### House / Deep House
- Kicks: ninekick*4 (classic four on the floor)
- Claps: nineclap on 2 and 4
- Hats: ninech on offbeats, nineoh for accents
- Bass: jvbass, subbass
- Chords: supersaw, arpy
- BPM: 120-128

### Hip-Hop / Boom Bap
- Kicks: eight0eight (decay 1.5, heavy and long)
- Snare: eightsnare (snap 0.7, tight)
- Hats: eightch*8 (steady 8ths)
- BPM: 85-100

### Trap
- Kicks: eight0eight (decay 2, freq 45 for sub-bass)
- Claps: eightclap on 3
- Hats: eightch with fast rolling patterns (fast 2, triplets)
- Open hat: eightoh for accents
- BPM: 130-150

### Electro
- Kicks: eight0eight (decay 0.8, punchy)
- Claps: eightclap
- Cowbell: eightcow (the essential electro sound)
- Toms: eighttom with different freq values
- BPM: 120-130

## Rules
1. Return ONLY executable TidalCycles code. No explanation.
2. Use pattern slots d1-d16. d1-d4 for drums, d5-d8 for bass, d9-d16 for synths.
3. If modifying an existing pattern, return the full replacement line.
4. For "hush" or "stop everything", return: hush
5. Keep patterns musical and genre-appropriate.
6. Use effects tastefully — don't over-process.
7. ONLY use sample names and synth names listed above. NEVER invent names.
8. When using synths, always include a note pattern for pitch.
9. Always start with setcps if the user mentions BPM.
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
