"""2026-11-27 18:00 — NEW family "hot-potato": "Hot Potato"
10 neon balls (one per colour) bounce inside a neon ring, zero gravity, real elastic collisions.
One ball carries the BOMB: a burning fuse spark + a countdown arc around it. Touching another ball passes the
bomb to it (zap). When the arc runs out (always on the beat, fuse length = N bars, shorter every round) the holder
POPS: sparks, shockwave, the blast pushes its neighbours away, and the sparks fly into the survivors, which grow.
The next fuse jumps to the ball closest to the blast. 10 -> 1. Bigger survivors = more contacts, so the late
rounds become frantic passing. The final pop lands on a bar line: the ring floods in the winner's colour.
Colour dots on top = who is still in; counter = balls left.
Wall bounces = music (song.note); pass = zap; ball-ball contact = tick; pop = pop + thump; fuse ticks in the
last beats = tick; sparks reaching survivors = soft chime.

usage: python3 concepts/2026-11-27_pm_hot_potato.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 6
CX, CY, RR = 540.0, 1010.0, 440.0
N = 10
R0 = float(os.environ.get("R0", "36"))
GROWK = float(os.environ.get("GROWK", "0.85"))
V0 = float(os.environ.get("V0", "520"))
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
# random_song(2026112800, avoid=all logged recipes + 08:00 japanese) -> synthwave 106 G minor glass
MUSIC_SEED = int(os.environ.get("MSEED", "2026112800"))
RECENT = [dict(genre="trance_lite", bpm=123, key="F", mode="minor", lead="pluck"),
          dict(genre="bossa", bpm=96, key="G#", mode="major", lead="ep"),
          dict(genre="space", bpm=76, key="B", mode="lydian", lead="bell"),
          dict(genre="desert", bpm=104, key="F#", mode="phrygian_dominant", lead="flute"),
          dict(genre="chiptune", bpm=124, key="F#", mode="mixolydian", lead="square"),
          dict(genre="cinematic", bpm=84, key="C#", mode="harmonic_minor", lead="harp"),
          dict(genre="citypop", bpm=105, key="G#", mode="major", lead="ep"),
          dict(genre="japanese", bpm=90, key="F", mode="phrygian", lead="koto")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)
BAR = song.chord_len
FUSE_BARS = [int(x) for x in os.environ.get("FUSE", "4,4,3,3,3,3,2,2,2").split(",")]
COLS = [neon.hsv(k / N, 0.78, 1.0) for k in range(N)]
PAL = {"bg": ((0.03, 0.01, 0.08), (0.00, 0.00, 0.03)), "ring": (0.85, 0.85, 1.0), "balls": COLS,
       "accent": (1.0, 0.95, 0.85)}
RING_COL = (0.70, 0.75, 1.0)
GREY = (0.40, 0.40, 0.48)

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)

def radius_for(alive_n):
    return R0 * (N / alive_n) ** GROWK

# ---------------- state ----------------
p = np.zeros((N, 2)); v = np.zeros((N, 2))
for i in range(N):
    for _ in range(1000):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0, RR - R0 - 20)
        q = np.array([CX + rr * math.cos(a), CY + rr * math.sin(a)])
        if all(np.hypot(*(q - p[j])) > 2 * R0 + 14 for j in range(i)):
            p[i] = q; break
    a = rng.uniform(0, 2 * math.pi)
    v[i] = [V0 * math.cos(a), V0 * math.sin(a)]
colour = np.arange(N)
alive = np.ones(N, bool)
rad = np.full(N, R0)
rad_target = np.full(N, R0)
grow_at = np.full(N, -1.0)
out_t = np.full(N, -1.0)
holder = int(rng.integers(N))
round_k = 0
fuse_start = 0.0
fuse_end = FUSE_BARS[0] * BAR
last_pass_t = -9.0
pass_log = []          # (t, round, from, to)
pop_log = []           # (t, ball)
hit_cool = np.zeros(N) - 9
t = 0.0
events, sparks, streams, build_keys = [], [], [], []
winner = None
payoff_t = None
last_tick_beat = -1

def progress():
    if payoff_t is not None:
        return 1.0
    k = (N - int(alive.sum())) / (N - 1)
    within = (t - fuse_start) / max(1e-6, fuse_end - fuse_start)
    return float(np.clip(0.08 + 0.85 * k + 0.07 * within, 0, 1))

def pop(i):
    global holder, round_k, fuse_start, fuse_end, winner, payoff_t
    alive[i] = False
    out_t[i] = t
    pop_log.append((t, i))
    song.sfx(t, "pop", float((p[i, 0] - CX) / RR), 1.0)
    song.sfx(t, "thump", 0.0, 0.6)
    events.append((t, "pop", (float(p[i, 0]), float(p[i, 1]), int(colour[i]), float(rad[i]))))
    for _ in range(60):
        a = fx_rng.uniform(0, 2 * math.pi); s_ = fx_rng.uniform(150, 700)
        sparks.append([p[i, 0], p[i, 1], math.cos(a) * s_, math.sin(a) * s_, fx_rng.uniform(8, 20), t, COLS[colour[i]]])
    al = np.where(alive)[0]
    # blast pushes neighbours away
    for j in al:
        d = p[j] - p[i]
        dist = math.hypot(*d) + 1e-6
        reach = 260 + 2 * rad[i]
        if dist < reach:
            v[j] += d / dist * 650 * (1 - dist / reach)
    if len(al) == 1:
        winner = int(al[0])
        payoff_t = t
        song.accent(t)
        song.sfx(t, "chime", 0.0, 1.0)
        song.sfx(t, "shatter", 0.0, 0.35)
        for _ in range(160):
            a = fx_rng.uniform(0, 2 * math.pi); s_ = fx_rng.uniform(200, 1200)
            sparks.append([CX, CY, math.cos(a) * s_, math.sin(a) * s_, fx_rng.uniform(10, 26), t, COLS[colour[winner]]])
        holder = None
        rad_target[winner] = radius_for(1) * 0 + rad_target[winner]
        return
    # sparks stream into survivors -> they grow
    newr = radius_for(len(al))
    for j in al:
        streams.append((t, float(p[i, 0]), float(p[i, 1]), int(j), int(colour[i])))
        rad_target[j] = newr
        grow_at[j] = t + 0.35
    # next fuse: closest survivor to the blast
    dist = [math.hypot(*(p[j] - p[i])) for j in al]
    holder = int(al[int(np.argmin(dist))])
    round_k += 1
    fuse_start = t
    fuse_end = t + FUSE_BARS[min(round_k, len(FUSE_BARS) - 1)] * BAR
    events.append((t, "newfuse", (holder, float(p[i, 0]), float(p[i, 1]))))

def physics_step(dt):
    global holder, last_pass_t, last_tick_beat
    al = np.where(alive)[0]
    # growth (smooth, after the sparks arrive)
    for j in al:
        if grow_at[j] >= 0 and t >= grow_at[j]:
            rad[j] += (rad_target[j] - rad[j]) * min(1.0, dt * 9)
    p[al] += v[al] * dt
    # keep a lively, size-dependent cruising speed
    for j in al:
        sp = math.hypot(*v[j]) + 1e-6
        tgt = V0 * (R0 / rad[j]) ** 0.25
        v[j] *= 1 + (tgt / sp - 1) * min(1.0, dt * 0.8)
    # ball-ball
    for a in range(len(al)):
        i = al[a]
        for b in range(a + 1, len(al)):
            j = al[b]
            d = p[j] - p[i]
            dist = math.hypot(*d)
            rs = rad[i] + rad[j]
            if 1e-6 < dist < rs:
                nrm = d / dist
                mi, mj = rad[i] ** 2, rad[j] ** 2
                over = rs - dist
                p[i] -= nrm * over * mj / (mi + mj); p[j] += nrm * over * mi / (mi + mj)
                rel = np.dot(v[j] - v[i], nrm)
                if rel < 0:
                    J = 2 * rel / (1 / mi + 1 / mj)
                    v[i] += J / mi * nrm; v[j] -= J / mj * nrm
                    cpt = p[i] + nrm * rad[i]
                    if holder in (i, j) and t - last_pass_t > 0.30 and payoff_t is None:
                        other = j if holder == i else i
                        pass_log.append((t, round_k, holder, other))
                        holder = other
                        last_pass_t = t
                        song.sfx(t, "zap", float((cpt[0] - CX) / RR), 0.55)
                        events.append((t, "pass", (float(cpt[0]), float(cpt[1]), int(colour[other]))))
                        for _ in range(14):
                            a_ = fx_rng.uniform(0, 2 * math.pi); s_ = fx_rng.uniform(80, 380)
                            sparks.append([cpt[0], cpt[1], math.cos(a_) * s_, math.sin(a_) * s_, fx_rng.uniform(6, 13), t, (1.0, 0.85, 0.5)])
                    elif -rel > 120:
                        song.sfx(t, "tick", float((cpt[0] - CX) / RR), min(0.35, 0.12 + -rel / 2500))
    # ring
    for j in al:
        d = p[j] - [CX, CY]
        dist = math.hypot(*d)
        lim = RR - rad[j]
        if dist > lim:
            nrm = d / dist
            p[j] = np.array([CX, CY]) + nrm * lim
            vn = np.dot(v[j], nrm)
            if vn > 0:
                v[j] -= 2 * vn * nrm
                if t - hit_cool[j] > 0.07:
                    hit_cool[j] = t
                    song.note(t, float(nrm[0]), vel=min(1.0, 0.5 + vn / 1200))
                    events.append((t, "hit", (float(CX + nrm[0] * RR), float(CY + nrm[1] * RR), int(colour[j]))))
    # fuse ticks on the last beats
    if holder is not None:
        b = int(math.floor(t / song.beat + 1e-9))
        left = fuse_end - t
        if b != last_tick_beat and left < 4 * song.beat + 1e-6 and left > 0.05:
            last_tick_beat = b
            song.sfx(t, "tick", 0.0, 0.5)
            events.append((t, "tick", 0))

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
LEVEL_R = sorted({round(radius_for(k), 1) for k in range(1, N + 1)})
SPRITES = {r: neon.SkinSprites(COLS + [GREY], r, skin="orb") for r in LEVEL_R}
STARS = [(fx_rng.uniform(0, W), fx_rng.uniform(0, H), fx_rng.uniform(0.6, 2.0), fx_rng.uniform(0.06, 0.25)) for _ in range(260)]

def draw_ball(x, y, r, ci, glow=True):
    lv = min(LEVEL_R, key=lambda q: (q < r - 0.5, abs(q - r)))
    spr = SPRITES[lv]
    k = r / lv
    ctx.save(); ctx.translate(x, y); ctx.scale(k, k)
    if glow:
        s, G = spr.glow[ci]
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source_surface(s, -G, -G); ctx.paint(); ctx.restore()
    s, P = spr.core[ci]
    ctx.set_source_surface(s, -P, -P); ctx.paint()
    ctx.restore()

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    rc = RING_COL
    if payoff_t is not None:
        rc = neon.mix(RING_COL, COLS[colour[winner]], min(1.0, (t - payoff_t) / 0.4))
    elif holder is not None:
        rc = neon.mix(RING_COL, COLS[colour[holder]], 0.35)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 900)
    ga = 0.04 + 0.08 * pr + 0.02 * math.sin(t * 2.0)
    if payoff_t is not None:
        ga = 0.25 * math.exp(-(t - payoff_t) * 0.7) + 0.08
    rg.add_color_stop_rgba(0, *rc, ga); rg.add_color_stop_rgba(1, *rc, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for x, y, rr, a in STARS:
        ctx.set_source_rgba(0.8, 0.8, 1.0, a * (0.7 + 0.3 * math.sin(t * 1.3 + x))); ctx.arc(x, y, rr, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    ctx.save()
    shake = 0.0
    for et, kind, data in events[-30:]:
        if kind == "pop" and 0 <= t - et < 0.4:
            shake = max(shake, (10 if payoff_t is not None and et == payoff_t else 6) * (1 - (t - et) / 0.4))
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    # floor glow of the ring in the winner's colour after the payoff
    if payoff_t is not None:
        k = min(1.0, (t - payoff_t) / 0.5)
        gr = cairo.RadialGradient(CX, CY, 0, CX, CY, RR)
        cw = COLS[colour[winner]]
        gr.add_color_stop_rgba(0, *cw, 0.10 * k); gr.add_color_stop_rgba(0.8, *cw, 0.22 * k); gr.add_color_stop_rgba(1, *cw, 0.32 * k)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(gr); ctx.arc(CX, CY, RR, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    tension = 0.0
    if holder is not None:
        left = fuse_end - t
        tension = max(0.0, 1 - left / (4 * song.beat)) * 0.5
    neon.ring(ctx, CX, CY, RR, rc, t, heat=tension * 0.6, width=5.5)
    # wall-hit flashes, pass flashes, pop shockwaves
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, data in events[-90:]:
        if kind == "hit" and 0 <= t - et < 0.3:
            a = 1 - (t - et) / 0.3
            x, y, c = data
            gr = cairo.RadialGradient(x, y, 0, x, y, 46)
            gr.add_color_stop_rgba(0, *COLS[c], 0.5 * a); gr.add_color_stop_rgba(1, *COLS[c], 0)
            ctx.set_source(gr); ctx.arc(x, y, 46, 0, 2 * math.pi); ctx.fill()
        if kind == "pass" and 0 <= t - et < 0.35:
            a = 1 - (t - et) / 0.35
            x, y, c = data
            ctx.set_source_rgba(1.0, 0.85, 0.5, 0.7 * a); ctx.set_line_width(3)
            ctx.new_path(); ctx.arc(x, y, 10 + 50 * (1 - a), 0, 2 * math.pi); ctx.stroke()
        if kind == "pop" and 0 <= t - et < 0.9:
            a = 1 - (t - et) / 0.9
            x, y, c, r0 = data
            ctx.set_source_rgba(*COLS[c], 0.75 * a); ctx.set_line_width(3 + 12 * a)
            ctx.new_path(); ctx.arc(x, y, r0 + 420 * (1 - a), 0, 2 * math.pi); ctx.stroke()
            gr = cairo.RadialGradient(x, y, 0, x, y, r0 * 3)
            gr.add_color_stop_rgba(0, 1, 1, 1, 0.8 * a ** 2); gr.add_color_stop_rgba(0.4, *COLS[c], 0.4 * a ** 2); gr.add_color_stop_rgba(1, *COLS[c], 0)
            ctx.set_source(gr); ctx.arc(x, y, r0 * 3, 0, 2 * math.pi); ctx.fill()
        if kind == "newfuse" and 0 <= t - et < 0.35:
            # the fuse spark flies from the blast to the next holder
            h, x0, y0 = data
            k = (t - et) / 0.35
            x = x0 + (p[h, 0] - x0) * k; y = y0 + (p[h, 1] - y0) * k
            gr = cairo.RadialGradient(x, y, 0, x, y, 30)
            gr.add_color_stop_rgba(0, 1, 0.95, 0.8, 0.9); gr.add_color_stop_rgba(1, 1, 0.6, 0.2, 0)
            ctx.set_source(gr); ctx.arc(x, y, 30, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    # spark streams flying into survivors
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for st_, x0, y0, j, c in streams:
        k = (t - st_) / 0.35
        if not 0 <= k <= 1 or not alive[j] and j != winner:
            continue
        for m in range(6):
            km = min(1.0, max(0.0, k * 1.3 - m * 0.06))
            ang = m * 1.1 + j
            bend = math.sin(km * math.pi) * 40
            x = x0 + (p[j, 0] - x0) * km + math.cos(ang) * bend
            y = y0 + (p[j, 1] - y0) * km + math.sin(ang) * bend
            ctx.set_source_rgba(*COLS[c], 0.7 * (1 - km * 0.5)); ctx.arc(x, y, 4, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    # balls
    for i in range(N):
        if alive[i] or i == winner:
            draw_ball(p[i, 0], p[i, 1], rad[i], int(colour[i]))
    # bomb: countdown arc + fuse spark on the holder
    if holder is not None:
        h = holder
        x, y = p[h]; r = rad[h]
        left = max(0.0, fuse_end - t)
        frac = left / (fuse_end - fuse_start)
        hot = 1 - frac
        c = neon.mix((1.0, 0.95, 0.75), (1.0, 0.25, 0.20), min(1.0, hot * 1.3))
        beat_ph = (t / song.beat) % 1.0
        flash = 1.0 + (0.8 * (1 - beat_ph) if left < 4 * song.beat else 0.25 * (1 - beat_ph))
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        a0 = -math.pi / 2
        ctx.set_source_rgba(1, 1, 1, 0.12); ctx.set_line_width(3)
        ctx.new_path(); ctx.arc(x, y, r + 14, 0, 2 * math.pi); ctx.stroke()
        for w, a in [(26, 0.10), (12, 0.30)]:
            ctx.set_source_rgba(*c, a * flash); ctx.set_line_width(w)
            ctx.new_path(); ctx.arc(x, y, r + 13, a0, a0 + 2 * math.pi * frac); ctx.stroke()
        ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.5), 0.95); ctx.set_line_width(6)
        ctx.new_path(); ctx.arc(x, y, r + 14, a0, a0 + 2 * math.pi * frac); ctx.stroke()
        # danger glow grows as the fuse burns down
        gr = cairo.RadialGradient(x, y, r * 0.8, x, y, r * (1.8 + 0.8 * hot))
        gr.add_color_stop_rgba(0, *c, 0.30 * hot * flash); gr.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(gr); ctx.arc(x, y, r * (1.8 + 0.8 * hot), 0, 2 * math.pi); ctx.fill()
        # the burning tip of the fuse runs along the arc
        ta = a0 + 2 * math.pi * frac
        sx, sy = x + (r + 14) * math.cos(ta), y + (r + 14) * math.sin(ta)
        gr = cairo.RadialGradient(sx, sy, 0, sx, sy, 38)
        gr.add_color_stop_rgba(0, 1, 1, 0.9, 1.0); gr.add_color_stop_rgba(0.3, 1, 0.75, 0.3, 0.6); gr.add_color_stop_rgba(1, 1, 0.4, 0.1, 0)
        ctx.set_source(gr); ctx.arc(sx, sy, 38, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        for _ in range(2):
            a_ = fx_rng.uniform(0, 2 * math.pi); s_ = fx_rng.uniform(60, 260)
            sparks.append([sx, sy, math.cos(a_) * s_, math.sin(a_) * s_ - 60, fx_rng.uniform(5, 11), t, (1.0, 0.8, 0.4)])
    # sparks (moving)
    live = [s for s in sparks if t - s[5] < 0.7]
    sparks[:] = live
    by = {}
    for s in live:
        age = t - s[5]
        x = s[0] + s[2] * age * (1 - age * 0.6); y = s[1] + s[3] * age * (1 - age * 0.6)
        a = 1 - age / 0.7
        by.setdefault((s[6], round(a, 1)), []).append((x, y, s[4] * (0.5 + a)))
    for (c, a), q in by.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.4), alpha=a * 0.9)
    ctx.restore()
    # who is still in (top row of colour dots)
    for k in range(N):
        x = 540 + (k - (N - 1) / 2) * 92
        y = 330
        grey = not alive[k] and k != winner
        c = GREY if grey else COLS[k]
        big = 1.4 if k == winner else (1.15 if k == holder else 1.0)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        gr = cairo.RadialGradient(x, y, 0, x, y, 38 * big)
        gr.add_color_stop_rgba(0, *c, 0.10 if grey else 0.42); gr.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(gr); ctx.arc(x, y, 38 * big, 0, 2 * math.pi); ctx.fill(); ctx.restore()
        ctx.save(); ctx.set_source_rgba(*c, 0.3 if grey else 1.0); ctx.arc(x, y, 15 * big, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.2 if grey else 0.7); ctx.arc(x - 4, y - 5, 4 * big, 0, 2 * math.pi); ctx.fill(); ctx.restore()
        if k == holder:
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source_rgba(1.0, 0.8, 0.45, 0.8); ctx.set_line_width(2.5)
            ctx.new_path(); ctx.arc(x, y, 24, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    if counter and payoff_t is None:
        n = int(alive.sum())
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(120)
        txt = str(n)
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1700)
        ctx.text_path(txt)
        c2 = neon.mix(rc, (1, 1, 1), 0.45)
        ctx.set_source_rgba(*c2, 0.10); ctx.set_line_width(20); ctx.stroke_preserve()
        ctx.set_source_rgba(*c2, 0.95); ctx.fill()
        ctx.restore()
    if payoff_t is not None:
        dtp = t - payoff_t
        fa = max(0.0, 0.5 - dtp * 2.5)
        if fa > 0:
            ctx.set_source_rgba(*neon.mix(COLS[colour[winner]], (1, 1, 1), 0.7), fa); ctx.paint()
        if dtp < 1.4:
            a = 1 - dtp / 1.4
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*COLS[colour[winner]], 0.8 * a); ctx.set_line_width(4 + 18 * a)
            ctx.new_path(); ctx.arc(CX, CY, RR + 1500 * dtp, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
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
        if holder is not None and payoff_t is None and t >= fuse_end - 1e-9:
            pop(holder)
        if payoff_t is None or True:
            physics_step(dt)
        t += dt
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
    if t > 85:
        break

if ff:
    ff.stdin.close(); ff.wait()
rounds = []
for k, (pt, b) in enumerate(pop_log):
    ps = [x for x in pass_log if x[1] == k]
    last = ps[-1][0] if ps else None
    rounds.append((k, round(pt, 1), len(ps), None if last is None else round(pt - last, 2), int(colour[b])))
print("seed", SEED, "rounds (k, pop_t, passes, last_pass_before_pop, popped colour)", rounds)
print("winner", winner, "payoff", payoff_t and round(payoff_t, 2), "duration", round(t, 2), "final r", round(float(rad.max()), 1))
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
