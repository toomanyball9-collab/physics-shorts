"""2026-11-29 08:00 — chain-reaction (variation of Glass Floors): "Tipping Cups"
A neon machine of four tipping cups (shishi-odoshi style), each on a lever with a glowing COUNTERWEIGHT on the
other arm. Bigger cups have bigger counterweights. A dropper drops a ball on the beat into the top cup
(1 -> 2 -> 3 -> 4 per beat, switching on bar lines; colour changes every 4 bars -> strata).
Real lever physics: the cup tips when the balls inside out-weigh its counterweight (torque), pours everything
into the next cup and the counterweight swings it back. Dumps can set off the next cup at once (chain).
The bottom basin has the biggest counterweight: when it is completely packed it creaks (heats red, shakes),
and on the bar it tips over and pours the whole load out of the machine; then everything rests empty (loop).
Sound: balls bouncing on cup walls = music (song.note); a cup tipping = whoosh; lever hitting its stop = thump;
balls landing on a pile = tick; final tip = accent.

usage: python3 concepts/2026-11-29_am_tipping_cups.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 6
ITERS = int(os.environ.get("ITERS", "6"))
BR = float(os.environ.get("BR", "13"))
G = 1500.0
TAIL = 3.0
DT = 1.0 / (FPS * SUB)
dt = DT
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
DEBUG = "DEBUG" in os.environ
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
# random_song(2026112902, avoid=all posted recipes incl. 11-28 dreamwave) -> celtic 102 A# dorian harp 3/4
MUSIC_SEED = int(os.environ.get("MSEED", "2026112902"))
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
          dict(genre="synthwave", bpm=106, key="G", mode="minor", lead="glass"),
          dict(genre="kpop_bright", bpm=117, key="E", mode="major", lead="pluck"),
          dict(genre="dreamwave", bpm=88, key="D#", mode="lydian", lead="celesta")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)
BEAT = song.beat
BAR = song.chord_len

# strata colours (change every 4 bars)
BCOLS = [(0.35, 0.85, 1.0), (0.45, 1.0, 0.70), (0.80, 1.0, 0.40), (1.0, 0.82, 0.30), (1.0, 0.55, 0.35),
         (1.0, 0.42, 0.62), (0.72, 0.50, 1.0)]
PAL = {"bg": ((0.01, 0.025, 0.07), (0.00, 0.00, 0.03)), "ring": (0.7, 0.9, 1.0), "balls": BCOLS, "accent": (1, 1, 1)}
MACH = (0.62, 0.86, 1.0)
HOT = (1.0, 0.22, 0.25)
CWC = (0.95, 0.92, 1.0)

DROP_X, DROP_Y = float(os.environ.get("DROPX", "458")), 175.0
TIERS = [float(x) for x in os.environ.get("TIERS", "9,24,40").split(",")]
TIER_BARS = [math.ceil(x / BAR) for x in TIERS]
LG = float(os.environ.get("LG", "3.0"))
PIV = float(os.environ.get("PIV", "16"))
CWH = float(os.environ.get("CWH", "0.3"))
OMAX = float(os.environ.get("OMAX", "3.2"))            # lever gravity factor (speed of the tipping motion)
CAP = [float(x) for x in os.environ.get("CAP", "8,24,46,175").split(",")]
PRE = [int(x) for x in os.environ.get("PRE", "6,16,12,0").split(",")]


class Lever:
    def __init__(self, cx, cy, w, d, s, gap, b, N, tmax, flare=0.62, lip=0.85):
        self.s = s                      # +1: cup right of the pivot (tips clockwise, pours right); -1 mirrored
        self.px, self.py = cx - s * (w / 2 + gap), cy + d / 2 + PIV   # pivot BELOW the load -> decisive tipping
        self.w, self.d, self.N, self.tmax = w, d, N, tmax
        self.b = b
        hw, hd, r = w / 2, d / 2, 12.0
        inner_x, outer_x = cx - s * hw, cx + s * hw
        L = d * lip
        # inner wall (tall, vertical), round-ish bottom, outer wall flared outward (angle `flare` from vertical)
        self.local = np.array([[inner_x - s * 4, cy - hd], [inner_x, cy + hd - r], [inner_x + s * r, cy + hd],
                               [outer_x - s * r, cy + hd], [outer_x, cy + hd - r],
                               [outer_x + s * L * math.sin(flare), cy + hd - r - L * math.cos(flare)]]) - [self.px, self.py]
        self.cw_rel = np.array([-s * b, CWH * b])          # hangs a bit below the pivot -> returns reliably
        self.M = N * abs(cx - self.px) / b
        self.th, self.om = 0.0, 0.0
        self.latched = False
        self.load = 0.0
        self.tips = 0
        self.flash = 0.0
        self.ratio = 0.0

    def rot(self, pts, th=None):
        a = self.s * (self.th if th is None else th)
        c, sn = math.cos(a), math.sin(a)
        x, y = pts[..., 0], pts[..., 1]
        return np.stack([x * c - y * sn + self.px, x * sn + y * c + self.py], -1)

    def poly(self, th=None):
        return self.rot(self.local, th)

    def cw(self):
        return self.rot(self.cw_rel)

    def inside(self, pos):
        """balls inside the cup: test in the cup's own (rest) frame."""
        a = -self.s * self.th
        c, sn = math.cos(a), math.sin(a)
        x, y = pos[:, 0] - self.px, pos[:, 1] - self.py
        lx, ly = x * c - y * sn, x * sn + y * c
        xs = self.local[:, 0]
        return (lx > xs.min() - 4) & (lx < xs.max() + 4) & (ly > self.local[:, 1].min() - 2 * BR) & (ly < self.local[:, 1].max() + 2)


