"""2026-11-19 08:00 — ring-break: "Break Through"
One ball inside 10 nested neon rings made of glowing bricks. Visible rules:
  1. Every hit cracks the brick it lands on (it dims and shows cracks); after a few hits the brick breaks.
  2. A broken brick leaves a hole — but it slowly grows back. Get through before it heals!
  3. When a ball gets through, the whole ring shatters and a new ball joins.
The camera zooms out ring by ring. The last ring is thick and strong: every crack heats it red until a
brick finally gives way — then it bursts on the bar line. Tail crossfades back to the opening frame.

usage: python3 concepts/2026-11-19_am_break_through.py <seed> [--sim | --audio]
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
N_GAP = 10                        # breakable rings before the last one
R0, R_FINAL = 90.0, 470.0
RADII = [R0 + (R_FINAL - R0) * k / N_GAP for k in range(N_GAP + 1)]   # last = sealed ring
SCREEN_SPEED = 540.0
PAYOFF_TARGET = 61.5
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv      # simulate + render audio.wav only (physics is identical)
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
PAL = neon.PALETTES["sunset"]
MUSIC_SEED = 20261123
SKIN = "orb"

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)   # drawing-only randomness (keeps physics identical to --sim)
RECENT = [dict(genre="custom", bpm=100, key="C", mode="major", lead="sine"),
          dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass"),
          dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)          # tropical, as logged for this slot
NSEG = [int(os.environ.get("NSEG0", "8"))] * 4 + [int(os.environ.get("NSEG1", "10"))] * 4 + [int(os.environ.get("NSEG2", "12"))] * 3
HPM = float(os.environ.get("HPM", "1.6"))
HP = [max(2, round(h * HPM)) for h in [2, 2, 2, 3, 3, 3, 3, 4, 4, 4]] + [int(os.environ.get("HPF", "14"))]
REGEN = float(os.environ.get("REGEN", "2.2"))      # seconds until a broken brick has grown back

def zoom_for(r):
    return (150 + 0.67 * r) / r

OMEGA = [(0.35 + 0.35 * rng.random()) * (1 if k % 2 == 0 else -1) for k in range(N_GAP + 1)]
hp = [[HP[k]] * NSEG[k] for k in range(N_GAP + 1)]
broke_t = [[None] * NSEG[k] for k in range(N_GAP + 1)]     # when a brick broke (None = intact)
seg_hit_t = [[-9.0] * NSEG[k] for k in range(N_GAP + 1)]
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

def seg_of(k, rel):
    n = NSEG[k]
    return int(((rel % (2 * math.pi)) / (2 * math.pi)) * n) % n

def is_open(k, j, tt):
    bt = broke_t[k][j]
    return bt is not None and tt - bt < REGEN

def damage(k):
    tot = HP[k] * NSEG[k]
    return 1 - sum(max(0, h) for h in hp[k]) / tot

def progress():
    if burst_t is not None:
        return 1.0
    if cur < N_GAP:
        return 0.85 * (cur + min(1.0, (t - ring_t0) / 5.0) * 0.5) / N_GAP
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

def shatter(k, tt, pan):
    alive[k] = False
    r = RADII[k]; rr = rot(k, tt)
    n = NSEG[k]; span = 2 * math.pi / n
    for j in range(n):
        if is_open(k, j, tt):
            continue
        ac = rr + span * (j + 0.5)
        sp = rng.uniform(160, 420) * (1 + k * 0.05)
        frags.append([CX + r * math.cos(ac), CY + r * math.sin(ac), math.cos(ac) * sp, math.sin(ac) * sp,
                      ac, span * 0.8, r, 0.0, rng.uniform(-3, 3), ring_color(k), tt])
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
    N = NSEG[N_GAP]
    for m in range(N):
        ac = rot(N_GAP, t) + 2 * math.pi * (m + 0.5) / N
        sp = rng.uniform(600, 1200)
        frags.append([CX + r * math.cos(ac), CY + r * math.sin(ac), math.cos(ac) * sp, math.sin(ac) * sp,
                      ac, 2 * math.pi / N * 0.8, r, 0.0, rng.uniform(-5, 5), neon.mix(PAL["ring"], (1, .2, .2), 0.7), t])
    for _ in range(60):
        a = rng.uniform(0, 2 * math.pi)
        sparks.append([CX + r * math.cos(a), CY + r * math.sin(a), rng.uniform(10, 26), t, PAL["accent"]])
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
    bh = math.asin(min(1.0, BR / r))
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-6
    escaped = None
    for i in np.where(dist + BR > r)[0]:
        ang = math.atan2(d[i, 1], d[i, 0])
        rel = wrap(ang - rr)
        j0, j1, j2 = seg_of(k, rel - bh * 0.8), seg_of(k, rel), seg_of(k, rel + bh * 0.8)
        through = k < N_GAP and is_open(k, j0, t) and is_open(k, j1, t) and is_open(k, j2, t)
        if through or (k < N_GAP and dist[i] > r and is_open(k, j1, t)):
            if dist[i] > r + BR * 0.3 and escaped is None:
                escaped = i
            continue
        nrm = d[i] / dist[i]
        p[i] -= nrm * (dist[i] + BR - r)
        vn = np.dot(v[i], nrm)
        if vn > 0:
            v[i] -= 2 * vn * nrm
            jit = rng.uniform(-0.15, 0.15)
            c, s_ = math.cos(jit), math.sin(jit)
            v[i] = [v[i][0] * c - v[i][1] * s_, v[i][0] * s_ + v[i][1] * c]
            pan = float(d[i, 0] / r)
            song.note(t, pan)
            hit_flash = 1.0
            hx, hy = CX + nrm[0] * r, CY + nrm[1] * r
            sparks.append([hx, hy, rng.uniform(6, 12), t, ring_color(k)])
            j = j1
            if not is_open(k, j, t):
                if broke_t[k][j] is not None:          # it had grown back: fresh brick again
                    broke_t[k][j] = None; hp[k][j] = HP[k]
                hp[k][j] -= 1
                seg_hit_t[k][j] = t
                if k == N_GAP:
                    cracks.append(rel)
                if hp[k][j] <= 0:
                    broke_t[k][j] = t
                    song.sfx(t, "shatter", pan, 0.35)
                    for _ in range(5):
                        sparks.append([hx, hy, rng.uniform(8, 16), t, PAL["accent"]])
                    events.append((t, "brick", (k, j)))
                    if k == N_GAP and burst_pending is None:
                        burst_pending = song.next_bar(t)
    # bricks that grew back are whole again
    for kk in (k,):
        for jj in range(NSEG[kk]):
            if broke_t[kk][jj] is not None and t - broke_t[kk][jj] >= REGEN:
                broke_t[kk][jj] = None; hp[kk][jj] = HP[kk]
    if escaped is not None:
        pan = float(d[escaped, 0] / r)
        shatter(k, t, pan)
        sparks.extend([[p[escaped][0], p[escaped][1], rng.uniform(10, 22), t, PAL["accent"]] for _ in range(6)])
        spawn_from(escaped, 1)
        song.sfx(t + 0.05, "pop", pan, 0.8)
        cur += 1
        ring_t0 = t
        if cur == N_GAP:
            final_t0 = t
            events.append((t, "final", cur))
    if cur == N_GAP:
        heat = min(1.0, damage(N_GAP) * 2.2)
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
        n = NSEG[k]; span = 2 * math.pi / n
        base = PAL["ring"] if k == N_GAP else ring_color(k)
        wid = 8.0 if k == N_GAP else 5.0
        for j in range(n):
            a0_, a1_ = rr + span * j + 0.03, rr + span * (j + 1) - 0.03
            if is_open(k, j, t):
                grow = (t - broke_t[k][j]) / REGEN          # hole slowly closing
                if grow > 0.55:
                    mid = (a0_ + a1_) / 2; half = (a1_ - a0_) / 2 * (grow - 0.55) / 0.45
                    arc_ring(CX, CY, R, mid - half, mid + half, base, alpha * 0.35, 0.0, 3.0, 0.6)
                continue
            frac = max(0.0, hp[k][j]) / HP[k]
            flash = max(0.0, 1 - (t - seg_hit_t[k][j]) / 0.25)
            col_ = neon.mix(base, (1, 1, 1), 0.5 * flash)
            hh = heat if k == N_GAP else 0.0
            arc_ring(CX, CY, R, a0_, a1_, col_, alpha * (0.35 + 0.65 * frac), hh, wid, glow * (0.6 + 0.4 * frac + 0.6 * flash))
            if frac < 1.0:                               # cracks on damaged bricks
                ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_width(2.0)
                ctx.set_source_rgba(1, 0.9, 0.8, 0.6 * alpha)
                ncr = int((1 - frac) * 4) + 1
                for q in range(ncr):
                    am = a0_ + (a1_ - a0_) * ((q * 0.37 + j * 0.13) % 1)
                    ux, uy = math.cos(am), math.sin(am)
                    px_, py_ = -uy, ux
                    L = 9 + 7 * q
                    ctx.move_to(CX + ux * (R - L), CY + uy * (R - L))
                    ctx.line_to(CX + ux * R + px_ * (4 - 3 * (q % 3)), CY + uy * R + py_ * (4 - 3 * (q % 3)))
                    ctx.line_to(CX + ux * (R + L * 0.6), CY + uy * (R + L * 0.6))
                    ctx.stroke()
                ctx.restore()
    # flying fragments
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
            ctx.new_path(); ctx.arc(CX, CY, RADII[k] * z + (500 if kind == "break" else 2200) * age, 0, 2 * math.pi); ctx.stroke()
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
print("bricks broken", sum(1 for e in events if e[1] == "brick"))
print("final_t0", final_t0 and round(final_t0, 1), "burst", burst_t and round(burst_t, 2), "duration", round(t, 2), "balls", len(p))
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
