// SuperDirt startup file for TidalCycles
// Auto-loads on SuperCollider launch from:
//   ~/Library/Application Support/SuperCollider/startup.scd
// Source: brain/music/setup/superdirt-startup.scd

(
s.options.numBuffers = 4096;
s.options.memSize = 65536;
s.options.maxNodes = 2048;
s.options.numOutputBusChannels = 2;
s.options.numInputBusChannels = 2;

s.boot;

s.doWhenBooted({
    Routine({
        ~dirt = SuperDirt(2, s);
        ~dirt.loadSoundFiles;
        s.sync;
        ~dirt.start(57120, 0 ! 12);

    // =========================================================
    // GLOBAL EFFECTS — master bus processing
    // =========================================================

    // Master compressor + saturation on output (glues the mix)
    SynthDef(\masterFX, { |out = 0|
        var sig;
        sig = In.ar(out, 2);
        // Gentle saturation (warmth)
        sig = (sig * 1.2).tanh;
        // Bus compressor — glue everything together
        sig = Compander.ar(sig, sig, thresh: 0.6, slopeBelow: 1, slopeAbove: 0.3,
            clampTime: 0.005, relaxTime: 0.1);
        // Slight stereo width
        sig = [sig[0] + (sig[1] * 0.1), sig[1] + (sig[0] * 0.1)];
        sig = Limiter.ar(sig, 0.95);
        ReplaceOut.ar(out, sig);
    }).add;

    s.sync;
    Synth.tail(s, \masterFX);

    // =========================================================
    // TR-808 DRUM SYNTHS — the real deal, synthesised
    // =========================================================

    // --- 808 kick: long sine decay with pitch sweep, THE bass drum ---
    SynthDef(\eight0eight, { |out, sustain = 1, freq = 55, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1, decay = 1.2, tone = 0.5|
        var env, penv, sound, click;
        // Pitch envelope: starts high, sweeps down to fundamental
        penv = EnvGen.ar(Env([freq * 8, freq * 2, freq], [0.005, 0.06]));
        // Amplitude envelope: punchy attack, long decay
        env = EnvGen.ar(Env.perc(0.001, sustain * decay), doneAction: 2);
        sound = SinOsc.ar(penv);
        // Add harmonics for tone
        sound = sound + (SinOsc.ar(penv * 2) * tone * 0.3);
        // Transient click
        click = EnvGen.ar(Env.perc(0.001, 0.01)) * WhiteNoise.ar * 0.3;
        sound = (sound + click) * env * gain;
        // Soft clip for warmth
        sound = (sound * 1.5).tanh;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 808 snare: tuned oscillators + noise, tight or loose ---
    SynthDef(\eightsnare, { |out, sustain = 1, freq = 185, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1, tone = 0.5, snap = 0.8|
        var env, nenv, body, noise, sound;
        env = EnvGen.ar(Env.perc(0.001, sustain * 0.4), doneAction: 2);
        nenv = EnvGen.ar(Env.perc(0.001, sustain * 0.25));
        // Body: two tuned oscillators
        body = SinOsc.ar(freq) + SinOsc.ar(freq * 1.6) * 0.5;
        body = body * env * tone;
        // Noise: bandpass filtered for snare rattle
        noise = BPF.ar(WhiteNoise.ar, 4000, 0.6) * nenv * snap;
        sound = (body + noise) * gain;
        sound = HPF.ar(sound, 100);
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 808 clap: multiple noise bursts with pre-delay ---
    SynthDef(\eightclap, { |out, sustain = 1, freq = 1000, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env1, env2, env3, envMain, sound;
        // Three quick bursts + main hit (the classic clap shape)
        env1 = EnvGen.ar(Env.perc(0.001, 0.008));
        env2 = EnvGen.ar(Env([0, 0, 1, 0], [0.012, 0.001, 0.008]));
        env3 = EnvGen.ar(Env([0, 0, 1, 0], [0.024, 0.001, 0.008]));
        envMain = EnvGen.ar(Env([0, 0, 1, 0], [0.035, 0.001, sustain * 0.3]), doneAction: 2);
        sound = BPF.ar(WhiteNoise.ar, 1200, 0.7);
        sound = sound * (env1 + env2 + env3 + envMain);
        // Reverb tail
        sound = sound + (CombL.ar(sound * envMain, 0.05, 0.035, 0.15) * 0.4);
        sound = sound * gain;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 808 closed hat: tuned metallic noise, short ---
    SynthDef(\eightch, { |out, sustain = 1, freq = 6000, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.001, 0.06 * sustain), doneAction: 2);
        // Six metallic partials (like real 808 hat circuit)
        sound = Mix(SinOsc.ar([205.35, 304.41, 369.64, 522.71, 540.54, 800.0] * (freq / 6000)));
        sound = HPF.ar(sound, 5000);
        sound = sound * env * gain * 0.6;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 808 open hat: same circuit, longer decay ---
    SynthDef(\eightoh, { |out, sustain = 1, freq = 6000, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.001, 0.3 * sustain), doneAction: 2);
        sound = Mix(SinOsc.ar([205.35, 304.41, 369.64, 522.71, 540.54, 800.0] * (freq / 6000)));
        sound = HPF.ar(sound, 5000);
        sound = sound * env * gain * 0.6;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 808 cowbell: two detuned square waves ---
    SynthDef(\eightcow, { |out, sustain = 1, freq = 560, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.001, sustain * 0.4), doneAction: 2);
        sound = Pulse.ar(freq, 0.5) + Pulse.ar(freq * 1.5, 0.5);
        sound = BPF.ar(sound, freq * 2, 0.3);
        sound = sound * env * gain * 0.5;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 808 rimshot: short noise + pitched click ---
    SynthDef(\eightrim, { |out, sustain = 1, freq = 1700, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.0005, 0.04), doneAction: 2);
        sound = SinOsc.ar(freq) + HPF.ar(WhiteNoise.ar, 3000);
        sound = sound * env * gain * 0.6;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 808 tom: pitched sine with decay ---
    SynthDef(\eighttom, { |out, sustain = 1, freq = 100, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, penv, sound;
        penv = EnvGen.ar(Env([freq * 1.5, freq], [0.04]));
        env = EnvGen.ar(Env.perc(0.001, sustain * 0.5), doneAction: 2);
        sound = SinOsc.ar(penv);
        sound = sound * env * gain;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // =========================================================
    // TR-909 DRUM SYNTHS — punchier, more attack
    // =========================================================

    // --- 909 kick: shorter, punchier than 808, more click ---
    SynthDef(\ninekick, { |out, sustain = 1, freq = 55, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1, drive = 1.5|
        var env, penv, sound, click;
        penv = EnvGen.ar(Env([freq * 10, freq * 1.5, freq], [0.003, 0.03]));
        env = EnvGen.ar(Env.perc(0.0005, sustain * 0.7), doneAction: 2);
        sound = SinOsc.ar(penv);
        click = EnvGen.ar(Env.perc(0.0005, 0.006)) * HPF.ar(WhiteNoise.ar, 2000) * 0.6;
        sound = (sound + click) * env * gain;
        sound = (sound * drive).tanh;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 909 snare: pitched body + bright noise, snappy ---
    SynthDef(\ninesnare, { |out, sustain = 1, freq = 185, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1, snap = 0.9|
        var env, nenv, body, noise, sound;
        env = EnvGen.ar(Env.perc(0.0005, sustain * 0.3), doneAction: 2);
        nenv = EnvGen.ar(Env.perc(0.001, sustain * 0.2));
        body = SinOsc.ar(freq) * env * 0.7;
        body = body + (SinOsc.ar(freq * 0.5) * env * 0.3);
        noise = HPF.ar(WhiteNoise.ar, 1500) * nenv * snap;
        sound = (body + noise) * gain;
        sound = (sound * 1.3).tanh;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 909 closed hat: bright, cutting ---
    SynthDef(\ninech, { |out, sustain = 1, freq = 8000, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.001, 0.04 * sustain), doneAction: 2);
        sound = Mix(SinOsc.ar([205, 304, 370, 523, 541, 800] * (freq / 8000)));
        sound = HPF.ar(sound, 7000);
        // Add noise brightness
        sound = sound + (HPF.ar(WhiteNoise.ar, 9000) * 0.3);
        sound = sound * env * gain * 0.5;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 909 open hat: longer, sizzle ---
    SynthDef(\nineoh, { |out, sustain = 1, freq = 8000, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.001, 0.35 * sustain), doneAction: 2);
        sound = Mix(SinOsc.ar([205, 304, 370, 523, 541, 800] * (freq / 8000)));
        sound = HPF.ar(sound, 7000);
        sound = sound + (HPF.ar(WhiteNoise.ar, 9000) * 0.3);
        sound = sound * env * gain * 0.5;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 909 clap: tighter than 808, more crack ---
    SynthDef(\nineclap, { |out, sustain = 1, freq = 1000, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env1, env2, envMain, sound;
        env1 = EnvGen.ar(Env.perc(0.001, 0.006));
        env2 = EnvGen.ar(Env([0, 0, 1, 0], [0.01, 0.001, 0.006]));
        envMain = EnvGen.ar(Env([0, 0, 1, 0], [0.022, 0.001, sustain * 0.2]), doneAction: 2);
        sound = BPF.ar(WhiteNoise.ar, 1500, 0.5);
        sound = sound * (env1 + env2 + envMain);
        sound = sound + (CombL.ar(sound * envMain, 0.04, 0.025, 0.1) * 0.3);
        sound = HPF.ar(sound, 500);
        sound = sound * gain;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

    // --- 909 ride: long metallic shimmer ---
    SynthDef(\nineride, { |out, sustain = 1, freq = 6000, speed = 1, begin = 0, end = 1, pan, accelerate, offset, gain = 1|
        var env, sound;
        env = EnvGen.ar(Env.perc(0.001, sustain * 0.8), doneAction: 2);
        sound = Mix(SinOsc.ar([205, 370, 523, 800, 1050, 2400] * (freq / 6000))
            * [0.15, 0.15, 0.15, 0.15, 0.2, 0.2]);
        sound = sound + (BPF.ar(WhiteNoise.ar, 8000, 0.2) * 0.2);
        sound = sound * env * gain * 0.4;
        OffsetOut.ar(out, DirtPan.ar(sound, ~dirt.numChannels, pan));
    }).add;

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
    "*** 28 synths loaded ***".postln;
    "*** 808: eight0eight eightsnare eightclap eightch eightoh eightcow eightrim eighttom ***".postln;
    "*** 909: ninekick ninesnare nineclap ninech nineoh nineride ***".postln;
    "*** Synths: supersaw acid reese subbass darkpad hooversynth superchip ***".postln;
    "*** Synths: superfm noise303 techstab drone metallic distsaw ***".postln;
    "*** Master FX: compressor + saturation + limiter ***".postln;
    }).play;
});
)
