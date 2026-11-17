"""2026-11-18 18:00 — shrinking-arena: "Shrinking Cage"
A rotating neon cage shrinks a little on EVERY wall hit. It starts as a big triangle with one ball;
as it shrinks it gains a side (square, pentagon, hexagon) and a new ball drops in. Balls leave glowing
trails that paint spirograph patterns. The smaller the cage, the faster the hits — the music speeds up
by itself. At the end 7 balls are jammed in a tiny hexagon; the cage strains, heats red, shakes and
bursts on a bar line. The tail crossfades back to the opening frame for a clean loop.

usage: python3 concepts/2026-11-18_pm_shrinking_cage.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 4
CX, CY = W / 2, 930
BR = 22.0
A0 = 250.0                       # starting apothem (world px)
A_MIN = 3.08 * BR                # 7 balls hex-packed in a hexagon
A_FLOOR = A_MIN * 0.93
FINAL_A = A_MIN * 1.12
SCREEN_SPEED = 520.0
PAYOFF_TARGET = 61.0
TAIL = 3.0
SHRINK = float(os.environ.get("SHRINK", "0.0047"))
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
PAL = neon.PALETTES["sunset"]
MUSIC_SEED = 202611203
RECENT = [dict(genre="custom", bpm=100, key="C", mode="major", lead="sine"),
          dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass")]

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)
song = music.random_song(MUSIC_SEED, avoid=RECENT)

# phases: (apothem threshold, sides, balls)
PHASES = [(1e9, 3, 2), (228, 4, 3), (200, 5, 4), (168, 6, 5), (134, 6, 6), (104, 6, 7)]
TWISTS = [241, 214, 186, 151, 119]          # spin reversals between shape changes (a visible change every ~5 s)
CAGE_COLS = [PAL["balls"][2], PAL["balls"][1], PAL["balls"][0], PAL["balls"][3], PAL["ring"], PAL["balls"][3], PAL["accent"]]

def zoom_for(a):
    return (A0 / a) ** 0.8

# ---------------- state ----------------
a = A0
theta = rng.uniform(0, 2 * math.pi)
omega = 0.35
phase = 0
sides = 3
z = 1.0
a0_ = rng.uniform(0, 2 * math.pi)
p = np.array([[CX - 60.0, CY + 30.0], [CX + 70.0, CY - 20.0]])
v = np.array([[math.cos(a0_) * SCREEN_SPEED, math.sin(a0_) * SCREEN_SPEED],
              [-math.cos(a0_ + 0.9) * SCREEN_SPEED, -math.sin(a0_ + 0.9) * SCREEN_SPEED]])
col = np.array([0, 1])
cool = np.array([0.0, 0.0])
hits = 0
hit_flash = 0.0
heat = 0.0
final_t0 = None
final_dur = None
burst_pending = None
burst_t = None
frags = []          # [x, y, vx, vy, ang, len, rot, vrot, color, t0]  (world)
sparks = []         # [x, y, size, t0, color]  (world)
events = []
build_keys = []
t = 0.0

def normals():
    return [theta + 2 * math.pi * k / sides for k in range(sides)]

def corners(a_, th, n):
    rc = a_ / math.cos(math.pi / n)
    return [(CX + rc * math.cos(th + math.pi / n + 2 * math.pi * k / n),
             CY + rc * math.sin(th + math.pi / n + 2 * math.pi * k / n)) for k in range(n)]

def progress():
    if burst_t is not None:
        return 1.0
    if final_t0 is None:
        x = math.log((A0 - A_FLOOR) / max(a - A_FLOOR, 1e-3)) / math.log((A0 - A_FLOOR) / (FINAL_A - A_FLOOR))
        return 0.85 * min(1.0, x)
    return 0.85 + 0.15 * heat

def free_spot():
    for _ in range(200):
        r = rng.uniform(0, a * 0.55); ang = rng.uniform(0, 2 * math.pi)
        q = np.array([CX + r * math.cos(ang), CY + r * math.sin(ang)])
        if len(p) == 0 or np.min(np.hypot(*(p - q).T)) > 2 * BR + 2:
            return q
    return np.array([CX, CY])

def add_ball():
    global p, v, col, cool
    q = free_spot()
    ang = rng.uniform(0, 2 * math.pi)
    sp = SCREEN_SPEED / z
    p = np.vstack([p, q]); v = np.vstack([v, [math.cos(ang) * sp, math.sin(ang) * sp]])
    col = np.concatenate([col, [len(col) % len(PAL["balls"])]]); cool = np.concatenate([cool, [0.0]])
    sparks.extend([[q[0], q[1], rng.uniform(8, 18), t, PAL["accent"]] for _ in range(8)])
    song.sfx(t, "pop", float((q[0] - CX) / A0), 0.9)
    events.append((t, "ball", len(p)))

twist_i = 0

def advance_phase():
    global phase, sides, omega, twist_i
    while twist_i < len(TWISTS) and a <= TWISTS[twist_i]:
        twist_i += 1
        omega = -omega * 1.15
        song.sfx(t, "whoosh", 0.0, 0.6)
        events.append((t, "twist", twist_i))
    while phase + 1 < len(PHASES) and a <= PHASES[phase + 1][0]:
        phase += 1
        n_new, b_new = PHASES[phase][1], PHASES[phase][2]
        if n_new != sides:
            sides = n_new
            omega = -omega * 1.12
            song.sfx(t, "whoosh", 0.0, 0.8)
            events.append((t, "morph", sides))
        while len(p) < b_new:
            add_ball()

def do_burst():
    global burst_t, v
    burst_t = t
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    radial = d / dist[:, None]
    v = radial * rng.uniform(380, 760, len(p))[:, None] * (A0 / 430.0 + 0.4)
    pts = corners(a, theta, sides)
    for k in range(sides):
        x0, y0 = pts[k]; x1, y1 = pts[(k + 1) % sides]
        for m in range(3):
            fx = x0 + (x1 - x0) * (m + 0.5) / 3; fy = y0 + (y1 - y0) * (m + 0.5) / 3
            ang = math.atan2(y1 - y0, x1 - x0)
            out = math.atan2(fy - CY, fx - CX)
            sp = rng.uniform(500, 1000)
            frags.append([fx, fy, math.cos(out) * sp, math.sin(out) * sp, ang, math.hypot(x1 - x0, y1 - y0) / 3 * 0.9,
                          0.0, rng.uniform(-6, 6), neon.mix(CAGE_COLS[phase], (1, .2, .2), 0.7), t])
    for _ in range(70):
        ang = rng.uniform(0, 2 * math.pi); r = rng.uniform(0, a * 1.1)
        sparks.append([CX + r * math.cos(ang), CY + r * math.sin(ang), rng.uniform(10, 26), t, PAL["accent"]])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    events.append((t, "burst", 0))

def physics_step(dt):
    global p, v, a, hits, hit_flash, heat, final_t0, final_dur, burst_pending, theta
    theta += omega * dt
    p += v * dt
    if burst_t is not None:
        return
    cool[:] -= dt
    n = len(p)
    # ball-ball
    if n > 1:
        d = p[None, :, :] - p[:, None, :]
        dd = np.hypot(d[..., 0], d[..., 1]) + np.eye(n) * 1e9
        ii, jj = np.where(np.triu(dd < 2 * BR))
        for i, j in zip(ii, jj):
            if dd[i, j] < 1e-3:
                ang = rng.uniform(0, 2 * math.pi); nrm = np.array([math.cos(ang), math.sin(ang)])
            else:
                nrm = (p[j] - p[i]) / dd[i, j]
            over = min(2 * BR - dd[i, j], 3.0)
            p[i] -= nrm * over / 2; p[j] += nrm * over / 2
            rel = np.dot(v[j] - v[i], nrm)
            if rel < 0:
                v[i] += nrm * rel; v[j] -= nrm * rel
                song.sfx(t, "tick", float((p[i][0] - CX) / A0), 0.2)
    # cage walls (half-planes)
    rel_p = p - (CX, CY)
    for ang in normals():
        u = np.array([math.cos(ang), math.sin(ang)])
        dist = rel_p @ u
        over = dist + BR - a
        for i in np.where(over > 0)[0]:
            p[i] -= u * min(over[i], 4.0)
            vn = np.dot(v[i], u)
            if vn > 0:
                v[i] -= 2 * vn * u
                jit = rng.uniform(-0.08, 0.08); c, s = math.cos(jit), math.sin(jit)
                v[i] = [v[i][0] * c - v[i][1] * s, v[i][0] * s + v[i][1] * c]
                if cool[i] <= 0:
                    cool[i] = 0.04
                    hits += 1
                    hit_flash = 1.0
                    song.note(t, float(rel_p[i, 0] / A0 * 1.5))
                    hx, hy = p[i] + u * BR
                    sparks.append([hx, hy, rng.uniform(5, 10), t, CAGE_COLS[phase]])
                    if final_t0 is None:
                        a -= SHRINK * (a - A_FLOOR)
        rel_p = p - (CX, CY)
    advance_phase()
    if final_t0 is None and a <= FINAL_A and len(p) == 7:
        final_t0 = t
        final_dur = float(np.clip(PAYOFF_TARGET - t, 7.0, 12.0))
        events.append((t, "final", 0))
    if final_t0 is not None:
        heat = min(1.0, (t - final_t0) / final_dur)
        a = max(A_MIN, FINAL_A - (FINAL_A - A_MIN) * heat)      # the cage keeps squeezing
        if heat >= 1.0 and burst_pending is None:
            burst_pending = song.next_bar(t)
    target = SCREEN_SPEED / z
    sp = np.hypot(v[:, 0], v[:, 1]) + 1e-6
    v *= (target / sp)[:, None]

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
trail = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
tctx = cairo.Context(trail)
prev_screen = {}
first = None
sprite_cache = {}

def sprites_for(rpx):
    q = max(4, int(round(rpx)))
    if q not in sprite_cache:
        sprite_cache[q] = neon.BallSprites(PAL["balls"], q)
    return sprite_cache[q]

def S(x, y):
    return CX + (x - CX) * z, CY + (y - CY) * z

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gcol = neon.mix(PAL["accent"], (1.0, 0.3, 0.35), heat * 0.8)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 950)
    ga = (0.04 + 0.15 * pr + 0.03 * math.sin(t * 2.2))
    if burst_t is not None:
        ga *= math.exp(-(t - burst_t) * 1.5)
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    # trails (fade, then add this frame's segments)
    tctx.save(); tctx.set_operator(cairo.OPERATOR_DEST_OUT)
    tctx.set_source_rgba(0, 0, 0, 0.055 if burst_t is None else 0.15); tctx.paint(); tctx.restore()
    trail.flush()
    tarr = np.ndarray((H, W, 4), np.uint8, buffer=trail.get_data())
    tarr[tarr[:, :, 3] < 14] = 0          # 8-bit fading never reaches zero: clear the grey residue
    trail.mark_dirty()
    tctx.save(); tctx.set_operator(cairo.OPERATOR_ADD); tctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i, (x, y) in enumerate(p):
        sx, sy = S(x, y)
        c = PAL["balls"][int(col[i]) % len(PAL["balls"])]
        if i in prev_screen and burst_t is None:
            px_, py_ = prev_screen[i]
            if abs(px_ - sx) + abs(py_ - sy) < 120:
                for w_, a_ in ((14, 0.10), (4.5, 0.55)):
                    tctx.set_source_rgba(*c, a_); tctx.set_line_width(w_)
                    tctx.move_to(px_, py_); tctx.line_to(sx, sy); tctx.stroke()
        prev_screen[i] = (sx, sy)
    tctx.restore()

    ctx.save()
    shake = 0.0
    if burst_t is None and heat > 0.4:
        shake = 10 * ((heat - 0.4) / 0.6) ** 2
    if burst_t is not None:
        shake = 28 * math.exp(-(t - burst_t) * 6)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    ctx.set_source_surface(trail, 0, 0); ctx.paint()
    # cage
    if burst_t is None:
        pts = [S(x, y) for x, y in corners(a - 3.0 * hit_flash, theta, sides)]
        ccol = CAGE_COLS[phase]
        # morph flash
        mf = 0.0
        for et, kind, _ in events:
            if kind in ("morph", "ball", "twist") and 0 <= t - et < 0.5:
                mf = max(mf, 1 - (t - et) / 0.5)
        neon.polygon_ring(ctx, pts, neon.mix(ccol, (1, 1, 1), 0.35 * mf + 0.25 * hit_flash), heat=heat, t=t, width=5.0 + 2 * mf)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        for (x, y) in pts:
            gr = cairo.RadialGradient(x, y, 0, x, y, 22)
            gr.add_color_stop_rgba(0, 1, 1, 1, 0.75); gr.add_color_stop_rgba(1, 1, 1, 1, 0)
            ctx.set_source(gr); ctx.arc(x, y, 22, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
    # fragments
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for fx, fy, _vx, _vy, ang, ln, frot, _vr, fc, ft0 in frags:
        age = t - ft0; fa = max(0.0, 1 - age / 2.2)
        if fa <= 0: continue
        sx, sy = S(fx, fy)
        ctx.save(); ctx.translate(sx, sy); ctx.rotate(ang + frot)
        for w_, a_ in ((16, 0.18), (6, 0.9)):
            ctx.set_source_rgba(*fc, a_ * fa); ctx.set_line_width(w_)
            ctx.move_to(-ln * z / 2, 0); ctx.line_to(ln * z / 2, 0); ctx.stroke()
        ctx.restore()
    ctx.restore()
    # shockwave
    if burst_t is not None:
        age = t - burst_t
        if age < 1.2:
            aa = (1 - age / 1.2) * 0.8
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*PAL["accent"], aa); ctx.set_line_width(3 + 16 * aa)
            ctx.arc(CX, CY, a * z + 2000 * age, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    # balls
    spr = sprites_for(BR * z)
    pts_b = [S(x, y) for x, y in p]
    vis = [(q, int(c)) for q, c in zip(pts_b, col) if -80 < q[0] < W + 80 and -80 < q[1] < H + 80]
    spr.draw(ctx, [q for q, _ in vis], [c for _, c in vis])
    # sparks
    live = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = live
    groups = {}
    for x, y, sz, st, c in live:
        al = 1 - (t - st) / 0.5
        sx, sy = S(x, y)
        groups.setdefault((c, round(al, 1)), []).append((sx, sy, sz * (0.6 + al)))
    for (c, al), q in groups.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.4), alpha=al * 0.9)
    ctx.restore()
    # live counter: wall hits
    if counter and burst_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(110)
        txt = f"{hits:,}"
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1700)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix(CAGE_COLS[phase], (1, 1, 1), 0.55), (1, .3, .3), heat)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(22); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if burst_t is not None:
        fa = max(0.0, 0.5 - (t - burst_t) * 2.5)
        if fa > 0:
            ctx.set_source_rgba(1, 1, 1, fa); ctx.paint()
        end = burst_t + TAIL
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
log = []
while True:
    for _ in range(SUB):
        physics_step(dt)
        if burst_pending is not None and burst_t is None and t >= burst_pending:
            do_burst()
        for f in frags:
            f[0] += f[2] * dt; f[1] += f[3] * dt; f[6] += f[7] * dt
        t += dt
    zt = zoom_for(a) if burst_t is None else zoom_for(a) * 0.85
    z += (zt - z) * 0.05
    hit_flash *= 0.8
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 300 == 0:
        log.append((round(t), round(a), sides, len(p), hits))
    if not SIM_ONLY:
        draw(); surf.flush()
        if first is None:
            first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if burst_t is not None and t >= burst_t + TAIL:
        break
    if t > 85:
        break

if ff:
    ff.stdin.close(); ff.wait()
print("seed", SEED, "log(t,a,sides,balls,hits)", log)
print("phase events", [(round(e[0], 1), e[1], e[2]) for e in events if e[1] in ("morph", "ball", "final", "twist")])
print("final_t0", final_t0 and round(final_t0, 1), "burst", burst_t and round(burst_t, 2), "duration", round(t, 2), "hits", hits)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