LAYOUT = os.environ.get("LAYOUT", "")
LEVERS = [Lever(430, 420, 104, 78, +1, 44, 64, CAP[0], 1.12),
          Lever(636, 790, 180, 108, -1, 50, 84, CAP[1], 1.12),
          Lever(445, 1142, 262, 150, +1, 52, 96, CAP[2], 1.10),
          Lever(545, 1665, 520, 200, -1, 56, 96, CAP[3], 1.0, flare=0.5, lip=0.95)]
BASIN = LEVERS[-1]
if "--layout" in sys.argv:
    for k, L in enumerate(LEVERS):
        q0, q1 = L.poly(0.0), L.poly(L.tmax)
        print(k, "rest x", q0[:, 0].min().round(), q0[:, 0].max().round(), "y", q0[:, 1].min().round(), q0[:, 1].max().round(),
              "| tipped lip", q1[-1].round(), "corner", q1[-2].round(), "lowest", q1[:, 1].max().round())
    sys.exit()

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 777)

p = np.zeros((0, 2)); v = np.zeros((0, 2)); col = np.zeros(0, int); note_cool = np.zeros(0)
t = 0.0
heat = 0.0
full_t = None
payoff_pending = None
payoff_t = None
sparks, events, build_keys = [], [], []
next_drop = 0.0
drop_k = 0
tick_cool = -9.0
max_n = 0
lost = []
fastlog = []
pushlog = []
prev_cnt = [0] * len(LEVERS)


def per_beat(tt):
    b = int(tt / BAR)
    n = 1
    for tb in TIER_BARS:
        if b >= tb:
            n += 1
    return n


def colour_at(tt):
    return int(tt / (4 * BAR)) % len(BCOLS)


def progress():
    if payoff_t is not None:
        return 1.0
    return float(np.clip(0.1 + 0.65 * BASIN.ratio + 0.25 * min(1, t / 58), 0, 1))


def add_balls(xy, vv, c):
    global p, v, col, note_cool
    p = np.vstack([p, xy]); v = np.vstack([v, vv])
    col = np.append(col, c)
    note_cool = np.append(note_cool, np.full(len(xy), -9.0))


def release():
    global next_drop, drop_k
    while t >= next_drop and payoff_t is None and t < 75:
        x = DROP_X + rng.uniform(-4, 4)
        add_balls(np.array([[x, DROP_Y + 12]]), np.array([[rng.uniform(-15, 15), 80.0]]), [colour_at(next_drop)])
        drop_k += 1
        next_drop += BEAT / per_beat(next_drop + 1e-6)


