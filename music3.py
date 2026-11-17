"""Music engine v3 (prototype): same Song events as music.py, rendered with REAL sampled
instruments (FluidR3 GM soundfont, MIT licence) through fluidsynth, then mixed with
pedalboard (compressor, reverb, limiter).

    import music, music3
    song = music.random_song(seed, avoid=recent)      # unchanged: note()/sfx()/accent() as before
    ...
    music3.render(song, "audio.wav", duration, build=lambda t: 0..1)

Requires: apt-get install fluidsynth fluid-soundfont-gm ; pip install mido pedalboard
"""
import math, os, subprocess, tempfile, wave
import numpy as np
import mido
import music

SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
SR = 44100

# lead voice -> General MIDI program
LEAD_GM = {"pluck": 46, "bell": 14, "marimba": 12, "ep": 4, "kalimba": 108, "musicbox": 10, "celesta": 8,
           "harp": 46, "glass": 11, "flute": 73, "square": 80, "saw": 81, "steeldrum": 114, "koto": 107}
PAD_GM = {"pad": 89, "arp_pad": 89, "strings": 49}
BASS_GM = {"lofi": 32, "jazzhop": 32, "bossa": 32, "synthwave": 38, "trance_lite": 38, "chiptune": 38,
           "kpop_bright": 38, "citypop": 33, "cinematic": 43, "waltz": 43, "musicbox": 43}
# drum notes (GM channel 10)
KICK, SNARE, RIM, CHH, OHH, SHAKER, CRASH, RIDE = 36, 38, 37, 42, 46, 70, 49, 51


class _Midi:
    def __init__(self):
        self.ev = []   # (t, msg)

    def prog(self, ch, p):
        self.ev.append((0.0, mido.Message("program_change", channel=ch, program=p)))

    def cc(self, t, ch, c, v):
        self.ev.append((t, mido.Message("control_change", channel=ch, control=c, value=int(np.clip(v, 0, 127)))))

    def note(self, t, ch, m, vel, dur):
        if m < 0 or m > 127 or t < 0:
            return
        self.ev.append((t, mido.Message("note_on", channel=ch, note=int(m), velocity=int(np.clip(vel, 1, 127)))))
        self.ev.append((t + dur, mido.Message("note_off", channel=ch, note=int(m), velocity=0)))

    def save(self, path):
        mf = mido.MidiFile(ticks_per_beat=480)
        tr = mido.MidiTrack(); mf.tracks.append(tr)
        tr.append(mido.MetaMessage("set_tempo", tempo=500000))   # 120 bpm -> 960 ticks per second
        last = 0
        for t, msg in sorted(self.ev, key=lambda x: (x[0], x[1].type == "note_on")):
            tick = int(round(t * 960))
            msg.time = max(0, tick - last); last = tick
            tr.append(msg)
        mf.save(path)


def _read(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels())


