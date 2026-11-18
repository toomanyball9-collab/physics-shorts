"""2026-11-19 18:00 — escape (variation): "Hex Escape"
Same feel as Ring Escape, new arena: one ball inside 12 rotating neon HEXAGONS nested in each other,
each with a gap in one side. Every time a ball slips through a gap, that hexagon shatters into glowing
sticks and the escaping ball spawns 2 more. The camera zooms out layer by layer. The last hexagon is
sealed: every hit cracks it, it heats red and shakes, and the pressure from inside bursts it outward
on a bar line. The tail crossfades back to the opening frame for a clean loop.

usage: python3 concepts/2026-11-19_pm_hex_escape.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 4
CX, CY = W / 2, 930
BR = 12.0                         # ball radius (world)
N_GAP = 12                        # rings with gaps
R0, R_FINAL = 74.0, 440.0       # apothems of the inner / outer hexagon
RADII = [R0 + (R_FINAL - R0) * k / N_GAP for k in range(N_GAP + 1)]   # last = sealed ring
SCREEN_SPEED = 540.0
PAYOFF_TARGET = 61.5
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 12
AUDIO_ONLY = "--audio" in sys.argv      # simulate + render audio.wav only (physics is identical)
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
PAL = neon.PALETTES["synthwave"]
MUSIC_SEED = 202611400
SKIN = "orb"

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)   # drawing-only randomness (keeps physics identical to --sim)
RECENT = [dict(genre="custom", bpm=100, key="C", mode="major", lead="sine"),
          dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass"),
          dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep"),
          dict(genre="tropical", bpm=112, key="A", mode="major", lead="marimba")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)
NS = 6
GAP_MAX = math.radians(50)

def zoom_for(r):
    return (150 + 0.67 * r) / r

# per-ring gap: opens linearly from "ball-sized" so the escape time is Rayleigh-distributed
# around the target interval (survival = exp(-(age/T)^2), mean = 0.886 T)
TARGET = [5.0 - 2.0 * k / (N_GAP - 1) for k in range(N_GAP)]
T_K = [x / 0.886 for x in TARGET]
GAP_RATE, BALL_ANG = [], []
for k in range(N_GAP):
    n_k = 1 + 2 * k
    h_k = float(os.environ.get("GK", "0.8")) * SCREEN_SPEED / (1.3 * (150 + 0.67 * RADII[k]))
    GAP_RATE.append(4 * math.pi / (n_k * h_k * T_K[k] ** 2))
    BALL_ANG.append(2 * math.asin(BR / RADII[k]) * 0.7)
GAP0 = [BALL_ANG[k] + GAP_RATE[k] * 0.35 * T_K[k] for k in range(N_GAP)]   # how waiting rings look
OMEGA = [(0.55 + 0.5 * rng.random()) * (1 if k % 2 == 0 else -1) for k in range(N_GAP + 1)]
ROT0 = [rng.uniform(0, 2 * math.pi) for _ in range(N_GAP + 1)]

def ring_color(k):
    cols = PAL["balls"]
    x = k / N_GAP * (len(cols) - 1)
    i = min(int(x), len(cols) - 2)
    return neon.mix(cols[i], cols[i + 1], x - i)

# ---------------- state ----------------
a0 = rng.uniform(0, 2 * math.pi)
z = zoom_for(R0)
spd = SCREEN_SPEED / z
p = np.array([[CX + 10.0, CY - 5.0]])
v = np.array([[math.cos(a0) * spd, math.sin(a0) * spd]])
col = np.array([0])
cur = 0                      # index of the innermost remaining ring
ring_t0 = 0.0                # when the current ring became the boundary
alive = [True] * (N_GAP + 1)
frags = []                   # [x, y, vx, vy, ang_center, span, radius, rot, vrot, color, t0]
sparks = []                  # [x, y, size, t0, color]
cracks = []                  # angles (relative to ring rotation) on the final ring
hit_flash = 0.0
heat = 0.0
final_t0 = None
final_dur = None
burst_pending = None
burst_t = None
events = []                  # (t, kind, k)
build_keys = []              # (t, build)
t = 0.0

def rot(k, tt):
    return ROT0[k] + OMEGA[k] * tt

def gap_now(k, tt):
    if k >= N_GAP:
        return 0.0
    age = tt - ring_t0
    return min(GAP_MAX, BALL_ANG[k] + GAP_RATE[k] * min(age, 3.0 * T_K[k]))

def progress():
    if burst_t is not None:
        return 1.0
    if cur < N_GAP:
        return 0.85 * (cur + min(1.0, (t - ring_t0) / T_K[cur]) * 0.5) / N_GAP
    return 0.85 + 0.15 * heat

def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi

def spawn_from(i, n_new):
    global p, v, col
    ps, vs, cs = [], [], []
    for j in range(n_new):
        ang = rng.uniform(0.5, 1.4) * (1 if j % 2 == 0 else -1)
        c, s = math.cos(ang), math.sin(ang)
        vx, vy = v[i]
        vs.append([vx * c - vy * s, vx * s + vy * c])
        dx, dy = p[i][0] - CX, p[i][1] - CY
        dl = math.hypot(dx, dy) + 1e-6
        tx, ty = -dy / dl, dx / dl                       # tangential direction
        off = (2 * BR + 2) * (1 if j % 2 == 0 else -1)
        ps.append([p[i][0] + tx * off - dx / dl * 2, p[i][1] + ty * off - dy / dl * 2])
        cs.append(int(rng.integers(len(PAL["balls"]))))
    p = np.vstack([p, ps]); v = np.vstack([v, vs]); col = np.concatenate([col, cs])

def hex_path_pts(a, rr, g):
    """open hexagon outline (world coords) with a gap of angular width g centred on edge 0 (normal at rr)"""
    ux, uy = math.cos(rr), math.sin(rr)
    tx, ty = -uy, ux
    mx, my = CX + a * ux, CY + a * uy
    rc = a / math.cos(math.pi / NS)
    verts = [(CX + rc * math.cos(rr + math.pi / NS + 2 * math.pi * m / NS), CY + rc * math.sin(rr + math.pi / NS + 2 * math.pi * m / NS))
             for m in range(NS)]
    if g <= 0:
        return verts + [verts[0]]
    lg = a * math.tan(g / 2)
    return [(mx + tx * lg, my + ty * lg)] + verts + [(mx - tx * lg, my - ty * lg)]

def boundary_r(a, rel):
    """distance from centre to the hexagon side along polar angle rel (relative to edge-0 normal)"""
    sec = 2 * math.pi / NS
    x = (rel + sec / 2) % sec - sec / 2
    return a / math.cos(x)

def add_sticks(pts, per_edge, sp_rng, sp_mul, color, tt):
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        for m in range(per_edge):
            fa, fb = m / per_edge, (m + 1) / per_edge
            ax_, ay_ = x0 + (x1 - x0) * fa, y0 + (y1 - y0) * fa
            bx_, by_ = x0 + (x1 - x0) * fb, y0 + (y1 - y0) * fb
            mx, my = (ax_ + bx_) / 2, (ay_ + by_) / 2
            out = math.atan2(my - CY, mx - CX)
            sp = rng.uniform(*sp_rng) * sp_mul
            frags.append([mx, my, math.cos(out) * sp, math.sin(out) * sp, math.atan2(by_ - ay_, bx_ - ax_),
                          math.hypot(bx_ - ax_, by_ - ay_) * 0.88, 0.0, 0.0, rng.uniform(-4, 4), color, tt])

def shatter(k, tt, pan):
    alive[k] = False
    r = RADII[k]; g = gap_now(k, tt); rr = rot(k, tt)
    add_sticks(hex_path_pts(r, rr, g), 2 + k // 4, (160, 420), 1 + k * 0.05, ring_color(k), tt)
    song.sfx(tt, "shatter", pan, 0.6)
    song.sfx(tt + 0.02, "chime", pan, 0.7)
    events.append((tt, "break", k))

def do_burst():
    global burst_t, v
    burst_t = t
    r = RADII[N_GAP]
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    radial = d / dist[:, None]
    v = v * 0.3 + radial * rng.uniform(280, 820, len(p))[:, None]
    add_sticks(hex_path_pts(r, rot(N_GAP, t), 0), 4, (600, 1200), 1.0, neon.mix(PAL["ring"], (1, .2, .2), 0.7), t)
    for _ in range(60):
        a = rng.uniform(0, 2 * math.pi)
        rb = boundary_r(r, a - rot(N_GAP, t))
        sparks.append([CX + rb * math.cos(a), CY + rb * math.sin(a), rng.uniform(10, 26), t, PAL["accent"]])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    alive[N_GAP] = False
    events.append((t, "burst", N_GAP))

def physics_step(dt):
    global p, v, cur, ring_t0, hit_flash, heat, final_t0, final_dur, burst_pending, z
    p += v * dt
    if burst_t is not None:
        return
    # ball-ball contacts (light)
    n = len(p)
    if n > 1:
        d = p[None, :, :] - p[:, None, :]
        dd = np.hypot(d[..., 0], d[..., 1]) + np.eye(n) * 1e9
        ii, jj = np.where(np.triu(dd < 2 * BR))
        for i, j in zip(ii, jj):
            if dd[i, j] < 1e-3:
                a_ = rng.uniform(0, 2 * math.pi); nrm = np.array([math.cos(a_), math.sin(a_)])
            else:
                nrm = (p[j] - p[i]) / dd[i, j]
            over = min(2 * BR - dd[i, j], 2.0)
            p[i] -= nrm * over / 2; p[j] += nrm * over / 2
            rel = np.dot(v[j] - v[i], nrm)
            if rel < 0:
                v[i] += nrm * rel; v[j] -= nrm * rel
                song.sfx(t, "tick", float((p[i][0] - CX) / 500), 0.25)
    k = cur
    r = RADII[k]
    rr = rot(k, t)
    g = gap_now(k, t)
    bh = math.asin(BR / r)
    d = p - (CX, CY)
    escaped = None
    for m in range(NS):
        ang_m = rr + 2 * math.pi * m / NS
        u = np.array([math.cos(ang_m), math.sin(ang_m)])
        proj = d @ u
        for i in np.where(proj + BR > r)[0]:
            if m == 0 and k < N_GAP:
                rel = wrap(math.atan2(d[i, 1], d[i, 0]) - rr)
                if abs(rel) < g / 2 - bh * 0.7 or proj[i] > r:
                    if proj[i] > r + BR * 0.3 and escaped is None:
                        escaped = i
                    continue
            p[i] -= u * (proj[i] + BR - r)
            d[i] = p[i] - (CX, CY)
            vn = np.dot(v[i], u)
            if vn > 0:
                v[i] -= 2 * vn * u
                jit = rng.uniform(-0.12, 0.12)
                c, s_ = math.cos(jit), math.sin(jit)
                v[i] = [v[i][0] * c - v[i][1] * s_, v[i][0] * s_ + v[i][1] * c]
                pan = float(d[i, 0] / r)
                song.note(t, pan)
                hit_flash = 1.0
                hx, hy = p[i] + u * BR
                sparks.append([hx, hy, rng.uniform(6, 12), t, ring_color(k)])
                if k == N_GAP:
                    cracks.append(wrap(math.atan2(hy - CY, hx - CX) - rr))
    if escaped is not None:
        pan = float(d[escaped, 0] / r)
        shatter(k, t, pan)
        sparks.extend([[p[escaped][0], p[escaped][1], rng.uniform(10, 22), t, PAL["accent"]] for _ in range(6)])
        spawn_from(escaped, 2)
        song.sfx(t + 0.05, "pop", pan, 0.8)
        cur += 1
        ring_t0 = t
        if cur == N_GAP:
            final_t0 = t
            final_dur = float(np.clip(PAYOFF_TARGET - t, 7.5, 14.0))
            events.append((t, "final", cur))
    if cur == N_GAP and final_t0 is not None:
        heat = min(1.0, (t - final_t0) / final_dur)
        if heat >= 1.0 and burst_pending is None:
            burst_pending = song.next_bar(t)
    # keep a steady on-screen pace
    target = SCREEN_SPEED / z
    sp = np.hypot(v[:, 0], v[:, 1]) + 1e-6
    v *= (target / sp)[:, None]

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
sprite_cache = {}

def sprites_for(rpx):
    q = max(4, int(round(rpx)))
    if q not in sprite_cache:
        sprite_cache[q] = neon.SkinSprites(PAL["balls"], q, skin=SKIN)
    return sprite_cache[q]

def S(x, y):
    return CX + (x - CX) * z, CY + (y - CY) * z

def arc_ring(cx, cy, R, a0, a1, rgb, alpha=1.0, heat_=0.0, width=5.0, glow=1.0):
    c = neon.mix(rgb, (1.0, 0.18, 0.22), heat_)
    pulse = 1.0 + heat_ * 0.6 * (0.5 + 0.5 * math.sin(t * 26))
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for w, a in [(46, 0.05), (28, 0.09), (16, 0.16), (9, 0.35)]:
        ctx.set_source_rgba(*c, a * pulse * alpha * glow); ctx.set_line_width(w * pulse)
        ctx.new_path(); ctx.arc(cx, cy, R, a0, a1); ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.65), 0.95 * alpha); ctx.set_line_width(width)
    ctx.new_path(); ctx.arc(cx, cy, R, a0, a1); ctx.stroke(); ctx.restore()

def hex_ring(a_px, rr, g, rgb, alpha=1.0, heat_=0.0, width=5.0, glow=1.0):
    pts = [(CX + (x - CX) * 1.0, CY + (y - CY) * 1.0) for x, y in hex_path_pts(a_px, rr, g)]
    c = neon.mix(rgb, (1.0, 0.18, 0.22), heat_)
    pulse = 1.0 + heat_ * 0.6 * (0.5 + 0.5 * math.sin(t * 26))
    def path():
        ctx.new_path(); ctx.move_to(*pts[0])
        for q in pts[1:]: ctx.line_to(*q)
        if g <= 0: ctx.close_path()
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for w, a in [(46, 0.05), (28, 0.09), (16, 0.16), (9, 0.35)]:
        ctx.set_source_rgba(*c, a * pulse * alpha * glow); ctx.set_line_width(w * pulse); path(); ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.65), 0.95 * alpha); ctx.set_line_width(width); path(); ctx.stroke()
    ctx.restore()
    return pts

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    # breathing centre glow that intensifies with the build
    gcol = neon.mix(PAL["accent"], (1.0, 0.3, 0.35), heat * 0.8)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 900)
    ga = 0.04 + 0.16 * pr + 0.03 * math.sin(t * 2.0)
    if burst_t is not None:
        ga *= math.exp(-(t - burst_t) * 1.5)
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 0.0
    if burst_t is None and heat > 0.45:
        shake = 9 * ((heat - 0.45) / 0.55) ** 2
    if burst_t is not None:
        shake = 28 * math.exp(-(t - burst_t) * 6)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    # rings (outer first)
    for k in range(N_GAP, -1, -1):
        if not alive[k]:
            continue
        R = RADII[k] * z
        if R > 1400:
            continue
        rr = rot(k, t)
        is_cur = k == cur
        alpha = 1.0 if is_cur else max(0.25, 0.75 - 0.08 * (k - cur))
        glow = 1.0 + (0.6 * hit_flash if is_cur else 0.0)
        if k == N_GAP:
            hex_ring(R, rr, 0, PAL["ring"], alpha, heat if is_cur else 0.0, 6.0, glow)
            if cracks:
                ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_width(2.2)
                cc = neon.mix((1, 1, 1), (1, .35, .3), heat)
                for j, ca in enumerate(cracks[-260:]):
                    a = ca + rr
                    rb = boundary_r(R, ca)
                    L = 10 + 26 * heat * ((j * 37) % 11) / 10
                    ux, uy = math.cos(a), math.sin(a)
                    px_, py_ = -uy, ux
                    wob = ((j * 53) % 7 - 3) * 2.0
                    ctx.set_source_rgba(*cc, 0.55)
                    ctx.move_to(CX + ux * (rb - L), CY + uy * (rb - L))
                    ctx.line_to(CX + ux * (rb - L / 2) + px_ * wob, CY + uy * (rb - L / 2) + py_ * wob)
                    ctx.line_to(CX + ux * (rb + L * 0.4), CY + uy * (rb + L * 0.4))
                    ctx.stroke()
                ctx.restore()
        else:
            g = gap_now(k, t) if is_cur else BALL_ANG[k]
            pts = hex_ring(R, rr, g, ring_color(k), alpha, 0.0, 5.0, glow)
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            for ex, ey in (pts[0], pts[-1]):
                gr = cairo.RadialGradient(ex, ey, 0, ex, ey, 18)
                gr.add_color_stop_rgba(0, 1, 1, 1, 0.8 * alpha); gr.add_color_stop_rgba(1, 1, 1, 1, 0)
                ctx.set_source(gr); ctx.arc(ex, ey, 18, 0, 2 * math.pi); ctx.fill()
            ctx.restore()
    # flying fragments
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for fx, fy, _vx, _vy, ang, ln, _u1, frot, _vr, fc, ft0 in frags:
        age = t - ft0
        fa = max(0.0, 1 - age / 2.2)
        if fa <= 0:
            continue
        sx, sy = S(fx, fy)
        ctx.save(); ctx.translate(sx, sy); ctx.rotate(ang + frot)
        for w_, a_ in [(16, 0.16), (6, 0.9)]:
            ctx.set_source_rgba(*fc, a_ * fa); ctx.set_line_width(w_)
            ctx.move_to(-ln * z / 2, 0); ctx.line_to(ln * z / 2, 0); ctx.stroke()
        ctx.restore()
    ctx.restore()
    # shockwaves for each break and the burst
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, k in events:
        if kind not in ("break", "burst"):
            continue
        age = t - et
        dur = 0.7 if kind == "break" else 1.2
        if 0 <= age < dur:
            a = (1 - age / dur) * (0.5 if kind == "break" else 0.8)
            c = ring_color(k) if kind == "break" else PAL["accent"]
            ctx.set_source_rgba(*c, a); ctx.set_line_width(3 + 16 * a)
            aw = RADII[k] * z + (500 if kind == "break" else 2200) * age
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            pts_ = [(CX + (x - CX) * 1.0, CY + (y - CY) * 1.0) for x, y in hex_path_pts(aw, rot(k, et), 0)]
            ctx.new_path(); ctx.move_to(*pts_[0])
            for q in pts_[1:]: ctx.line_to(*q)
            ctx.close_path(); ctx.stroke()
    ctx.restore()
    # balls
    spr = sprites_for(BR * z)
    pts = [S(x, y) for x, y in p]
    vis = [(q, int(c)) for q, c in zip(pts, col) if -60 < q[0] < W + 60 and -60 < q[1] < H + 60]
    spr.draw(ctx, [q for q, _ in vis], [c for _, c in vis])
    # sparks
    live = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = live
    by_col = {}
    for x, y, sz, st, c in live:
        a = 1 - (t - st) / 0.5
        sx, sy = S(x, y)
        by_col.setdefault((c, round(a, 1)), []).append((sx, sy, sz * (0.6 + a)))
    for (c, a), pts_ in by_col.items():
        neon.sparkles(ctx, pts_, neon.mix(c, (1, 1, 1), 0.4), alpha=a * 0.9)
    ctx.restore()
    # live counter: rings left
    if counter and burst_t is None:
        left = sum(alive)
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(120)
        txt = str(left)
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1690)
        ctx.text_path(txt)
        cc = neon.mix(ring_color(min(cur, N_GAP)), (1, 1, 1), 0.55)
        cc = neon.mix(cc, (1, .3, .3), heat)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(22); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if burst_t is not None:
        fa = max(0.0, 0.5 - (t - burst_t) * 2.5)
        if fa > 0:
            ctx.set_source_rgba(1, 1, 1, fa); ctx.paint()
        # loop: crossfade back to the opening frame
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
while True:
    for _ in range(SUB):
        physics_step(dt)
        if burst_pending is not None and burst_t is None and t >= burst_pending:
            do_burst()
        for f in frags:
            f[0] += f[2] * dt; f[1] += f[3] * dt; f[7] += f[8] * dt
        t += dt
    # smooth camera zoom toward the current boundary ring
    zt = zoom_for(RADII[min(cur, N_GAP)])
    if burst_t is not None:
        zt = zoom_for(R_FINAL) * 0.92
    z += (zt - z) * 0.035
    hit_flash *= 0.82
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if not SIM_ONLY:
        draw(); surf.flush()
        if first is None:
            first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if burst_t is not None and t >= burst_t + TAIL:
        break
    if t > 80:
        break

if ff:
    ff.stdin.close(); ff.wait()
brk = [round(e[0], 1) for e in events if e[1] == "break"]
print("seed", SEED, "breaks", brk)
print("intervals", [round(b - a, 1) for a, b in zip([0] + brk, brk)])
print("final_t0", final_t0 and round(final_t0, 1), "burst", burst_t and round(burst_t, 2), "duration", round(t, 2), "balls", len(p))
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
