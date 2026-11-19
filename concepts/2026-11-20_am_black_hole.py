"""2026-11-20 08:00 — orbits: "Black Hole"
A tiny black hole sits in the centre of a neon ring.
  Rule 1: a launcher riding the ring fires a ball on every beat (1 → 2 → 4 per beat as the song builds).
  Rule 2: the black hole pulls every ball (real 1/r^2 gravity) and swallows any ball that touches it.
          Every ball it swallows makes it bigger (radius grows with mass, like a real horizon) and its pull stronger.
Balls swirl, slingshot and bounce off the ring (each bounce = a note). The more it eats, the faster it eats.
Tension: the bigger the hole, the harder its tide pulls on the ring — the ring heats red, cracks and shakes.
Payoff (on a bar line): the ring tears, every fragment and ball spirals in, the hole flares white (on the beat),
then the picture crossfades back to the opening frame for a clean loop.

usage: python3 concepts/2026-11-20_am_black_hole.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 8
CX, CY, R = W / 2, 960, 450.0
BR = 11.0
RH0 = 16.0
R_CRIT = float(os.environ.get("R_CRIT", "160"))
K_GROW = float(os.environ.get("K_GROW", "0.8"))       # px of horizon radius per swallowed ball
GM_PER_PX = float(os.environ.get("GMK", "2.0e5"))      # GM = GM_PER_PX * r_h (Schwarzschild: r_s ∝ M)
SPEED = 520.0
AIM = float(os.environ.get("AIM", "1.2"))             # launch angle spread off the radial (rad)
AIM0 = float(os.environ.get("AIM0", "0.15"))
VMAX = 1500.0
TAIL = 1.9
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
RATE_STEPS = [(0.0, 1), (float(os.environ.get("T2", "10")), 2), (float(os.environ.get("T3", "26")), 4)]

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)
song = music.Song.from_genre("cinematic", seed=202611203)        # 78bpm A# minor harp arp, key lift
PAL = dict(neon.PALETTES["ocean"]); PAL["bg"] = ((0.01, 0.02, 0.07), (0.00, 0.00, 0.02))
COLS = PAL["balls"]
RING_COL = (0.45, 0.70, 1.0)

# ---------------- state ----------------
p = np.zeros((0, 2)); v = np.zeros((0, 2)); col = np.zeros(0, int); bid = np.zeros(0, int)
next_id = 0
t = 0.0
rh = RH0
eaten = 0
launched = 0
next_shot = 0.25
launcher_a = -math.pi / 2
heat = 0.0
tear_pending = None
tear_t = None
flash_t = None
frags, sparks, streaks, events, build_keys = [], [], [], [], []
hit_cool = {}
last_eat_sfx = -1.0
gulp = 0.0
eat_rate = 0.0            # smoothed swallows per second (drives disk colour)
trails = {}

def shots_per_beat(tt):
    r = 1
    for t0, k in RATE_STEPS:
        if tt >= t0: r = k
    return r

def progress():
    if tear_t is not None:
        return 1.0
    return min(1.0, 0.22 * min(1, t / 10) + 0.78 * (rh - RH0) / (R_CRIT - RH0))

def add_ball(x, y, vx, vy, c):
    global p, v, col, bid, next_id
    p = np.vstack([p, [x, y]]); v = np.vstack([v, [vx, vy]])
    col = np.concatenate([col, [c]]); bid = np.concatenate([bid, [next_id]]); next_id += 1

def remove(mask_keep):
    global p, v, col, bid
    p, v, col, bid = p[mask_keep], v[mask_keep], col[mask_keep], bid[mask_keep]

def fire():
    global launched
    a = launcher_a
    ux, uy = math.cos(a), math.sin(a)
    off = rng.uniform(AIM0, AIM) * (1 if rng.random() < 0.5 else -1)
    da = a + math.pi + off
    x, y = CX + ux * (R - BR - 4), CY + uy * (R - BR - 4)
    add_ball(x, y, SPEED * math.cos(da), SPEED * math.sin(da), launched % len(COLS))
    launched += 1
    song.sfx(t, "tick", float(ux), 0.4)
    events.append((t, "shot", a))

def gm():
    return GM_PER_PX * rh

def swallow(idx):
    """Balls that touch the horizon disappear into it; the hole grows."""
    global rh, eaten, last_eat_sfx, gulp
    for i in idx:
        d = p[i] - (CX, CY)
        ang = math.atan2(d[1], d[0])
        streaks.append([ang, float(np.hypot(*d)), t, int(col[i])])
        eaten += 1
        rh += K_GROW * (RH0 / rh) ** 0.15
        gulp = min(1.0, gulp + 0.35)
        events.append((t, "eat", ang))
    if len(idx) and t - last_eat_sfx > 0.09:
        last_eat_sfx = t
        d = p[idx[0]] - (CX, CY)
        song.sfx(t, "zap", float(d[0] / R), 0.22 + 0.04 * min(len(idx), 4))

TEAR_N = 30

def do_tear():
    global tear_t
    tear_t = t
    for m in range(TEAR_N):
        ac = 2 * math.pi * (m + 0.5) / TEAR_N
        ox, oy = math.cos(ac), math.sin(ac)
        frags.append([CX + R * ox, CY + R * oy, -ox * rng.uniform(40, 120), -oy * rng.uniform(40, 120),
                      ac, 2 * math.pi / TEAR_N * 0.85, 0.0, rng.uniform(-3, 3), True])
    for _ in range(70):
        a = rng.uniform(0, 2 * math.pi)
        sparks.append([CX + R * math.cos(a), CY + R * math.sin(a), rng.uniform(10, 24), t, (1, 0.6, 0.5)])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    song.sfx(t + 0.05, "whoosh", 0.0, 0.9)
    events.append((t, "tear", 0))

def physics_step(dt):
    global p, v, heat, tear_pending
    n = len(p)
    G = gm() * (1.0 if tear_t is None else 1.0 + 7.0 * min(1.0, (t - tear_t) / 0.6))
    if n:
        d = p - (CX, CY)
        r2 = d[:, 0] ** 2 + d[:, 1] ** 2 + 30.0 ** 2
        r = np.sqrt(r2)
        acc = -G * d / (r2 * r)[:, None]
        if tear_t is not None:     # everything spirals in after the ring tears
            tang = np.stack([-d[:, 1], d[:, 0]], 1) / r[:, None]
            acc += tang * 260.0 - d / r[:, None] * 420.0
        v += acc * dt
        sp = np.hypot(v[:, 0], v[:, 1])
        lim = np.minimum(1.0, (VMAX * (1.6 if tear_t is not None else 1.0)) / (sp + 1e-6))
        v *= lim[:, None]
        p += v * dt
        # ring
        if tear_t is None:
            d = p - (CX, CY)
            dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
            over = dist + BR - R
            for i in np.where(over > 0)[0]:
                nrm = d[i] / dist[i]
                p[i] -= nrm * over[i]
                vn = float(np.dot(v[i], nrm))
                if vn > 0:
                    v[i] -= 2 * vn * nrm
                    key = int(bid[i])
                    if vn > 120 and t - hit_cool.get(key, -9) > 0.14:
                        hit_cool[key] = t
                        song.note(t, float(nrm[0]), vel=min(1.0, 0.45 + vn / 1200))
                        events.append((t, "hit", (float(p[i, 0] + nrm[0] * BR), float(p[i, 1] + nrm[1] * BR), int(col[i]))))
        # horizon
        d = p - (CX, CY)
        dist = np.hypot(d[:, 0], d[:, 1])
        inside = dist < rh + BR * 0.6
        if inside.any():
            swallow(list(np.where(inside)[0]))
            remove(~inside)
    if tear_t is None:
        heat = float(np.clip((rh - 0.55 * R_CRIT) / (0.45 * R_CRIT), 0, 1))
        if rh >= R_CRIT and tear_pending is None:
            tear_pending = song.next_bar(t)
            events.append((t, "crit", 0))

def collide():
    if len(p) < 2:
        return
    tree = cKDTree(p)
    pairs = tree.query_pairs(2 * BR, output_type="ndarray")
    if len(pairs) == 0:
        return
    i, j = pairs[:, 0], pairs[:, 1]
    d = p[j] - p[i]
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    nrm = d / dist[:, None]
    over = 2 * BR - dist
    np.add.at(p, i, -nrm * (over * 0.5)[:, None])
    np.add.at(p, j, nrm * (over * 0.5)[:, None])
    rel = np.sum((v[j] - v[i]) * nrm, 1)
    app = rel < 0
    imp = rel[app][:, None] * nrm[app]
    np.add.at(v, i[app], imp)
    np.add.at(v, j[app], -imp)

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = neon.BallSprites(COLS, BR, glow=2.8, glow_alpha=0.5)

def disk_color():
    """Accretion disk colour follows how fast it is eating: ice blue -> violet -> gold -> white-hot."""
    k = min(1.0, eat_rate / 9.0)
    stops = [(0.45, 0.75, 1.0), (0.70, 0.45, 1.0), (1.0, 0.62, 0.30), (1.0, 0.95, 0.85)]
    x = k * (len(stops) - 1); i = min(int(x), len(stops) - 2)
    return neon.mix(stops[i], stops[i + 1], x - i)

def draw_hole(ctx, r_h, dc, swirl):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    # outer glow
    g = cairo.RadialGradient(CX, CY, r_h, CX, CY, r_h * 4.2 + 60)
    g.add_color_stop_rgba(0, *dc, 0.38); g.add_color_stop_rgba(0.3, *dc, 0.12); g.add_color_stop_rgba(1, *dc, 0)
    ctx.set_source(g); ctx.arc(CX, CY, r_h * 4.2 + 60, 0, 2 * math.pi); ctx.fill()
    # swirling accretion arcs
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for k in range(9):
        rr = r_h * (1.25 + 0.17 * k) + 4
        a0 = swirl * (1.6 - 0.12 * k) + k * 1.9
        span = 1.3 + 0.5 * math.sin(k * 2.3)
        for w_, a_ in ((10, 0.06), (3.2, 0.30 - 0.025 * k)):
            ctx.set_source_rgba(*neon.mix(dc, (1, 1, 1), 0.25), a_)
            ctx.set_line_width(w_ * (0.6 + r_h / 120))
            ctx.new_path(); ctx.arc(CX, CY, rr, a0, a0 + span); ctx.stroke()
            ctx.new_path(); ctx.arc(CX, CY, rr, a0 + math.pi, a0 + math.pi + span * 0.7); ctx.stroke()
    ctx.restore()
    # event horizon (true black) + photon ring
    ctx.set_source_rgb(0, 0, 0); ctx.arc(CX, CY, r_h, 0, 2 * math.pi); ctx.fill()
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for w_, a_ in ((12, 0.10), (5, 0.35), (1.8, 0.95)):
        ctx.set_source_rgba(*neon.mix(dc, (1, 1, 1), 0.55), a_); ctx.set_line_width(w_)
        ctx.new_path(); ctx.arc(CX, CY, r_h + 1.5, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()

CRACKS = [(a, L) for a, L in zip(np.linspace(0, 2 * math.pi, 17)[:-1] + 0.21, [1, .7, .85, .6, .9, .65, .8, .55, 1, .75, .6, .9, .7, .8, .6, .85])]

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    dc = disk_color()
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 980)
    ga = 0.03 + 0.10 * pr
    rg.add_color_stop_rgba(0, *dc, ga); rg.add_color_stop_rgba(1, *dc, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 0.0
    if tear_t is None and heat > 0.45:
        shake = 7 * ((heat - 0.45) / 0.55) ** 2
    if tear_t is not None:
        shake = 18 * math.exp(-(t - tear_t) * 4)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    # ring (pulled slightly inward by the tide as the hole grows)
    if tear_t is None:
        squeeze = 10 * heat ** 2
        neon.ring(ctx, CX, CY, R + 3 - squeeze, RING_COL, t, heat=heat)
        if heat > 0.15:
            hh = (heat - 0.15) / 0.85
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ncr = int(math.ceil(hh * len(CRACKS)))
            for j, (ang, L) in enumerate(CRACKS[:ncr]):
                grow = min(1.0, hh * len(CRACKS) - j)
                ln = 62 * L * grow
                ux, uy = math.cos(ang), math.sin(ang); px_, py_ = -uy, ux
                rr0 = R + 3 - squeeze
                pts = [(rr0, 0), (rr0 - ln * 0.35, 6), (rr0 - ln * 0.7, -5), (rr0 - ln, 2)]
                for w_, a_ in ((7, 0.18), (2.2, 0.85)):
                    ctx.set_source_rgba(1.0, 0.5 + 0.3 * (1 - heat), 0.45, a_ * grow); ctx.set_line_width(w_)
                    ctx.move_to(CX + ux * pts[0][0] + px_ * pts[0][1], CY + uy * pts[0][0] + py_ * pts[0][1])
                    for r_, o_ in pts[1:]:
                        ctx.line_to(CX + ux * r_ + px_ * o_, CY + uy * r_ + py_ * o_)
                    ctx.stroke()
            ctx.restore()
        # launcher
        a = launcher_a
        ex, ey = CX + math.cos(a) * (R + 3), CY + math.sin(a) * (R + 3)
        last_shot = max([e[0] for e in events[-6:] if e[1] == "shot"] or [-9])
        pulse = max(0.0, 1 - (t - last_shot) / 0.22)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        gr = cairo.RadialGradient(ex, ey, 0, ex, ey, 60 + 24 * pulse)
        gr.add_color_stop_rgba(0, 1, 1, 1, 0.45 + 0.5 * pulse); gr.add_color_stop_rgba(0.4, *RING_COL, 0.25 + 0.3 * pulse); gr.add_color_stop_rgba(1, *RING_COL, 0)
        ctx.set_source(gr); ctx.arc(ex, ey, 84, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        ctx.save(); ctx.translate(ex, ey); ctx.rotate(a + math.pi)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        for w_, a_ in ((14, 0.25), (6, 0.95)):
            ctx.set_source_rgba(*neon.mix(RING_COL, (1, 1, 1), 0.7), a_); ctx.set_line_width(w_)
            ctx.move_to(-4, -30); ctx.line_to(26 + 6 * pulse, 0); ctx.line_to(-4, 30); ctx.stroke()
        ctx.restore()
    else:
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for fx, fy, _vx, _vy, ac, span, frot, _vr, alive in frags:
            if not alive: continue
            rr_f = math.hypot(fx - CX, fy - CY)
            a_f = math.atan2(fy - CY, fx - CX)
            sp_f = span * min(1.6, R / max(rr_f, 1.0)) ** 0.5
            for w_, a_ in ((16, 0.15), (6, 0.9)):
                ctx.set_source_rgba(*neon.mix(RING_COL, (1, .3, .25), 0.7), a_); ctx.set_line_width(w_)
                ctx.new_path(); ctx.arc(CX, CY, max(rr_f, rh + 4), a_f - sp_f / 2, a_f + sp_f / 2); ctx.stroke()
        ctx.restore()
    # ring hit flashes
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, info in events[-160:]:
        if kind == "hit" and 0 <= t - et < 0.3:
            x, y, c = info; age = (t - et) / 0.3
            ctx.set_source_rgba(*neon.mix(COLS[c], (1, 1, 1), 0.4), 0.55 * (1 - age)); ctx.set_line_width(2.5)
            ctx.new_path(); ctx.arc(x, y, 8 + 22 * age, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    # trails
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for i in range(len(p)):
        tr = trails.get(int(bid[i]))
        if not tr or len(tr) < 3: continue
        c = COLS[col[i]]
        ctx.set_source_rgba(*c, 0.22); ctx.set_line_width(BR * 0.9)
        ctx.move_to(*tr[0])
        for q in tr[1:]: ctx.line_to(*q)
        ctx.line_to(p[i, 0], p[i, 1]); ctx.stroke()
    ctx.restore()
    # swallowed balls stretching into the horizon (spaghettification)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    live = []
    for s in streaks:
        ang, r0, st, c = s
        age = (t - st) / 0.35
        if age >= 1: continue
        live.append(s)
        a1 = ang + 0.9 * age
        rr = rh + (r0 - rh) * (1 - age) * 0.4
        ctx.set_source_rgba(*neon.mix(COLS[c], (1, 1, 1), 0.3), 0.8 * (1 - age)); ctx.set_line_width(BR * 0.8 * (1 - age) + 1)
        ctx.new_path(); ctx.arc(CX, CY, max(rh + 2, rr), ang, a1); ctx.stroke()
    streaks[:] = live
    ctx.restore()
    # balls
    if len(p):
        SPR.draw(ctx, [(x, y) for x, y in p], list(col), glow=len(p) < 500)
    # black hole on top
    draw_hole(ctx, rh + 3 * gulp, dc, t * (1.2 + rh / 60))
    # sparks
    live = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = live
    for x, y, sz, st, c in live:
        al = 1 - (t - st) / 0.5
        neon.sparkles(ctx, [(x, y, sz * (0.6 + al))], neon.mix(c, (1, 1, 1), 0.4), alpha=al * 0.9)
    ctx.restore()
    # live counter: swallowed balls
    if counter and flash_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(110)
        txt = f"{eaten:,}"
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1640)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix(dc, (1, 1, 1), 0.45), (1, .3, .3), heat * 0.7)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(22); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if flash_t is not None:
        dt_f = t - flash_t
        sa = max(0.0, 0.8 - dt_f * 1.1)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*neon.mix(dc, (1, 1, 1), 0.6), sa); ctx.set_line_width(26 * sa + 2)
            ctx.arc(CX, CY, rh + 2000 * dt_f, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        fa = max(0.0, 0.85 - dt_f * 2.2)
        if fa > 0:
            ctx.set_source_rgba(1, 1, 1, fa); ctx.paint()
        xf = (t - (flash_t + TAIL - 1.3)) / 1.3
        if xf > 0 and first is not None:
            ctx.set_source_surface(first, 0, 0); ctx.paint_with_alpha(min(1.0, xf) ** 1.4)

ff = None
if not SIM_ONLY:
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", OUT
    ], stdin=subprocess.PIPE)

# opening: a handful of balls already swirling around the tiny hole
for k_ in range(7):
    a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(160, 380)
    sp = rng.uniform(380, 520)
    tang = a + math.pi / 2 + rng.uniform(-0.6, 0.6)
    add_ball(CX + rr * math.cos(a), CY + rr * math.sin(a), sp * math.cos(tang), sp * math.sin(tang), k_ % len(COLS))
# ...and a few on low orbits, so swallows happen in the first seconds (first one inside ~1 s)
add_ball(CX + 250, CY - 240, -330, 300, 1)
add_ball(CX - 330, CY + 170, 300, -40, 2)
add_ball(CX + 60, CY + 400, 130, -250, 0)

dt = 1.0 / (FPS * SUB)
frame = 0
log = []
prev_eaten = 0
while True:
    for s_ in range(SUB):
        if tear_t is None:
            launcher_a += dt * 0.55
        gap = song.beat / shots_per_beat(t)
        if tear_pending is None and tear_t is None and t >= next_shot:
            fire()
            next_shot = round((t + gap) / gap) * gap
            if next_shot <= t: next_shot += gap
        physics_step(dt)
        if s_ % 2 == 0:
            collide()
        if tear_pending is not None and tear_t is None and t >= tear_pending:
            do_tear()
        if tear_t is not None:
            for f in frags:
                if not f[8]: continue
                dx, dy = f[0] - CX, f[1] - CY
                rr = math.hypot(dx, dy) + 1e-6
                k = min(1.0, (t - tear_t) / 0.5)
                f[2] += (-dx / rr * 900 * k - dy / rr * 380 * k) * dt
                f[3] += (-dy / rr * 900 * k + dx / rr * 380 * k) * dt
                f[0] += f[2] * dt; f[1] += f[3] * dt
                f[6] = math.atan2(f[1] - CY, f[0] - CX) - f[4]
                if rr < rh + 10:
                    f[8] = False
                    rh_new = rh + 0.0
                    streaks.append([math.atan2(dy, dx), rr, t, 0])
            if flash_t is None and t >= tear_t + 2 * song.beat:
                flash_t = t
                song.sfx(t, "thump", 0.0, 1.0)
                song.sfx(t + 0.01, "chime", 0.0, 0.8)
                song.accent(t)
                events.append((t, "flash", 0))
                remove(np.zeros(len(p), bool))
                for f in frags: f[8] = False
        t += dt
    # smoothed swallows per second
    eat_rate += ((eaten - prev_eaten) * FPS - eat_rate) * (1.0 / (FPS * 1.2))
    prev_eaten = eaten
    gulp *= 0.88
    for i in range(len(p)):
        k = int(bid[i])
        tr = trails.setdefault(k, [])
        tr.append((float(p[i, 0]), float(p[i, 1])))
        if len(tr) > 7: tr.pop(0)
    if frame % 120 == 0:
        alive = set(int(b) for b in bid)
        for k in list(trails):
            if k not in alive: del trails[k]
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 300 == 0:
        log.append((round(t), len(p), round(rh), eaten))
    if not SIM_ONLY:
        draw(); surf.flush()
        if first is None:
            first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if flash_t is not None and t >= flash_t + TAIL:
        break
    if t > 85:
        break

if ff:
    ff.stdin.close(); ff.wait()
print("seed", SEED, "log(t,balls,rh,eaten)", log)
print("crit", [round(e[0], 1) for e in events if e[1] == "crit"], "tear", tear_t and round(tear_t, 2),
      "flash", flash_t and round(flash_t, 2), "duration", round(t, 2), "launched", launched, "eaten", eaten)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
