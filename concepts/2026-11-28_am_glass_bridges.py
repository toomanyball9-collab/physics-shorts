"""2026-11-28 08:00 — marble-race (variation): "Glass Bridges"
8 neon marbles race down a tall neon course; the camera follows the pack downward.
Rule: every section ends with a GLASS BRIDGE over a little catch-bin. The glass shows its strength as glowing
pips — exactly one pip per marble it can carry (= marbles still racing minus one). Every marble that rolls
onto it uses up one pip (the glass dims and heats up). When the pips are gone the glass glows red, and the
next marble that touches it breaks it and falls into the bin below: OUT (it stays there, grey).
So the last marble to reach each bridge is always the one that falls. 8 -> 7 -> ... -> 1.
The final bridge carries only one marble: the first of the last two crosses, the second breaks it.
On the next bar the whole course floods in the winner's colour; tail crossfades back to the opening.
Race-order dots at the top (eliminated colours go grey), counter = marbles left.
Sound: ramp/bumper/spinner bounces = music (song.note); pip used = tick; glass break = shatter;
marble landing in the bin = thump; start = whoosh; winner = chime.

usage: python3 concepts/2026-11-28_am_glass_bridges.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 8
G = float(os.environ.get("GRAV", "1400"))
DRAG = G / float(os.environ.get("VT", "1100")) ** 2
MR = 24.0
XL, XR = 70.0, 1010.0
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
# random_song(2026112936, avoid=all posted recipes up to 11-27 pm synthwave) -> kpop_bright 117 E major pluck
MUSIC_SEED = int(os.environ.get("MSEED", "2026112936"))
RECENT = [dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass"),
          dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep"),
          dict(genre="musicbox", bpm=95, key="E", mode="harmonic_minor", lead="celesta"),
          dict(genre="tropical", bpm=112, key="A", mode="major", lead="marimba"),
          dict(genre="cinematic", bpm=78, key="A#", mode="minor", lead="harp"),
          dict(genre="waltz", bpm=93, key="D", mode="major", lead="ep"),
          dict(genre="synthwave", bpm=104, key="G#", mode="dorian", lead="saw"),
          dict(genre="gamelan", bpm=94, key="D#", mode="major", lead="bell"),
          dict(genre="lofi", bpm=74, key="F#", mode="major", lead="kalimba"),
          dict(genre="celtic", bpm=116, key="A#", mode="mixolydian", lead="flute"),
          dict(genre="jazzhop", bpm=89, key="C", mode="major", lead="harp"),
          dict(genre="trance_lite", bpm=123, key="F", mode="minor", lead="pluck"),
          dict(genre="bossa", bpm=96, key="G#", mode="major", lead="ep"),
          dict(genre="space", bpm=76, key="B", mode="lydian", lead="bell"),
          dict(genre="desert", bpm=104, key="F#", mode="phrygian_dominant", lead="flute"),
          dict(genre="chiptune", bpm=124, key="F#", mode="mixolydian", lead="square"),
          dict(genre="cinematic", bpm=84, key="C#", mode="harmonic_minor", lead="harp"),
          dict(genre="citypop", bpm=105, key="G#", mode="major", lead="ep"),
          dict(genre="japanese", bpm=90, key="F", mode="phrygian", lead="koto"),
          dict(genre="synthwave", bpm=106, key="G", mode="minor", lead="glass")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)
COLS = [(1.0, 0.25, 0.30), (1.0, 0.58, 0.18), (1.0, 0.92, 0.25), (0.45, 1.0, 0.35),
        (0.20, 0.90, 1.0), (0.30, 0.45, 1.0), (0.72, 0.38, 1.0), (1.0, 0.38, 0.78)]
GREY = (0.45, 0.45, 0.52)
PAL = {"bg": ((0.015, 0.02, 0.07), (0.00, 0.00, 0.03)), "ring": (0.8, 0.85, 1.0), "balls": COLS,
       "accent": (1.0, 0.95, 0.85)}
# course tubes: deep blue -> violet -> magenta -> teal, glass = ice
SEC_COLS = [(0.35, 0.55, 1.0), (0.55, 0.42, 1.0), (0.80, 0.40, 1.0), (1.0, 0.42, 0.75), (0.30, 0.80, 1.0),
            (0.40, 1.0, 0.80), (0.70, 0.75, 1.0), (0.95, 0.90, 1.0)]
GLASS = (0.78, 0.94, 1.0)
HOT = (1.0, 0.22, 0.25)
P = {k: float(os.environ.get(k, v)) for k, v in dict(NA="2", NB="2", NC="2", ND="3", NE="2", NF="2", NG="2", NH="1",
                                                     SPW="1.6", SPW2="1.9", BW="240", DROP="110").items()}

DROP = P["DROP"]
rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)

# ---------------- course ----------------
SEG = []        # x0, y0, x1, y1, section
BUMP = []       # x, y, R, section
PEGS = []       # x, y, r, section (small pegs)
SPIN = []       # cx, cy, half, omega, phase, section
BRIDGES = []    # dict(seg, x0, y0, x1, y1, bin segs, ...)
sec = 0


def seg(x0, y0, x1, y1, s=None):
    SEG.append((x0, y0, x1, y1, sec if s is None else s))
    return len(SEG) - 1


def ramp_y(x0, y0, x1, y1, x):
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def zigzag(y, n, drop, start_left=True, gap=95, bridge=False):
    """n ramps; with bridge=True the last ramp carries a glass bridge (bigger pitch: room for the bin)."""
    for i in range(n):
        last = bridge and i == n - 1
        pitch = drop + 100
        yh = y
        if (i % 2 == 0) == start_left:
            xa, xb = XL, XR - gap
        else:
            xa, xb = XR, XL + gap
        ya, yb = yh, yh + drop
        if last:
            bw = P["BW"]
            # glass in the middle of the ramp (in ramp direction)
            c0 = xa + (xb - xa) * 0.30
            c1 = c0 + bw * (1 if xb > xa else -1)
            gy0, gy1 = ramp_y(xa, ya, xb, yb, c0), ramp_y(xa, ya, xb, yb, c1)
            seg(xa, ya, c0, gy0)
            gs = seg(c0, gy0, c1, gy1)
            seg(c1, gy1, xb, yb)
            lo, hi = min(c0, c1), max(c0, c1)
            ylo = max(gy0, gy1) + 2.4 * MR + 22
            b0 = seg(lo - 4, ramp_y(xa, ya, xb, yb, lo) + 6, lo - 4, ylo)
            b1 = seg(hi + 4, ramp_y(xa, ya, xb, yb, hi) + 6, hi + 4, ylo)
            b2 = seg(lo - 4, ylo, hi + 4, ylo)
            pa = seg(c0, gy0, c0, gy0); pb = seg(c1, gy1, c1, gy1)      # glass pieces left after the break
            BRIDGES.append(dict(seg=gs, pieces=(pa, pb), hole=None, x0=c0, y0=gy0, x1=c1, y1=gy1, lo=lo, hi=hi, ybin=ylo, bins=(b0, b1, b2),
                                dirx=(1 if xb > xa else -1), sec=sec, touched=set(), state=0, t_spent=None,
                                t_break=None, doomed=None, used_t=[]))
            pitch = drop + 100 + 2.4 * MR + 60
        else:
            seg(xa, ya, xb, yb)
        y = yh + pitch
    return y - pitch + drop


START_Y = 220.0
START_SEG = seg(250, START_Y, 830, START_Y, 0)          # start shelf (opens at t = 0.35)
seg(250, 60, 250, START_Y, 0); seg(830, 60, 830, START_Y, 0)
# A: plain zigzag, bridge 1
y = zigzag(330, int(P["NA"]), DROP, True, bridge=True)
# B: peg forest, bridge 2
sec = 1
y0 = y + 150
for row in range(6):
    xs = np.arange(150 if row % 2 == 0 else 225, 960, 150)
    for x in xs:
        PEGS.append((float(x), y0 + row * 105, 13, sec))
y = zigzag(y0 + 5 * 105 + 140, int(P["NB"]), DROP, False, bridge=True)
# C: spinning bar, bridge 3
sec = 2
SPIN.append((540, y + 360, 285, P["SPW"], 0.3, sec))
y = zigzag(y + 700, int(P["NC"]), DROP, True, bridge=True)
# D: steep zigzag, bridge 4
sec = 3
y = zigzag(y + 90, int(P["ND"]), DROP + 50, False, bridge=True)
# E: bumper diamond, bridge 5
sec = 4
y0 = y + 140
rows = [[540], [400, 680], [260, 540, 820], [400, 680], [540]]
for r_, xs in enumerate(rows):
    for x in xs:
        BUMP.append((x, y0 + r_ * 140, 38, sec))
y = zigzag(y0 + 4 * 140 + 130, int(P["NE"]), DROP, True, bridge=True)
# F: twin spinners, bridge 6
sec = 5
SPIN.append((305, y + 330, 215, P["SPW2"], 0.0, sec))
SPIN.append((775, y + 330, 215, -P["SPW2"], 1.2, sec))
y = zigzag(y + 640, int(P["NF"]), DROP, False, bridge=True)
# G: peg slalom (wide pegs), bridge 6
sec = 6
y0 = y + 150
for row in range(4):
    xs = np.arange(190 if row % 2 == 0 else 300, 930, 220)
    for x in xs:
        PEGS.append((float(x), y0 + row * 125, 20, sec))
y = zigzag(y0 + 3 * 125 + 150, int(P["NG"]), DROP, True, bridge=True)
# H: run-out to the podium (no bridge)
sec = 7
y = zigzag(y + 90, int(P["NH"]), DROP, False, bridge=False)
# podium: a flat shelf the winner rolls onto
sec = 8
PODIUM_Y = y + 230
seg(XL, PODIUM_Y - 120, 420, PODIUM_Y); seg(420, PODIUM_Y, 660, PODIUM_Y); seg(660, PODIUM_Y, XR, PODIUM_Y - 120)
COURSE_END = PODIUM_Y + 200
NBR = len(BRIDGES)
SEGA = np.array([[s[0], s[1]] for s in SEG]); SEGB = np.array([[s[2], s[3]] for s in SEG])
SEGS = np.array([s[4] for s in SEG])
GLASS_SEGS = {b["seg"]: k for k, b in enumerate(BRIDGES)}
BIN_SEGS = set(s for b in BRIDGES for s in b["bins"])
PIECE_SEGS = set(s for b in BRIDGES for s in b["pieces"])
seg_on = np.ones(len(SEG), bool)
for k_ in PIECE_SEGS:
    seg_on[k_] = False
BUMPA = np.array([[b[0], b[1]] for b in BUMP]); BUMPR = np.array([b[2] for b in BUMP])
PEGA = np.array([[q[0], q[1]] for q in PEGS]); PEGR = np.array([q[2] for q in PEGS])
bump_flash = np.zeros(len(BUMP))
peg_flash = np.zeros(len(PEGS))

# ---------------- marbles ----------------
NM = 8
order0 = rng.permutation(NM)
p = np.array([[290 + i * 71.4 + rng.uniform(-4, 4), START_Y - MR - 0.5] for i in range(NM)])
v = np.array([[rng.uniform(-15, 15), 0.0] for _ in range(NM)])
colour = order0.copy()
alive = np.ones(NM, bool)
doomed = np.zeros(NM, bool)
out_t = np.full(NM, -1.0)
in_bin = np.full(NM, -1)
landed = np.zeros(NM, bool)
hit_cool = np.zeros(NM) - 9
trail = [[] for _ in range(NM)]
STARS = [(fx_rng.uniform(0, W), fx_rng.uniform(-2000, 16000), fx_rng.uniform(0.6, 2.2), fx_rng.uniform(0.08, 0.3)) for _ in range(460)]
t = 0.0
events, sparks, shards, build_keys = [], [], [], []
winner = None
finish_t = None
payoff_pending = None
payoff_t = None
cam_y, zoom = 650.0, 0.8
started = False


def racers():
    return [i for i in range(NM) if alive[i] and not doomed[i]]


def cap(b):
    """pips this bridge can carry right now = marbles still racing (not doomed) minus one."""
    B = BRIDGES[b]
    if B["state"] >= 1:
        return len(B["touched"])
    return max(1, len(racers()) - 1)


def bridges_passed(i):
    return sum(1 for B in BRIDGES if i in B["touched"])


def race_order():
    key = []
    for i in range(NM):
        if i == winner:
            key.append((0, 0, 0, i))
        elif alive[i]:
            key.append((1, -bridges_passed(i), -p[i, 1], i))
        else:
            key.append((2, -out_t[i], 0, i))
    return [k[-1] for k in sorted(key)]


def progress():
    if payoff_t is not None:
        return 1.0
    n_out = NM - int(alive.sum()) - (1 if winner is not None else 0)
    lead = max((p[i, 1] for i in range(NM) if alive[i]), default=COURSE_END)
    pos = np.clip((lead - 300) / (BRIDGES[-1]["y0"] - 300), 0, 1)
    return float(np.clip(0.55 * pos + 0.4 * n_out / (NM - 1) + 0.05 * min(1, t / 5), 0, 1))


def touch_bridge(i, b):
    """marble i rolls onto bridge b."""
    global winner, finish_t
    B = BRIDGES[b]
    if i in B["touched"] or doomed[i] and B["doomed"] != i:
        return
    if B["state"] == 0:
        c = cap(b)
        B["touched"].add(i)
        B["used_t"].append(t)
        pan = float((p[i, 0] - 540) / 470)
        song.sfx(t, "tick", pan, 0.55)
        events.append((t, "pip", (b, i)))
        if len(B["touched"]) >= c:
            B["state"] = 1
            B["t_spent"] = t
            behind = [j for j in racers() if j not in B["touched"]]
            for j in behind:
                doomed[j] = True
                B["doomed"] = j
            song.sfx(t, "zap", pan, 0.35)
            events.append((t, "spent", b))
            if len(behind) == 1 and len(racers()) == 1:
                winner = racers()[0]
            # a bridge further down that the leaders already reached may now be spent as well
            for b2, B2 in enumerate(BRIDGES):
                if b2 != b and B2["state"] == 0 and B2["touched"] and len(B2["touched"]) >= cap(b2):
                    B2["state"] = 1
                    B2["t_spent"] = t
                    bh = [j for j in racers() if j not in B2["touched"]]
                    for j in bh:
                        doomed[j] = True
                        B2["doomed"] = j
                    events.append((t, "spent", b2))
                    if len(racers()) == 1:
                        winner = racers()[0]
    elif B["state"] == 1 and i == B["doomed"]:
        # the spent glass breaks under the last marble
        B["state"] = 2
        B["t_break"] = t
        seg_on[B["seg"]] = False
        # only the spot under the extra marble gives way: a marble-sized hole, the rest of the glass stays
        xd = float(np.clip(p[i, 0], B["lo"] + 1.4 * MR, B["hi"] - 1.4 * MR))
        h0, h1 = xd - 1.4 * MR, xd + 1.4 * MR
        B["hole"] = (h0, h1)
        for kk, (u0, u1) in zip(B["pieces"], ((B["lo"], h0), (h1, B["hi"]))):
            if u1 - u0 > 6:
                SEGA[kk] = [u0, ramp_y(B["x0"], B["y0"], B["x1"], B["y1"], u0)]
                SEGB[kk] = [u1, ramp_y(B["x0"], B["y0"], B["x1"], B["y1"], u1)]
                seg_on[kk] = True
        alive[i] = False
        out_t[i] = t
        in_bin[i] = b
        pan = float((p[i, 0] - 540) / 470)
        song.sfx(t, "shatter", pan, 0.9)
        events.append((t, "out", (i, b)))
        n = 4
        xs = np.linspace(h0, h1, n + 1)
        for a, c in zip(xs[:-1], xs[1:]):
            xm = (a + c) / 2
            ym = ramp_y(B["x0"], B["y0"], B["x1"], B["y1"], xm)
            shards.append(dict(x=xm, y=ym, vx=fx_rng.uniform(-140, 140), vy=fx_rng.uniform(-260, 0), a=math.atan2(B["y1"] - B["y0"], B["x1"] - B["x0"]),
                               va=fx_rng.uniform(-8, 8), L=abs(c - a) * 0.9, th=10, c=HOT, t0=t))
        for _ in range(26):
            sparks.append([fx_rng.uniform(h0, h1), ramp_y(B["x0"], B["y0"], B["x1"], B["y1"], xd) + fx_rng.normal(0, 8),
                           fx_rng.uniform(8, 20), t, GLASS])



def physics_step(dt):
    global started, payoff_pending
    if not started and t >= 0.35:
        started = True
        seg_on[START_SEG] = False
        song.sfx(t, "whoosh", 0.0, 0.6)
        events.append((t, "start", 0))
    v[:, 1] += G * dt
    spd = np.hypot(v[:, 0], v[:, 1])
    v[:] -= v * (DRAG * spd * dt)[:, None]
    p[:] += v * dt
    live = [i for i in range(NM) if alive[i]]
    dead = [i for i in range(NM) if not alive[i]]
    # marble-marble (racers only; marbles in a bin only touch each other's bin -> skip)
    for a in range(len(live)):
        for b in range(a + 1, len(live)):
            i, j = live[a], live[b]
            d = p[j] - p[i]
            dist = math.hypot(*d)
            if 1e-6 < dist < 2 * MR:
                nrm = d / dist
                over = 2 * MR - dist
                p[i] -= nrm * over / 2; p[j] += nrm * over / 2
                rel = np.dot(v[j] - v[i], nrm)
                if rel < 0:
                    imp = 0.9 * rel * nrm
                    v[i] += imp; v[j] -= imp
                    if -rel > 160:
                        song.sfx(t, "tick", float((p[i, 0] - 540) / 470), min(0.3, 0.12 + -rel / 2200))
    for i in range(NM):
        near = seg_on & (np.minimum(SEGA[:, 1], SEGB[:, 1]) < p[i, 1] + 60) & (np.maximum(SEGA[:, 1], SEGB[:, 1]) > p[i, 1] - 60)
        for k in np.where(near)[0]:
            if not alive[i] and k not in BIN_SEGS:
                continue
            a, b = SEGA[k], SEGB[k]
            ab = b - a
            u = np.clip(np.dot(p[i] - a, ab) / np.dot(ab, ab), 0, 1)
            q = a + ab * u
            d = p[i] - q
            dist = math.hypot(*d)
            if 1e-6 < dist < MR:
                nrm = d / dist
                if k in GLASS_SEGS and alive[i]:
                    bi = GLASS_SEGS[k]
                    touch_bridge(i, bi)
                    if not seg_on[k]:
                        continue
                p[i] = q + nrm * MR
                vn = np.dot(v[i], nrm)
                if vn < 0:
                    vt = v[i] - vn * nrm
                    v[i] = vt * 0.99985 - 0.32 * vn * nrm
                    if not alive[i]:
                        v[i] = vt * 0.9 - 0.25 * vn * nrm
                        if not landed[i] and -vn > 120:
                            landed[i] = True
                            song.sfx(t, "thump", float((p[i, 0] - 540) / 470), 0.8)
                            events.append((t, "land", (i,)))
                    elif -vn > 170 and t - hit_cool[i] > 0.09:
                        hit_cool[i] = t
                        song.note(t, float((p[i, 0] - 540) / 470), vel=min(1.0, 0.45 + -vn / 1400))
                        events.append((t, "hit", (float(q[0]), float(q[1]), int(colour[i]), int(SEGS[k]))))
        if not alive[i]:
            continue
        # bumpers
        if len(BUMP):
            d = p[i] - BUMPA
            dist = np.hypot(d[:, 0], d[:, 1])
            for k in np.where(dist < BUMPR + MR)[0]:
                nrm = d[k] / (dist[k] + 1e-6)
                p[i] = BUMPA[k] + nrm * (BUMPR[k] + MR)
                vn = np.dot(v[i], nrm)
                if vn < 0:
                    v[i] = v[i] - 2.0 * vn * nrm
                    sp = math.hypot(*v[i])
                    if sp < 480:
                        v[i] *= 480 / (sp + 1e-6)
                    bump_flash[k] = 1.0
                    if t - hit_cool[i] > 0.06:
                        hit_cool[i] = t
                        song.note(t, float((p[i, 0] - 540) / 470), vel=0.9)
        # pegs (light bounce)
        if len(PEGS):
            d = p[i] - PEGA
            dist = np.hypot(d[:, 0], d[:, 1])
            for k in np.where(dist < PEGR + MR)[0]:
                nrm = d[k] / (dist[k] + 1e-6)
                p[i] = PEGA[k] + nrm * (PEGR[k] + MR)
                vn = np.dot(v[i], nrm)
                if vn < 0:
                    vt = v[i] - vn * nrm
                    v[i] = vt * 0.98 - 0.55 * vn * nrm
                    peg_flash[k] = 1.0
                    if -vn > 120 and t - hit_cool[i] > 0.07:
                        hit_cool[i] = t
                        song.note(t, float((p[i, 0] - 540) / 470), vel=min(1.0, 0.4 + -vn / 1200))
        # spinners
        for k in range(len(SPIN)):
            cx, cy, half, om, ph, s_ = SPIN[k]
            if abs(p[i, 1] - cy) > half + MR + 5:
                continue
            aa = ph + om * t
            A = np.array([cx - half * math.cos(aa), cy - half * math.sin(aa)])
            Bp = np.array([cx + half * math.cos(aa), cy + half * math.sin(aa)])
            ab = Bp - A
            u = np.clip(np.dot(p[i] - A, ab) / np.dot(ab, ab), 0, 1)
            q = A + ab * u
            d = p[i] - q
            dist = math.hypot(*d)
            if 1e-6 < dist < MR + 3:
                nrm = d / dist
                p[i] = q + nrm * (MR + 3)
                vw = om * np.array([-(q[1] - cy), q[0] - cx])
                vr = v[i] - vw
                vn = np.dot(vr, nrm)
                if vn < 0:
                    vt = vr - vn * nrm
                    v[i] = vw + vt * 0.999 - 0.55 * vn * nrm
                    if -vn > 150 and t - hit_cool[i] > 0.08:
                        hit_cool[i] = t
                        song.note(t, float((p[i, 0] - 540) / 470), vel=min(1.0, 0.5 + -vn / 1400))
                        events.append((t, "spin", (float(q[0]), float(q[1]), int(colour[i]), k)))
        # outer walls
        if p[i, 0] < XL + MR:
            p[i, 0] = XL + MR; v[i, 0] = abs(v[i, 0]) * 0.4
        if p[i, 0] > XR - MR:
            p[i, 0] = XR - MR; v[i, 0] = -abs(v[i, 0]) * 0.4
        # safety: a marble that got past a bridge level without touching the glass still counts as crossing
        for b, B in enumerate(BRIDGES):
            if i in B["touched"] or B["state"] == 2:
                continue
            far = B["x1"]
            yb = ramp_y(B["x0"], B["y0"], B["x1"], B["y1"], far)
            if (p[i, 0] - far) * B["dirx"] > 0 and yb - 90 < p[i, 1] < yb + 40:
                touch_bridge(i, b)
        # a marble that was still on the glass when it broke falls into the bin too (out)
        if alive[i]:
            for b, B in enumerate(BRIDGES):
                if B["state"] == 2 and B["hole"][0] < p[i, 0] < B["hole"][1] and max(B["y0"], B["y1"]) + MR * 0.6 < p[i, 1] < B["ybin"] + 5:
                    alive[i] = False
                    out_t[i] = t
                    in_bin[i] = b
                    events.append((t, "out", (i, b)))
                    events.append((t, "extra", (i, b)))
                    song.sfx(t, "whoosh", float((p[i, 0] - 540) / 470), 0.5)
                    if len(racers()) == 1 and winner is None and not any(doomed[j] and alive[j] for j in range(NM)):
                        globals()["winner"] = racers()[0]
    if finish_t is None and int(alive.sum()) == 1:
        globals()["winner"] = int(np.where(alive)[0][0])
        globals()["finish_t"] = t
        song.sfx(t + 0.03, "chime", 0.0, 1.0)
        events.append((t, "finish", (winner,)))
    if winner is not None and finish_t is not None and payoff_pending is None:
        payoff_pending = song.next_bar(t + 0.3)
    for s in shards:
        s["vy"] += G * 0.8 * dt
        s["x"] += s["vx"] * dt; s["y"] += s["vy"] * dt; s["a"] += s["va"] * dt


def do_payoff():
    global payoff_t
    payoff_t = t
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 0.5)
    x, y = p[winner]
    for _ in range(140):
        a = fx_rng.uniform(0, 2 * math.pi)
        rr = fx_rng.uniform(40, 560)
        sparks.append([x + rr * math.cos(a), y + rr * math.sin(a), fx_rng.uniform(10, 28), t, COLS[colour[winner]]])
    events.append((t, "payoff", 0))


# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
sprite_cache = {}


def sprites(rpx):
    q = max(5, int(round(rpx)))
    if q not in sprite_cache:
        sprite_cache[q] = neon.SkinSprites(COLS + [GREY], q, skin="orb")
    return sprite_cache[q]


def S(x, y):
    return 540 + (x - 540) * zoom, H * 0.47 + (y - cam_y) * zoom


def tube(pts, rgb, alpha=1.0, width=4.0, glowk=1.0):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for w, a in [(34, 0.05), (18, 0.10), (9, 0.25)]:
        ctx.set_source_rgba(*rgb, a * alpha * glowk); ctx.set_line_width(w * zoom * width / 4)
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_source_rgba(*neon.mix(rgb, (1, 1, 1), 0.6), 0.92 * alpha); ctx.set_line_width(max(1.5, width * zoom))
    ctx.move_to(*pts[0])
    for q in pts[1:]:
        ctx.line_to(*q)
    ctx.stroke(); ctx.restore()


def sec_col(s):
    c = SEC_COLS[s % len(SEC_COLS)]
    if payoff_t is not None:
        k = min(1.0, (t - payoff_t) / 0.5)
        c = neon.mix(c, COLS[colour[winner]], 0.85 * k)
    return c


def view_y(y):
    return abs(y - cam_y) * zoom < H * 0.62


def draw_bridge(b):
    B = BRIDGES[b]
    if not (view_y(B["y0"]) or view_y(B["ybin"])):
        return
    sc = sec_col(B["sec"])
    # bin (a small neon cup under the glass)
    b0, b1, b2 = B["bins"]
    pts = [S(SEG[b0][0], SEG[b0][1]), S(SEG[b0][2], SEG[b0][3]), S(SEG[b1][2], SEG[b1][3]), S(SEG[b1][0], SEG[b1][1])]
    tube(pts, neon.mix(sc, (0.6, 0.6, 0.7), 0.4), 0.55, 3.0)
    c_ = cap(b)
    used = len(B["touched"])
    frac = used / max(1, c_)
    if B["state"] == 2:
        age = t - B["t_break"]
        col = neon.mix(HOT, (0.45, 0.25, 0.35), min(1.0, age / 2.0))
        pulse = 1.0 + 2.0 * math.exp(-age * 5)
        spans = [(SEGA[kk][0], SEGB[kk][0]) for kk in B["pieces"] if seg_on[kk]]
    elif B["state"] == 1:
        col = HOT
        pulse = 1.2 + 0.6 * math.sin(t * 14)
        spans = [(B["x0"], B["x1"])]
    else:
        col = neon.mix(GLASS, (1.0, 0.65, 0.35), 0.75 * frac ** 1.3)
        pulse = 1.0
        spans = [(B["x0"], B["x1"])]
    th = 14.0 * (1 - 0.55 * frac) if B["state"] == 0 else 7.0
    for u0, u1 in spans:
        a0 = S(u0, ramp_y(B["x0"], B["y0"], B["x1"], B["y1"], u0))
        a1 = S(u1, ramp_y(B["x0"], B["y0"], B["x1"], B["y1"], u1))
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        for w_, al in ((th + 40, 0.05), (th + 22, 0.10), (th + 10, 0.18)):
            ctx.set_source_rgba(*col, al * pulse * 1.5); ctx.set_line_width(w_ * zoom)
            ctx.move_to(*a0); ctx.line_to(*a1); ctx.stroke()
        ctx.restore()
        ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        ctx.set_source_rgba(*col, 0.42); ctx.set_line_width(th * zoom)
        ctx.move_to(*a0); ctx.line_to(*a1); ctx.stroke()
        ang = math.atan2(a1[1] - a0[1], a1[0] - a0[0])
        nx, ny = math.sin(ang), -math.cos(ang)
        off = th * zoom / 2
        ctx.set_source_rgba(*neon.mix(col, (1, 1, 1), 0.65), 0.95); ctx.set_line_width(max(1.5, 2.5 * zoom))
        ctx.move_to(a0[0] + nx * off, a0[1] + ny * off); ctx.line_to(a1[0] + nx * off, a1[1] + ny * off); ctx.stroke()
        ctx.set_source_rgba(*neon.mix(col, (1, 1, 1), 0.3), 0.6); ctx.set_line_width(max(1.0, 1.6 * zoom))
        ctx.move_to(a0[0] - nx * off, a0[1] - ny * off); ctx.line_to(a1[0] - nx * off, a1[1] - ny * off); ctx.stroke()
        ctx.restore()
    ctx.save(); ctx.set_source_rgba(1, 1, 1, 0.8)
    for q in (S(B["x0"], B["y0"]), S(B["x1"], B["y1"])):
        ctx.arc(q[0], q[1], 4.5 * zoom, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    if B["state"] == 2:
        return
    # pips: one per marble it can carry; used pips go dark (they fade out over 0.3 s)
    n = c_
    for k in range(n):
        u = (k + 1) / (n + 1)
        x = B["x0"] + (B["x1"] - B["x0"]) * u
        y = ramp_y(B["x0"], B["y0"], B["x1"], B["y1"], x) + 26
        sx, sy = S(x, y)
        lit = k >= used
        if not lit:
            age = t - B["used_t"][k] if k < len(B["used_t"]) else 9
            fl = max(0.0, 1 - age / 0.3)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        if lit or fl > 0:
            al = 1.0 if lit else fl
            cc = GLASS if B["state"] == 0 else HOT
            g = cairo.RadialGradient(sx, sy, 0, sx, sy, 16 * zoom)
            g.add_color_stop_rgba(0, *cc, 0.7 * al); g.add_color_stop_rgba(1, *cc, 0)
            ctx.set_source(g); ctx.arc(sx, sy, 16 * zoom, 0, 2 * math.pi); ctx.fill()
            ctx.set_source_rgba(1, 1, 1, 0.95 * al); ctx.arc(sx, sy, (5.5 + 5 * (1 - al if not lit else 0)) * zoom, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        if not lit:
            ctx.save(); ctx.set_source_rgba(*neon.mix(col, (1, 1, 1), 0.2), 0.45); ctx.set_line_width(max(1.0, 1.5 * zoom))
            ctx.arc(sx, sy, 5.5 * zoom, 0, 2 * math.pi); ctx.stroke(); ctx.restore()


def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gc = COLS[colour[winner]] if payoff_t is not None else sec_col(int(np.clip(pr * 6.99, 0, 6)))
    rg = cairo.RadialGradient(540, H * 0.5, 0, 540, H * 0.5, 1100)
    ga = 0.04 + 0.10 * pr + 0.02 * math.sin(t * 2.0)
    if payoff_t is not None:
        ga = 0.18 * math.exp(-(t - payoff_t) * 0.8) + 0.06
    rg.add_color_stop_rgba(0, *gc, ga); rg.add_color_stop_rgba(1, *gc, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for x, y, rr, a in STARS:
        sy = H * 0.47 + (y - cam_y * 0.45) * 0.6
        sy = sy % (H + 200) - 100
        ctx.set_source_rgba(0.75, 0.8, 1.0, a); ctx.arc(x, sy, rr, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    shake = 0.0
    for B in BRIDGES:
        if B["t_break"] is not None and t - B["t_break"] < 0.35:
            shake = max(shake, 9 * (1 - (t - B["t_break"]) / 0.35))
    if payoff_t is not None:
        shake = max(shake, 14 * math.exp(-(t - payoff_t) * 5))
    ctx.save()
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    ytop, ybot = cam_y - H * 0.6 / zoom, cam_y + H * 0.6 / zoom
    for x in (XL, XR):
        tube([S(x, max(60, ytop)), S(x, min(COURSE_END, ybot))], (0.5, 0.58, 1.0), 0.5, 3.0)
    for k, (x0, y0, x1, y1, s_) in enumerate(SEG):
        if not seg_on[k] or k in GLASS_SEGS or k in BIN_SEGS or k in PIECE_SEGS or not (view_y(y0) or view_y(y1)):
            continue
        tube([S(x0, y0), S(x1, y1)], sec_col(s_), 1.0, 5.5)
    for b in range(NBR):
        draw_bridge(b)
    # pegs
    for k, (x, y, r_, s_) in enumerate(PEGS):
        if not view_y(y):
            continue
        sx, sy = S(x, y)
        f = peg_flash[k]
        c = neon.mix(sec_col(s_), (1, 1, 1), 0.5 * f)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        g = cairo.RadialGradient(sx, sy, 0, sx, sy, (r_ + 22) * zoom)
        g.add_color_stop_rgba(0, *c, 0.45 + 0.4 * f); g.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(g); ctx.arc(sx, sy, (r_ + 22) * zoom, 0, 2 * math.pi); ctx.fill(); ctx.restore()
        ctx.save(); ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.6), 0.95); ctx.arc(sx, sy, r_ * zoom * 0.8, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    for k, (x, y, R, s_) in enumerate(BUMP):
        if not view_y(y):
            continue
        sx, sy = S(x, y)
        f = bump_flash[k]
        c = neon.mix(sec_col(s_), (1, 1, 1), 0.5 * f)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        for w, a in [(30, 0.06), (16, 0.12), (8, 0.3)]:
            ctx.set_source_rgba(*c, a * (1 + 1.5 * f)); ctx.set_line_width(w * zoom)
            ctx.new_path(); ctx.arc(sx, sy, R * zoom, 0, 2 * math.pi); ctx.stroke()
        g = cairo.RadialGradient(sx, sy, 0, sx, sy, R * zoom)
        g.add_color_stop_rgba(0, *c, 0.10 + 0.35 * f); g.add_color_stop_rgba(1, *c, 0.02)
        ctx.set_source(g); ctx.arc(sx, sy, R * zoom, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        ctx.save(); ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.65), 0.9); ctx.set_line_width(max(1.5, 3.5 * zoom))
        ctx.new_path(); ctx.arc(sx, sy, R * zoom * (1 + 0.12 * f), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    for k in range(len(SPIN)):
        cx, cy, half, om, ph, s_ = SPIN[k]
        if not view_y(cy):
            continue
        aa = ph + om * t
        tube([S(cx - half * math.cos(aa), cy - half * math.sin(aa)), S(cx + half * math.cos(aa), cy + half * math.sin(aa))], sec_col(s_), 1.0, 7.0, 1.3)
        sx, sy = S(cx, cy)
        ctx.save(); ctx.set_source_rgba(1, 1, 1, 0.9); ctx.arc(sx, sy, 7 * zoom, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    # hit flashes
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, data in events[-60:]:
        if kind in ("hit", "spin") and 0 <= t - et < 0.3:
            a = 1 - (t - et) / 0.3
            x, y, c, _ = data
            sx, sy = S(x, y)
            g = cairo.RadialGradient(sx, sy, 0, sx, sy, 40 * zoom)
            g.add_color_stop_rgba(0, *COLS[c], 0.5 * a); g.add_color_stop_rgba(1, *COLS[c], 0)
            ctx.set_source(g); ctx.arc(sx, sy, 40 * zoom, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    # trails
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(NM):
        if (not alive[i] and i != winner) or len(trail[i]) < 3:
            continue
        pts = [S(x, y) for x, y in trail[i]]
        n = len(pts)
        for k in range(1, n):
            a = (k / n) ** 1.6
            ctx.set_source_rgba(*COLS[colour[i]], 0.38 * a); ctx.set_line_width(MR * zoom * 1.3 * a)
            ctx.move_to(*pts[k - 1]); ctx.line_to(*pts[k]); ctx.stroke()
    ctx.restore()
    spr = sprites(MR * zoom)
    pts, cis = [], []
    for i in range(NM):
        if not alive[i] and i != winner:
            ci = len(COLS) if t - out_t[i] > 0.6 else colour[i]
        else:
            ci = colour[i]
        sx, sy = S(*p[i])
        if -60 < sy < H + 60:
            pts.append((sx, sy)); cis.append(ci)
    spr.draw(ctx, pts, cis)
    # doomed marble: red warning ring while it rolls toward the spent glass
    for i in range(NM):
        if doomed[i] and alive[i]:
            sx, sy = S(*p[i])
            k = 0.5 + 0.5 * math.sin(t * 14)
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*HOT, 0.35 + 0.35 * k); ctx.set_line_width(3)
            ctx.new_path(); ctx.arc(sx, sy, MR * zoom * (1.5 + 0.2 * k), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    if winner is not None:
        sx, sy = S(*p[winner])
        k = 0.5 + 0.5 * math.sin(t * 8)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_rgba(*COLS[colour[winner]], 0.35 + 0.25 * k); ctx.set_line_width(4)
        ctx.new_path(); ctx.arc(sx, sy, MR * zoom * (1.6 + 0.3 * k), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    # shards
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    keep = []
    for s in shards:
        age = t - s["t0"]
        if age > 2.0:
            continue
        keep.append(s)
        a = max(0.0, 1 - age / 2.0)
        x, y = S(s["x"], s["y"])
        dx, dy = math.cos(s["a"]) * s["L"] / 2 * zoom, math.sin(s["a"]) * s["L"] / 2 * zoom
        for w_, al in ((s["th"] + 14, 0.12), (s["th"] + 3, 0.35), (4, 0.9)):
            ctx.set_source_rgba(*neon.mix(neon.mix(GLASS, s["c"], 0.5), (1, 1, 1), 0.3 if al > 0.5 else 0), al * a)
            ctx.set_line_width(w_ * zoom)
            ctx.move_to(x - dx, y - dy); ctx.line_to(x + dx, y + dy); ctx.stroke()
    shards[:] = keep
    ctx.restore()
    live = [s for s in sparks if t - s[3] < 0.6]
    sparks[:] = live
    by = {}
    for x, y, sz, st_, c in live:
        a = 1 - (t - st_) / 0.6
        sx, sy = S(x, y)
        by.setdefault((c, round(a, 1)), []).append((sx, sy, sz * (0.6 + a) * max(0.6, zoom)))
    for (c, a), pts_ in by.items():
        neon.sparkles(ctx, pts_, neon.mix(c, (1, 1, 1), 0.4), alpha=a * 0.9)
    ctx.restore()
    # race order dots (top) on a dark glass band so they never mix with the course
    ctx.save()
    ctx.new_path()
    x0b, x1b, y0b, y1b, rb = 150, 930, 76, 160, 42
    ctx.arc(x0b + rb, y0b + rb, rb, math.pi / 2, 3 * math.pi / 2); ctx.arc(x1b - rb, y0b + rb, rb, -math.pi / 2, math.pi / 2)
    ctx.close_path()
    ctx.set_source_rgba(0.01, 0.01, 0.04, 0.82); ctx.fill_preserve()
    ctx.set_source_rgba(0.6, 0.65, 1.0, 0.25); ctx.set_line_width(2); ctx.stroke()
    ctx.restore()
    order = race_order()
    for slot, i in enumerate(order):
        x = 540 + (slot - 3.5) * 92
        y = 118.0
        grey = not alive[i] and i != winner
        c = (0.42, 0.42, 0.5) if grey else COLS[colour[i]]
        big = 1.35 if i == winner else 1.0
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        g = cairo.RadialGradient(x, y, 0, x, y, 40 * big)
        g.add_color_stop_rgba(0, *c, 0.12 if grey else 0.45); g.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(g); ctx.arc(x, y, 40 * big, 0, 2 * math.pi); ctx.fill(); ctx.restore()
        ctx.save(); ctx.set_source_rgba(*c, 0.35 if grey else 1.0); ctx.arc(x, y, 17 * big, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.25 if grey else 0.7); ctx.arc(x - 5, y - 6, 5 * big, 0, 2 * math.pi); ctx.fill(); ctx.restore()
        if doomed[i] and alive[i]:
            ctx.save(); ctx.set_source_rgba(*HOT, 0.5 + 0.4 * math.sin(t * 14)); ctx.set_line_width(3)
            ctx.arc(x, y, 25, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    if counter and payoff_t is None:
        n = int(alive.sum())
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(110)
        txt = str(n)
        xb, yb, tw, th_, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1820)
        ctx.text_path(txt)
        cc = neon.mix(gc, (1, 1, 1), 0.45)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(20); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if payoff_t is not None:
        fa = max(0.0, 0.45 - (t - payoff_t) * 2.5)
        if fa > 0:
            ctx.set_source_rgba(*neon.mix(COLS[colour[winner]], (1, 1, 1), 0.7), fa); ctx.paint()
        age = t - payoff_t
        if age < 1.3:
            sx, sy = S(*p[winner])
            a = 1 - age / 1.3
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*COLS[colour[winner]], 0.8 * a); ctx.set_line_width(4 + 18 * a)
            ctx.new_path(); ctx.arc(sx, sy, 40 + 1800 * age, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        end = payoff_t + TAIL
        xf = (t - (end - 1.4)) / 1.4
        if xf > 0 and first is not None:
            ctx.set_source_surface(first, 0, 0); ctx.paint_with_alpha(min(1.0, xf) ** 1.5)


ff = None
if not SIM_ONLY:
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", OUT
    ], stdin=subprocess.PIPE)

dt = 1.0 / (FPS * SUB)
frame = 0
while True:
    for _ in range(SUB):
        physics_step(dt)
        if payoff_pending is not None and payoff_t is None and t >= payoff_pending:
            do_payoff()
        t += dt
    bump_flash *= 0.85
    peg_flash *= 0.85
    for i in range(NM):
        trail[i].append((float(p[i, 0]), float(p[i, 1])))
        if len(trail[i]) > 14:
            trail[i].pop(0)
    # camera: frame every marble still racing (incl. a doomed one until it falls), then the winner
    ids = [i for i in range(NM) if alive[i]]
    if winner is not None and finish_t is not None:
        ids = [winner]
    ys = p[ids, 1]
    lo, hi = ys.min(), ys.max()
    zt = float(np.clip(1500 / (hi - lo + 800), 0.6, 0.95))
    if winner is not None and finish_t is not None:
        zt = 0.82
    ct = (lo + hi) / 2 + 110 / zt
    cam_y += (ct - cam_y) * 0.08
    zoom += (zt - zoom) * 0.04
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if PREVIEW and any(abs(t - pt) < 0.5 / FPS for pt in PREVIEW):
        draw(); surf.flush(); surf.write_to_png(f"prev_{t:05.1f}.png")
    if os.environ.get("DEBUG") and frame % 120 == 0:
        print(round(t), [(int(x), int(y)) for x, y in p], list(alive.astype(int)), list(doomed.astype(int)))
    if not SIM_ONLY:
        draw(); surf.flush()
        if first is None:
            first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if payoff_t is not None and t >= payoff_t + TAIL:
        break
    if t > 85:
        break

if ff:
    ff.stdin.close(); ff.wait()
outs = [(round(e[0], 1), e[2][1]) for e in events if e[1] == "out"]
spent = [(round(B["t_spent"], 1) if B["t_spent"] else None) for B in BRIDGES]
print("seed", SEED, "outs (t, bridge)", outs, "spent", spent)
print("finish", finish_t and round(finish_t, 2), "payoff", payoff_t and round(payoff_t, 2), "duration", round(t, 2),
      "winner colour", winner is not None and int(colour[winner]), "bridges y", [round(B["y0"]) for B in BRIDGES], "end", round(COURSE_END))
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
