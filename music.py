"""Music engine for physics-shorts: musical, varied, original — never existing songs.

Every simulation event becomes a note snapped to a tempo grid and chosen musically
(arpeggio, motif, melodic walk or call-and-response) over a genre-specific bed:
chords with voicings, bass, texture layer and drums that arrive as the build rises,
optional key lift at the climax, swing, 4/4 or 3/4, stereo delay + reverb.

Quick use (pick a genre preset, everything else is randomised from the seed):
    import music
    song = music.Song.from_genre("lofi", seed=42)          # or music.random_song(seed, avoid=[...recent recipes])
    song.note(t, pan)          # for each split / hit / cut event
    song.accent(t)             # big moment (burst)
    song.render("audio.wav", duration, build=lambda t: 0..1)
    print(song.recipe())       # log this in concepts.md

Manual use is still possible:
    music.Song(bpm=96, key="D", mode="major", progression="I-V-vi-IV", lead="pluck")
"""
import math, wave, json
import numpy as np

SR = 44100
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
KEYS = list(NOTE)
MODES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10],
         "lydian": [0, 2, 4, 6, 7, 9, 11], "mixolydian": [0, 2, 4, 5, 7, 9, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10],
         "harmonic_minor": [0, 2, 3, 5, 7, 8, 11], "phrygian_dominant": [0, 1, 4, 5, 7, 8, 10]}
# melody filters (subsets the lead is snapped to; chords still come from the 7-note mode)
MELODY_SCALES = {"full": None, "penta_major": [0, 2, 4, 7, 9], "penta_minor": [0, 3, 5, 7, 10],
                 "in": [0, 1, 5, 7, 8], "hirajoshi": [0, 2, 3, 7, 8], "whole_tone": [0, 2, 4, 6, 8, 10],
                 "blues": [0, 3, 5, 6, 7, 10]}
ROMAN = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6}
PROGRESSIONS = {
    "major": ["I-V-vi-IV", "vi-IV-I-V", "I-vi-IV-V", "I-IV-vi-V", "IV-V-iii-vi", "I-iii-IV-V", "I-V-IV-V",
              "ii-V-I-vi", "IV-I-V-vi", "I-IV-ii-V", "vi-ii-V-I", "I-vi-ii-V", "IV-V-vi-I", "I-V-vi-iii-IV-I-IV-V"],
    "minor": ["i-VI-III-VII", "i-iv-VI-V", "i-VII-VI-VII", "i-iv-VII-III", "VI-VII-i-i", "i-v-VI-iv",
              "i-III-VII-VI", "iv-v-i-i", "i-VI-iv-v"],
    "dorian": ["i-IV-i-IV", "i-ii-IV-i", "i-VII-IV-i", "i-IV-VII-i"],
    "lydian": ["I-II-I-II", "I-II-vii-I", "I-II-V-I"],
    "mixolydian": ["I-VII-IV-I", "I-v-IV-I", "I-VII-v-IV"],
    "phrygian": ["i-II-i-II", "i-II-VII-i"],
    "harmonic_minor": ["i-iv-V-i", "i-VI-V-i", "i-iv-VI-V"],
    "phrygian_dominant": ["I-II-I-II", "I-II-vii-I", "I-iv-II-I"],
}
VOICINGS = {"triad": [0, 2, 4], "seventh": [0, 2, 4, 6], "sus2": [0, 1, 4], "add9": [0, 2, 4, 8], "sus4": [0, 3, 4]}
ARPS = [[0, 1, 2, 3, 4, 3, 2, 1], [0, 2, 1, 3, 2, 4, 3, 5], [0, 1, 2, 4, 3, 2, 1, 2], [4, 3, 2, 1, 0, 1, 2, 3],
        [0, 2, 4, 5, 4, 2, 3, 1], [0, 0, 2, 1, 3, 2, 4, 3], [0, 3, 1, 4, 2, 5, 3, 1]]
LEADS = ["pluck", "bell", "marimba", "ep", "kalimba", "musicbox", "celesta", "harp", "glass", "flute", "square",
         "saw", "steeldrum", "koto"]

