// SuperDirt startup file for TidalCycles
// Auto-loads on SuperCollider launch from:
//   ~/Library/Application Support/SuperCollider/startup.scd
// Source: brain/music/setup/superdirt-startup.scd

(
s.options.numBuffers = 4096;
s.options.memSize = 65536;
s.options.maxNodes = 1024;
s.options.numOutputBusChannels = 2;
s.options.numInputBusChannels = 2;

s.waitForBoot {
    ~dirt = SuperDirt(2, s);
    ~dirt.loadSoundFiles;
    s.sync;
    ~dirt.start(57120, 0 ! 12);

    // =========================================================
    // CUSTOM SYNTHS — techno / electronic production
    // =========================================================

    // --- supersaw: detuned saw stack (trance/techno leads, Justice-style stabs) ---
    SynthDef(\supersaw, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1, detune = 0.3|
        var env, sound, freqs;
        env = EnvGen.ar(Env.perc(0.01, sustain), doneAction: 2);
        freqs = freq * (1 + ([-1, -0.5, 0, 0.5, 1] * detune / 100));
        sound = Mix(Saw.ar(freqs));
        sound = sound * env * gain;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- acid: 303-style acid bass with built-in resonant filter ---
    SynthDef(\acid, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1, resonance = 0.4|
        var env, fenv, sound;
        env = EnvGen.ar(Env.perc(0.01, sustain), doneAction: 2);
        fenv = EnvGen.ar(Env.perc(0.01, sustain * 0.3)) * freq * 4;
        sound = Saw.ar(freq);
        sound = RLPF.ar(sound, (freq + fenv).clip(20, 18000), resonance.linexp(0, 1, 1, 0.05));
        sound = sound * env * gain;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- reese: detuned saw pair for deep bass (drum & bass, techno) ---
    SynthDef(\reese, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1, detune = 0.5|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.02, sustain), doneAction: 2);
        sound = Mix(Saw.ar(freq * [1, 1 + (detune / 100)]));
        sound = LPF.ar(sound, freq * 4);
        sound = sound * env * gain;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- subbass: pure sine sub for heavy low end ---
    SynthDef(\subbass, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.01, sustain), doneAction: 2);
        sound = SinOsc.ar(freq) + (SinOsc.ar(freq * 2) * 0.2);
        sound = sound * env * gain;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- darkpad: evolving dark pad (ambient techno, dub techno) ---
    SynthDef(\darkpad, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1, detune = 0.2|
        var env, sound;
        env = EnvGen.ar(Env.linen(0.3, sustain * 0.5, sustain * 0.2), doneAction: 2);
        sound = Mix(LFSaw.ar(freq * [1, 1.005, 0.995, 2.01] * (1 + (detune / 100))));
        sound = LPF.ar(sound, SinOsc.kr(0.1).range(freq, freq * 3));
        sound = sound * env * gain * 0.3;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- hoover: the classic hoover/mentasm sound (rave, hard techno) ---
    SynthDef(\hooversynth, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.01, sustain), doneAction: 2);
        sound = Mix(Saw.ar(freq * [1, 1.01, 1.02, 0.99, 0.98, 2.01]));
        sound = BPF.ar(sound, XLine.kr(freq * 6, freq * 2, sustain), 0.5);
        sound = sound * env * gain * 0.3;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- superchip: 8-bit chiptune square waves ---
    SynthDef(\superchip, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.01, sustain), doneAction: 2);
        sound = Pulse.ar(freq, 0.5) + Pulse.ar(freq * 1.01, 0.25);
        sound = sound * env * gain * 0.5;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- superfm: FM synthesis (metallic, bell-like, industrial) ---
    SynthDef(\superfm, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1, fmamt = 1|
        var env, mod, sound;
        env = EnvGen.ar(Env.perc(0.01, sustain), doneAction: 2);
        mod = SinOsc.ar(freq * 2) * freq * fmamt;
        sound = SinOsc.ar(freq + mod);
        sound = sound * env * gain;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- noise303: filtered noise for percussion, risers, sweeps ---
    SynthDef(\noise303, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1, resonance = 0.3|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.005, sustain), doneAction: 2);
        sound = WhiteNoise.ar;
        sound = RLPF.ar(sound, freq, resonance.linexp(0, 1, 1, 0.01));
        sound = sound * env * gain;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- techstab: short, sharp techno stab (Ben Klock / Marcel Dettmann style) ---
    SynthDef(\techstab, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.001, sustain * 0.3), doneAction: 2);
        sound = Mix(Pulse.ar(freq * [1, 1.5, 2], [0.5, 0.3, 0.2]));
        sound = HPF.ar(sound, 200);
        sound = sound * env * gain * 0.5;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- drone: long evolving drone (ambient, dub techno) ---
    SynthDef(\drone, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.linen(0.5, sustain, 0.5), doneAction: 2);
        sound = Mix(SinOsc.ar(freq * [1, 1.001, 2, 2.002, 3.01]) * [0.4, 0.4, 0.2, 0.2, 0.1]);
        sound = sound + (LPF.ar(PinkNoise.ar, freq * 2) * 0.05);
        sound = sound * env * gain * 0.4;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- metallic: metallic percussion (hi-hats, industrial hits) ---
    SynthDef(\metallic, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.001, sustain * 0.2), doneAction: 2);
        sound = Mix(SinOsc.ar(freq * [1, 1.34, 2.405, 3.09, 4.76]) * [0.3, 0.2, 0.2, 0.15, 0.15]);
        sound = HPF.ar(sound, 2000);
        sound = sound * env * gain;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- distsaw: hard-clipped distorted saw (industrial techno) ---
    SynthDef(\distsaw, { |out, sustain = 1, freq = 440, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1, drive = 4|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.01, sustain), doneAction: 2);
        sound = Saw.ar(freq);
        sound = (sound * drive).tanh;
        sound = sound * env * gain * 0.5;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    "*** SuperDirt started on port 57120 ***".postln;
    "*** 13 custom synths loaded ***".postln;
    "*** supersaw acid reese subbass darkpad hooversynth superchip ***".postln;
    "*** superfm noise303 techstab drone metallic distsaw ***".postln;
};
)
