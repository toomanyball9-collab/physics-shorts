"""2026-11-22 18:00 — chaos-divergence (new family): "One Survives"
48 rainbow balls are launched from the SAME spot, each aimed 0.0002° (3 µrad) apart, inside a neon ring
(zero gravity, constant speed) with three fixed neon pegs and a single gap at the top. They are ghosts (they pass
through each other), so at first they move as one ball. Every bounce off a peg multiplies the tiny difference:
the blob stretches into a line, a rainbow fan, then full chaos. Any ball that flies out through the gap is gone
(chime + whoosh) and drifts away. The counter shows how many are left. When only ONE is left, it wins: on the
next bar the ring floods with the winner's colour (shockwave + accent). Bounces are perfectly elastic.
Ring and peg hits play the notes. Tail crossfades back to the opening frame (one stacked blob) for a clean loop.

usage: python3 concepts/2026-11-22_pm_one_survives.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 8
CX, CY = W / 2, 930.0
R = 430.0
BR = float(os.environ.get("BR", "16"))
N = 48
G = float(os.environ.get("G", "0"))
VTOP = float(os.environ.get("VTOP", "540"))          # speed at the very top of the ring (= speed everywhere when G = 0)
GAP_C = -math.pi / 2                                  # gap centre: top
GW = math.radians(float(os.environ.get("GW", "16")))  # gap half-width (angle)
EPS = float(os.environ.get("EPS", "3e-6"))            # launch-angle step between neighbours (rad)
NPEG = int(os.environ.get("NPEG", "3"))               # fixed neon pegs (convex bumpers) inside the ring
PEG_R = float(os.environ.get("PEGR", "46"))
PEG_D = float(os.environ.get("PEGD", "200"))
PEG_ROT = math.radians(float(os.environ.get("PEGROT", "90")))
PEGS = [(CX + PEG_D * math.cos(PEG_ROT + 2 * math.pi * k / NPEG), CY + PEG_D * math.sin(PEG_ROT + 2 * math.pi * k / NPEG)) for k in range(NPEG)]
TAIL = 3.4
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 41
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
SCAN = os.environ.get("SCAN") == "1"
OUT = "out_noaudio.mp4"
MUSIC_SEED = int(os.environ.get("MSEED", "2026112265"))   # random_song(seed, avoid=last 8) -> celtic / flute
RECENT = [dict(genre="citypop", bpm=102, key="E", mode="major", lead="ep"),
          dict(genre="tropical", bpm=112, key="A", mode="major", lead="marimba"),
          dict(genre="musicbox", bpm=95, key="E", mode="harmonic_minor", lead="celesta"),
          dict(genre="cinematic", bpm=78, key="A#", mode="minor", lead="harp"),
          dict(genre="waltz", bpm=93, key="D", mode="major", lead="ep"),
          dict(genre="synthwave", bpm=104, key="G#", mode="dorian", lead="saw"),
          dict(genre="gamelan", bpm=94, key="D#", mode="major", lead="bell"),
          dict(genre="lofi", bpm=74, key="F#", mode="major", lead="kalimba")]

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)
song = music.random_song(MUSIC_SEED, avoid=RECENT) if MUSIC_SEED else music.Song.from_genre("ambient", seed=1)

COLS = [neon.hsv(0.83 * i / (N - 1), 0.78, 1.0) for i in range(N)]
PAL = {"bg": ((0.02, 0.02, 0.06), (0.00, 0.00, 0.02)), "ring": (0.92, 0.92, 1.0), "balls": COLS, "accent": (1, 1, 1)}

# launch: every ball from the same point, angles EPS apart
LX, LY = CX + rng.uniform(-60, 60), CY + rng.uniform(-60, 60)
LA = rng.uniform(-math.pi, math.pi)
E = -G * (CY - R) + 0.5 * VTOP ** 2                     # energy per unit mass: 0.5 v^2 - G y
def speed_at(y):
    return math.sqrt(max(0.0, 2 * (E + G * y)))
s0 = speed_at(LY)
ang = LA + EPS * (np.arange(N) - (N - 1) / 2)
p = np.stack([np.full(N, LX), np.full(N, LY)], 1)
v = np.stack([np.cos(ang) * s0, np.sin(ang) * s0], 1)
inside = np.ones(N, bool)
gone = np.zeros(N, bool)        # left the screen
esc_t = np.full(N, np.nan)
last_hit = np.full(N, -9.0)
t = 0.0
events, sparks, build_keys = [], [], []
trails = [[] for _ in range(N)]
winner = None
win_t = None
payoff_t = None
payoff_done = False
n_bounce = 0

def n_left():
    return int(inside.sum())

def progress():
    if payoff_done:
        return 1.0
    esc = N - n_left()
    return min(1.0, 0.22 * min(1.0, t / 22) + 0.78 * (esc / (N - 1)) ** 0.8)

def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi

BANG = math.asin(BR / R)

def physics_step(dt):
    global p, v, winner, win_t, payoff_t, n_bounce
    act = ~gone
    p[act] += v[act] * dt + np.array([0, 0.5 * G * dt * dt])
    v[act, 1] += G * dt
    d = p - (CX, CY)
    dist = np.hypot(d[:, 0], d[:, 1]) + 1e-9
    a = np.arctan2(d[:, 1], d[:, 0])
    rel = np.abs((a - GAP_C + math.pi) % (2 * math.pi) - math.pi)
    # inside balls hitting the ring
    for i in np.where(inside & (dist + BR > R))[0]:
        if rel[i] < GW - BANG:                       # fully inside the gap: it is getting out
            if dist[i] > R + BR:
                inside[i] = False
                esc_t[i] = t
                pan = float(d[i, 0] / R)
                song.sfx(t, "chime", pan, 0.8)
                song.sfx(t + 0.01, "whoosh", pan, 0.35)
                events.append((t, "escape", i))
                gx, gy = CX + R * math.cos(GAP_C), CY + R * math.sin(GAP_C)
                sparks.extend([[p[i][0], p[i][1], fx_rng.uniform(10, 22), t, COLS[i]] for _ in range(10)])
                if n_left() == 1 and winner is None:
                    winner = int(np.where(inside)[0][0])
                    win_t = t
                    payoff_t = song.next_bar(t + 0.25)
            continue
        if rel[i] < GW + BANG and dist[i] > R - BR * 0.2:
            # clipping the gap's end cap: bounce off the cap (a point at the edge of the gap)
            pass
        u = d[i] / dist[i]
        p[i] -= u * (dist[i] + BR - R)
        vn = np.dot(v[i], u)
        if vn > 0:
            v[i] -= 2 * vn * u
            sp = speed_at(p[i][1]); cur = math.hypot(*v[i]) + 1e-9
            v[i] *= sp / cur                          # exact energy conservation
            n_bounce += 1
            if t - last_hit[i] > 0.05:
                last_hit[i] = t
                song.note(t, float(d[i, 0] / R))
                events.append((t, "hit", (float(CX + u[0] * R), float(CY + u[1] * R), i)))
    # fixed pegs (convex: every hit multiplies the tiny differences)
    for (pxc, pyc) in PEGS:
        db = p - (pxc, pyc)
        dbn = np.hypot(db[:, 0], db[:, 1]) + 1e-9
        for i in np.where((~gone) & (dbn < PEG_R + BR))[0]:
            u = db[i] / dbn[i]
            p[i] = np.array([pxc, pyc]) + u * (PEG_R + BR)
            vn = np.dot(v[i], u)
            if vn < 0:
                v[i] -= 2 * vn * u
                sp = speed_at(p[i][1]); cur = math.hypot(*v[i]) + 1e-9
                v[i] *= sp / cur
                n_bounce += 1
                if t - last_hit[i] > 0.05:
                    last_hit[i] = t
                    song.note(t, float((pxc - CX) / R))
                    events.append((t, "bump", (float(pxc + u[0] * PEG_R), float(pyc + u[1] * PEG_R), i)))
    # gap end caps act like small posts
    for side in (-1, 1):
        ca = GAP_C + side * GW
        cxp, cyp = CX + R * math.cos(ca), CY + R * math.sin(ca)
        dc = p - (cxp, cyp)
        dcn = np.hypot(dc[:, 0], dc[:, 1]) + 1e-9
        for i in np.where((~gone) & (dcn < BR))[0]:
            u = dc[i] / dcn[i]
            p[i] = np.array([cxp, cyp]) + u * BR
            vn = np.dot(v[i], u)
            if vn < 0:
                v[i] -= 2 * vn * u
                sp = speed_at(p[i][1]); cur = math.hypot(*v[i]) + 1e-9
                v[i] *= sp / cur
                if t - last_hit[i] > 0.05:
                    last_hit[i] = t
                    song.note(t, float((cxp - CX) / R))
                    events.append((t, "hit", (cxp, cyp, i)))
    # escaped balls slide off the OUTSIDE of the ring (they can't pass through the tube)
    for i in np.where((~inside) & (~gone) & (dist - BR < R) & (dist > R * 0.8))[0]:
        if rel[i] < GW:
            continue
        u = d[i] / dist[i]
        p[i] = np.array([CX, CY]) + u * (R + BR)
        vn = np.dot(v[i], u)
        if vn < 0:
            v[i] -= 1.6 * vn * u
    # off screen -> gone
    off = (~inside) & ((p[:, 1] > H + 80) | (p[:, 0] < -80) | (p[:, 0] > W + 80))
    gone[off] = True

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = neon.BallSprites(COLS, BR, glow=3.4, glow_alpha=0.6)
WHITE_SPR = neon.BallSprites([(1, 1, 1)], BR, glow=3.4, glow_alpha=0.5)

def ring_arc(a0, a1, rgb, alpha=1.0, width=6.0, glow=1.0):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for w, a in [(46, 0.05), (28, 0.09), (16, 0.16), (9, 0.35)]:
        ctx.set_source_rgba(*rgb, a * alpha * glow); ctx.set_line_width(w)
        ctx.new_path(); ctx.arc(CX, CY, R, a0, a1); ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*neon.mix(rgb, (1, 1, 1), 0.6), 0.95 * alpha); ctx.set_line_width(width)
    ctx.new_path(); ctx.arc(CX, CY, R, a0, a1); ctx.stroke(); ctx.restore()

def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    idx_in = np.where(inside)[0]
    if payoff_done:
        gcol = COLS[winner]
    else:
        gcol = tuple(np.mean([COLS[i] for i in idx_in], axis=0)) if len(idx_in) else (1, 1, 1)
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 950)
    ga = 0.04 + 0.12 * pr + 0.03 * math.sin(t * 2.0)
    if payoff_done:
        ga = 0.22 * math.exp(-(t - payoff_t) * 0.9) + 0.06
    rg.add_color_stop_rgba(0, *gcol, ga); rg.add_color_stop_rgba(1, *gcol, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 0.0
    if payoff_done:
        shake = 16 * math.exp(-(t - payoff_t) * 6)
    if shake > 0.3:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    # ring (with the gap) — floods with the winner's colour at the payoff
    rc = PAL["ring"]
    glow = 1.0 + 0.5 * max(0.0, 1 - (t - max([e[0] for e in events[-60:] if e[1] == "hit"] or [-9])) / 0.12)
    if payoff_done:
        k = min(1.0, (t - payoff_t) / 0.25)
        rc = neon.mix(rc, COLS[winner], 0.85 * k)
        glow = 1.0 + 1.6 * math.exp(-(t - payoff_t) * 2.5)
    ring_arc(GAP_C + GW, GAP_C + 2 * math.pi - GW, rc, 1.0, 6.0, glow)
    # gap caps
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for side in (-1, 1):
        ca = GAP_C + side * GW
        ex, ey = CX + R * math.cos(ca), CY + R * math.sin(ca)
        gr = cairo.RadialGradient(ex, ey, 0, ex, ey, 34)
        gr.add_color_stop_rgba(0, *neon.mix(rc, (1, 1, 1), 0.6), 0.95); gr.add_color_stop_rgba(0.4, *rc, 0.45)
        gr.add_color_stop_rgba(1, *rc, 0)
        ctx.set_source(gr); ctx.arc(ex, ey, 34, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    # pegs (neon bumpers) — flash when hit
    last_b = {}
    for et, kind, info in events[-200:]:
        if kind == "bump":
            k = min(range(NPEG), key=lambda j: (PEGS[j][0] - info[0]) ** 2 + (PEGS[j][1] - info[1]) ** 2)
            last_b[k] = (et, info[2])
    for k, (pxc, pyc) in enumerate(PEGS):
        et, bi = last_b.get(k, (-9, 0))
        fl = max(0.0, 1 - (t - et) / 0.2)
        pc = neon.mix(rc, COLS[bi], 0.6 * fl)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        gr = cairo.RadialGradient(pxc, pyc, PEG_R * 0.2, pxc, pyc, PEG_R * 1.9)
        gr.add_color_stop_rgba(0, *pc, 0.10 + 0.25 * fl); gr.add_color_stop_rgba(0.5, *pc, 0.07 + 0.15 * fl); gr.add_color_stop_rgba(1, *pc, 0)
        ctx.set_source(gr); ctx.arc(pxc, pyc, PEG_R * 1.9, 0, 2 * math.pi); ctx.fill()
        for w, a_ in [(26, 0.07), (14, 0.15), (7, 0.35)]:
            ctx.set_source_rgba(*pc, a_ * (1 + 1.2 * fl)); ctx.set_line_width(w)
            ctx.new_path(); ctx.arc(pxc, pyc, PEG_R, 0, 2 * math.pi); ctx.stroke()
        ctx.restore()
        ctx.set_source_rgba(*neon.mix(pc, (1, 1, 1), 0.6), 0.95); ctx.set_line_width(4.5)
        ctx.new_path(); ctx.arc(pxc, pyc, PEG_R, 0, 2 * math.pi); ctx.stroke()
    # hit flashes on the ring
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, info in events[-200:]:
        if kind in ("hit", "bump") and 0 <= t - et < 0.3:
            x, y, i = info; age = (t - et) / 0.3
            ctx.set_source_rgba(*neon.mix(COLS[i], (1, 1, 1), 0.4), 0.45 * (1 - age)); ctx.set_line_width(2.5)
            ctx.new_path(); ctx.arc(x, y, 8 + 22 * age, 0, 2 * math.pi); ctx.stroke()
        if kind == "escape" and 0 <= t - et < 0.6:
            age = (t - et) / 0.6
            gx, gy = CX + R * math.cos(GAP_C), CY + R * math.sin(GAP_C)
            ctx.set_source_rgba(*COLS[info], 0.6 * (1 - age)); ctx.set_line_width(3 + 6 * (1 - age))
            ctx.new_path(); ctx.arc(gx, gy, 20 + 120 * age, 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    # payoff shockwave from the winner + around the ring
    if payoff_done:
        age = t - payoff_t
        if age < 1.3:
            a = 1 - age / 1.3
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*COLS[winner], 0.8 * a); ctx.set_line_width(4 + 18 * a)
            ctx.new_path(); ctx.arc(CX, CY, R + 1500 * age, 0, 2 * math.pi); ctx.stroke()
            wx, wy = p[winner]
            ctx.set_source_rgba(*neon.mix(COLS[winner], (1, 1, 1), 0.5), 0.9 * a); ctx.set_line_width(3 + 8 * a)
            ctx.new_path(); ctx.arc(wx, wy, BR + 400 * age, 0, 2 * math.pi); ctx.stroke()
            ctx.restore()
    # trails
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    together = False
    for i in range(N):
        tr = trails[i]
        if len(tr) < 2 or gone[i]:
            continue
        c = (1, 1, 1) if together else COLS[i]
        L = len(tr)
        for j in range(1, L):
            a = (j / L) ** 1.4 * 0.42
            ctx.set_source_rgba(*c, a); ctx.set_line_width(2 + 8 * j / L)
            ctx.move_to(*tr[j - 1]); ctx.line_to(*tr[j]); ctx.stroke()
    ctx.restore()
    # balls (all 48 drawn; while they still overlap, a white core shows they are stacked on one spot)
    vis = [i for i in range(N) if not gone[i]]
    order = sorted(vis, key=lambda i: (i == winner, i))
    SPR.draw(ctx, [tuple(p[i]) for i in order], order)
    q = p[inside] if inside.any() else p
    spread = float(np.hypot(*(q.max(0) - q.min(0))))
    wa = max(0.0, 1 - spread / (1.6 * BR))
    if wa > 0:
        WHITE_SPR.draw(ctx, [tuple(q.mean(0))], [0], glow=False)
    if winner is not None:
        wx, wy = p[winner]
        pulse = 0.5 + 0.5 * math.sin(t * 8)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_rgba(*neon.mix(COLS[winner], (1, 1, 1), 0.5), 0.35 + 0.35 * pulse); ctx.set_line_width(3)
        ctx.new_path(); ctx.arc(wx, wy, BR * (1.8 + 0.3 * pulse), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    live = [s for s in sparks if t - s[3] < 0.55]
    sparks[:] = live
    groups = {}
    for x, y, sz, st, c in live:
        al = 1 - (t - st) / 0.55
        groups.setdefault((c, round(al, 1)), []).append((x, y, sz * (0.6 + al)))
    for (c, al), q in groups.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.4), alpha=al * 0.9)
    ctx.restore()
    if counter:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(120)
        txt = str(n_left())
        xb, yb, tw, th, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1690)
        ctx.text_path(txt)
        cc = neon.mix(gcol, (1, 1, 1), 0.45)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(22); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if payoff_done:
        fa = max(0.0, 0.35 - (t - payoff_t) * 1.8)
        if fa > 0:
            ctx.set_source_rgba(*neon.mix(COLS[winner], (1, 1, 1), 0.6), fa); ctx.paint()
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
spread_log = []
while True:
    for _ in range(SUB):
        physics_step(dt)
        if payoff_t is not None and not payoff_done and t >= payoff_t:
            payoff_done = True
            song.accent(t)
            song.sfx(t, "chime", 0.0, 1.0)
            song.sfx(t + 0.01, "shatter", 0.0, 0.35)
            events.append((t, "payoff", winner))
            for k in range(80):
                a = fx_rng.uniform(0, 2 * math.pi)
                sparks.append([CX + R * math.cos(a), CY + R * math.sin(a), fx_rng.uniform(10, 26), t, COLS[winner]])
        t += dt
    for i in range(N):
        if not gone[i]:
            trails[i].append((float(p[i][0]), float(p[i][1])))
            if len(trails[i]) > 16:
                trails[i].pop(0)
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 120 == 0:
        q = p[inside] if inside.any() else p
        spread_log.append((round(t), round(float(np.hypot(*(q.max(0) - q.min(0)))), 0)))
    if not SIM_ONLY:
        draw(); surf.flush()
        if first is None:
            first = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
            c2 = cairo.Context(first); c2.set_source_surface(surf, 0, 0); c2.paint()
        ff.stdin.write(bytes(surf.get_data()))
    frame += 1
    if payoff_done and t >= payoff_t + TAIL:
        break
    if t > 75:
        break
    if SCAN and ((not np.all(np.isnan(esc_t)) and np.nanmin(esc_t) < 9.0) or (win_t is not None and win_t > 61) or t > 63 and win_t is None):
        break

if ff:
    ff.stdin.close(); ff.wait()
et = np.sort(esc_t[~np.isnan(esc_t)])
if SCAN:
    clump = max([int(np.sum((et >= x) & (et < x + 0.5))) for x in et] or [0])
    ok = len(et) >= N - 1 and et[0] >= 9 and win_t is not None and 53 <= win_t <= 60.5 and inside[winner]
    print("SCAN", SEED, "ok" if ok else "--", "first", round(float(et[0]), 1) if len(et) else None, "n", len(et),
          "win", win_t and round(win_t, 1), "pay", payoff_t and round(payoff_t, 1), "clump", clump,
          "q", [round(float(x), 1) for x in et[[0, 11, 23, 35, 44]]] if len(et) >= 45 else None)
    sys.exit(0)
print("seed", SEED, "spread", spread_log[:12])
print("escapes", len(et), "first", et[:3].round(1).tolist() if len(et) else None, "deciles", et[::5].round(1).tolist())
print("winner", winner, "win_t", win_t and round(win_t, 2), "payoff", payoff_t and round(payoff_t, 2), "duration", round(t, 2),
      "winner escaped later", bool(winner is not None and not inside[winner]), "bounces", n_bounce, "bumps", sum(1 for e in events if e[1] == "bump"))
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