# genre presets: ranges / choices the seed picks from
GENRES = {
    "lofi":       dict(bpm=(72, 88), modes=["dorian", "minor", "major"], voicing=["seventh", "add9"], lead=["ep", "kalimba", "harp"],
                       melody=["walk", "motif"], mscale=["full", "penta_minor"], drums="lofi", texture="pad", swing=0.18, meter=4),
    "synthwave":  dict(bpm=(96, 112), modes=["minor", "dorian"], voicing=["triad", "add9"], lead=["saw", "square", "glass"],
                       melody=["arp", "motif"], mscale=["full"], drums="pop4", texture="arp_pad", swing=0.0, meter=4),
    "ambient":    dict(bpm=(70, 84), modes=["lydian", "major"], voicing=["add9", "sus2"], lead=["glass", "bell", "celesta"],
                       melody=["walk", "arp"], mscale=["penta_major", "full"], drums="none", texture="pad", swing=0.0, meter=4),
    "musicbox":   dict(bpm=(84, 100), modes=["major", "harmonic_minor"], voicing=["triad"], lead=["musicbox", "celesta"],
                       melody=["motif", "callresponse"], mscale=["full"], drums="none", texture="pad", swing=0.0, meter=3),
    "chiptune":   dict(bpm=(110, 124), modes=["major", "minor", "mixolydian"], voicing=["triad"], lead=["square"],
                       melody=["arp", "motif"], mscale=["full", "penta_major"], drums="chip", texture="arp_pad", swing=0.0, meter=4),
    "citypop":    dict(bpm=(96, 110), modes=["major"], voicing=["seventh", "add9"], lead=["ep", "glass", "saw"],
                       melody=["motif", "callresponse"], mscale=["full"], drums="pop4", texture="pad", swing=0.08, meter=4),
    "bossa":      dict(bpm=(86, 100), modes=["major", "dorian"], voicing=["seventh"], lead=["harp", "ep", "flute"],
                       melody=["walk", "callresponse"], mscale=["full"], drums="bossa", texture="pad", swing=0.12, meter=4),
    "cinematic":  dict(bpm=(76, 92), modes=["minor", "harmonic_minor", "lydian"], voicing=["triad", "sus2"], lead=["celesta", "bell", "harp"],
                       melody=["motif", "arp"], mscale=["full"], drums="halftime", texture="strings", swing=0.0, meter=4),
    "celtic":     dict(bpm=(100, 116), modes=["dorian", "mixolydian"], voicing=["triad", "sus4"], lead=["flute", "harp", "pluck"],
                       melody=["motif", "walk"], mscale=["full", "penta_major"], drums="halftime", texture="pad", swing=0.0, meter=3),
    "japanese":   dict(bpm=(80, 96), modes=["minor", "phrygian"], voicing=["sus2", "sus4"], lead=["koto", "kalimba", "flute"],
                       melody=["walk", "motif"], mscale=["in", "hirajoshi"], drums="none", texture="pad", swing=0.0, meter=4),
    "desert":     dict(bpm=(92, 108), modes=["phrygian_dominant", "harmonic_minor"], voicing=["triad"], lead=["koto", "pluck", "flute"],
                       melody=["walk", "motif"], mscale=["full"], drums="halftime", texture="pad", swing=0.0, meter=4),
    "kpop_bright":dict(bpm=(108, 120), modes=["major"], voicing=["add9", "triad"], lead=["pluck", "glass", "bell"],
                       melody=["arp", "callresponse"], mscale=["full"], drums="pop4", texture="arp_pad", swing=0.0, meter=4),
    "jazzhop":    dict(bpm=(80, 94), modes=["dorian", "major"], voicing=["seventh"], lead=["ep", "harp"],
                       melody=["walk", "callresponse"], mscale=["full", "blues"], drums="lofi", texture="pad", swing=0.22, meter=4),
    "dreamwave":  dict(bpm=(84, 98), modes=["lydian"], voicing=["add9", "sus2"], lead=["glass", "celesta", "saw"],
                       melody=["arp", "walk"], mscale=["whole_tone", "full"], drums="halftime", texture="strings", swing=0.0, meter=4),
    "waltz":      dict(bpm=(92, 112), modes=["major", "harmonic_minor"], voicing=["triad", "seventh"], lead=["harp", "musicbox", "ep"],
                       melody=["motif", "arp"], mscale=["full"], drums="none", texture="strings", swing=0.0, meter=3),
    "gamelan":    dict(bpm=(88, 104), modes=["major", "phrygian"], voicing=["sus2"], lead=["bell", "steeldrum", "marimba"],
                       melody=["arp", "motif"], mscale=["penta_major", "in"], drums="none", texture="arp_pad", swing=0.0, meter=4),
    "trance_lite":dict(bpm=(116, 126), modes=["minor"], voicing=["triad", "add9"], lead=["saw", "pluck", "glass"],
                       melody=["arp"], mscale=["full"], drums="pop4", texture="arp_pad", swing=0.0, meter=4),
    "tropical":   dict(bpm=(100, 112), modes=["major", "mixolydian"], voicing=["triad", "add9"], lead=["steeldrum", "marimba", "pluck"],
                       melody=["motif", "callresponse"], mscale=["penta_major", "full"], drums="bossa", texture="pad", swing=0.1, meter=4),
    "lullaby":    dict(bpm=(70, 82), modes=["major"], voicing=["triad", "add9"], lead=["musicbox", "celesta", "harp"],
                       melody=["motif"], mscale=["penta_major", "full"], drums="none", texture="pad", swing=0.0, meter=3),
    "space":      dict(bpm=(74, 90), modes=["lydian", "dorian", "minor"], voicing=["sus2", "add9"], lead=["glass", "saw", "bell"],
                       melody=["walk", "arp"], mscale=["whole_tone", "full", "penta_minor"], drums="halftime", texture="strings", swing=0.0, meter=4),
}


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-t * d)


