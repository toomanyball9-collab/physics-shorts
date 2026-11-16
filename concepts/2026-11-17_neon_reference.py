import math, sys, subprocess, wave
import numpy as np
import cairo
from scipy.spatial import cKDTree
import neon, music

# ---------------- settings ----------------
W, H, FPS = 1080, 1920, 60
SUB = 4
CX, CY, R = W / 2, 960, 470
SPEED = 520.0                 # constant ball speed
BALL_R = 14.0
PACK = 0.80                   # area fraction that counts as "completely full"
COOLDOWN = 0.5
AFTER_BURST = 2.2
MAX_T = 45.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
SIM_ONLY = "--sim" in sys.argv
OUT = "out_noaudio.mp4"
FONT = "Noto Sans CJK KR"

rng = np.random.default_rng(SEED)
CAP = int(PACK * (R / BALL_R) ** 2)
PAL = neon.PALETTES[sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "synthwave"]
SPR = neon.BallSprites(PAL["balls"], BALL_R)
song = music.Song(bpm=100, key="D", mode="major", progression="vi-IV-I-V", lead="pluck", seed=SEED)

a0 = rng.uniform(0, 2 * math.pi)
p = np.array([[CX, CY]])
v = np.array([[math.cos(a0) * SPEED, math.sin(a0) * SPEED]])
cd = np.array([0.0])
hue = np.array([0])

events = []      # (time, kind)
t = 0.0
burst_t = None
pop = 0.0
frags = None

surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
ff = None
if not SIM_ONLY:
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", OUT
    ], stdin=subprocess.PIPE)

def hsv(h, s=0.85, v_=1.0):
    i = int(h * 6) % 6; f = h * 6 - int(h * 6)
    p_, q, t_ = v_ * (1 - s), v_ * (1 - f * s), v_ * (1 - (1 - f) * s)
    return [(v_, t_, p_), (q, v_, p_), (p_, v_, t_), (p_, q, v_), (t_, p_, v_), (v_, p_, q)][i]

def text_center(txt, y, size, rgb, scale=1.0):
    ctx.save()
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size * scale)
    xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
    ctx.move_to(W / 2 - tw / 2 - xb, y)
    ctx.text_path(txt)
    ctx.set_source_rgba(0, 0, 0, 0.85); ctx.set_line_width(10 * scale)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke_preserve()
    ctx.set_source_rgb(*rgb); ctx.fill()
    ctx.restore()

bg = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
bc = cairo.Context(bg)
lg = cairo.LinearGradient(0, 0, 0, H)
lg.add_color_stop_rgb(0, 0.04, 0.05, 0.14)
lg.add_color_stop_rgb(1, 0.01, 0.01, 0.05)
bc.set_source(lg); bc.paint()