def wall_setup(pp):
    """per lever: wall segments with interior normals + which balls are inside the cup (from positions before the step)."""
    out = []
    for L in LEVERS:
        q = L.poly()
        qc = np.vstack([q, q[:1]])
        # orientation: interior is on the left or right of the edge direction
        area = 0.5 * np.sum(qc[:-1, 0] * qc[1:, 1] - qc[1:, 0] * qc[:-1, 1])
        sg = 1.0 if area > 0 else -1.0
        ins = np.ones(len(pp), bool)
        for k in range(len(q)):
            e = qc[k + 1] - qc[k]
            cr = e[0] * (pp[:, 1] - qc[k, 1]) - e[1] * (pp[:, 0] - qc[k, 0])
            ins &= sg * cr > -2.0
        segs = []
        for k in range(len(q) - 1):
            e = q[k + 1] - q[k]
            ln = math.hypot(*e)
            nin = sg * np.array([-e[1], e[0]]) / ln
            side = ((pp - q[k]) @ nin) >= 0                 # which side of this wall the ball was on
            segs.append((q[k], q[k + 1], nin, side))
        out.append((ins, segs))
    return out


def seg_solve(walls):
    """push balls out of the cup walls (thick neon tubes): balls inside the cup stay inside, outside stay outside."""
    global p
    contact = np.zeros(len(p), bool)
    R = BR + 4.0
    for ins, segs in walls:
        for a, b, nin, side in segs:
            ab = b - a
            L2 = ab @ ab
            ap = p - a
            u = (ap @ ab) / L2
            near = (u > -R / math.sqrt(L2)) & (u < 1 + R / math.sqrt(L2))
            sd = ap @ nin
            near &= np.abs(sd) < R + 2
            if not near.any():
                continue
            idx = np.where(near)[0]
            uu = u[idx]
            mid = (uu >= 0) & (uu <= 1)
            sdi = sd[idx]
            inn = side[idx]
            # straight part of the wall
            push = np.zeros((len(idx), 2))
            m1 = mid & inn & (sdi < R)
            push[m1] = nin * (R - sdi[m1])[:, None]
            m2 = mid & ~inn & (sdi > -R)
            push[m2] = -nin * (R + sdi[m2])[:, None]
            # end caps (round)
            cap = ~mid
            if cap.any():
                cp = np.where(uu[cap, None] < 0, a, b)
                d = p[idx[cap]] - cp
                dist = np.hypot(d[:, 0], d[:, 1])
                m3 = (dist < R) & (dist > 1e-6)
                pc = np.zeros((cap.sum(), 2))
                pc[m3] = d[m3] / dist[m3, None] * (R - dist[m3])[:, None]
                push[cap] = pc
            pm = np.hypot(push[:, 0], push[:, 1])
            hit = pm > 0
            if DEBUG and (pm > 12).any() and len(pushlog) < 12:
                z = np.argmax(pm)
                pushlog.append((round(t, 3), round(float(pm[z]), 1), bool(inn[z]), bool(mid[z]), round(float(sdi[z]), 1), round(float(uu[z]), 2), p[idx[z]].round().tolist(), a.round().tolist(), b.round().tolist()))
            p[idx] += push
            contact[idx[hit]] = True
    return contact


