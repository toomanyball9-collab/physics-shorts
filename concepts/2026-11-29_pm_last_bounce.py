"""2026-11-29 18:00 — floor-survival (new family): "Last Bounce"
8 neon balls bounce on two floors of glowing neon tiles inside a tall neon box (gravity; every tile is a
trampoline that sends the ball back up to the same height, so they bounce in time with the music: one
bounce = 2 beats). Every bounce WEARS the tile it lands on: the tile gets thinner (thickness = bounces left)
and turns red on its last bounce. Landing on a red tile breaks it and the ball falls through. Fall through
the upper floor -> you land on the lower floor; fall through the lower floor -> you're OUT (grey, drops into
the pit). Colour dots on top = who's still in, counter = balls left. When one ball is left, on the next bar
the arena floods with the winner's colour.
Sound: tile bounces = music (song.note); wall hits = tick; tile breaking = shatter; ball out = zap (+ thump in
the pit); payoff = accent.

usage: python3 concepts/2026-11-29_pm_last_bounce.py <seed> [--sim | --audio | --search N]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 6
DT = 1.0 / (FPS * SUB)
G = 1500.0
TAIL = 3.0
BR = float(os.environ.get("BR", "28"))
NB = 8
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY or "--search" in sys.argv
OUT = "out_noaudio.mp4"
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
# random_song(2026112921, avoid=all posted recipes + 11-29 08:00 celtic) -> gamelan 93 C phrygian marimba
MUSIC_SEED = int(os.environ.get("MSEED", "2026112921"))
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
          dict(genre="kpop_bright", bpm=117, key="E", mode="major", lead="pluck"),
          dict(genre="dreamwave", bpm=88, key="D#", mode="lydian", lead="celesta"),
          dict(genre="celtic", bpm=102, key="A#", mode="dorian", lead="harp")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)
BEAT = song.beat
BAR = song.chord_len
V0 = G * BEAT                     # bounce period = 2 beats

COLS = [(1.0, 0.30, 0.38), (1.0, 0.60, 0.20), (1.0, 0.90, 0.30), (0.45, 1.0, 0.45),
        (0.25, 0.90, 1.0), (0.35, 0.50, 1.0), (0.75, 0.40, 1.0), (1.0, 0.45, 0.85)]
GREY = (0.42, 0.45, 0.55)
PAL = {"bg": ((0.02, 0.015, 0.06), (0.00, 0.00, 0.025)), "ring": (0.8, 0.85, 1.0), "balls": COLS, "accent": (1, 1, 1)}
BOX = (0.62, 0.70, 1.0)
TILE_C = (0.45, 0.85, 1.0)
HOT = (1.0, 0.22, 0.25)

XL, XR = 120.0, 960.0
FLOORS = [float(x) for x in os.environ.get("FLOORS", "760,1150,1540").split(",")]   # top surface of each floor
NF = len(FLOORS)
OUT_LVL = NF
PIT_Y = 1790.0
NT = int(os.environ.get("NT", "12"))
TW = (XR - XL) / NT
# life (bounces a tile can take) per floor "min-max,..." -> lower floors are thicker
LIVES = [tuple(int(y) for y in x.split("-")) for x in os.environ.get("LIVES", "2-10,7-28,6-40").split(",")]
LIFE_MAX = max(b for a, b in LIVES)
TH0, TH1 = 4.0, float(os.environ.get("TH1", "1.1"))


def thick(L):
    return 7.0 + 21.0 * (max(L, 0) / LIFE_MAX) ** 0.6                # tile thickness = TH0 + TH1 * life

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)


class World:
    pass


def setup():
    w = World()
    w.life = [rng.integers(a, b + 1, NT).astype(float) for a, b in LIVES]
    w.flash = [np.zeros(NT) for _ in range(NF)]
    w.p = np.zeros((NB, 2)); w.v = np.zeros((NB, 2))
    xs = XL + TW * 0.5 + (np.arange(NB) + 0.5) * (XR - XL - TW) / NB
    order = rng.permutation(NB)
    for k, i in enumerate(order):
        w.p[i] = [xs[k], 0]
        # random phase in the bounce: height on the parabola above floor 1
        ph = rng.uniform(0, 1)
        tt = ph * 2 * BEAT
        y = FLOORS[0] - BR - (V0 * tt - 0.5 * G * tt * tt)
        w.p[i, 1] = y
        w.v[i] = [rng.choice([-1, 1]) * rng.uniform(140, 300), -V0 + G * tt]
    w.level = np.zeros(NB, int)       # 0: on floor 1, 1: on floor 2, 2: out
    w.out_t = np.full(NB, np.nan)
    w.pit = []
    return w


wd = setup()
t = 0.0
events, sparks, shards, build_keys = [], [], [], []
note_cool = np.full(NB, -9.0)
wall_cool = -9.0
payoff_pending = None
payoff_t = None
winner = None
last_out = None
falls = []
trails = [[] for _ in range(NB)]
drop2 = []


def alive():
    return np.where(wd.level < OUT_LVL)[0]


def progress():
    if payoff_t is not None:
        return 1.0
    n = len(alive())
    return float(np.clip(0.12 + 0.75 * (NB - n) / (NB - 1) + 0.13 * min(1, t / 58), 0, 1))


def tile_of(x):
    k = int((x - XL) // TW)
    return min(max(k, 0), NT - 1)


def break_tile(f, k):
    wd.life[f][k] = 0
    x0 = XL + k * TW
    y = FLOORS[f]
    song.sfx(t, "shatter", float(((x0 + TW / 2) - W / 2) / 450), 0.45)
    for q in range(4):
        shards.append(dict(x=x0 + (q + 0.5) * TW / 4, y=y + 6, vx=fx_rng.uniform(-120, 120), vy=fx_rng.uniform(-150, 50),
                           a=fx_rng.uniform(0, 3), va=fx_rng.uniform(-5, 5), L=TW / 3.2, c=HOT, t0=t))
    for _ in range(14):
        sparks.append([x0 + fx_rng.uniform(0, TW), y + fx_rng.normal(0, 5), fx_rng.uniform(6, 14), t, HOT])
    events.append((t, "break", f, k))


def step(dt):
    global wall_cool, payoff_pending, winner, last_out
    p, v = wd.p, wd.v
    act = wd.level < OUT_LVL
    v[:, 1] += G * dt
    pp = p.copy()
    p += v * dt
    # walls
    for i in range(NB):
        if p[i, 0] < XL + BR and v[i, 0] < 0:
            p[i, 0] = 2 * (XL + BR) - p[i, 0]; v[i, 0] *= -1
            if act[i] and t - wall_cool > 0.12:
                wall_cool = t; song.sfx(t, "tick", -0.8, 0.18)
        if p[i, 0] > XR - BR and v[i, 0] > 0:
            p[i, 0] = 2 * (XR - BR) - p[i, 0]; v[i, 0] *= -1
            if act[i] and t - wall_cool > 0.12:
                wall_cool = t; song.sfx(t, "tick", 0.8, 0.18)
    # floors
    for i in range(NB):
        if wd.level[i] >= OUT_LVL:
            continue
        for f in range(NF):
            y = FLOORS[f]
            k = tile_of(p[i, 0])
            if v[i, 1] > 0 and pp[i, 1] < y and p[i, 1] + BR > y and (pp[i, 1] + BR <= y or wd.life[f][k] > 0):
                if wd.life[f][k] <= 0:
                    continue                         # hole: keep falling
                if wd.life[f][k] <= 1 and payoff_pending is None:
                    break_tile(f, k)                 # the last bounce breaks it -> falls through
                    falls.append((round(t, 2), i, f))
                    continue
                if payoff_pending is None:
                    wd.life[f][k] -= 1
                wd.flash[f][k] = 1.0
                p[i, 1] = y - BR - (p[i, 1] + BR - y)
                v[i, 1] = -V0
                if f > wd.level[i]:
                    drop2.append((round(t, 1), f))
                wd.level[i] = f
                if t - note_cool[i] > 0.05:
                    note_cool[i] = t
                    song.note(t, float((p[i, 0] - W / 2) / 450), vel=0.8)
                if len(sparks) < 300:
                    for _ in range(3):
                        sparks.append([p[i, 0] + fx_rng.normal(0, 10), y, fx_rng.uniform(5, 10), t, COLS[i]])
            # underside of a floor (a ball bouncing up from below)
            th = thick(LIFE_MAX) + 4
            if v[i, 1] < 0 and pp[i, 1] - BR >= y + th > p[i, 1] - BR:
                k = tile_of(p[i, 0])
                if wd.life[f][k] > 0:
                    p[i, 1] = 2 * (y + th + BR) - p[i, 1]; v[i, 1] *= -1
        # fell below the lower floor -> out
        if p[i, 1] - BR > FLOORS[-1] + 30 and wd.level[i] < OUT_LVL:
            wd.level[i] = OUT_LVL
            wd.out_t[i] = t
            last_out = t
            song.sfx(t, "zap", float((p[i, 0] - W / 2) / 450), 0.5)
            events.append((t, "out", i))
            al = alive()
            if len(al) == 1 and payoff_pending is None:
                winner = int(al[0])
                payoff_pending = song.next_bar(t + 0.25)
    for sh in shards:
        sh["vy"] += G * 0.8 * dt
        sh["x"] += sh["vx"] * dt; sh["y"] += sh["vy"] * dt; sh["a"] += sh["va"] * dt
    # pit: out balls come to rest on the pit floor in a row
    for i in range(NB):
        if wd.level[i] == OUT_LVL:
            if i not in wd.pit and p[i, 1] + BR >= PIT_Y:
                wd.pit.append(i)
                song.sfx(t, "thump", float((p[i, 0] - W / 2) / 450), 0.35)
            if i in wd.pit:
                slot = wd.pit.index(i)
                tx = W / 2 + (slot - 3.5) * (2 * BR + 10)
                p[i, 1] = PIT_Y - BR; v[i, 1] = 0
                p[i, 0] += (tx - p[i, 0]) * min(1, 6 * dt); v[i, 0] = 0
    # ball-ball collisions (equal mass, elastic) among balls still in play
    idx = alive()
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            i, j = idx[a], idx[b]
            d = p[j] - p[i]
            dist = math.hypot(d[0], d[1])
            if 1e-6 < dist < 2 * BR:
                n = d / dist
                rel = (v[j] - v[i]) @ n
                over = 2 * BR - dist
                p[i] -= n * over / 2; p[j] += n * over / 2
                if rel < 0:
                    v[i] += rel * n; v[j] -= rel * n
                    song.sfx(t, "tick", float((p[i, 0] - W / 2) / 450), 0.22)
    # keep horizontal speeds lively but moderate; vertical speed bounded
    for i in idx:
        s = abs(v[i, 0])
        if s < 90:
            v[i, 0] = math.copysign(90, v[i, 0] if v[i, 0] != 0 else 1)
        elif s > 420:
            v[i, 0] *= 420 / s
        v[i, 1] = float(np.clip(v[i, 1], -V0 * 1.05, 1600))


def do_payoff():
    global payoff_t
    payoff_t = t
    song.accent(t)
    song.sfx(t, "chime", 0.0, 0.9)
    x, y = wd.p[winner]
    for _ in range(80):
        a = fx_rng.uniform(0, 2 * math.pi); r = fx_rng.uniform(10, 120)
        sparks.append([x + r * math.cos(a), y + r * math.sin(a), fx_rng.uniform(8, 20), t, COLS[winner]])
    events.append((t, "payoff", winner))


if "--search" in sys.argv:
    pass

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = neon.BallSprites(COLS + [GREY], BR, glow=2.4, glow_alpha=0.55)
STARS = [(fx_rng.uniform(0, W), fx_rng.uniform(0, H), fx_rng.uniform(0.6, 2.0), fx_rng.uniform(0.05, 0.22)) for _ in range(200)]


def tube(pts, rgb, alpha=1.0, width=5.0, glowk=1.0):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for w_, a in [(40, 0.04), (24, 0.08), (13, 0.15), (7, 0.30)]:
        ctx.set_source_rgba(*rgb, min(1.0, a * alpha * glowk)); ctx.set_line_width(w_ * width / 5)
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


def glow_dot(x, y, r, c, a):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *c, a); g.add_color_stop_rgba(0.4, *c, a * 0.35); g.add_color_stop_rgba(1, *c, 0)
    ctx.set_source(g); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill(); ctx.restore()


def rrect(x, y, w, h, r):
    r = min(r, h / 2, w / 2)
    ctx.new_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi); ctx.close_path()


def draw_tiles(flood):
    for f in range(NF):
        y = FLOORS[f]
        for k in range(NT):
            L = wd.life[f][k]
            if L <= 0:
                continue
            x0 = XL + k * TW + 3
            th = thick(L)
            last = L <= 1
            c = HOT if last else neon.mix(TILE_C, (1.0, 0.75, 0.35), float(np.clip((3 - L) / 2, 0, 1)) * 0.7)
            if flood is not None:
                c = neon.mix(c, COLS[winner], flood)
            fl = wd.flash[f][k]
            pulse = 0.5 + 0.5 * math.sin(t * 14 + k) if last else 0.0
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            gr = cairo.LinearGradient(0, y - 30, 0, y + th + 30)
            ga = 0.10 + 0.25 * fl + 0.12 * pulse + (0.25 * flood if flood else 0)
            gr.add_color_stop_rgba(0, *c, 0); gr.add_color_stop_rgba(0.5, *c, ga); gr.add_color_stop_rgba(1, *c, 0)
            ctx.set_source(gr); ctx.rectangle(x0 - 6, y - 30, TW - 0, th + 60); ctx.fill(); ctx.restore()
            rrect(x0, y, TW - 6, th, 4)
            ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.25 + 0.4 * fl), 0.55 + 0.25 * fl + 0.2 * pulse); ctx.fill_preserve()
            ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.6), 0.9); ctx.set_line_width(2); ctx.stroke()


def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    flood = None
    if payoff_t is not None:
        flood = min(1.0, (t - payoff_t) / 0.4)
    gc = COLS[winner] if flood is not None else neon.mix((0.45, 0.45, 1.0), HOT, max(0.0, pr - 0.6) / 0.4 * 0.5)
    rg = cairo.RadialGradient(W / 2, H * 0.55, 0, W / 2, H * 0.55, 1100)
    ga = 0.04 + 0.10 * pr if flood is None else 0.10 + 0.22 * math.exp(-(t - payoff_t) * 0.8)
    rg.add_color_stop_rgba(0, *gc, ga); rg.add_color_stop_rgba(1, *gc, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for x, y, rr, a in STARS:
        ctx.set_source_rgba(0.75, 0.8, 1.0, a * (0.7 + 0.3 * math.sin(t * 1.3 + x))); ctx.arc(x, y, rr, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    # box
    bc = BOX if flood is None else neon.mix(BOX, COLS[winner], flood)
    for x in (XL - 8, XR + 8):
        tube([(x, 330), (x, FLOORS[-1] + 60)], bc, 0.9, 4.5, 1.0 + (0.8 * flood if flood else 0))
    # pit
    tube([(XL - 8, PIT_Y + 8), (XR + 8, PIT_Y + 8)], (0.45, 0.5, 0.75), 0.55, 4.0)
    draw_tiles(flood)
    # balls
    pos, ci = [], []
    for i in range(NB):
        x, y = wd.p[i]
        if y > H + 40:
            continue
        pos.append((x, y)); ci.append(len(COLS) if wd.level[i] == OUT_LVL else i)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for i in range(NB):
        if wd.level[i] >= OUT_LVL:
            continue
        tr = trails[i]
        for k, (x, y) in enumerate(tr):
            a = (k + 1) / len(tr)
            ctx.set_source_rgba(*COLS[i], 0.16 * a); ctx.arc(x, y, BR * (0.35 + 0.5 * a), 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    SPR.draw(ctx, pos, ci)
    if winner is not None and flood is not None:
        x, y = wd.p[winner]
        glow_dot(x, y, 140, COLS[winner], 0.5 * (1 - 0.5 * flood) + 0.2)
    # shards: glowing chunks of the broken tile tumbling down
    keep = []
    for s in shards:
        age = t - s["t0"]
        if age > 1.6 or s["y"] > H + 50:
            continue
        keep.append(s)
        a = max(0.0, 1 - age / 1.6)
        sz = s["L"] * 0.8
        glow_dot(s["x"], s["y"], sz * 1.8, s["c"], 0.35 * a)
        ctx.save(); ctx.translate(s["x"], s["y"]); ctx.rotate(s["a"])
        rrect(-sz / 2, -5, sz, 10, 3)
        ctx.set_source_rgba(*neon.mix(s["c"], (1, 1, 1), 0.35), 0.85 * a); ctx.fill()
        ctx.restore()
    shards[:] = keep
    lv = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = lv
    by = {}
    for x, y, sz, st, c in lv:
        al = 1 - (t - st) / 0.5
        by.setdefault((c, round(al, 1)), []).append((x, y - 30 * (t - st), sz * (0.5 + al)))
    for (c, al), q in by.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.5), alpha=al * 0.9)
    # who is still in: 8 colour dots on top
    for i in range(NB):
        x = W / 2 + (i - 3.5) * 74
        y = 220
        on = wd.level[i] < OUT_LVL
        c = COLS[i] if on else GREY
        if on:
            glow_dot(x, y, 34 if i != winner else 60, c, 0.55)
        ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.35 if on else 0.0), 0.95 if on else 0.35)
        ctx.arc(x, y, 13 if on else 9, 0, 2 * math.pi); ctx.fill()
    if counter and payoff_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(80)
        txt = f"{len(alive())}"
        xb, yb, tw, th_, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1892)
        ctx.text_path(txt)
        cc = neon.mix((0.85, 0.9, 1.0), (1, 1, 1), 0.3)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(18); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.92); ctx.fill()
        ctx.restore()
    if payoff_t is not None:
        dtp = t - payoff_t
        fa = max(0.0, 0.4 - dtp * 2.5)
        if fa > 0:
            ctx.set_source_rgba(*neon.mix(COLS[winner], (1, 1, 1), 0.6), fa); ctx.paint()
        if dtp < 1.3:
            a = 1 - dtp / 1.3
            x, y = wd.p[winner]
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*COLS[winner], 0.75 * a); ctx.set_line_width(4 + 16 * a)
            ctx.new_path(); ctx.arc(x, y, 40 + 1300 * dtp, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
        end = payoff_t + TAIL
        xf = (t - (end - 1.4)) / 1.4
        if xf > 0 and first is not None:
            ctx.set_source_surface(first, 0, 0); ctx.paint_with_alpha(min(1.0, xf) ** 1.5)


def run(render):
    global t, first
    ff = None
    if render:
        ff = subprocess.Popen([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", OUT
        ], stdin=subprocess.PIPE)
    frame = 0
    while True:
        for _ in range(SUB):
            step(DT)
            if payoff_pending is not None and payoff_t is None and t >= payoff_pending:
                do_payoff()
            t += DT
        for f in range(NF):
            wd.flash[f] *= 0.85
        for i in range(NB):
            trails[i].append((float(wd.p[i, 0]), float(wd.p[i, 1])))
            del trails[i][:-12]
        if frame % 15 == 0:
            build_keys.append((t, progress()))
        if PREVIEW and any(abs(t - pt) < 0.5 / FPS for pt in PREVIEW):
            draw(); surf.flush(); surf.write_to_png(f"prev_{t:05.1f}.png")
        if render:
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


run(not SIM_ONLY)
outs = sorted((round(float(wd.out_t[i]), 1), i) for i in range(NB) if not np.isnan(wd.out_t[i]))
f1 = [x[0] for x in falls if x[2] == 0]
print("seed", SEED, "payoff", payoff_t and round(payoff_t, 2), "duration", round(t, 2), "winner", winner,
      "outs", [o[0] for o in outs], "first floor-1 falls", f1[:8])
print("music", song.recipe_str())
if "--detail" in sys.argv:
    for f in range(NF):
        print("breaks f%d" % f, [round(e[0], 1) for e in events if e[1] == "break" and e[2] == f])
    print("drops", drop2)

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