def _voice(kind, f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s2 = lambda k: np.sin(2 * np.pi * f * k * t)
    if kind == "pluck":
        s = sum(s2(k) * (0.6 ** (k - 1)) * np.exp(-t * (3 + 2.5 * k)) for k in range(1, 6)); return s * _env(n, .003, 1.5)
    if kind == "bell":
        s = s2(1) + .5 * s2(2.76) * np.exp(-t * 4) + .25 * s2(5.40) * np.exp(-t * 7); return s * _env(n, .002, 1.8)
    if kind == "marimba":
        return (s2(1) + .35 * s2(4) * np.exp(-t * 18)) * _env(n, .002, 4.5)
    if kind == "ep":
        return np.sin(2 * np.pi * f * t + 1.2 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 3)) * _env(n, .004, 2.2)
    if kind == "kalimba":
        return (s2(1) + .4 * s2(5.9) * np.exp(-t * 25) + .2 * s2(2) * np.exp(-t * 6)) * _env(n, .002, 3.0)
    if kind == "musicbox":
        return (s2(2) + .6 * s2(4) * np.exp(-t * 5) + .3 * s2(6.2) * np.exp(-t * 9)) * _env(n, .001, 2.6) * .7
    if kind == "celesta":
        return (s2(1) + .3 * s2(4.0) * np.exp(-t * 6) + .15 * s2(7.3) * np.exp(-t * 12)) * _env(n, .002, 2.0)
    if kind == "harp":
        s = sum(s2(k) * (0.5 ** (k - 1)) * np.exp(-t * (1.5 + k)) for k in range(1, 5)); return s * _env(n, .004, 1.2)
    if kind == "glass":
        return (s2(1) + .25 * s2(2.0) + .15 * s2(3.01)) * np.minimum(1, t / .04) * np.exp(-t * 1.4) * .8
    if kind == "flute":
        vib = .004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / .3)
        ph = 2 * np.pi * f * np.cumsum(1 + vib) / SR
        breath = np.random.default_rng(int(f)).standard_normal(n) * .03 * np.exp(-t * 8)
        return (np.sin(ph) + .2 * np.sin(2 * ph) + breath) * np.minimum(1, t / .05) * np.exp(-t * 1.6) * .8
    if kind == "square":
        s = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 3, 5, 7, 9)); return s * _env(n, .002, 3.0) * .55
    if kind == "saw":
        s = sum(np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * k * .8) for k in range(1, 9))
        s += .5 * sum(np.sin(2 * np.pi * f * 1.006 * k * t) / k * np.exp(-t * k * .8) for k in range(1, 6))
        return s * _env(n, .006, 2.0) * .45
    if kind == "steeldrum":
        return (s2(1) + .5 * s2(2.0) * np.exp(-t * 6) + .35 * s2(3.0) * np.exp(-t * 9) + .2 * s2(4.15) * np.exp(-t * 12)) * _env(n, .002, 3.2) * .7
    if kind == "koto":
        bend = 1 + .02 * np.exp(-t * 30)
        ph = 2 * np.pi * f * np.cumsum(bend) / SR
        s = sum(np.sin(k * ph) * (.55 ** (k - 1)) * np.exp(-t * (2 + 2 * k)) for k in range(1, 6)); return s * _env(n, .002, 1.6)
    raise ValueError(kind)