def draw():
    n = len(p)
    fill = n / CAP
    neon.background(ctx, W, H, PAL)
    ctx.save()
    shake = 0.0
    if burst_t is None and fill > 0.8:
        shake = 6 * ((fill - 0.8) / 0.2) ** 2
    if burst_t is not None:
        shake = 26 * math.exp(-(t - burst_t) * 6)
    if shake > 0:
        ctx.translate(rng.uniform(-shake, shake), rng.uniform(-shake, shake))
    if burst_t is None:
        neon.ring(ctx, CX, CY, R + 3, PAL["ring"], t, heat=max(0.0, (fill - 0.6) / 0.4))
    else:
        dt_b = t - burst_t
        sa = max(0.0, 0.7 - dt_b * 1.3)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*PAL["accent"], sa); ctx.set_line_width(22 * sa + 2)
            ctx.arc(CX, CY, R + 2200 * dt_b, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for fx, fy, ang, rot, span, _vx, _vy, _w in frags:
            ctx.save(); ctx.translate(fx, fy); ctx.rotate(rot)
            ctx.set_operator(cairo.OPERATOR_ADD)
            for w_, a_ in [(18, 0.15), (7, 0.9)]:
                ctx.set_source_rgba(*PAL["ring"], a_ * max(0, 1 - dt_b * 0.5)); ctx.set_line_width(w_)
                ctx.arc(-R * math.cos(ang), -R * math.sin(ang), R + 3, ang - span / 2, ang + span / 2); ctx.stroke()
            ctx.restore()
    vis = [(i, (x, y)) for i, (x, y) in enumerate(p) if -40 < x < W + 40 and -40 < y < H + 40]
    SPR.draw(ctx, [q for _, q in vis], [int(hue[i]) for i, _ in vis], glow=n < 1200)
    ctx.restore()
    if burst_t is None:
        text_center(f"{n:,}", 1660, 150, mix_white(PAL["accent"]), scale=1.0 + 0.2 * pop)
    else:
        fa = max(0.0, 0.45 - (t - burst_t) * 2.5)
        if fa > 0:
            ctx.set_source_rgba(1, 1, 1, fa); ctx.paint()

def mix_white(c):
    return neon.mix(c, (1, 1, 1), 0.6)

def do_burst():
    global burst_t, frags, v
    burst_t = t
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    radial = d / dist[:, None]
    jit = rng.uniform(-0.3, 0.3, len(p))
    c, s = np.cos(jit), np.sin(jit)
    radial = np.stack([radial[:, 0] * c - radial[:, 1] * s, radial[:, 0] * s + radial[:, 1] * c], 1)
    v = v * 0.3 + radial * (rng.uniform(250, 1100, len(p)) * (0.4 + 0.6 * dist / R))[:, None]
    frags = []
    N = 22
    for k in range(N):
        ang = 2 * math.pi * (k + 0.5) / N
        sp = rng.uniform(600, 1100)
        frags.append([CX + R * math.cos(ang), CY + R * math.sin(ang), ang, 0.0,
                      2 * math.pi / N * 0.85, math.cos(ang) * sp, math.sin(ang) * sp, rng.uniform(-5, 5)])
    song.accent(t)

def collide():
    """ball-ball: push apart + elastic exchange along the normal"""
    global p, v
    if len(p) < 2:
        return
    pairs = cKDTree(p).query_pairs(2 * BALL_R, output_type="ndarray")
    if len(pairs) == 0:
        return
    i, j = pairs[:, 0], pairs[:, 1]
    d = p[j] - p[i]
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    nrm = d / dist[:, None]
    over = (2 * BALL_R - dist) * 0.5
    corr = nrm * over[:, None]
    np.add.at(p, i, -corr)
    np.add.at(p, j, corr)
    rel = np.sum((v[j] - v[i]) * nrm, axis=1)
    app = rel < 0
    imp = nrm[app] * rel[app, None]
    np.add.at(v, i[app], imp)
    np.add.at(v, j[app], -imp)

frame = 0
dt = 1.0 / (FPS * SUB)
log_next = 0
while True:
    for _ in range(SUB):
        p += v * dt
        cd -= dt
        if burst_t is None:
            collide()
            n = len(p)
            d = p - (CX, CY)
            dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
            over = dist + BALL_R - R
            hit = np.where(over > 0)[0]
            if len(hit):
                nrm = d[hit] / dist[hit, None]
                p[hit] -= nrm * over[hit, None]
                vn = np.sum(v[hit] * nrm, axis=1)
                out = vn > 0
                v[hit[out]] -= 2 * vn[out, None] * nrm[out]
                ready = hit[cd[hit] <= 0]
                room = CAP - n
                if len(ready) and room > 0:
                    ready = ready[:room]
                    ang = rng.uniform(0.3, 0.8, len(ready)) * rng.choice([-1, 1], len(ready))
                    c, s_ = np.cos(ang), np.sin(ang)
                    vv = v[ready]
                    nv = np.stack([vv[:, 0] * c - vv[:, 1] * s_, vv[:, 0] * s_ + vv[:, 1] * c], 1)
                    nrm_r = nrm[np.searchsorted(hit, ready)]
                    p = np.vstack([p, p[ready] - nrm_r * BALL_R])
                    v = np.vstack([v, nv])
                    cd[ready] = COOLDOWN
                    cd = np.concatenate([cd, np.full(len(ready), COOLDOWN)])
                    hue = np.concatenate([hue, rng.integers(0, len(PAL['balls']), len(ready))])
                    song.note(t, pan=float((p[ready[0]][0] - CX) / R))
                    pop = 1.0
            # keep everyone moving at a steady pace
            sp = np.hypot(v[:, 0], v[:, 1]) + 1e-6
            v *= (SPEED / sp)[:, None]
            if len(p) >= CAP:
                do_burst()
        else:
            for f in frags:
                f[0] += f[5] * dt; f[1] += f[6] * dt; f[3] += f[7] * dt
        t += dt
    pop *= 0.85
    if not SIM_ONLY:
        draw(); surf.flush()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if SIM_ONLY and t >= log_next:
        print(f"t={t:5.1f}s balls={len(p)}"); log_next += 1
    if burst_t is not None and t >= burst_t + AFTER_BURST:
        break
    if t >= MAX_T:
        break

if ff:
    ff.stdin.close(); ff.wait()
print("duration", round(t, 2), "CAP", CAP, "burst_t", burst_t)

# ---------------- music ----------------
if not SIM_ONLY:
    song.render("audio.wav", t, build=lambda tt: min(1.0, tt / burst_t) if burst_t else 0.5)