def lever_step(dt):
    global full_t, payoff_pending, heat
    for k, L in enumerate(LEVERS):
        ins = L.inside(p) if len(p) else np.zeros(0, bool)
        rx = p[ins, 0] - L.px if len(p) else np.zeros(0)
        tau_balls = float(rx.sum())                        # m = 1, g factored out
        cwp = L.cw()
        tau_cw = L.M * (cwp[0] - L.px)
        cnt = int(ins.sum())
        L.load = cnt
        # ratio of tipping torque to holding torque (gauge for the glow)
        L.ratio = float(np.clip(L.s * tau_balls / max(1e-6, -L.s * tau_cw), 0, 1.3)) if L.th < 0.05 else L.ratio
        I = L.M * L.b ** 2 + float((rx ** 2).sum()) + 0.15 * L.M * L.b ** 2 + 4000
        alpha = L.s * (tau_balls + tau_cw) * G * LG / I - 2.2 * L.om
        if L is BASIN and payoff_t is None:
            if L.ratio >= 1.0 and full_t is None:
                full_t = t
                payoff_pending = song.next_bar(t + 0.3)
                song.sfx(t, "chime", 0.0, 0.5)
                events.append((t, "full", cnt))
            L.latched = True                               # held until the bar (creaking)
        if L.latched:
            L.th, L.om = 0.0, 0.0
            continue
        prev = L.th
        L.om += alpha * dt
        om_max = OMAX * 260.0 / max(260.0, abs(L.local[:, 0]).max())    # dashpot: rim speed stays below ~OMAX*260 px/s
        L.om = float(np.clip(L.om, -om_max, om_max))
        L.th += L.om * dt
        if L.th < 0:
            if L.om < -1.2:
                song.sfx(t, "thump", float((L.px - W / 2) / 500), min(0.5, 0.12 + abs(L.om) / 14))
            L.th, L.om = 0.0, -L.om * 0.22 if L.om < -1.2 else 0.0
        if L.th > L.tmax:
            if L.om > 1.0:
                song.sfx(t, "thump", float((L.px - W / 2) / 500), min(0.45, 0.1 + L.om / 16))
            L.th, L.om = L.tmax, -L.om * 0.18
        if prev < 0.12 <= L.th:
            L.tips += 1
            L.flash = 1.0
            song.sfx(t, "whoosh", float(L.s * 0.5), 0.35 + 0.1 * k)
            events.append((t, "tip", k, cnt))
            if DEBUG:
                print(f"  t={t:5.2f} tip L{k} cnt={cnt}")


def physics_step(dt):
    global p, v, col, note_cool, tick_cool, max_n
    lever_step(dt)
    n = len(p)
    if not n:
        return
    v[:, 1] += G * dt
    v -= v * 0.10 * dt
    pp = p.copy()
    p += v * dt
    walls = wall_setup(pp)
    pairs = cKDTree(p).query_pairs(2 * BR + 1.0, output_type="ndarray") if n > 1 else np.zeros((0, 2), int)
    i, j = (pairs[:, 0], pairs[:, 1]) if len(pairs) else (None, None)
    contact = np.zeros(n, bool)
    for it in range(ITERS):
        if i is not None:
            d = p[j] - p[i]
            dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
            over = 2 * BR - dist
            m = over > 0
            if m.any():
                corr = (d[m] / dist[m, None]) * (over[m] * 0.5)[:, None]
                np.add.at(p, i[m], -corr); np.add.at(p, j[m], corr)
        contact |= seg_solve(walls)
    nv = (p - pp) / dt
    # wall bounces -> notes (balls hitting a cup wall fast)
    hitw = np.where(contact & (np.hypot(v[:, 0], v[:, 1]) > 420) & (np.hypot(nv[:, 0], nv[:, 1]) < 0.75 * np.hypot(v[:, 0], v[:, 1])))[0]
    for ii in hitw:
        if t - note_cool[ii] > 0.35:
            note_cool[ii] = t
            song.note(t, float((p[ii, 0] - W / 2) / 500), vel=min(1.0, 0.3 + np.hypot(*v[ii]) / 1600))
    # restitution on cup walls: a little bounce
    if i is not None:
        cnt = np.bincount(np.concatenate([i, j]), minlength=n)
        calm = (cnt >= 3)
        nv[calm] *= 1 - 5.0 * dt
        if len(i) and t - tick_cool > 0.14:
            dv = v[:, 1] - nv[:, 1]
            land = np.where(dv > 650)[0]
            if len(land) > 3:
                tick_cool = t
                song.sfx(t, "tick", 0.0, min(0.3, 0.08 + len(land) / 70))
    nv[contact] *= 1 - 3.0 * dt
    sp = np.hypot(nv[:, 0], nv[:, 1])
    if DEBUG and (sp > 1000).any() and len(fastlog) < 40:
        for ii in np.where(sp > 1000)[0][:2]:
            fastlog.append((round(t, 2), p[ii].round().tolist(), v[ii].round().tolist(), nv[ii].round().tolist(), bool(contact[ii])))
    fast = sp > 1400
    if fast.any():
        nv[fast] *= (1400 / sp[fast])[:, None]
    v = nv
    max_n = max(max_n, n)
    keep = (p[:, 1] < H + 150) & (p[:, 0] > -150) & (p[:, 0] < W + 150)
    if not keep.all():
        if DEBUG:
            for q in p[~keep]:
                lost.append((round(t, 1), int(q[0]), int(pp[~keep][0][1])))
        p, v, col, note_cool = p[keep], v[keep], col[keep], note_cool[keep]


