"""Shared music engine for physics-shorts: musical, soft, original.

Every simulation event becomes a note that is snapped to a tempo grid and chosen from the
current chord, over a pad + bass bed, with stereo delay and reverb. Never uses existing songs.

Usage:
    import music
    song = music.Song(bpm=96, key="D", mode="major", progression="I-V-vi-IV", lead="pluck", seed=3)
    song.note(t, pan=-0.3)            # call for each split/hit/cut event (rate-limited inside)
    song.accent(t)                    # big moment (burst): low thump + bright chord swell
    song.render("audio.wav", duration, build=lambda t: 0..1)   # build curve adds hats/density
"""
import math, wave
import numpy as np

SR = 44100
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
MODES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10],
         "lydian": [0, 2, 4, 6, 7, 9, 11], "mixolydian": [0, 2, 4, 5, 7, 9, 10]}
ROMAN = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6}
PROGRESSIONS = ["I-V-vi-IV", "vi-IV-I-V", "I-vi-IV-V", "ii-V-I-vi", "I-IV-vi-V", "i-VI-III-VII", "i-iv-VI-V",
                "IV-V-iii-vi", "I-iii-IV-iv"]
ARPS = [[0, 1, 2, 3, 4, 3, 2, 1], [0, 2, 1, 3, 2, 4, 3, 5], [0, 1, 2, 4, 3, 2, 1, 2], [4, 3, 2, 1, 0, 1, 2, 3],
        [0, 2, 4, 5, 4, 2, 3, 1]]


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-t * d)


def _voice(kind, f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    if kind == "pluck":
        s = sum(np.sin(2 * np.pi * f * k * t) * (0.6 ** (k - 1)) * np.exp(-t * (3 + 2.5 * k)) for k in range(1, 6))
        return s * _env(n, 0.003, 1.5)
    if kind == "bell":
        s = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 4) \
            + 0.25 * np.sin(2 * np.pi * f * 5.40 * t) * np.exp(-t * 7)
        return s * _env(n, 0.002, 1.8)
    if kind == "marimba":
        s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 18)
        return s * _env(n, 0.002, 4.5)
    if kind == "ep":  # soft electric piano
        mod = np.sin(2 * np.pi * f * 2 * t) * 1.2 * np.exp(-t * 3)
        return np.sin(2 * np.pi * f * t + mod) * _env(n, 0.004, 2.2)
    raise ValueError(kind)


def _chord_degrees(sym):
    minor = sym[0].islower() or sym.endswith("m")
    deg = ROMAN[sym.strip("m").upper()]
    return deg, minor