def render(song, path, duration, build=None, peak=0.5):
    from pedalboard import Pedalboard, Compressor, Reverb, Limiter, HighpassFilter, LowShelfFilter

    end = min(duration, song.accents[0] if song.accents else duration)
    b = build or (lambda t: min(1.0, t / max(end, 1e-3)))
    if song.lift:
        tt = 0.0
        while tt < end and b(tt) < 0.8: tt += song.chord_len
        song._lift_t = tt if tt < end else None

    M = _Midi()
    LEAD, PAD, BASS, ARP, ACC, DR = 0, 1, 2, 3, 4, 9
    M.prog(LEAD, LEAD_GM.get(song.lead, 46))
    M.prog(PAD, PAD_GM.get(song.texture, 89))
    M.prog(BASS, BASS_GM.get(song.genre, 33))
    M.prog(ARP, 46 if song.texture != "arp_pad" else 45)
    M.prog(ACC, 48)
    for ch, rev, cho in ((LEAD, 70, 30), (PAD, 90, 60), (BASS, 20, 0), (ARP, 60, 20), (ACC, 100, 40), (DR, 30, 0)):
        M.cc(0, ch, 91, rev); M.cc(0, ch, 93, cho)

    # chords: pad swells with the build, bass enters at 12%, arps at 20%
    t = 0.0
    while t < end + 0.01:
        ch = song.chord_at(t); k = b(t)
        M.cc(t, PAD, 11, 70 + 50 * k)
        for m in ch:
            M.note(t, PAD, m + 12, 40 + 35 * k, song.chord_len + 0.15)
        if k > 0.12:
            M.note(t, BASS, ch[0] - 12, 60 + 45 * min(1, k * 1.4), song.beat * 1.6)
            M.note(t + 2 * song.beat, BASS, ch[0] - 12 + (7 if song.meter == 4 else 0), 50 + 35 * k, song.beat * 1.2)
        if k > 0.2:
            step = song.beat / 2
            for i in range(int(song.chord_len / step)):
                M.note(t + i * step, ARP, ch[i % len(ch)] + 24, 30 + 40 * min(1, k * 1.2), step * 1.5)
        t += song.chord_len

    # drums arrive with the build (same feel as v2, real kit)
    t, i = 0.0, 0
    sub = song.beat / 2
    while t < end and song.drums != "none":
        k = b(t); pos = i % (2 * song.meter)
        sw = song.swing * sub if i % 2 else 0.0
        if k > 0.35:
            g = min(1.0, (k - 0.35) / 0.4)
            v = lambda base: base * (0.55 + 0.45 * g)
            if song.drums == "lofi":
                if pos in (0, 5): M.note(t, DR, KICK, v(95), .1)
                if pos in (2, 6): M.note(t, DR, RIM, v(70), .1)
                M.note(t + sw, DR, CHH, v(45), .05)
            elif song.drums == "pop4":
                if pos % 2 == 0: M.note(t, DR, KICK, v(100), .1)
                if pos in (2, 6): M.note(t, DR, SNARE, v(80), .1)
                M.note(t, DR, CHH, v(50 if pos % 2 else 35), .05)
            elif song.drums == "halftime":
                if pos == 0: M.note(t, DR, KICK, v(100), .1)
                if pos == 4: M.note(t, DR, SNARE, v(78), .1)
                M.note(t + sw, DR, SHAKER if k < 0.75 else CHH, v(40), .05)
            elif song.drums == "bossa":
                if pos in (0, 3, 4, 7): M.note(t, DR, KICK, v(80), .1)
                if pos in (1, 3, 6): M.note(t, DR, RIM, v(70), .1)
                M.note(t + sw, DR, SHAKER, v(40), .05)
            elif song.drums == "chip":
                if pos % 4 == 0: M.note(t, DR, KICK, v(100), .1)
                if pos in (2, 6): M.note(t, DR, SNARE, v(80), .1)
                M.note(t, DR, CHH, v(45), .05)
        t += sub; i += 1

    # lead: every wall hit, already quantised + harmonised by music.Song.note()
    for tq, mm, pan, vel in song.notes:
        if tq > duration: continue
        mm = mm + song._transpose(tq)
        M.cc(tq, LEAD, 10, 64 + 50 * pan)
        M.note(tq, LEAD, mm, 72 + 30 * vel * (0.7 + 0.3 * b(tq)), song.beat * 0.9)

    # payoff: crash + strings chord + low octave
    for ta in song.accents:
        M.note(ta, DR, CRASH, 110, 1.0); M.note(ta, DR, KICK, 120, .2)
        for m in song.chord_at(ta):
            M.note(ta, ACC, m + 12, 95, 2.4); M.note(ta, ACC, m + 24, 80, 2.4)
        M.note(ta, BASS, song.chord_at(ta)[0] - 12, 120, 2.0)

    with tempfile.TemporaryDirectory() as td:
        mid, raw = os.path.join(td, "s.mid"), os.path.join(td, "s.wav")
        M.save(mid)
        subprocess.run(["fluidsynth", "-ni", "-q", "-g", "0.6", "-r", str(SR), "-F", raw, SF2, mid],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        x = _read(raw)

    n = int((duration + 2.5) * SR)
    out = np.zeros((n, 2), np.float32)
    out[:min(n, len(x))] += x[:n]

    # physical sound effects from v2 at their exact times
    rng = np.random.default_rng(song.seed)
    cache, last_k = {}, {}
    for ts, kind, pan, vel in sorted(song.sfxs):
        if ts > duration or ts - last_k.get(kind, -1) < 0.035: continue
        last_k[kind] = ts
        key = (kind, int(ts * 7) % 4)
        if key not in cache: cache[key] = music._sfx(kind, rng).astype(np.float32)
        sig = cache[key] * 0.12 * vel
        s0 = int(ts * SR); seg = sig[: max(0, n - s0)]
        out[s0:s0 + len(seg), 0] += seg * math.sqrt(0.5 * (1 - pan))
        out[s0:s0 + len(seg), 1] += seg * math.sqrt(0.5 * (1 + pan))

    board = Pedalboard([HighpassFilter(30), LowShelfFilter(cutoff_frequency_hz=120, gain_db=1.5),
                        Compressor(threshold_db=-18, ratio=2.5, attack_ms=15, release_ms=180),
                        Reverb(room_size=0.55, damping=0.5, wet_level=0.18, dry_level=0.9, width=1.0),
                        Limiter(threshold_db=-3.0, release_ms=120)])
    y = board(out.T.copy(), SR).T
    y *= peak / (np.abs(y).max() + 1e-9)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((y * 32767).astype(np.int16).tobytes())