def do_payoff():
    global payoff_t
    payoff_t = t
    song.accent(t)
    song.sfx(t, "whoosh", -0.4, 1.0)
    song.sfx(t, "thump", 0.0, 0.9)
    BASIN.latched = False
    BASIN.om = 1.2
    BASIN.flash = 1.0
    q = BASIN.poly()
    for _ in range(60):
        a = fx_rng.integers(len(q) - 1)
        u = fx_rng.uniform()
        x, y = q[a] * (1 - u) + q[a + 1] * u
        sparks.append([x, y, fx_rng.uniform(8, 18), t, neon.mix(MACH, HOT, 0.7)])
    events.append((t, "payoff", 0))


def preload():
    """balls already resting in the cups at t = 0 (the machine is mid-cycle when the video starts)."""
    global p, v, col, note_cool, t
    for L, n_ in zip(LEVERS, PRE):
        q = L.poly()
        xs = (q[1:5, 0].min() + BR + 8, q[1:5, 0].max() - BR - 8)
        y0 = q[:, 1].max() - BR - 8
        k = 0
        row = 0
        while k < n_:
            ncol = int((xs[1] - xs[0]) / (2 * BR + 1))
            for c_ in range(ncol):
                if k >= n_:
                    break
                add_balls(np.array([[xs[0] + c_ * (2 * BR + 1) + (BR if row % 2 else 0), y0 - row * (2 * BR - 1)]]),
                          np.zeros((1, 2)), [0])
                k += 1
            row += 1
    # settle with levers held
    for L in LEVERS:
        L.latched = True
    for _ in range(int(1.5 / dt)):
        physics_step(dt)
    for L in LEVERS:
        L.latched = False
    v[:] = 0
    t = 0.0


# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = neon.BallSprites(BCOLS, BR, glow=2.6, glow_alpha=0.5)
STARS = [(fx_rng.uniform(0, W), fx_rng.uniform(0, H), fx_rng.uniform(0.6, 2.0), fx_rng.uniform(0.05, 0.22)) for _ in range(200)]


def tube(pts, rgb, alpha=1.0, width=5.0, glowk=1.0, closed=False):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for w, a in [(40, 0.04), (24, 0.08), (13, 0.15), (7, 0.30)]:
        ctx.set_source_rgba(*rgb, min(1.0, a * alpha * glowk)); ctx.set_line_width(w * width / 5)
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        if closed:
            ctx.close_path()
        ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_source_rgba(*neon.mix(rgb, (1, 1, 1), 0.6), 0.95 * alpha); ctx.set_line_width(width * 0.9)
    ctx.move_to(*pts[0])
    for q in pts[1:]:
        ctx.line_to(*q)
    if closed:
        ctx.close_path()
    ctx.stroke(); ctx.restore()


def glow_dot(x, y, r, c, a):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *c, a); g.add_color_stop_rgba(0.4, *c, a * 0.35); g.add_color_stop_rgba(1, *c, 0)
    ctx.set_source(g); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill(); ctx.restore()


