"""2026-11-21 08:00 — escape (variation): "Colour Gate"
Ring Escape's structure with a new, visible rule: 12 rotating neon rings, each gap is a coloured GATE
(a glowing membrane in pink / gold / mint / blue). A ball changes colour every time it bounces
(pink → gold → mint → blue → pink …). It can only pass a gate of its OWN colour; any other colour
bounces off the membrane. Passing a gate shatters that ring and the escaping ball spawns 2 more.
The camera zooms out ring by ring. The last ring is sealed: every hit heats it (red, glow pulse,
shake — no crack lines), and the pressure from inside bursts it outward on a bar line.
Tail crossfades back to the opening frame for a clean loop.

usage: python3 concepts/2026-11-21_am_color_gate.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 4
CX, CY = W / 2, 930
BR = 12.0
N_GAP = 12
R0, R_FINAL = 74.0, 450.0
RADII = [R0 + (R_FINAL - R0) * k / N_GAP for k in range(N_GAP + 1)]
SCREEN_SPEED = 540.0
PAYOFF_TARGET = 61.0
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 54
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
COLS = [(1.0, 0.28, 0.62), (1.0, 0.80, 0.22), (0.25, 1.0, 0.62), (0.30, 0.58, 1.0)]   # pink, gold, mint, blue
PAL = {"bg": ((0.02, 0.02, 0.08), (0.00, 0.00, 0.03)), "ring": (0.85, 0.88, 1.0), "balls": COLS,
       "accent": (1.0, 0.95, 0.85)}
NC = len(COLS)
MUSIC_SEED = 20261121 * 10 + 7
SKIN = "orb"

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)
song = music.Song.from_genre("synthwave", seed=MUSIC_SEED)
GAP_MAX = math.radians(58)
MATCHF = float(os.environ.get("MATCHF", "4.2"))   # gap-rate boost (only 1 colour in 4 may pass)

def zoom_for(r):
    return (150 + 0.67 * r) / r

TARGET = [5.2 - 2.2 * k / (N_GAP - 1) for k in range(N_GAP)]
T_K = [x / 0.886 for x in TARGET]
GAP_RATE, BALL_ANG = [], []
for k in range(N_GAP):
    n_k = 1 + 2 * k
    h_k = float(os.environ.get("GK", "0.8")) * SCREEN_SPEED / (1.3 * (150 + 0.67 * RADII[k]))
    GAP_RATE.append(MATCHF * 4 * math.pi / (n_k * h_k * T_K[k] ** 2))
    BALL_ANG.append(2 * math.asin(BR / RADII[k]) * 1.25)
OMEGA = [(0.5 + 0.45 * rng.random()) * (1 if k % 2 == 0 else -1) for k in range(N_GAP + 1)]
ROT0 = [rng.uniform(0, 2 * math.pi) for _ in range(N_GAP + 1)]
GATE = []
for k in range(N_GAP):
    c = int(rng.integers(NC))
    while GATE and c == GATE[-1]:
        c = int(rng.integers(NC))
    GATE.append(c)

def tube_color(k):
    if k >= N_GAP:
        return PAL["ring"]
    return neon.mix(COLS[GATE[k]], PAL["ring"], 0.40)

# ---------------- state ----------------
a0 = rng.uniform(0, 2 * math.pi)
z = zoom_for(R0)
spd = SCREEN_SPEED / z
p = np.array([[CX + 10.0, CY - 5.0]])
v = np.array([[math.cos(a0) * spd, math.sin(a0) * spd]])
col = np.array([int(rng.integers(NC))])
flip = np.array([-9.0])          # time of last colour change (for the flip pulse)
cur = 0
ring_t0 = 0.0
alive = [True] * (N_GAP + 1)
frags, sparks = [], []
hit_flash = 0.0
gate_flash = 0.0
heat = 0.0
final_t0 = None
heat_per_hit = 0.0
burst_pending = None
burst_t = None
events = []
build_keys = []
n_bounce = n_block = 0
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
    global p, v, col, flip
    ps, vs, cs = [], [], []
    for j in range(n_new):
        ang = rng.uniform(0.5, 1.4) * (1 if j % 2 == 0 else -1)
        c, s = math.cos(ang), math.sin(ang)
        vx, vy = v[i]
        vs.append([vx * c - vy * s, vx * s + vy * c])
        dx, dy = p[i][0] - CX, p[i][1] - CY
        dl = math.hypot(dx, dy) + 1e-6
        tx, ty = -dy / dl, dx / dl
        off = (2 * BR + 2) * (1 if j % 2 == 0 else -1)
        ps.append([p[i][0] + tx * off - dx / dl * 2, p[i][1] + ty * off - dy / dl * 2])
        cs.append((int(col[i]) + 1 + j) % NC)
    p = np.vstack([p, ps]); v = np.vstack([v, vs]); col = np.concatenate([col, cs])
    flip = np.concatenate([flip, [t, t]])

def shatter(k, tt, pan):
    alive[k] = False
    r = RADII[k]; g = gap_now(k, tt); rr = rot(k, tt)
    N = 10 + k
    span_total = 2 * math.pi - g
    for m in range(N):
        span = span_total / N
        ac = rr + g / 2 + span * (m + 0.5)
        sp = rng.uniform(160, 420) * (1 + k * 0.05)
        frags.append([CX + r * math.cos(ac), CY + r * math.sin(ac), math.cos(ac) * sp, math.sin(ac) * sp,
                      ac, span * 0.86, r, 0.0, rng.uniform(-3, 3), tube_color(k), tt])
    song.sfx(tt, "shatter", pan, 0.6)
    song.sfx(tt + 0.02, "chime", pan, 0.8)
    events.append((tt, "break", k))

def do_burst():
    global burst_t, v
    burst_t = t
    r = RADII[N_GAP]
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    radial = d / dist[:, None]
    v = v * 0.3 + radial * rng.uniform(280, 820, len(p))[:, None]
    N = 28
    for m in range(N):
        ac = rot(N_GAP, t) + 2 * math.pi * (m + 0.5) / N
        sp = rng.uniform(600, 1200)
        frags.append([CX + r * math.cos(ac), CY + r * math.sin(ac), math.cos(ac) * sp, math.sin(ac) * sp,
                      ac, 2 * math.pi / N * 0.85, r, 0.0, rng.uniform(-5, 5), neon.mix(PAL["ring"], (1, .2, .2), 0.7), t])
    for _ in range(70):
        a = rng.uniform(0, 2 * math.pi)
        sparks.append([CX + r * math.cos(a), CY + r * math.sin(a), rng.uniform(10, 26), t, COLS[int(rng.integers(NC))]])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    alive[N_GAP] = False
    events.append((t, "burst", N_GAP))

def physics_step(dt):
    global p, v, cur, ring_t0, hit_flash, gate_flash, heat, final_t0, heat_per_hit, burst_pending, n_bounce, n_block
    p += v * dt
    if burst_t is not None:
        return
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
                song.sfx(t, "tick", float((p[i][0] - CX) / 500), 0.22)
    k = cur
    r = RADII[k]
    rr = rot(k, t)
    g = gap_now(k, t)
    bh = math.asin(BR / r)
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-9
    escaped = None
    for i in np.where(dist + BR > r)[0]:
        rel = wrap(math.atan2(d[i, 1], d[i, 0]) - rr)
        in_gap = k < N_GAP and abs(rel) < g / 2 - bh * 0.6
        if in_gap and col[i] == GATE[k]:
            if dist[i] > r + BR * 0.3 and escaped is None:
                escaped = i
            continue
        if dist[i] > r + BR * 0.5:          # already outside (passing): let it go
            continue
        u = d[i] / dist[i]
        p[i] -= u * (dist[i] + BR - r)
        vn = np.dot(v[i], u)
        if vn > 0:
            v[i] -= 2 * vn * u
            jit = rng.uniform(-0.12, 0.12)
            c, s_ = math.cos(jit), math.sin(jit)
            v[i] = [v[i][0] * c - v[i][1] * s_, v[i][0] * s_ + v[i][1] * c]
            pan = float(d[i, 0] / r)
            song.note(t, pan)
            col[i] = (col[i] + 1) % NC           # every bounce: next colour
            flip[i] = t
            n_bounce += 1
            hx, hy = p[i] + u * BR
            if in_gap:
                n_block += 1
                gate_flash = 1.0
                sparks.extend([[hx, hy, rng.uniform(8, 16), t, COLS[GATE[k]]] for _ in range(3)])
            else:
                hit_flash = 1.0
                sparks.append([hx, hy, rng.uniform(6, 12), t, COLS[col[i]]])
            if k == N_GAP and final_t0 is not None:
                heat = min(1.0, heat + heat_per_hit)
    if escaped is not None:
        pan = float(d[escaped, 0] / r)
        shatter(k, t, pan)
        sparks.extend([[p[escaped][0], p[escaped][1], rng.uniform(10, 22), t, COLS[col[escaped]]] for _ in range(8)])
        spawn_from(escaped, 2)
        song.sfx(t + 0.05, "pop", pan, 0.8)
        cur += 1
        ring_t0 = t
        if cur == N_GAP:
            final_t0 = t
            final_dur = float(np.clip(PAYOFF_TARGET - 1.0 - t, 7.0, 14.5))
            # expected hits: each ball meets the ring about every 1.45 R of travel
            rate = len(p) * (SCREEN_SPEED / zoom_for(R_FINAL)) / (1.45 * R_FINAL)
            heat_per_hit = 1.0 / (rate * final_dur)
            events.append((t, "final", cur))
    if cur == N_GAP and heat >= 1.0 and burst_pending is None:
        burst_pending = song.next_bar(t)
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
        sprite_cache[q] = neon.SkinSprites(COLS, q, skin=SKIN)
    return sprite_cache[q]

def S(x, y):
    return CX + (x - CX) * z, CY + (y - CY) * z

def arc_tube(R, a0, a1, rgb, alpha=1.0, heat_=0.0, width=5.0, glow=1.0):
    c = neon.mix(rgb, (1.0, 0.18, 0.22), heat_)
    pulse = 1.0 + heat_ * 0.6 * (0.5 + 0.5 * math.sin(t * 26))
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for w, a in [(46, 0.05), (28, 0.09), (16, 0.16), (9, 0.35)]:
        ctx.set_source_rgba(*c, a * pulse * alpha * glow); ctx.set_line_width(w * pulse)
        ctx.new_path(); ctx.arc(CX, CY, R, a0, a1); ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.65), 0.95 * alpha); ctx.set_line_width(width)
    ctx.new_path(); ctx.arc(CX, CY, R, a0, a1); ctx.stroke(); ctx.restore()

def gate(R, rr, g, c, alpha, flash):
    """coloured membrane across the gap + bright coloured caps"""
    a0, a1 = rr - g / 2, rr + g / 2
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    shimmer = 0.75 + 0.25 * math.sin(t * 7.0 + R * 0.05)
    for w, a in [(38, 0.10), (20, 0.20), (9, 0.42)]:
        ctx.set_source_rgba(*c, a * alpha * (shimmer + 1.5 * flash)); ctx.set_line_width(w)
        ctx.new_path(); ctx.arc(CX, CY, R, a0, a1); ctx.stroke()
    ctx.set_dash([7, 9], t * 20)
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.35), min(1.0, 0.9 * alpha * (shimmer + flash))); ctx.set_line_width(4.5)
    ctx.new_path(); ctx.arc(CX, CY, R, a0, a1); ctx.stroke()
    ctx.set_dash([])
    for a in (a0, a1):
        ex, ey = CX + R * math.cos(a), CY + R * math.sin(a)
        gr = cairo.RadialGradient(ex, ey, 0, ex, ey, 32)
        gr.add_color_stop_rgba(0, *neon.mix(c, (1, 1, 1), 0.5), 0.95 * alpha); gr.add_color_stop_rgba(0.4, *c, 0.5 * alpha)
        gr.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(gr); ctx.arc(ex, ey, 32, 0, 2 * math.pi); ctx.fill()
    ctx.restore()

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    gcol = neon.mix(COLS[GATE[cur]] if cur < N_GAP else PAL["accent"], (1.0, 0.3, 0.35), heat * 0.8)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 900)
    ga = 0.04 + 0.14 * pr + 0.03 * math.sin(t * 2.0)
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
            arc_tube(R, 0, 2 * math.pi, PAL["ring"], alpha, heat if is_cur else 0.0, 6.0, glow)
        else:
            g = gap_now(k, t) if is_cur else BALL_ANG[k] * 1.6
            arc_tube(R, rr + g / 2, rr + 2 * math.pi - g / 2, tube_color(k), alpha, 0.0, 5.0, glow)
            gate(R, rr, g, COLS[GATE[k]], alpha, gate_flash if is_cur else 0.0)
    # fragments
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for fx, fy, _vx, _vy, ac, span, r, frot, _vr, fc, ft0 in frags:
        age = t - ft0
        fa = max(0.0, 1 - age / 2.2)
        if fa <= 0:
            continue
        sx, sy = S(fx, fy)
        ctx.save(); ctx.translate(sx, sy); ctx.rotate(frot)
        for w_, a_ in [(16, 0.16), (6, 0.9)]:
            ctx.set_source_rgba(*fc, a_ * fa); ctx.set_line_width(w_)
            ctx.new_path(); ctx.arc(-r * z * math.cos(ac), -r * z * math.sin(ac), r * z, ac - span / 2, ac + span / 2); ctx.stroke()
        ctx.restore()
    ctx.restore()
    # shockwaves
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, k in events:
        if kind not in ("break", "burst"):
            continue
        age = t - et
        dur = 0.7 if kind == "break" else 1.2
        if 0 <= age < dur:
            a = (1 - age / dur) * (0.5 if kind == "break" else 0.8)
            c = COLS[GATE[k]] if kind == "break" else PAL["accent"]
            ctx.set_source_rgba(*c, a); ctx.set_line_width(3 + 16 * a)
            ctx.new_path(); ctx.arc(CX, CY, RADII[k] * z + (500 if kind == "break" else 2200) * age, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    # balls (+ a quick white pulse right after a colour flip)
    spr = sprites_for(BR * z)
    pts = [S(x, y) for x, y in p]
    vis = [(q, int(c), f) for q, c, f in zip(pts, col, flip) if -60 < q[0] < W + 60 and -60 < q[1] < H + 60]
    spr.draw(ctx, [q for q, _, _ in vis], [c for _, c, _ in vis])
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for (x, y), c, f in vis:
        age = t - f
        if 0 <= age < 0.25:
            a = 1 - age / 0.25
            rr_ = BR * z * (1.0 + 1.2 * (1 - a))
            ctx.set_source_rgba(*neon.mix(COLS[c], (1, 1, 1), 0.5), 0.6 * a); ctx.set_line_width(2.5)
            ctx.new_path(); ctx.arc(x, y, rr_, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
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
    if counter and burst_t is None:
        left = sum(alive)
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(120)
        txt = str(left)
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1690)
        ctx.text_path(txt)
        cc = neon.mix(COLS[GATE[cur]] if cur < N_GAP else PAL["ring"], (1, 1, 1), 0.45)
        cc = neon.mix(cc, (1, .3, .3), heat)
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
while True:
    for _ in range(SUB):
        physics_step(dt)
        if burst_pending is not None and burst_t is None and t >= burst_pending:
            do_burst()
        for f in frags:
            f[0] += f[2] * dt; f[1] += f[3] * dt; f[7] += f[8] * dt
        t += dt
    zt = zoom_for(RADII[min(cur, N_GAP)])
    if burst_t is not None:
        zt = zoom_for(R_FINAL) * 0.92
    z += (zt - z) * 0.035
    hit_flash *= 0.82
    gate_flash *= 0.85
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
print("final_t0", final_t0 and round(final_t0, 1), "burst", burst_t and round(burst_t, 2), "duration", round(t, 2),
      "balls", len(p), "bounces", n_bounce, "blocked", n_block)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