def _sfx(kind, rng):
    def nz(d): return rng.standard_normal(int(d * SR))
    def tt(d): return np.arange(int(d * SR)) / SR
    def hp(x, k=1): 
        for _ in range(k): x = np.diff(np.concatenate([[0], x]))
        return x
    def lp(x, w): return np.convolve(x, np.ones(w) / w, mode="same")
    if kind == "slice":      # quick airy swish + bright metallic snick
        t1 = tt(0.16); sw = hp(nz(0.16)) * np.sin(np.pi * np.minimum(1, t1 / 0.16)) ** 2 * 0.6
        t2 = tt(0.12); f = 3200 + 1800 * np.exp(-t2 * 40)
        sn = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t2 * 45) * 0.7 + hp(nz(0.12), 2) * np.exp(-t2 * 70) * 0.5
        out = np.zeros(int(0.22 * SR)); out[:len(sw)] += sw; o = int(0.09 * SR); out[o:o + len(sn)] += sn[:len(out) - o]
        return out
    if kind == "pop":        # soft bubble pop
        t1 = tt(0.12); f = 900 * np.exp(-t1 * 25) + 300
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t1 * 35)
    if kind == "shatter":    # glassy break: noise burst + inharmonic tinkles
        t1 = tt(0.6); x = hp(nz(0.6), 2) * np.exp(-t1 * 9) * 0.6
        for _ in range(7):
            fr = rng.uniform(2500, 6500); st = rng.uniform(0, 0.25)
            x += np.sin(2 * np.pi * fr * t1) * np.exp(-np.maximum(t1 - st, 0) * 20) * (t1 > st) * 0.15
        return x
    if kind == "whoosh":
        t1 = tt(0.35); return lp(nz(0.35), 6) * np.sin(np.pi * t1 / 0.35) ** 2 * 0.8
    if kind == "tick":       # tiny ball-ball contact
        t1 = tt(0.03); return (np.sin(2 * np.pi * 2400 * t1) * 0.5 + hp(nz(0.03)) * 0.3) * np.exp(-t1 * 160)
    if kind == "chime":      # escape / goal
        t1 = tt(1.2); return sum(np.sin(2 * np.pi * f * t1) * np.exp(-t1 * d) for f, d in ((1568, 3), (2349, 4), (3136, 6))) * 0.4
    if kind == "thump":
        t1 = tt(0.4); return np.sin(2 * np.pi * np.cumsum(70 * np.exp(-t1 * 12) + 40) / SR) * np.exp(-t1 * 10)
    if kind == "zap":
        t1 = tt(0.18); f = 1800 * np.exp(-t1 * 18) + 200
        return np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t1 * 22) * 0.3
    raise ValueError(kind)


def _chord_symbol(sym):
    return ROMAN[sym.strip("m").upper()]