class Song:
    def __init__(self, bpm=96, key="D", mode="major", progression="I-V-vi-IV", lead="pluck",
                 bars_per_chord=1, grid=0.25, seed=0, max_rate=12.0):
        self.rng = np.random.default_rng(seed)
        self.bpm, self.beat = bpm, 60.0 / bpm
        self.root = 48 + NOTE[key]
        self.scale = MODES[mode]
        self.prog = [_chord_degrees(s) for s in progression.split("-")]
        self.chord_len = 4 * self.beat * bars_per_chord
        self.grid = grid * self.beat           # 0.25 = sixteenth notes
        self.lead = lead
        self.arp = ARPS[int(self.rng.integers(len(ARPS)))]
        self.min_gap = 1.0 / max_rate
        self.notes, self.accents = [], []
        self._last_slot, self._step = -1, 0

    def chord_at(self, t):
        deg, _ = self.prog[int(t / self.chord_len) % len(self.prog)]
        return [self.root + self.scale[(deg + k) % 7] + 12 * ((deg + k) // 7) for k in (0, 2, 4)]

    def note(self, t, pan=0.0, vel=1.0):
        slot = math.ceil(t / self.grid)
        if slot <= self._last_slot or (slot - self._last_slot) * self.grid < self.min_gap:
            return
        self._last_slot = slot
        tq = slot * self.grid
        ch = self.chord_at(tq)
        tones = ch + [m + 12 for m in ch] + [ch[0] + 24]
        m = tones[self.arp[self._step % len(self.arp)] % len(tones)] + 12
        self._step += 1
        self.notes.append((tq, m, float(np.clip(pan, -1, 1)), vel))

    def accent(self, t):
        self.accents.append(t)

    def render(self, path, duration, build=None, peak=0.5):
        n = int((duration + 2.5) * SR)
        L, R = np.zeros(n), np.zeros(n)
        cache = {}

        def put(sig, t0, g, pan=0.0):
            s0 = int(t0 * SR)
            if s0 >= n: return
            seg = sig[: n - s0] * g
            L[s0:s0 + len(seg)] += seg * math.sqrt(0.5 * (1 - pan))
            R[s0:s0 + len(seg)] += seg * math.sqrt(0.5 * (1 + pan))

        end = min(duration, self.accents[0] if self.accents else duration)
        b = build or (lambda t: min(1.0, t / max(end, 1e-3)))
        # pad + bass bed
        t = 0.0
        while t < end + 0.01:
            ch = self.chord_at(t); dur = self.chord_len + 0.8
            m = int(dur * SR); tt = np.arange(m) / SR
            env = np.minimum(1, tt / 0.6) * np.clip((dur - tt) / 0.8, 0, 1)
            pad = sum(np.sin(2 * np.pi * midi_hz(x) * tt) + 0.7 * np.sin(2 * np.pi * midi_hz(x) * 1.003 * tt)
                      for x in ch) * env
            put(pad, t, 0.020 + 0.012 * b(t))
            if b(t) > 0.15:
                put(_voice("marimba", midi_hz(ch[0] - 12), 1.5) * 1.3, t, 0.22 * min(1, b(t) * 1.5))
                put(_voice("marimba", midi_hz(ch[0] - 12), 1.5) * 1.3, t + 2 * self.beat, 0.15 * b(t))
            t += self.chord_len
        # soft hats that come in with the build
        t = 0.0
        while t < end:
            k = b(t)
            if k > 0.45:
                m = int(0.05 * SR)
                hat = self.rng.standard_normal(m) * np.exp(-np.arange(m) / SR * 90)
                hat = np.diff(np.concatenate([[0], hat]))
                put(hat, t, 0.035 * (k - 0.45) / 0.55, pan=0.25 if int(t / (self.beat / 2)) % 2 else -0.25)
            t += self.beat / 2
        # lead notes
        for tq, mm, pan, vel in self.notes:
            if tq > duration: continue
            key = (self.lead, mm)
            if key not in cache: cache[key] = _voice(self.lead, midi_hz(mm), 1.6)
            put(cache[key], tq, 0.13 * vel, pan)
        # accents: low thump + chord swell
        for ta in self.accents:
            m = int(2.2 * SR); tt = np.arange(m) / SR
            f = 58 * np.exp(-tt * 2.2) + 34
            put(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.8), ta, 0.5)
            for x in self.chord_at(ta):
                for o in (12, 24):
                    put(_voice("bell", midi_hz(x + o), 2.5), ta, 0.06, pan=float(self.rng.uniform(-0.5, 0.5)))
        # stereo ping-pong delay (3/8 beat)
        d = int(self.beat * 0.75 * SR)
        for _ in range(4):
            L[d:] += R[:-d] * 0.28; R[d:] += L[:-d] * 0.28
        # reverb: convolve with decaying noise impulse
        m = int(1.8 * SR)
        ir = self.rng.standard_normal(m) * np.exp(-np.arange(m) / SR * 3.2)
        ir /= np.sqrt(np.sum(ir ** 2))
        def conv(x):
            N = 1 << int(np.ceil(np.log2(len(x) + m)))
            return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[: len(x)]
        L, R = L + 0.22 * conv(L), R + 0.22 * conv(R)
        st = np.stack([L, R], 1)
        st = np.tanh(st * 1.4) / 1.4
        st *= peak / (np.abs(st).max() + 1e-9)
        with wave.open(path, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((st * 32767).astype(np.int16).tobytes())
