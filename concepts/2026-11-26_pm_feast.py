"""2026-11-26 18:00 — growing-ball (eat & grow, new twist) · Thanksgiving theme (leaf skin): "Thanksgiving Feast"
Four hungry neon orbs (cranberry, pumpkin, gold, plum) bounce inside a neon ring, zero gravity.
  Rule 1: six vents in the ring blow autumn leaves in on the beat (1 -> 2 -> 3 -> 6 per beat, switching on bars).
  Rule 2: an orb that touches a leaf eats it and grows (bigger = a little slower).
  Rule 3: when two orbs touch, the clearly bigger one swallows the smaller one; similar sizes just bounce off.
The last orb keeps feasting until it fills the whole ring: the ring heats red and shakes, and on the bar it bursts
outward under the pressure, the orb pops and all the leaves it ate fly out. Tail crossfades to the opening.
Sound: ring bounces = music (song.note); leaf eaten = tick; vent puff = soft whoosh; orb swallowed = pop;
ring bursting = shatter.

usage: python3 concepts/2026-11-26_pm_feast.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 4
CX, CY = W / 2, 960.0
R = 460.0
LR = 12.0                       # leaf radius (visual + physics)
RH0 = float(os.environ.get("RH0", "36"))
V0 = float(os.environ.get("V0", "470"))
DR = float(os.environ.get("DR", "1.1"))            # radius added per leaf
RATIO = float(os.environ.get("RATIO", "1.2"))
N0 = int(os.environ.get("N0", "20"))
FILL = 0.93
TAIL = 3.0
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
# Thanksgiving: warm, cosy major with an electric piano (bossa/jazzhop were used in the last 7 videos)
song = music.Song.from_genre("citypop", seed=int(os.environ.get("MSEED", "2026112612012")), key="G#",
                             mode="major", lead="ep")
BEAT = song.beat
BAR = song.chord_len
TIERS = [float(x) for x in os.environ.get("TIERS", "10,22,36").split(",")]
TIER_BARS = [math.ceil(x / BAR) for x in TIERS]
VENT_N = [1, 2, 3, 6]

HUNT = [(1.0, 0.28, 0.40), (1.0, 0.58, 0.16), (1.0, 0.86, 0.30), (0.72, 0.45, 1.0)]
NAMES = ["cranberry", "pumpkin", "gold", "plum"]
LEAF_COLS = [(0.95, 0.30, 0.12), (1.0, 0.62, 0.12), (0.98, 0.82, 0.25), (0.80, 0.22, 0.10), (0.70, 0.75, 0.20)]
RING_COL = (1.0, 0.72, 0.42)
PAL = {"bg": ((0.07, 0.025, 0.05), (0.015, 0.005, 0.02)), "ring": RING_COL, "balls": HUNT, "accent": (1, 0.9, 0.6)}

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 4242)
VENT_A = [-math.pi / 2 + k * math.pi / 3 for k in range(6)]
VENT_ORDER = [0, 3, 1, 4, 2, 5]

# ---------------- state ----------------
hp = np.array([[CX + 0.5 * R * math.cos(math.pi / 4 + k * math.pi / 2), CY + 0.5 * R * math.sin(math.pi / 4 + k * math.pi / 2)] for k in range(4)])
th0 = rng.uniform(0, 2 * math.pi, 4)
hv = np.stack([np.cos(th0), np.sin(th0)], 1) * V0
ha = np.full(4, RH0 ** 2)              # r^2
alive = [True] * 4
eaten_by = [None] * 4
out_t = [None] * 4
h_cool = np.full(4, -9.0)
h_gulp = np.full(4, -9.0)
leaves_eaten = np.zeros(4, int)
belly = [[] for _ in range(4)]          # visual only: leaves each orb has eaten (unit-disk pos, colour, angle)
belly_rng = np.random.default_rng(SEED + 99)

def place_leaf():
    for _ in range(500):
        rr = math.sqrt(rng.uniform(0.0, 1.0)) * (R - LR - 6)
        a = rng.uniform(0, 2 * math.pi)
        q = (CX + rr * math.cos(a), CY + rr * math.sin(a))
        if all(math.hypot(q[0] - x, q[1] - y) > 2 * RH0 + LR + 20 for x, y in hp) and \
           all(math.hypot(q[0] - x, q[1] - y) > 2 * LR + 10 for x, y in lp_init):
            return q
    return q

lp_init = []
for _ in range(N0):
    lp_init.append(place_leaf())
lp = np.array(lp_init)
lv = rng.normal(0, 12, (N0, 2))
lc = rng.integers(0, len(LEAF_COLS), N0)
lang = rng.uniform(0, 2 * math.pi, N0)
lspin = rng.normal(0, 0.6, N0)

t = 0.0
next_emit = 0.0
emit_k = 0
total_eaten = 0
fill_t = None
payoff_pending = payoff_t = None
winner = None
events, sparks, build_keys, gulps, burst_leaves, ring_frags = [], [], [], [], [], []


def radius(i):
    return math.sqrt(ha[i])


def speed_for(r):
    return max(220.0, V0 * (RH0 / r) ** 0.3)


def per_beat(tt):
    b = int(tt / BAR)
    k = sum(1 for tb in TIER_BARS if b >= tb)
    return VENT_N[k]


def biggest():
    rs = [radius(i) if alive[i] else 0 for i in range(4)]
    return int(np.argmax(rs)), max(rs)


def progress():
    if payoff_t is not None:
        return 1.0
    _, rmax = biggest()
    nal = sum(alive)
    return float(np.clip(0.1 * min(1, t / 5) + 0.55 * (rmax / R) ** 1.4 + 0.12 * (4 - nal) / 3 + 0.2 * min(1, t / 60), 0, 1))


def emit():
    """vents blow leaves in on the beat."""
    global lp, lv, lc, lang, lspin, next_emit, emit_k
    while t >= next_emit and fill_t is None:
        n = per_beat(next_emit + 1e-6)
        for m in range(n):
            vk = VENT_ORDER[(emit_k + m * (6 // n if n < 6 else 1)) % 6] if n < 6 else m
            a = VENT_A[vk]
            u = np.array([math.cos(a), math.sin(a)])
            pos = np.array([CX, CY]) + u * (R - LR - 4)
            spread = rng.uniform(-0.45, 0.45)
            d = -np.array([math.cos(a + spread), math.sin(a + spread)])
            sp = rng.uniform(240, 360)
            lp = np.vstack([lp, pos]); lv = np.vstack([lv, d * sp])
            lc = np.append(lc, rng.integers(0, len(LEAF_COLS))); lang = np.append(lang, rng.uniform(0, 6.28))
            lspin = np.append(lspin, rng.normal(0, 2.0))
            events.append((next_emit, "vent", vk))
        song.sfx(next_emit, "whoosh", 0.0, 0.10 if n < 6 else 0.07)
        emit_k += 1
        next_emit += BEAT


def eat_leaf(i, j):
    global total_eaten
    ha[i] = (math.sqrt(ha[i]) + DR) ** 2
    leaves_eaten[i] += 1
    total_eaten += 1
    h_gulp[i] = t
    gulps.append([float(lp[j, 0]), float(lp[j, 1]), i, t, int(lc[j]), float(lang[j])])
    a = belly_rng.uniform(0, 2 * math.pi); rr = math.sqrt(belly_rng.uniform(0, 1)) * 0.86
    belly[i].append([rr * math.cos(a), rr * math.sin(a), int(lc[j]), belly_rng.uniform(0, 6.28), belly_rng.normal(0, 0.4)])
    song.sfx(t, "tick", float((lp[j, 0] - CX) / R), 0.2)


def swallow(b, s):
    """big b swallows small s."""
    ha[b] += ha[s]
    leaves_eaten[b] += leaves_eaten[s]
    fb = radius(s) / math.sqrt(ha[b])
    for q in belly[s]:            # its leaves move into the bigger orb
        a = belly_rng.uniform(0, 2 * math.pi); rr = math.sqrt(belly_rng.uniform(0, 1)) * 0.86
        belly[b].append([rr * math.cos(a), rr * math.sin(a), q[2], q[3], q[4]])
    belly[s] = []
    alive[s] = False
    eaten_by[s] = b
    out_t[s] = t
    h_gulp[b] = t
    gulps.append([float(hp[s, 0]), float(hp[s, 1]), b, t, -1 - s, radius(s)])
    song.sfx(t, "pop", float((hp[s, 0] - CX) / R), 0.9)
    song.sfx(t + 0.02, "whoosh", 0.0, 0.3)
    events.append((t, "swallow", (b, s)))
    for _ in range(26):
        a = fx_rng.uniform(0, 6.28)
        sparks.append([hp[s, 0] + math.cos(a) * radius(s), hp[s, 1] + math.sin(a) * radius(s), fx_rng.uniform(8, 18), t, HUNT[s]])


def physics_step(dt):
    global lp, lv, lc, lang, lspin, fill_t, payoff_pending, winner
    # leaves drift
    if len(lp):
        lv *= math.exp(-1.7 * dt)
        lp += lv * dt
        lang += lspin * dt
        d = lp - (CX, CY)
        dc = np.hypot(d[:, 0], d[:, 1]) + 1e-9
        out = dc > R - LR
        if out.any():
            u = d[out] / dc[out, None]
            lp[out] = np.array([CX, CY]) + u * (R - LR)
            vn = (lv[out] * u).sum(1)
            lv[out] -= (1.6 * np.maximum(vn, 0))[:, None] * u
    # hunters
    for i in range(4):
        if not alive[i]:
            continue
        r = radius(i)
        sp = np.hypot(*hv[i]) + 1e-9
        target = speed_for(r)
        hv[i] *= 1 + (target / sp - 1) * min(1.0, 3 * dt)
        hp[i] += hv[i] * dt
        d = hp[i] - (CX, CY)
        dc = math.hypot(*d) + 1e-9
        dmax = max(0.0, R - r)
        if dc > dmax:
            u = d / dc
            hp[i] = np.array([CX, CY]) + u * dmax
            vn = hv[i] @ u
            if vn > 0:
                hv[i] -= 2 * vn * u
                if r > R - 8:              # wedged: jiggle
                    hv[i] = fx_free_dir(i) * speed_for(r)
                if t - h_cool[i] > 0.1:
                    h_cool[i] = t
                    song.note(t, float(u[0]), vel=0.45 + 0.4 * min(1.0, vn / V0))
                    events.append((t, "ring", (float(CX + u[0] * R), float(CY + u[1] * R), i)))
        # eat leaves
        if len(lp):
            dd = np.hypot(lp[:, 0] - hp[i, 0], lp[:, 1] - hp[i, 1])
            hit = np.where(dd < r + LR * 0.5)[0]
            if len(hit):
                for j in hit:
                    eat_leaf(i, j)
                keep = np.ones(len(lp), bool); keep[hit] = False
                lp, lv, lc, lang, lspin = lp[keep], lv[keep], lc[keep], lang[keep], lspin[keep]
    # hunter vs hunter
    for i in range(4):
        for j in range(i + 1, 4):
            if not (alive[i] and alive[j]):
                continue
            ri, rj = radius(i), radius(j)
            d = hp[j] - hp[i]
            dist = math.hypot(*d) + 1e-9
            if dist < ri + rj:
                if ri >= RATIO * rj:
                    swallow(i, j)
                elif rj >= RATIO * ri:
                    swallow(j, i)
                else:
                    n = d / dist
                    over = ri + rj - dist
                    mi, mj = ha[i], ha[j]
                    hp[i] -= n * over * mj / (mi + mj); hp[j] += n * over * mi / (mi + mj)
                    rel = (hv[j] - hv[i]) @ n
                    if rel < 0:
                        imp = 2 * rel / (mi + mj)
                        hv[i] += imp * mj * n; hv[j] -= imp * mi * n
                        song.sfx(t, "tick", float((hp[i, 0] - CX) / R), 0.45)
                        events.append((t, "bump", (float(hp[i, 0] + n[0] * ri), float(hp[i, 1] + n[1] * ri))))
    b, rmax = biggest()
    if fill_t is None and sum(alive) == 1 and rmax >= FILL * R:
        fill_t = t
        winner = b
        payoff_pending = song.next_bar(t + 0.4)
        song.sfx(t, "chime", 0.0, 0.7)


_dir_rng = np.random.default_rng(SEED + 7)
def fx_free_dir(i):
    a = _dir_rng.uniform(0, 2 * math.pi)
    return np.array([math.cos(a), math.sin(a)])


def do_payoff():
    global payoff_t
    payoff_t = t
    song.accent(t)
    song.sfx(t, "shatter", 0.0, 1.0)
    song.sfx(t + 0.03, "pop", 0.0, 1.0)
    n = min(380, int(leaves_eaten[winner]))
    for _ in range(n):
        a = fx_rng.uniform(0, 2 * math.pi)
        rr = math.sqrt(fx_rng.uniform(0, 1)) * radius(winner)
        sp = fx_rng.uniform(250, 1300)
        burst_leaves.append([hp[winner, 0] + rr * math.cos(a), hp[winner, 1] + rr * math.sin(a),
                             sp * math.cos(a), sp * math.sin(a), int(fx_rng.integers(len(LEAF_COLS))), fx_rng.uniform(0, 6.28), fx_rng.normal(0, 5)])
    for k in range(18):
        a0 = k * 2 * math.pi / 18
        ring_frags.append([a0, a0 + 2 * math.pi / 18 * 0.85, 0.0, fx_rng.uniform(500, 900), fx_rng.normal(0, 1.5)])
    events.append((t, "payoff", winner))


# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
LEAF = neon.SkinSprites(LEAF_COLS, 16, skin="leaf", glow=2.4, glow_alpha=0.35)
BELLY = neon.SkinSprites(LEAF_COLS, 13, skin="leaf", glow=2.0, glow_alpha=0.3)


def draw_leaf(x, y, ci, ang, scale=1.0, alpha=1.0, glow=True):
    if glow:
        s, G = LEAF.glow[ci]
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_surface(s, x - G, y - G); ctx.paint_with_alpha(0.8 * alpha); ctx.restore()
    s, P = LEAF.core[ci]
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang); ctx.scale(scale, scale)
    ctx.set_source_surface(s, -P, -P)
    if alpha < 1:
        ctx.paint_with_alpha(alpha)
    else:
        ctx.paint()
    ctx.restore()


def draw_orb(x, y, r, c, gulp=0.0, heat=0.0, bi=None):
    rr = r * (1 + 0.08 * gulp)
    c = neon.mix(c, (1.0, 0.25, 0.2), 0.0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    G = rr * 1.9 + 30
    g = cairo.RadialGradient(x, y, rr * 0.6, x, y, G)
    g.add_color_stop_rgba(0, *c, 0.42 + 0.3 * gulp); g.add_color_stop_rgba(0.35, *c, 0.14); g.add_color_stop_rgba(1, *c, 0)
    ctx.set_source(g); ctx.arc(x, y, G, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    g = cairo.RadialGradient(x - rr * 0.35, y - rr * 0.4, rr * 0.05, x, y, rr)
    g.add_color_stop_rgb(0, *neon.mix(c, (1, 1, 1), 0.7 if bi is None else 0.5))
    g.add_color_stop_rgb(0.45, *neon.mix(c, (1, 1, 1), 0.2))
    g.add_color_stop_rgb(1, *neon.mix(c, (0, 0, 0), 0.4))
    ctx.set_source(g); ctx.arc(x, y, rr, 0, 2 * math.pi); ctx.fill()
    if bi is not None:
        draw_belly(bi, x, y, rr)
    ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.7), 0.9); ctx.set_line_width(max(1.5, rr * 0.06))
    ctx.arc(x, y, rr * 0.97, 0, 2 * math.pi); ctx.stroke()
    ctx.save(); ctx.translate(x - rr * 0.38, y - rr * 0.42); ctx.rotate(-0.5); ctx.scale(rr * 0.30, rr * 0.17)
    ctx.set_source_rgba(1, 1, 1, 0.7 if rr < 120 else 0.42); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); ctx.fill()


def draw_belly(i, x, y, r):
    """the leaves it has eaten, swirling slowly inside the glass orb."""
    if not belly[i]:
        return
    ctx.save(); ctx.arc(x, y, r * 0.96, 0, 2 * math.pi); ctx.clip()
    sc = min(1.0, 0.55 + r / 300)
    rot = t * 0.25 * (1 if i % 2 == 0 else -1)
    cr, sr = math.cos(rot), math.sin(rot)
    for ux, uy, ci, ang, spn in belly[i][-420:]:
        px = x + (ux * cr - uy * sr) * r; py = y + (ux * sr + uy * cr) * r
        s_, P = BELLY.core[ci]
        ctx.save(); ctx.translate(px, py); ctx.rotate(ang + spn * t); ctx.scale(sc, sc)
        ctx.set_source_surface(s_, -P, -P); ctx.paint_with_alpha(0.55); ctx.restore()
    ctx.restore()


def draw_vents(heat):
    n_now = per_beat(t)
    for k, a in enumerate(VENT_A):
        u = (math.cos(a), math.sin(a))
        x, y = CX + u[0] * R, CY + u[1] * R
        recent = [et for et, kind, d in events[-60:] if kind == "vent" and d == k and 0 <= t - et < 0.35]
        f = (1 - (t - recent[-1]) / 0.35) if recent else 0.0
        c = neon.mix(RING_COL, (1, 1, 0.85), f)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        g = cairo.RadialGradient(x, y, 0, x, y, 70)
        g.add_color_stop_rgba(0, *c, 0.25 + 0.45 * f); g.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(g); ctx.arc(x, y, 70, 0, 2 * math.pi); ctx.fill()
        # chevrons pointing inward
        ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        for m in range(2):
            dd = 24 + m * 16 + 10 * f
            px, py = x - u[0] * dd, y - u[1] * dd
            nx, ny = -u[1], u[0]
            ctx.set_source_rgba(*c, (0.55 + 0.45 * f) * (1 - 0.35 * m)); ctx.set_line_width(4)
            ctx.move_to(px + nx * 11 + u[0] * 7, py + ny * 11 + u[1] * 7); ctx.line_to(px, py)
            ctx.line_to(px - nx * 11 + u[0] * 7, py - ny * 11 + u[1] * 7); ctx.stroke()
        ctx.restore()


def draw_legend():
    cx, y = 540, 300
    xs = [cx - 255 + k * 170 for k in range(4)]
    rs = [radius(i) if alive[i] else 0 for i in range(4)]
    for k in range(4):
        x = xs[k]
        if alive[k]:
            rr = 14 + 30 * min(1.0, rs[k] / (0.6 * R)) ** 0.7
            c = HUNT[k]; a = 1.0
        else:
            rr = 12; c = (0.38, 0.36, 0.42); a = 0.5
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        g = cairo.RadialGradient(x, y, 0, x, y, rr * 2.4)
        g.add_color_stop_rgba(0, *c, 0.45 * a); g.add_color_stop_rgba(1, *c, 0)
        ctx.set_source(g); ctx.arc(x, y, rr * 2.4, 0, 2 * math.pi); ctx.fill(); ctx.restore()
        ctx.set_source_rgba(*c, a); ctx.arc(x, y, rr, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.6 * a); ctx.arc(x - rr * 0.3, y - rr * 0.3, rr * 0.25, 0, 2 * math.pi); ctx.fill()
        if not alive[k] and eaten_by[k] is not None:
            # small arrow to the colour that swallowed it
            ctx.set_source_rgba(*HUNT[eaten_by[k]], 0.9); ctx.arc(x, y, 5, 0, 2 * math.pi); ctx.fill()


def draw(counter=True):
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    b, rmax = biggest()
    heat = 0.0 if payoff_t is not None else float(np.clip((rmax / R - 0.72) / (FILL - 0.72), 0, 1)) * (1.0 if sum(alive) == 1 else 0.6)
    lead_c = HUNT[b] if payoff_t is None else HUNT[winner]
    rg = cairo.RadialGradient(CX, CY, 0, CX, CY, 980)
    ga = 0.05 + 0.10 * pr + 0.02 * math.sin(t * 1.7)
    if payoff_t is not None:
        ga = 0.06 + 0.25 * math.exp(-(t - payoff_t) * 1.0)
    rg.add_color_stop_rgba(0, *lead_c, ga); rg.add_color_stop_rgba(1, *lead_c, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()

    ctx.save()
    shake = 0.0
    if payoff_t is None and heat > 0.6:
        shake = 5.0 * (heat - 0.6) / 0.4
    if payoff_t is not None:
        shake = 20 * math.exp(-(t - payoff_t) * 6)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    if payoff_t is None:
        rc = neon.mix(RING_COL, lead_c, 0.25 + 0.35 * pr)
        neon.ring(ctx, CX, CY, R, rc, t, heat=heat * 0.95)
        draw_vents(heat)
    else:
        # ring fragments fly outward (pressure from inside)
        dtp = t - payoff_t
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for a0, a1, _, sp, spin in ring_frags:
            am = (a0 + a1) / 2
            off = sp * dtp
            cx_, cy_ = CX + math.cos(am) * off, CY + math.sin(am) * off + 300 * dtp * dtp
            al = max(0.0, 1 - dtp / 2.2)
            c = neon.mix((1.0, 0.3, 0.25), RING_COL, min(1, dtp * 2))
            for w_, a_ in ((26, 0.1), (12, 0.3), (5, 0.95)):
                ctx.set_source_rgba(*c, a_ * al); ctx.set_line_width(w_)
                ctx.new_path(); ctx.arc(cx_, cy_, R, a0 + spin * dtp * 0.1, a1 + spin * dtp * 0.1); ctx.stroke()
        ctx.restore()
    # ring hit flashes
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, data in events[-120:]:
        if kind == "ring" and 0 <= t - et < 0.3 and payoff_t is None:
            x, y, k = data; a = 1 - (t - et) / 0.3
            ctx.set_source_rgba(*HUNT[k], 0.7 * a); ctx.set_line_width(3)
            ctx.new_path(); ctx.arc(x, y, 8 + 26 * (1 - a), 0, 2 * math.pi); ctx.stroke()
        elif kind == "swallow" and 0 <= t - et < 0.6:
            bb, ss = data; a = 1 - (t - et) / 0.6
            ctx.set_source_rgba(*neon.mix(HUNT[bb], (1, 1, 1), 0.4), 0.8 * a); ctx.set_line_width(5)
            ctx.new_path(); ctx.arc(hp[bb, 0], hp[bb, 1], radius(bb) + 10 + 70 * (1 - a), 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    # leaves
    for (x, y), ci, ang in zip(lp, lc, lang):
        draw_leaf(x, y, int(ci), ang)
    # gulps: eaten leaf / orb sliding into the eater
    live = []
    for g in gulps:
        x0, y0, i, gt, ci, extra = g
        dur = 0.18 if ci >= 0 else 0.35
        k = (t - gt) / dur
        if k >= 1:
            continue
        live.append(g)
        x = x0 + (hp[i, 0] - x0) * k; y = y0 + (hp[i, 1] - y0) * k
        if ci >= 0:
            draw_leaf(x, y, ci, extra, scale=1 - 0.7 * k, alpha=1 - k, glow=False)
        else:
            s = -1 - ci
            draw_orb(x, y, extra * (1 - 0.8 * k), HUNT[s])
    gulps[:] = live
    # orbs (biggest first so small ones stay visible on top)
    order = sorted([i for i in range(4) if alive[i] and (payoff_t is None)], key=lambda i: -radius(i))
    for i in order:
        gl = max(0.0, 1 - (t - h_gulp[i]) / 0.2)
        draw_orb(hp[i, 0], hp[i, 1], radius(i), HUNT[i], gulp=gl, bi=i)
    if payoff_t is not None:
        dtp = t - payoff_t
        if dtp < 0.35:
            draw_orb(hp[winner, 0], hp[winner, 1], radius(winner) * (1 + 0.25 * dtp / 0.35), HUNT[winner])
        for bl in burst_leaves:
            x, y, vx, vy, ci, ang, spn = bl
            draw_leaf(x + vx * dtp, y + vy * dtp + 260 * dtp * dtp, ci, ang + spn * dtp, alpha=max(0.0, 1 - dtp / 2.6), glow=dtp < 1.2)
    # sparks
    lv_ = [s for s in sparks if t - s[3] < 0.5]
    sparks[:] = lv_
    for x, y, sz, st, c in lv_:
        al = 1 - (t - st) / 0.5
        neon.sparkles(ctx, [(x, y, sz * (0.5 + al))], neon.mix(c, (1, 1, 1), 0.5), alpha=al * 0.9)
    ctx.restore()
    draw_legend()
    if counter and payoff_t is None:
        ctx.save()
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(88)
        txt = f"{total_eaten}"
        xb, yb, tw, th_, xa, ya = ctx.text_extents(txt)
        ctx.move_to(W / 2 - tw / 2 - xb, 1660)
        ctx.text_path(txt)
        cc = neon.mix(lead_c, (1, 1, 1), 0.35)
        ctx.set_source_rgba(*cc, 0.10); ctx.set_line_width(18); ctx.stroke_preserve()
        ctx.set_source_rgba(*cc, 0.95); ctx.fill()
        ctx.restore()
    if payoff_t is not None:
        dtp = t - payoff_t
        fa = max(0.0, 0.5 - dtp * 2.6)
        if fa > 0:
            ctx.set_source_rgba(*neon.mix(HUNT[winner], (1, 1, 1), 0.75), fa); ctx.paint()
        if dtp < 1.3:
            a = 1 - dtp / 1.3
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*HUNT[winner], 0.8 * a); ctx.set_line_width(4 + 18 * a)
            ctx.new_path(); ctx.arc(CX, CY, R + 1400 * dtp, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
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
log = []
while True:
    for _ in range(SUB):
        emit()
        physics_step(dt)
        if payoff_pending is not None and payoff_t is None and t >= payoff_pending:
            do_payoff()
        t += dt
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if frame % 300 == 0:
        log.append((round(t), [round(radius(i)) if alive[i] else 0 for i in range(4)], len(lp)))
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
    if t > 80:
        break

if ff:
    ff.stdin.close(); ff.wait()
print("seed", SEED, "outs", [(NAMES[k], round(out_t[k], 1), NAMES[eaten_by[k]]) for k in range(4) if out_t[k] is not None],
      "winner", winner is not None and NAMES[winner], "fill", fill_t and round(fill_t, 2), "payoff", payoff_t and round(payoff_t, 2),
      "duration", round(t, 2), "eaten", total_eaten)
if os.environ.get("LOG"):
    print(log)
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
