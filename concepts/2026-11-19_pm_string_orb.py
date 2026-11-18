"""2026-11-19 18:00 — growing-ball: "String Orb"
One clear, visible rule:
  Every time the orb hits the ring it grows a little — and its path stays behind as a glowing string.
Because it keeps the same speed but has less and less room, the bounces come faster and faster
(the melody speeds up by itself) while the string art spirals inward into a rosette.
When the orb fills the ring completely it buzzes against the wall, the ring heats red, and the
pressure from inside bursts the ring outward on a bar line; the orb shatters into hundreds of
small orbs. The tail crossfades back to the opening frame.

usage: python3 concepts/2026-11-19_pm_string_orb.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 8
CX, CY, R = W / 2, 940, 450.0
R0 = 26.0
V = float(os.environ.get("V", "720"))
DR = float(os.environ.get("DR", "3.1"))       # growth per bounce (px)
GAP_END = 5.0
STEP_DEG = float(os.environ.get("STEP", "86"))  # angular step around the ring per bounce
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
MUSIC_SEED = 20261200
RECENT = [dict(genre="custom", bpm=100, key="C", mode="major", lead="sine"),
          dict(genre="space", bpm=88, key="G", mode="dorian", lead="glass"),
          dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep"),
          dict(genre="tropical", bpm=112, key="A", mode="major", lead="marimba")]

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)
song = music.random_song(MUSIC_SEED, avoid=RECENT)
song.melody_scale = "penta_major"      # consonant pentatonic shimmer over the lydian chords
PAL = dict(neon.PALETTES["synthwave"])
GRAD = [(0.20, 0.90, 1.0), (0.45, 0.55, 1.0), (0.75, 0.35, 1.0), (1.0, 0.25, 0.85), (1.0, 0.45, 0.45), (1.0, 0.75, 0.30)]


def grad(u):
    u = min(max(u, 0.0), 0.9999) * (len(GRAD) - 1)
    i = int(u); return neon.mix(GRAD[i], GRAD[i + 1], u - i)


# ---------------- state ----------------
t = 0.0
r = R0
q = np.array([CX + rng.uniform(-40, 40), CY + rng.uniform(-60, 60)])
beta = math.radians((180 - STEP_DEG) / 2 + rng.uniform(-1.5, 1.5))
a_start = rng.uniform(0, 2 * math.pi)
u = V * np.array([math.cos(a_start), math.sin(a_start)])
bounces = 0
pts = [(q[0], q[1], 0.0)]          # string: bounce centres
hits = []                          # (x, y, t, colour) contact points on the ring
full_t = None
burst_pending = None
burst_t = None
frags, shards, sparks, build_keys = [], [], [], []
last_hit = -9.0
N_EST = (R - R0 - GAP_END) / DR


def heat():
    return float(np.clip((r / R - 0.55) / 0.43, 0, 1)) ** 1.6


def progress():
    if burst_t is not None:
        return 1.0
    return min(1.0, 0.15 * min(1, t / 10) + 0.85 * (r - R0) / (R - R0 - GAP_END))


def do_burst():
    global burst_t
    burst_t = t
    N = 28
    for m in range(N):
        ac = 2 * math.pi * (m + 0.5) / N
        sp = rng.uniform(450, 800)
        frags.append([CX + R * math.cos(ac), CY + R * math.sin(ac), math.cos(ac) * sp, math.sin(ac) * sp, ac,
                      2 * math.pi / N * 0.85, 0.0, rng.uniform(-4, 4)])
    for _ in range(320):
        a = rng.uniform(0, 2 * math.pi); rr = math.sqrt(rng.uniform(0, 1)) * (r - 10)
        x, y = q[0] + rr * math.cos(a), q[1] + rr * math.sin(a)
        sp = 200 + 1000 * rr / R + rng.uniform(0, 150)
        shards.append([x, y, math.cos(a) * sp, math.sin(a) * sp, int(rng.integers(len(GRAD)))])
    for _ in range(70):
        a = rng.uniform(0, 2 * math.pi)
        sparks.append([CX + R * math.cos(a), CY + R * math.sin(a), rng.uniform(10, 28), t, (1, 1, 1)])
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    song.sfx(t + 0.01, "pop", 0.0, 1.0)


def physics_step(dt):
    global q, u, r, bounces, full_t, burst_pending, last_hit
    if burst_t is not None:
        for s in shards:
            s[0] += s[2] * dt; s[1] += s[3] * dt; s[2] *= 0.997; s[3] *= 0.997
        for f in frags:
            f[0] += f[2] * dt; f[1] += f[3] * dt; f[6] += f[7] * dt
        return
    q = q + u * dt
    d = q - (CX, CY)
    dist = math.hypot(d[0], d[1])
    lim = R - r
    if dist > lim:
        n = d / dist
        un = float(u @ n)
        if un > 0:
            if bounces == 0:
                # set the incidence angle once, then it is preserved by perfect reflection
                tang = np.array([-n[1], n[0]])
                u = V * (-math.cos(beta) * n + math.sin(beta) * tang)
            else:
                u = u - 2 * un * n
            bounces += 1
            if full_t is None:
                r = min(R - GAP_END, r + DR)
            c = grad(bounces / N_EST)
            hits.append((CX + R * n[0], CY + R * n[1], t, c))
            pts.append((CX + n[0] * (R - r), CY + n[1] * (R - r), t))
            if t - last_hit > 0.02:
                song.note(t, float(n[0]) * 0.8, vel=0.9)
                last_hit = t
            if full_t is None and r >= R - GAP_END - 1e-6:
                full_t = t
                burst_pending = song.next_bar(t + 1.0)
        q = np.array([CX, CY]) + n * (R - r)


# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SHARD = neon.BallSprites(GRAD, 9, glow=2.6, glow_alpha=0.5)


def draw_orb(x, y, rr, c, pulse):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.RadialGradient(x, y, rr * 0.6, x, y, rr * 1.55)
    g.add_color_stop_rgba(0, *c, 0.30 + 0.25 * pulse); g.add_color_stop_rgba(1, *c, 0)
    ctx.set_source(g); ctx.arc(x, y, rr * 1.55, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    g = cairo.RadialGradient(x - rr * 0.35, y - rr * 0.4, rr * 0.05, x, y, rr)
    g.add_color_stop_rgba(0, *neon.mix(c, (1, 1, 1), 0.75), 0.80)
    g.add_color_stop_rgba(0.5, *neon.mix(c, (1, 1, 1), 0.15), 0.55)
    g.add_color_stop_rgba(1, *neon.mix(c, (0, 0, 0), 0.3), 0.70)
    ctx.set_source(g); ctx.arc(x, y, rr, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.7), 0.85 + 0.15 * pulse); ctx.set_line_width(max(2.0, rr * 0.035) + 4 * pulse)
    ctx.arc(x, y, rr - 1, 0, 2 * math.pi); ctx.stroke()
    ctx.save(); ctx.translate(x - rr * 0.38, y - rr * 0.42); ctx.rotate(-0.5); ctx.scale(rr * 0.28, rr * 0.15)
    ctx.set_source_rgba(1, 1, 1, 0.55); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()


def draw_string(alpha_k=1.0):
    seg = pts + ([(q[0], q[1], t)] if burst_t is None else [])
    if len(seg) < 2:
        return
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    n = len(seg)
    for w_, a_ in ((11, 0.07), (5, 0.22), (1.8, 0.85)):
        ctx.set_line_width(w_)
        for i in range(n - 1):
            c = grad(i / N_EST)
            age = t - seg[i + 1][2]
            fresh = 1.0 + 1.2 * math.exp(-max(age, 0) * 3)
            ctx.set_source_rgba(*c, min(1.0, a_ * fresh) * alpha_k)
            ctx.move_to(seg[i][0], seg[i][1]); ctx.line_to(seg[i + 1][0], seg[i + 1][1]); ctx.stroke()
    ctx.restore()


def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress(); hh = heat()
    cnow = grad(bounces / N_EST)
    gcol = neon.mix(cnow, (1.0, 0.25, 0.3), hh)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 950)
    ga = 0.04 + 0.12 * pr + 0.02 * math.sin(t * 1.8)
    if burst_t is not None:
        ga *= math.exp(-(t - burst_t) * 1.5)
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 0.0
    if burst_t is None and hh > 0.5:
        shake = 8 * ((hh - 0.5) / 0.5) ** 2
    if full_t is not None and burst_t is None:
        shake += 4
    if burst_t is not None:
        shake = 26 * math.exp(-(t - burst_t) * 6)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    ring_col = PAL["ring"]
    if burst_t is None:
        neon.ring(ctx, CX, CY, R + 4, ring_col, t, heat=hh)
        # contact flashes on the ring
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        for x, y, th, c in hits[-40:]:
            age = t - th
            if 0 <= age < 0.6:
                a = 1 - age / 0.6
                g = cairo.RadialGradient(x, y, 0, x, y, 70)
                g.add_color_stop_rgba(0, *neon.mix(c, (1, 1, 1), 0.5), 0.55 * a); g.add_color_stop_rgba(1, *c, 0)
                ctx.set_source(g); ctx.arc(x, y, 70, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        last = hits[-1][2] if hits else -9
        pulse = math.exp(-(t - last) * 9) if full_t is None else 0.6 + 0.4 * math.sin(t * 60)
        draw_orb(q[0], q[1], r, cnow, pulse)
        draw_string()
        sp = [(x, y, 14 * (1 - (t - th) / 0.4)) for x, y, th, c in hits[-20:] if 0 <= t - th < 0.4]
        if sp:
            neon.sparkles(ctx, sp, (1, 1, 1), alpha=0.8)
    else:
        dt_b = t - burst_t
        draw_string(max(0.0, 1 - dt_b / 0.8))
        sa = max(0.0, 0.75 - dt_b * 1.2)
        if sa > 0:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(1, 1, 1, sa); ctx.set_line_width(24 * sa + 2)
            ctx.arc(CX, CY, R + 1700 * dt_b, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        fa = max(0.0, 1 - dt_b / 2.2)
        for fx, fy, _vx, _vy, ac, span, frot, _vr in frags:
            ctx.save(); ctx.translate(fx, fy); ctx.rotate(frot)
            for w_, a_ in ((18, 0.15), (7, 0.9)):
                ctx.set_source_rgba(*neon.mix(ring_col, (1, .2, .2), 0.6), a_ * fa); ctx.set_line_width(w_)
                ctx.new_path(); ctx.arc(-R * math.cos(ac), -R * math.sin(ac), R + 4, ac - span / 2, ac + span / 2); ctx.stroke()
            ctx.restore()
        ctx.restore()
        SHARD.draw(ctx, [(s[0], s[1]) for s in shards], [s[4] for s in shards], glow=True)
    live = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = live
    if live:
        neon.sparkles(ctx, [(x, y, sz * (1.6 - (t - st) / 0.5)) for x, y, sz, st, c in live], (1, 1, 1), alpha=0.8)
    ctx.restore()
    if counter and burst_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(110)
        txt = f"{bounces:,}"
        xb, yb, tw, th_, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1660)
        ctx.text_path(txt)
        cc = neon.mix(neon.mix(cnow, (1, 1, 1), 0.4), (1, .3, .3), hh)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(22); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if burst_t is not None:
        fa = max(0.0, 0.55 - (t - burst_t) * 2.5)
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
        t += dt
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 300 == 0:
        log.append((round(t), bounces, round(r)))
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
print("seed", SEED, "log(t,bounces,r)", log)
print("full", full_t and round(full_t, 2), "burst", burst_t and round(burst_t, 2), "duration", round(t, 2), "bounces", bounces)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