def draw_lever(L, ox, oy):
    q = L.poly() + [ox, oy]
    hk = max(0.0, (L.ratio - 0.55) / 0.45) if L.th < 0.05 else 0.0
    if L is BASIN:
        hk = max(hk, heat)
    c = neon.mix(MACH, HOT, 0.85 * hk ** 1.5)
    pulse = 1.0 + 0.8 * L.flash
    if L is BASIN and heat > 0.8 and payoff_t is None:
        pulse += 0.6 * (0.5 + 0.5 * math.sin(t * 22)) * (heat - 0.8) / 0.2
    # stand (fixed): post down from the pivot
    px, py = L.px + ox, L.py + oy
    st = [(px - 26, py + 70), (px, py + 4), (px + 26, py + 70)]
    tube(st, (0.45, 0.55, 0.85), 0.6, 3.5)
    # arm: pivot -> cup inner wall (two struts) and pivot -> counterweight
    cwp = L.cw() + [ox, oy]
    tube([(px, py), tuple(cwp)], (0.55, 0.65, 0.95), 0.85, 4.0)
    tube([(px, py), tuple(q[1])], (0.55, 0.65, 0.95), 0.85, 4.0)
    tube([(px, py), tuple(q[0] * 0.35 + q[1] * 0.65)], (0.55, 0.65, 0.95), 0.6, 3.0)
    # cup
    tube([tuple(x) for x in q], c, 1.0, 6.0, pulse)
    # pivot
    glow_dot(px, py, 26, MACH, 0.5)
    ctx.set_source_rgba(1, 1, 1, 0.95); ctx.arc(px, py, 6.5, 0, 2 * math.pi); ctx.fill()
    # counterweight orb: size shows its weight
    rr = 9.0 + 3.1 * math.sqrt(L.M)
    cc = neon.mix(CWC, HOT, 0.6 * hk ** 1.5)
    glow_dot(cwp[0], cwp[1], rr * 2.6, cc, 0.35 + 0.3 * L.flash)
    g = cairo.RadialGradient(cwp[0] - rr * 0.35, cwp[1] - rr * 0.4, rr * 0.05, cwp[0], cwp[1], rr)
    g.add_color_stop_rgb(0, 1, 1, 1); g.add_color_stop_rgb(0.5, *neon.mix(cc, (1, 1, 1), 0.3)); g.add_color_stop_rgb(1, *neon.mix(cc, (0, 0, 0), 0.4))
    ctx.set_source(g); ctx.arc(cwp[0], cwp[1], rr, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*neon.mix(cc, (1, 1, 1), 0.7), 0.9); ctx.set_line_width(2); ctx.arc(cwp[0], cwp[1], rr - 1, 0, 2 * math.pi); ctx.stroke()
    # stop peg under the counterweight arm
    sx = L.px - L.s * (L.b * 0.55) + ox
    tube([(sx, L.py + 16 + oy), (sx, L.py + 40 + oy)], (0.45, 0.55, 0.85), 0.5, 3.0)


def draw_dropper(ox, oy):
    x, y = DROP_X + ox, DROP_Y + oy
    c = (0.85, 0.9, 1.0)
    last = next_drop - BEAT / per_beat(max(0.0, next_drop - 1e-3))
    pulse = max(0.0, 1 - (t - last) / 0.15) if drop_k else 0.0
    glow_dot(x, y, 80, c, 0.25 + 0.3 * pulse)
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.5), 0.95); ctx.set_line_width(5); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(x - 34, y - 30); ctx.line_to(x - 12, y); ctx.line_to(x + 12, y); ctx.line_to(x + 34, y - 30); ctx.stroke()
    # next colour preview dot on the hopper
    cc = BCOLS[colour_at(t)]
    glow_dot(x, y - 44, 22, cc, 0.6)