class Song:
    def __init__(self, bpm=96, key="D", mode="major", progression=None, lead="pluck", voicing="triad",
                 melody="arp", melody_scale="full", drums="none", texture="pad", swing=0.0, meter=4,
                 lift=False, grid=0.25, seed=0, max_rate=12.0, genre="custom"):
        self.rng = np.random.default_rng(seed)
        self.genre, self.seed = genre, seed
        self.bpm, self.beat = bpm, 60.0 / bpm
        self.key, self.mode = key, mode
        self.root = 48 + NOTE[key]
        self.scale = MODES[mode]
        progs = PROGRESSIONS[mode]
        self.progression = progression or progs[int(self.rng.integers(len(progs)))]
        self.prog = [_chord_symbol(s) for s in self.progression.split("-")]
        self.meter = meter
        self.chord_len = meter * self.beat
        self.grid = grid * self.beat
        self.lead, self.voicing, self.melody = lead, voicing, melody
        self.melody_scale, self.drums, self.texture = melody_scale, drums, texture
        self.swing, self.lift = swing, lift
        self.arp = ARPS[int(self.rng.integers(len(ARPS)))]
        self.motif = list(self.rng.choice([0, 1, 2, 3, 4, 2, 1, 5, -1], size=8))
        self.min_gap = 1.0 / max_rate
        self.notes, self.accents, self.sfxs = [], [], []
        self._last_slot, self._step, self._walk = -1, 0, 7
        self._lift_t = None

    # ---- construction helpers
    @classmethod
    def from_genre(cls, genre, seed=0, key=None, **over):
        g = GENRES[genre]; r = np.random.default_rng(seed)
        pick = lambda xs: xs[int(r.integers(len(xs)))]
        mode = over.pop("mode", pick(g["modes"]))
        kw = dict(bpm=int(r.integers(g["bpm"][0], g["bpm"][1] + 1)), key=key or pick(KEYS), mode=mode,
                  lead=pick(g["lead"]), voicing=pick(g["voicing"]), melody=pick(g["melody"]),
                  melody_scale=pick(g["mscale"]), drums=g["drums"], texture=g["texture"], swing=g["swing"],
                  meter=g["meter"], lift=bool(r.random() < 0.4), seed=seed, genre=genre)
        kw.update(over)
        return cls(**kw)

    def recipe(self):
        return dict(genre=self.genre, bpm=self.bpm, key=self.key, mode=self.mode, progression=self.progression,
                    lead=self.lead, voicing=self.voicing, melody=self.melody, melody_scale=self.melody_scale,
                    drums=self.drums, texture=self.texture, meter=self.meter, lift=self.lift, seed=self.seed)

    def recipe_str(self):
        r = self.recipe()
        return (f"{r['genre']} · {r['bpm']}bpm · {r['key']} {r['mode']} · {r['progression']} · {r['lead']} lead · "
                f"{r['melody']} melody ({r['melody_scale']}) · {r['voicing']} · {r['drums']} drums · {r['meter']}/4"
                + (" · key lift" if r["lift"] else ""))

    # ---- harmony
    def _transpose(self, t):
        return 2 if (self.lift and self._lift_t is not None and t >= self._lift_t) else 0

    def chord_at(self, t):
        deg = self.prog[int(t / self.chord_len) % len(self.prog)]
        tr = self._transpose(t)
        return [self.root + tr + self.scale[(deg + k) % 7] + 12 * ((deg + k) // 7) for k in VOICINGS[self.voicing]]

    def _snap_melody(self, m, t):
        ms = MELODY_SCALES[self.melody_scale]
        if ms is None: return m
        base = self.root + self._transpose(t)
        best = min(range(-3, 4), key=lambda d: (((m + d - base) % 12) not in ms, abs(d)))
        return m + best

    # ---- events
    def note(self, t, pan=0.0, vel=1.0):
        slot = math.ceil(t / self.grid)
        if slot <= self._last_slot or (slot - self._last_slot) * self.grid < self.min_gap:
            return
        self._last_slot = slot
        tq = slot * self.grid
        if self.swing and slot % 2 == 1:
            tq += self.swing * self.grid
        ch = self.chord_at(tq)
        tones = ch + [m + 12 for m in ch] + [ch[0] + 24]
        k = self._step
        if self.melody == "arp":
            m = tones[self.arp[k % len(self.arp)] % len(tones)]
        elif self.melody == "motif":
            bar = k // 8
            off = self.motif[k % 8] + (1 if bar % 4 == 2 else 0) - (1 if bar % 4 == 3 and k % 8 > 4 else 0)
            m = tones[off % len(tones)] + (12 if off >= len(tones) else 0)
        elif self.melody == "callresponse":
            off = self.motif[k % 8] if (k // 8) % 2 == 0 else 4 - self.motif[k % 8]
            m = tones[int(off) % len(tones)]
        else:  # walk: stepwise within the mode, landing on chord tones on strong slots
            self._walk += int(self.rng.choice([-2, -1, -1, 1, 1, 2]))
            self._walk = int(np.clip(self._walk, 0, 14))
            deg = self._walk
            m = self.root + self._transpose(tq) + self.scale[deg % 7] + 12 * (deg // 7)
            if slot % 4 == 0:
                m = min(tones, key=lambda x: abs(x - m))
        m = self._snap_melody(m + 12, tq)
        self._step += 1
        self.notes.append((tq, m, float(np.clip(pan, -1, 1)), vel))

    def accent(self, t):
        self.accents.append(t)

    def sfx(self, t, kind, pan=0.0, vel=1.0):
        """Physical sound effect at the EXACT event time (not quantised): slice, pop, shatter, whoosh,
        tick, chime, thump, zap. Use for actions; keep musical notes for wall/boundary hits only."""
        self.sfxs.append((t, kind, float(np.clip(pan, -1, 1)), vel))

    def next_bar(self, t):
        """Time of the next bar line at or after t — delay big payoffs (bursts) to land on it."""
        return math.ceil(t / self.chord_len - 1e-9) * self.chord_len

    # ---- rendering
    def render(self, path, duration, build=None, peak=0.5):
        n = int((duration + 2.5) * SR)
        L, R = np.zeros(n), np.zeros(n)
        cache = {}
        rng = self.rng

        def put(sig, t0, g, pan=0.0):
            s0 = int(t0 * SR)
            if s0 >= n or s0 < 0: return
            seg = sig[: n - s0] * g
            L[s0:s0 + len(seg)] += seg * math.sqrt(0.5 * (1 - pan))
            R[s0:s0 + len(seg)] += seg * math.sqrt(0.5 * (1 + pan))

        end = min(duration, self.accents[0] if self.accents else duration)
        b = build or (lambda t: min(1.0, t / max(end, 1e-3)))
        if self.lift:
            tt = 0.0
            while tt < end and b(tt) < 0.8: tt += self.chord_len
            self._lift_t = tt if tt < end else None

        def noise(d, decay, hp=True):
            m = int(d * SR); x = rng.standard_normal(m) * np.exp(-np.arange(m) / SR * decay)
            return np.diff(np.concatenate([[0], x])) if hp else x

        kick = lambda: np.sin(2 * np.pi * np.cumsum(50 * np.exp(-np.arange(int(.35 * SR)) / SR * 18) + 42) / SR) * np.exp(-np.arange(int(.35 * SR)) / SR * 9)
        # chords: pad / strings / arp_pad + bass
        t = 0.0
        while t < end + 0.01:
            ch = self.chord_at(t); dur = self.chord_len + 0.8; k = b(t)
            m = int(dur * SR); tt = np.arange(m) / SR
            env = np.minimum(1, tt / 0.6) * np.clip((dur - tt) / 0.8, 0, 1)
            if self.texture in ("pad", "arp_pad"):
                pad = sum(np.sin(2 * np.pi * midi_hz(x) * tt) + .7 * np.sin(2 * np.pi * midi_hz(x) * 1.003 * tt) for x in ch) * env
                put(pad, t, 0.018 + 0.012 * k)
            if self.texture == "strings":
                st = sum(sum(np.sin(2 * np.pi * midi_hz(x) * h * (1 + .002 * j) * tt) / h for h in range(1, 6) for j in (-1, 1)) for x in ch)
                put(st * env * np.minimum(1, tt / 1.2), t, 0.010 + 0.010 * k)
            if self.texture == "arp_pad" and k > 0.2:
                step = self.beat / 2
                for i in range(int(self.chord_len / step)):
                    x = ch[i % len(ch)] + 12
                    put(_voice("pluck", midi_hz(x), .5), t + i * step, .035 * min(1, k * 1.3), pan=-.3 if i % 2 else .3)
            if k > 0.12:
                bass = _voice("marimba", midi_hz(ch[0] - 12), 1.5) * 1.3
                put(bass, t, 0.22 * min(1, k * 1.5))
                if self.meter == 4: put(bass, t + 2 * self.beat, 0.15 * k)
                else: put(bass, t + 2 * self.beat, 0.10 * k)
            t += self.chord_len
        # drums, arriving with the build
        t, i = 0.0, 0
        sub = self.beat / 2
        while t < end:
            k = b(t); pos = i % (2 * self.meter)   # eighth-note position in bar
            sw = self.swing * sub if (i % 2 == 1) else 0.0
            if self.drums != "none" and k > 0.35:
                g = min(1.0, (k - 0.35) / 0.4)
                if self.drums == "lofi":
                    if pos in (0, 5): put(kick(), t, .35 * g)
                    if pos in (2, 6): put(noise(.18, 25, False) * .6, t, .10 * g)
                    put(noise(.05, 80), t + sw, .030 * g, pan=.2)
                elif self.drums == "pop4":
                    if pos % 2 == 0: put(kick(), t, .32 * g)
                    if pos in (2, 6): put(noise(.15, 30, False), t, .08 * g)
                    if pos % 2 == 1: put(noise(.05, 90), t, .035 * g, pan=-.2)
                elif self.drums == "halftime":
                    if pos == 0: put(kick(), t, .35 * g)
                    if pos == 4: put(noise(.25, 18, False), t, .09 * g)
                    put(noise(.04, 100), t + sw, .022 * g, pan=.25)
                elif self.drums == "bossa":
                    if pos in (0, 3, 4, 7): put(kick() * .7, t, .25 * g)
                    if pos in (1, 3, 6): put(noise(.03, 160), t, .06 * g, pan=-.3)
                    put(noise(.04, 90), t + sw, .02 * g, pan=.3)
                elif self.drums == "chip":
                    if pos % 4 == 0: put(np.sign(np.sin(2 * np.pi * np.cumsum(120 * np.exp(-np.arange(int(.12 * SR)) / SR * 30) + 50) / SR)) * np.exp(-np.arange(int(.12 * SR)) / SR * 25), t, .12 * g)
                    if pos in (2, 6): put(np.sign(noise(.1, 30, False)) * np.exp(-np.arange(int(.1 * SR)) / SR * 30), t, .05 * g)
                    put(np.sign(noise(.03, 120)) * np.exp(-np.arange(int(.03 * SR)) / SR * 120), t, .02 * g)
            t += sub; i += 1
        # lead
        for tq, mm, pan, vel in self.notes:
            if tq > duration: continue
            # notes are chosen before render() knows the lift point, so lift them here too
            # (otherwise the lead stays in the old key while the chords move up a whole step)
            mm = mm + self._transpose(tq)
            key = (self.lead, mm)
            if key not in cache: cache[key] = _voice(self.lead, midi_hz(mm), 1.6)
            put(cache[key], tq, 0.13 * vel, pan)
        # sound effects (exact timing, rate-limited per kind so dense moments stay clean)
        last_k = {}
        for ts, kind, pan, vel in sorted(self.sfxs):
            if ts > duration or ts - last_k.get(kind, -1) < 0.035: continue
            last_k[kind] = ts
            key = ("sfx", kind, int(ts * 7) % 4)
            if key not in cache: cache[key] = _sfx(kind, rng)
            put(cache[key], ts, 0.20 * vel, pan)
        # accents
        for ta in self.accents:
            m = int(2.2 * SR); tt = np.arange(m) / SR
            put(np.sin(2 * np.pi * np.cumsum(58 * np.exp(-tt * 2.2) + 34) / SR) * np.exp(-tt * 2.8), ta, .5)
            for x in self.chord_at(ta):
                for o in (12, 24):
                    put(_voice("bell", midi_hz(x + o), 2.5), ta, .055, pan=float(rng.uniform(-.5, .5)))
        # stereo ping-pong delay + reverb
        d = int(self.beat * 0.75 * SR)
        for _ in range(4):
            L[d:] += R[:-d] * .26; R[d:] += L[:-d] * .26
        m = int(1.8 * SR)
        ir = rng.standard_normal(m) * np.exp(-np.arange(m) / SR * 3.2); ir /= np.sqrt(np.sum(ir ** 2))
        def conv(x):
            N = 1 << int(np.ceil(np.log2(len(x) + m)))
            return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[: len(x)]
        L, R = L + .22 * conv(L), R + .22 * conv(R)
        st = np.stack([L, R], 1)
        st = np.tanh(st * 1.4) / 1.4
        st *= peak / (np.abs(st).max() + 1e-9)
        with wave.open(path, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((st * 32767).astype(np.int16).tobytes())


def random_song(seed, avoid=(), theme=None):
    """Pick a genre/recipe that differs from recent ones.
    avoid: list of recent recipe dicts (from concepts.md). Genre not reused if it appears in the last 7,
    and (genre, key, mode, lead) never repeats any entry."""
    r = np.random.default_rng(seed)
    recent_genres = [a.get("genre") for a in list(avoid)[-7:]]
    combos = {(a.get("genre"), a.get("key"), a.get("mode"), a.get("lead")) for a in avoid}
    names = [g for g in GENRES if g not in recent_genres] or list(GENRES)
    for i in range(200):
        g = names[int(r.integers(len(names)))]
        s = Song.from_genre(g, seed=seed * 1000 + i)
        if (s.genre, s.key, s.mode, s.lead) not in combos:
            return s
    return s
