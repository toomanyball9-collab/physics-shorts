"""2026-11-28 18:00 — multiplier-gates (new family): "Multiplier Rain"
A tall neon tank. A dropper at the top drops a ball on the beat (1 -> 2 -> 4 -> 8 per beat, switching on bar
lines). Three sliding neon GATES hang in the tank: a ball that falls through a gate is multiplied by the
number of pips on it (2, 3, 2) and takes the gate's colour; a ball that falls through all three becomes gold
(x12). Balls that miss the gates stay pale. The tank fills with colour strata showing how lucky each drop was.
When the settled pile reaches the fill line under the gates the tank is completely packed: the floor heats red
and shakes, and on the bar it gives way under the weight — everything falls out of the bottom.
Counter = balls in play. Sound: wall/floor bounces = music (song.note); multiplying = pop; floor break = shatter.

usage: python3 concepts/2026-11-28_pm_multiplier.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 6
ITERS = int(os.environ.get("ITERS", "8"))
CL, CR = 150.0, 930.0
CXC = (CL + CR) / 2
BR = float(os.environ.get("BR", "14"))
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
# random_song(2026112888, avoid=all posted recipes + 11-28 08:00 kpop_bright) -> dreamwave 89 D# lydian celesta
MUSIC_SEED = int(os.environ.get("MSEED", "2026112888"))
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
          dict(genre="kpop_bright", bpm=117, key="E", mode="major", lead="pluck")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)
BEAT = song.beat
BAR = song.chord_len

# colours: 0 pale (no gate), 1 cyan (gate 1), 2 violet (gate 2), 3 pink (gate 3), 4 gold (all three)
BCOLS = [(0.70, 0.80, 0.95), (0.25, 0.90, 1.0), (0.62, 0.42, 1.0), (1.0, 0.40, 0.75), (1.0, 0.82, 0.30)]
PAL = {"bg": ((0.02, 0.015, 0.07), (0.00, 0.00, 0.03)), "ring": (0.8, 0.85, 1.0), "balls": BCOLS, "accent": (1, 1, 1)}
TANK = (0.62, 0.70, 1.0)
HOT = (1.0, 0.22, 0.25)

DROP_Y = 200.0
FLOOR_Y = 1790.0
FILL_Y = float(os.environ.get("FILLY", "990"))
TIERS = [float(x) for x in os.environ.get("TIERS", "8,22,40").split(",")]
TIER_BARS = [math.ceil(x / BAR) for x in TIERS]
START_EVERY = float(os.environ.get("START", "1"))      # beats between drops in the first tier
# gates: y, half-width, multiplier, colour, slide centre, amplitude, period (beats)
GATES = [dict(y=440.0, hw=float(os.environ.get("HW1", "150")), n=2, c=1, A=240.0, T=6.0),
         dict(y=650.0, hw=float(os.environ.get("HW2", "110")), n=3, c=2, A=270.0, T=5.0),
         dict(y=860.0, hw=float(os.environ.get("HW3", "140")), n=2, c=3, A=250.0, T=7.0)]

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 777)
wall_rng = np.random.default_rng(SEED + 31)


def nozzle_x(tt):
    return CXC + 280 * math.sin(2 * math.pi * tt / (9 * BEAT))


# phases: the very first ball falls through all three gates (12 balls inside the first ~1.5 s)
def _cross_time(y, v0=60.0):
    d = y - DROP_Y - 10
    return (-v0 + math.sqrt(v0 * v0 + 2 * G * d)) / G
for gt in GATES:
    tc = _cross_time(gt["y"]) + 0.02
    gt["ph"] = math.asin(0.0) - 2 * math.pi * tc / (gt["T"] * BEAT)
GATES[1]["ph"] += math.pi            # middle gate slides the other way (still centred at the crossing)


def gate_x(k, tt):
    g = GATES[k]
    return CXC + g["A"] * math.sin(2 * math.pi * tt / (g["T"] * BEAT) + g["ph"])


p = np.zeros((0, 2)); v = np.zeros((0, 2)); col = np.zeros(0, int); passed = np.zeros(0, int)
note_cool = np.zeros(0)
t = 0.0
heat = 0.0
full_t = None
payoff_pending = None
payoff_t = None
shards, sparks, events, build_keys = [], [], [], []
gate_flash = [0.0] * len(GATES)
next_drop = 0.0
drop_k = 0
thump_cool = -9.0
max_n = 0
mult_count = [0, 0, 0]


def per_beat(tt):
    b = int(tt / BAR)
    n = 1.0 / START_EVERY
    for tb in TIER_BARS:
        if b >= tb:
            n *= 2
    return n


def progress():
    if payoff_t is not None:
        return 1.0
    return float(np.clip(0.08 + 0.72 * fill_now[0] + 0.2 * min(1, t / 60), 0, 1))


fill_now = [0.0]


def add_balls(xy, vv, c, ps):
    global p, v, col, passed, note_cool
    p = np.vstack([p, xy]); v = np.vstack([v, vv])
    col = np.append(col, c); passed = np.append(passed, ps)
    note_cool = np.append(note_cool, np.full(len(xy), -9.0))


def release():
    global next_drop, drop_k
    while t >= next_drop and payoff_t is None and full_t is None:
        x = nozzle_x(next_drop) + (rng.uniform(-3, 3) if drop_k else 0.0)
        add_balls(np.array([[x, DROP_Y + 10]]), np.array([[rng.uniform(-20, 20) if drop_k else 0.0, 60.0]]), [0], [0])
        drop_k += 1
        next_drop += BEAT / per_beat(next_drop + 1e-6)


def gates_step(pp):
    """balls that crossed a gate line (downwards) inside its span are multiplied."""
    global p, v, col, passed
    new_xy, new_v, new_c, new_ps = [], [], [], []
    for k, g in enumerate(GATES):
        gx = gate_x(k, t)
        bit = 1 << k
        hit = np.where((pp[:, 1] < g["y"]) & (p[:, 1] >= g["y"]) & (np.abs(p[:, 0] - gx) < g["hw"]) & ((passed & bit) == 0))[0]
        for i in hit:
            passed[i] |= bit
            c = 4 if passed[i] == 7 else g["c"]
            col[i] = c
            n = g["n"]
            x0, y0 = p[i]
            offs = (np.arange(n) - (n - 1) / 2) * (2 * BR + 2)
            spread = (np.arange(n) - (n - 1) / 2) * float(os.environ.get("SPREAD", "110"))
            nx0 = np.clip(x0 + offs[0], CL + BR, CR - BR)
            p[i, 0] = nx0
            v[i, 0] += spread[0]
            pp[i] = p[i] - v[i] * DT                 # PBD velocity = the new velocity (shift is not a speed)
            for j in range(1, n):
                new_xy.append([np.clip(x0 + offs[j], CL + BR, CR - BR), y0 + rng.uniform(-2, 2)])
                new_v.append([v[i, 0] - spread[0] + spread[j] + rng.uniform(-15, 15), v[i, 1]])
                new_c.append(c); new_ps.append(passed[i])
            gate_flash[k] = 1.0
            mult_count[k] += 1
            song.sfx(t, "pop", float((x0 - CXC) / 420), 0.35 + 0.1 * k)
            events.append((t, "mult", (k, float(x0), float(y0))))
            if len(sparks) < 400:
                for _ in range(3):
                    sparks.append([x0 + fx_rng.normal(0, 12), y0, fx_rng.uniform(6, 13), t, BCOLS[c]])
    if new_xy:
        add_balls(np.array(new_xy), np.array(new_v), new_c, new_ps)


def floor_surface(x):
    sag = 14.0 * max(0.0, (heat - 0.6) / 0.4) ** 1.5
    u = (x - CXC) / ((CR - CL) / 2)
    return FLOOR_Y + sag * (1 - u * u)


def physics_step(dt):
    global p, v, col, passed, note_cool, full_t, payoff_pending, thump_cool, heat, max_n
    n = len(p)
    if not n:
        return
    v[:, 1] += G * dt
    v -= v * 0.12 * dt
    sp = np.hypot(v[:, 0], v[:, 1])
    fast = sp > 1250
    if fast.any():
        v[fast] *= (1250 / sp[fast])[:, None]
    pp = p.copy()
    p += v * dt
    if payoff_t is None:
        gates_step(pp)
        n = len(p)
        pp = np.vstack([pp, p[len(pp):] - v[len(pp):] * dt])
    # wall impacts -> notes
    lo = np.where((p[:, 0] < CL + BR) & (v[:, 0] < -200))[0]
    hi = np.where((p[:, 0] > CR - BR) & (v[:, 0] > 200))[0]
    for idx, s in ((lo, 1), (hi, -1)):
        for ii in idx:
            if t - note_cool[ii] > 0.3:
                note_cool[ii] = t
                song.note(t, -0.8 * s, vel=min(1.0, 0.35 + abs(v[ii, 0]) / 1200))
    floor_on = payoff_t is None
    if floor_on:
        hit = np.where((p[:, 1] > FLOOR_Y - BR - 2) & (v[:, 1] > 250))[0]
        for ii in hit:
            if t - note_cool[ii] > 0.3:
                note_cool[ii] = t
                song.note(t, float((p[ii, 0] - CXC) / 420), vel=min(1.0, 0.35 + v[ii, 1] / 1800))
    WJ = wall_rng.uniform(0.0, 2.5, n)
    pairs = cKDTree(p).query_pairs(2 * BR + 1.0, output_type="ndarray") if n > 1 else np.zeros((0, 2), int)
    i, j = (pairs[:, 0], pairs[:, 1]) if len(pairs) else (None, None)
    for it in range(ITERS):
        if i is not None:
            d = p[j] - p[i]
            dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
            over = 2 * BR - dist
            m = over > 0
            if m.any():
                corr = (d[m] / dist[m, None]) * (over[m] * 0.5)[:, None]
                np.add.at(p, i[m], -corr); np.add.at(p, j[m], corr)
        wl = p[:, 0] < CL + BR; wr = p[:, 0] > CR - BR
        if wl.any():
            p[wl, 0] = CL + BR + WJ[wl]
        if wr.any():
            p[wr, 0] = CR - BR - WJ[wr]
        if floor_on:
            fy = floor_surface(p[:, 0]) - BR
            below = p[:, 1] > fy
            if below.any():
                p[below, 1] = fy[below]
    nv = (p - pp) / dt
    if i is not None:
        cnt = np.bincount(np.concatenate([i, j]), minlength=n)
        calm = (cnt >= 3) & (payoff_t is None)
        nv[calm] *= 1 - float(os.environ.get("CALM", "6")) * dt
        # balls landing on the pile: a soft tick now and then
        if len(i) and t - thump_cool > 0.12:
            dv = v[:, 1] - nv[:, 1]
            land = np.where(dv > 700)[0]
            if len(land) > 3:
                thump_cool = t
                song.sfx(t, "tick", 0.0, min(0.35, 0.1 + len(land) / 60))
    if floor_on:
        onf = p[:, 1] >= floor_surface(p[:, 0]) - BR - 0.5
        nv[onf, 0] *= 0.92
        nv[onf, 1] = np.minimum(nv[onf, 1], -0.15 * v[onf, 1])
    nv[:, 1] = np.maximum(nv[:, 1], -350.0)          # nothing gets flung upward out of the pile
    sp = np.hypot(nv[:, 0], nv[:, 1])
    fast = sp > 1400
    if fast.any():
        nv[fast] *= (1400 / sp[fast])[:, None]
    v = nv
    max_n = max(max_n, n)
    # fill level of the settled pile
    if payoff_t is None:
        # completely packed = the pile reaches the fill line across the WHOLE tank (2nd-lowest of 8 columns)
        sl = (np.hypot(v[:, 0], v[:, 1]) < 70) & (p[:, 1] > FILL_Y - 250)
        tops = []
        for c0 in np.linspace(CL, CR, 9)[:-1]:
            m = sl & (p[:, 0] >= c0) & (p[:, 0] < c0 + (CR - CL) / 8)
            ys = np.sort(p[m, 1])
            tops.append(ys[min(2, len(ys) - 1)] if len(ys) >= 3 else FLOOR_Y)
        topy = sorted(tops)[-2]
        fill = (FLOOR_Y - topy) / (FLOOR_Y - FILL_Y)
        fill_now[0] = float(np.clip(fill, 0, 1))
        heat = max(heat, float(np.clip((fill - 0.6) / 0.38, 0, 1)))
        if DEBUG and int(t * 360) % 360 == 0:
            print(f"t={t:.1f} n={n} fill={fill:.2f} drops={drop_k}")
        if fill >= 0.985 and full_t is None:
            full_t = t
            payoff_pending = song.next_bar(t + 0.05)
            song.sfx(t, "chime", 0.0, 0.6)
    keep = p[:, 1] < H + 200
    if not keep.all():
        p, v, col, passed, note_cool = p[keep], v[keep], col[keep], passed[keep], note_cool[keep]
    for s in shards:
        s["vy"] += G * 0.8 * dt
        s["x"] += s["vx"] * dt; s["y"] += s["vy"] * dt; s["a"] += s["va"] * dt


def do_payoff():
    global payoff_t
    payoff_t = t
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    xs = np.linspace(CL, CR, 19)
    c = neon.mix(TANK, HOT, heat)
    for a, b in zip(xs[:-1], xs[1:]):
        xm = (a + b) / 2
        u = (xm - CXC) / ((CR - CL) / 2)
        shards.append(dict(x=xm, y=floor_surface(xm) + 8, vx=fx_rng.uniform(-150, 150) + u * 140, vy=fx_rng.uniform(-200, 60),
                           a=0.0, va=fx_rng.uniform(-7, 7), L=(b - a) * 0.9, th=16, c=c, t0=t))
    for _ in range(70):
        sparks.append([fx_rng.uniform(CL, CR), FLOOR_Y + fx_rng.normal(0, 10), fx_rng.uniform(8, 20), t, c])
    # the pile loosens as it drops out of the tank
    v[:, 0] += rng.uniform(-90, 90, len(v))
    v[:, 1] += rng.uniform(0, 120, len(v))
    events.append((t, "payoff", 0))


# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = neon.BallSprites(BCOLS, BR, glow=2.6, glow_alpha=0.5)
STARS = [(fx_rng.uniform(0, W), fx_rng.uniform(0, H), fx_rng.uniform(0.6, 2.0), fx_rng.uniform(0.05, 0.22)) for _ in range(220)]


def tube(pts, rgb, alpha=1.0, width=5.0, glowk=1.0):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for w, a in [(40, 0.04), (24, 0.08), (13, 0.15), (7, 0.30)]:
        ctx.set_source_rgba(*rgb, a * alpha * glowk); ctx.set_line_width(w * width / 5)
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_source_rgba(*neon.mix(rgb, (1, 1, 1), 0.6), 0.95 * alpha); ctx.set_line_width(width * 0.9)
    ctx.move_to(*pts[0])
    for q in pts[1:]:
        ctx.line_to(*q)
    ctx.stroke(); ctx.restore()


def draw_gate(k, ox):
    g = GATES[k]
    gx = gate_x(k, t) + ox
    y = g["y"]
    c = BCOLS[g["c"]]
    f = gate_flash[k]
    x0, x1 = gx - g["hw"], gx + g["hw"]
    # membrane: soft colour field the balls fall through
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    gr = cairo.LinearGradient(0, y - 46, 0, y + 46)
    gr.add_color_stop_rgba(0, *c, 0.0); gr.add_color_stop_rgba(0.5, *c, 0.16 + 0.22 * f); gr.add_color_stop_rgba(1, *c, 0.0)
    ctx.set_source(gr); ctx.rectangle(x0, y - 46, x1 - x0, 92); ctx.fill()
    ctx.restore()
    tube([(x0, y), (x1, y)], neon.mix(c, (1, 1, 1), 0.3 * f), 1.0, 4.5, 1.0 + 1.2 * f)
    # end posts
    for x in (x0, x1):
        tube([(x, y - 22), (x, y + 22)], c, 1.0, 4.0)
    # pips = multiplier
    n = g["n"]
    for q in range(n):
        px = gx + (q - (n - 1) / 2) * 34
        py = y - 30
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        rg = cairo.RadialGradient(px, py, 0, px, py, 20)
        rg.add_color_stop_rgba(0, *c, 0.8); rg.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(rg); ctx.arc(px, py, 20, 0, 2 * math.pi); ctx.fill(); ctx.restore()
        ctx.save(); ctx.set_source_rgba(1, 1, 1, 0.95); ctx.arc(px, py, 7 + 2 * f, 0, 2 * math.pi); ctx.fill(); ctx.restore()


def draw_dropper(ox):
    x = nozzle_x(t) + ox
    y = DROP_Y
    c = (0.85, 0.9, 1.0)
    pulse = 0.0
    if drop_k:
        last = next_drop - BEAT / per_beat(max(0.0, next_drop - 1e-3))
        pulse = max(0.0, 1 - (t - last) / 0.15)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.RadialGradient(x, y, 0, x, y, 80)
    g.add_color_stop_rgba(0, *c, 0.25 + 0.3 * pulse); g.add_color_stop_rgba(1, *c, 0)
    ctx.set_source(g); ctx.arc(x, y, 80, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.5), 0.95); ctx.set_line_width(5); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(x - 34, y - 30); ctx.line_to(x - 12, y); ctx.line_to(x + 12, y); ctx.line_to(x + 34, y - 30); ctx.stroke()
    ctx.set_source_rgba(*c, 0.25); ctx.set_line_width(2)
    ctx.move_to(CXC - 310 + ox, y - 30); ctx.line_to(CXC + 310 + ox, y - 30); ctx.stroke()


def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gc = neon.mix((0.5, 0.45, 1.0), HOT, max(0.0, heat - 0.5) / 0.5 * 0.6)
    rg = cairo.RadialGradient(W / 2, H * 0.6, 0, W / 2, H * 0.6, 1100)
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
    if heat > 0.75 and payoff_t is None:
        shake = 3.5 * (heat - 0.75) / 0.25
    if payoff_t is not None:
        shake = max(shake, 16 * math.exp(-(t - payoff_t) * 5))
    ox = fx_rng.uniform(-shake, shake) if shake > 0 else 0.0
    oy = fx_rng.uniform(-shake, shake) if shake > 0 else 0.0
    ctx.save(); ctx.translate(0, oy)
    # fill line (dashed) just under the lowest gate
    ctx.save(); ctx.set_dash([14, 12], -t * 20); ctx.set_line_width(2.5)
    ctx.set_source_rgba(*neon.mix(TANK, HOT, heat), 0.35 + 0.4 * heat)
    ctx.move_to(CL + 10 + ox, FILL_Y); ctx.line_to(CR - 10 + ox, FILL_Y); ctx.stroke(); ctx.restore()
    # tank walls (bottom part heats with the load)
    wc = neon.mix(TANK, HOT, max(0.0, heat - 0.3) / 0.7)
    pulse = 1.0 + (0.6 * (0.5 + 0.5 * math.sin(t * 22)) * (heat - 0.8) / 0.2 if heat > 0.8 else 0)
    for x in (CL - 7, CR + 7):
        tube([(x + ox, 110), (x + ox, FILL_Y - 40)], TANK, 0.9, 4.5)
        tube([(x + ox, FILL_Y - 40), (x + ox, FLOOR_Y + 12)], wc, 1.0, 5.0, pulse)
    if payoff_t is None:
        pts = [(x + ox, floor_surface(x) + 10) for x in np.linspace(CL - 7, CR + 7, 24)]
        tube(pts, wc, 1.0, 6.0, pulse)
    draw_dropper(ox)
    for k in range(len(GATES)):
        draw_gate(k, ox)
    vis = p[:, 1] < H + 40
    SPR.draw(ctx, [(x + ox, y) for x, y in p[vis]], list(col[vis]))
    # shards
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    keep = []
    for s in shards:
        age = t - s["t0"]
        if age > 2.5 or s["y"] > H + 100:
            continue
        keep.append(s)
        a = max(0.0, 1 - age / 2.5)
        x, y = s["x"] + ox, s["y"]
        dx, dy = math.cos(s["a"]) * s["L"] / 2, math.sin(s["a"]) * s["L"] / 2
        for w_, al in ((s["th"] + 16, 0.12), (s["th"] + 4, 0.35), (max(2.0, s["th"] * 0.4), 0.9)):
            ctx.set_source_rgba(*neon.mix(s["c"], (1, 1, 1), 0.3 if al > 0.5 else 0), al * a); ctx.set_line_width(w_)
            ctx.move_to(x - dx, y - dy); ctx.line_to(x + dx, y + dy); ctx.stroke()
    shards[:] = keep
    ctx.restore()
    lv = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = lv
    by = {}
    for x, y, sz, st, c in lv:
        al = 1 - (t - st) / 0.5
        by.setdefault((c, round(al, 1)), []).append((x + ox, y - 40 * (t - st), sz * (0.5 + al)))
    for (c, al), q in by.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.5), alpha=al * 0.9)
    ctx.restore()
    if counter and payoff_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(84)
        txt = f"{len(p)}"
        xb, yb, tw, th_, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1888)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix((0.8, 0.85, 1.0), HOT, heat * 0.6), (1, 1, 1), 0.3)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(18); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.92); ctx.fill()
        ctx.restore()
    if payoff_t is not None:
        dtp = t - payoff_t
        fa = max(0.0, 0.5 - dtp * 2.8)
        if fa > 0:
            ctx.set_source_rgba(1, 1, 1, fa); ctx.paint()
        if dtp < 1.2:
            a = 1 - dtp / 1.2
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*BCOLS[4], 0.7 * a); ctx.set_line_width(4 + 16 * a)
            ctx.new_path(); ctx.arc(W / 2, FLOOR_Y, 60 + 1300 * dtp, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
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

frame = 0
while True:
    for _ in range(SUB):
        release()
        physics_step(dt)
        if payoff_pending is not None and payoff_t is None and t >= payoff_pending:
            do_payoff()
        t += dt
    for k in range(len(GATES)):
        gate_flash[k] *= 0.82
    if frame % 15 == 0:
        build_keys.append((t, progress()))
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
    if t > 80:
        break

if ff:
    ff.stdin.close(); ff.wait()
print("seed", SEED, "full", full_t and round(full_t, 2), "payoff", payoff_t and round(payoff_t, 2), "duration", round(t, 2),
      "drops", drop_k, "max balls", max_n, "mults", mult_count, "gold", int((col == 4).sum()))
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