def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gc = neon.mix((0.35, 0.6, 1.0), HOT, max(0.0, heat - 0.5) / 0.5 * 0.6)
    rg = cairo.RadialGradient(W / 2, H * 0.62, 0, W / 2, H * 0.62, 1100)
    ga = 0.04 + 0.10 * pr
    if payoff_t is not None:
        ga = 0.06 + 0.2 * math.exp(-(t - payoff_t) * 1.2)
    rg.add_color_stop_rgba(0, *gc, ga); rg.add_color_stop_rgba(1, *gc, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for x, y, rr, a in STARS:
        ctx.set_source_rgba(0.75, 0.8, 1.0, a * (0.7 + 0.3 * math.sin(t * 1.3 + x))); ctx.arc(x, y, rr, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    shake = 0.0
    if heat > 0.7 and payoff_t is None:
        shake = 3.0 * (heat - 0.7) / 0.3
    if payoff_t is not None:
        shake = max(shake, 12 * math.exp(-(t - payoff_t) * 5))
    ox = fx_rng.uniform(-shake, shake) if shake > 0 else 0.0
    oy = fx_rng.uniform(-shake, shake) if shake > 0 else 0.0
    draw_dropper(0, 0)
    for L in LEVERS:
        draw_lever(L, ox if L is BASIN else 0.0, oy if L is BASIN else 0.0)
    vis = (p[:, 1] < H + 40)
    SPR.draw(ctx, [(x, y) for x, y in p[vis]], list(col[vis]))
    lv = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = lv
    by = {}
    for x, y, sz, st, c in lv:
        al = 1 - (t - st) / 0.5
        by.setdefault((c, round(al, 1)), []).append((x, y - 40 * (t - st), sz * (0.5 + al)))
    for (c, al), q in by.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.5), alpha=al * 0.9)
    if counter and payoff_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(78)
        txt = f"{len(p)}"
        xb, yb, tw, th_, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1890)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix((0.8, 0.9, 1.0), HOT, heat * 0.6), (1, 1, 1), 0.3)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(18); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.92); ctx.fill()
        ctx.restore()
    if payoff_t is not None:
        dtp = t - payoff_t
        fa = max(0.0, 0.45 - dtp * 2.8)
        if fa > 0:
            ctx.set_source_rgba(1, 1, 1, fa); ctx.paint()
        if dtp < 1.2:
            a = 1 - dtp / 1.2
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*neon.mix(MACH, (1, 1, 1), 0.4), 0.7 * a); ctx.set_line_width(4 + 16 * a)
            ctx.new_path(); ctx.arc(BASIN.px, BASIN.py, 60 + 1300 * dtp, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        end = payoff_t + TAIL
        xf = (t - (end - 1.4)) / 1.4
        if xf > 0 and first is not None:
            ctx.set_source_surface(first, 0, 0); ctx.paint_with_alpha(min(1.0, xf) ** 1.5)


preload()
sparks.clear(); events.clear()
song.notes.clear(); song.sfxs.clear(); song._last_slot = -1
full_t = None; payoff_pending = None
for L in LEVERS:
    L.tips = 0; L.flash = 0.0

ff = None
if not SIM_ONLY:
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", OUT
    ], stdin=subprocess.PIPE)

frame = 0
while True:
    for _ in range(SUB):
        release()
        physics_step(dt)
        if full_t is not None and payoff_t is None:
            heat = min(1.0, heat + dt / max(0.3, payoff_pending - full_t))
        else:
            heat = max(heat, 0.0)
        if payoff_pending is not None and payoff_t is None and t >= payoff_pending:
            do_payoff()
        t += dt
    for L in LEVERS:
        L.flash *= 0.85
    if payoff_t is None and full_t is None:
        heat = max(0.0, (BASIN.ratio - 0.8) / 0.2 * 0.6)
    if frame % 15 == 0:
        build_keys.append((t, progress()))
        if DEBUG and frame % 60 == 0:
            print(f"t={t:5.1f} n={len(p)} loads={[L.load for L in LEVERS]} ratio={[round(L.ratio, 2) for L in LEVERS]}")
    if PREVIEW and any(abs(t - pt) < 0.5 / FPS for pt in PREVIEW):
        draw(); surf.flush(); surf.write_to_png(f"prev_{t:05.1f}.png")
    if not SIM_ONLY:
        draw(); surf.flush()
        if first is None:
            first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if payoff_t is not None and t >= payoff_t + TAIL:
        break
    if t > float(os.environ.get("TSTOP", "80")):
        break

if ff:
    ff.stdin.close(); ff.wait()
tips = [(round(e[0], 1), e[2], e[3]) for e in events if e[1] == "tip"]
print("seed", SEED, "full", full_t and round(full_t, 2), "payoff", payoff_t and round(payoff_t, 2), "duration", round(t, 2),
      "drops", drop_k, "max balls", max_n, "tips", [L.tips for L in LEVERS])
print("L2/L3 tips:", [x for x in tips if x[1] >= 2])
print("music", song.recipe_str())
if DEBUG:
    print("lost", len(lost), lost[:60])
    print("push", pushlog)

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
