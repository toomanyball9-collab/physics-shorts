"""2026-11-27 08:00 — marble-race (variation): "Knockout Duels"
A knockout BRACKET of 8 neon marbles, raced as 1-v-1 duels on one fixed course.
The bracket at the top is physical: every marble waits in its bracket slot. For each duel the two slot cups open,
both marbles drop onto the shelf and roll into the start box; the start bar lifts on the beat and they race down
(ramp, peg board, ramp, spinner, ramp, bumpers, final ramp).
Finish = a FLIP GATE in the last ramp: while open, its lip catches the first marble and drops it through the hole;
the falling winner knocks the flap shut, so the second marble rolls over it and off the end into the pit (OUT).
The winner rides the glass tube up the left side and drops into its next bracket slot; bracket lines light up in
its colour. QF x4 -> SF x2 -> final; the champion reaches the top slot and on the next bar the course floods in its
colour. Tail crossfades back to the opening frame.
Course/peg/bumper/spinner bounces = music (song.note); slot release = tick; start bar = whoosh; winner = chime;
flap shutting = thump; tube ride = whoosh; loser landing in the pit = thump.

usage: python3 concepts/2026-11-27_am_duels.py <seed> [--sim | --audio]
"""
import math, sys, subprocess, os
import numpy as np
import cairo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neon, music

W, H, FPS = 1080, 1920, 60
SUB = 8
G = float(os.environ.get("GRAV", "1900"))
DRAG = G / float(os.environ.get("VT", "1250")) ** 2
MR = 21.0
XL, XR = 80.0, 1018.0
TAIL = 3.0
TUBE_V = float(os.environ.get("TUBEV", "1900"))
SEED = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else 1
AUDIO_ONLY = "--audio" in sys.argv
SIM_ONLY = "--sim" in sys.argv or AUDIO_ONLY
OUT = "out_noaudio.mp4"
PREVIEW = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
# random_song(2026112786, avoid=all logged recipes up to 11-26 18:00 citypop) -> japanese 90 F phrygian koto
MUSIC_SEED = int(os.environ.get("MSEED", "2026112786"))
RECENT = [dict(genre="jazzhop", bpm=89, key="C", mode="major", lead="harp"),
          dict(genre="trance_lite", bpm=123, key="F", mode="minor", lead="pluck"),
          dict(genre="bossa", bpm=96, key="G#", mode="major", lead="ep"),
          dict(genre="space", bpm=76, key="B", mode="lydian", lead="bell"),
          dict(genre="desert", bpm=104, key="F#", mode="phrygian_dominant", lead="flute"),
          dict(genre="chiptune", bpm=124, key="F#", mode="mixolydian", lead="square"),
          dict(genre="cinematic", bpm=84, key="C#", mode="harmonic_minor", lead="harp"),
          dict(genre="citypop", bpm=105, key="G#", mode="major", lead="ep")]
song = music.random_song(MUSIC_SEED, avoid=RECENT)
COLS = [(1.0, 0.25, 0.30), (1.0, 0.58, 0.18), (1.0, 0.92, 0.25), (0.45, 1.0, 0.35),
        (0.20, 0.90, 1.0), (0.30, 0.45, 1.0), (0.72, 0.38, 1.0), (1.0, 0.38, 0.78)]
PAL = {"bg": ((0.00, 0.03, 0.07), (0.00, 0.01, 0.03)), "ring": (0.6, 0.95, 1.0), "balls": COLS,
       "accent": (1.0, 0.95, 0.85)}
BASE_COL = (0.35, 0.85, 1.0)
TUBE_COL = (0.75, 0.95, 1.0)
GREY = (0.42, 0.42, 0.50)

rng = np.random.default_rng(SEED)
fx_rng = np.random.default_rng(SEED + 999)

# ---------------- bracket (top) ----------------
L0 = [(540 + (k - 3.5) * 118, 335.0) for k in range(8)]
L1 = [((L0[2 * k][0] + L0[2 * k + 1][0]) / 2, 255.0) for k in range(4)]
L2 = [((L1[2 * k][0] + L1[2 * k + 1][0]) / 2, 175.0) for k in range(2)]
L3 = [(540.0, 98.0)]
LEVELS = [L0, L1, L2, L3]
RAIL_Y = 38.0
TUBE_X = 40.0

# ---------------- course ----------------
SEG = []
BUMP = []
PEGS = []
SPIN = []

def seg(x0, y0, x1, y1):
    SEG.append((x0, y0, x1, y1))
    return len(SEG) - 1

def lin(a, b):
    return lambda x: a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])

SHELF = seg(XL, 425, 962, 505)
BOX_X = 925.0
R1a, R1b = (XR, 605.0), (230.0, 790.0)
r1y = lin(R1a, R1b)
seg(*R1a, *R1b)
START_BAR = seg(BOX_X, 518, BOX_X, r1y(BOX_X))
# peg board
for r_ in range(3):
    y = 865 + r_ * 75
    xs = [XL + 70 + k * 112 for k in range(8)] if r_ % 2 == 0 else [XL + 126 + k * 112 for k in range(7)]
    for x in xs:
        PEGS.append((x, y, 10.0))
R2a, R2b = (XL, 1080.0), (830.0, 1250.0)
seg(*R2a, *R2b)
SPIN.append((918, 1328, float(os.environ.get("SPH", "84")), float(os.environ.get("SPW", "2.1")), float(rng.uniform(0, 3.14))))
R3a, R3b = (XR, 1410.0), (255.0, 1575.0)
seg(*R3a, *R3b)
BUMP += [(165, 1632, 24), (335, 1652, 24)]
R4a, R4b = (XL, 1702.0), (880.0, 1792.0)
r4y = lin(R4a, R4b)
H0, H1 = 612.0, 678.0                     # hole in the last ramp
seg(R4a[0], R4a[1], H0, r4y(H0))
seg(H1, r4y(H1), *R4b)
FLAP = seg(H0, r4y(H0), H1, r4y(H1))      # closed flap (floor over the hole)
LIP = seg(H1, r4y(H1) - 74, H1, r4y(H1))  # open gate lip that catches the leader
PIT_X0, PIT_Y = 880.0, 1893.0
seg(PIT_X0, R4b[1] + 2, PIT_X0, PIT_Y)
seg(PIT_X0, PIT_Y, XR, PIT_Y)
SEGA = np.array([[s[0], s[1]] for s in SEG], float); SEGB = np.array([[s[2], s[3]] for s in SEG], float)
seg_on = np.ones(len(SEG), bool)
seg_on[FLAP] = False
OBST = BUMP + PEGS
OBA = np.array([[b[0], b[1]] for b in OBST], float); OBR = np.array([b[2] for b in OBST], float)
ob_flash = np.zeros(len(OBST))

# winner tube path: below the hole -> along the bottom -> up the left side -> rail -> slot
def tube_path(slot_xy):
    hx = (H0 + H1) / 2
    return [(hx, r4y(hx) + 40), (hx, 1862), (TUBE_X, 1862), (TUBE_X, RAIL_Y), (slot_xy[0], RAIL_Y), slot_xy]

def path_len(P):
    return sum(math.hypot(P[k + 1][0] - P[k][0], P[k + 1][1] - P[k][1]) for k in range(len(P) - 1))

def path_at(P, s):
    for k in range(len(P) - 1):
        L = math.hypot(P[k + 1][0] - P[k][0], P[k + 1][1] - P[k][1])
        if s <= L:
            u = s / L if L > 0 else 0
            return (P[k][0] + (P[k + 1][0] - P[k][0]) * u, P[k][1] + (P[k + 1][1] - P[k][1]) * u)
        s -= L
    return P[-1]

# ---------------- marbles ----------------
NM = 8
colour = rng.permutation(NM)
p = np.array(L0, float)
v = np.zeros((NM, 2))
state = ["slot"] * NM        # slot, drop, race, tube, pit, champ
slot_of = [(0, k) for k in range(NM)]   # (level, index)
tube_s = np.zeros(NM)
tube_P = [None] * NM
hit_cool = np.zeros(NM) - 9
trail = [[] for _ in range(NM)]
out_t = np.full(NM, -1.0)
lit = {}                     # (level, idx) -> colour index of marble that reached it
for k in range(NM):
    lit[(0, k)] = int(colour[k])
# duel schedule: (level, slotA, slotB)
DUELS = [(0, 0, 1), (0, 2, 3), (0, 4, 5), (0, 6, 7), (1, 0, 1), (1, 2, 3), (2, 0, 1)]
occupant = {(0, k): k for k in range(NM)}
duel_released = -1
duel_started = -1
duel_marbles = {}
duel_winner = {}
duel_tw = {}
duel_tl = {}
gate_open = True
gate_shut_t = -9.0
gate_duel = [None]
start_t = {}
champion = None
champ_t = None
payoff_pending = payoff_t = None
bar_open_t = -9.0
t = 0.0
events, sparks, build_keys = [], [], []

# duel 0 starts in the start box already
def place_in_box(i, k):
    x = BOX_X + MR + 2 + k * (2 * MR + 3)
    p[i] = [x + rng.uniform(-1.5, 1.5), r1y(x) - MR - 1.5]
    state[i] = "race"
for k, i in enumerate((0, 1)):
    place_in_box(i, k)
    occupant.pop((0, i))
duel_released = 0
duel_marbles[0] = (0, 1)

def progress():
    if payoff_t is not None:
        return 1.0
    d = max(duel_started, 0)
    base = d / 7.0
    if duel_started in start_t:
        base += min(1.0, (t - start_t[duel_started]) / 7.0) / 7.0
    if champion is not None:
        base = 1.0
    return float(np.clip(0.08 + 0.92 * base, 0, 1))

def release(d):
    global duel_released
    lv, a, b = DUELS[d]
    ms = []
    for s in (a, b):
        i = occupant.pop((lv, s))
        state[i] = "drop"
        v[i] = [rng.uniform(-30, 30), 0]
        ms.append(i)
        song.sfx(t, "tick", float((p[i, 0] - 540) / 470), 0.5)
        events.append((t, "release", (lv, s)))
    duel_marbles[d] = tuple(ms)
    duel_released = d

def in_box(i):
    return state[i] in ("race", "drop") and p[i, 0] > BOX_X and p[i, 1] > 520 and p[i, 1] < 640

def shut_gate(winner_i):
    global gate_open, gate_shut_t
    gate_open = False
    gate_shut_t = t
    seg_on[LIP] = False
    seg_on[FLAP] = True
    song.sfx(t, "thump", 0.2, 0.55)

def open_gate():
    global gate_open
    gate_open = True
    seg_on[LIP] = True
    seg_on[FLAP] = False

def collide_segments(i):
    near = seg_on & (np.minimum(SEGA[:, 1], SEGB[:, 1]) < p[i, 1] + 50) & (np.maximum(SEGA[:, 1], SEGB[:, 1]) > p[i, 1] - 50)
    for k in np.where(near)[0]:
        a, b = SEGA[k], SEGB[k]
        ab = b - a
        u = np.clip(np.dot(p[i] - a, ab) / np.dot(ab, ab), 0, 1)
        q = a + ab * u
        d = p[i] - q
        dist = math.hypot(*d)
        if 1e-6 < dist < MR:
            nrm = d / dist
            p[i] = q + nrm * MR
            vn = np.dot(v[i], nrm)
            if vn < 0:
                vt = v[i] - vn * nrm
                v[i] = vt * 0.99985 - 0.32 * vn * nrm
                if -vn > 170 and t - hit_cool[i] > 0.09:
                    hit_cool[i] = t
                    if state[i] == "pit":
                        song.sfx(t, "thump", 0.7, min(0.6, 0.2 + -vn / 2000))
                    else:
                        song.note(t, float((p[i, 0] - 540) / 470), vel=min(1.0, 0.45 + -vn / 1400))
                    events.append((t, "hit", (float(q[0]), float(q[1]), int(colour[i]))))

def physics_step(dt):
    global duel_started, bar_open_t, champion, champ_t, payoff_pending
    phys = [i for i in range(NM) if state[i] in ("drop", "race", "pit")]
    for i in phys:
        v[i, 1] += G * dt
        sp = math.hypot(*v[i])
        v[i] -= v[i] * DRAG * sp * dt
        p[i] += v[i] * dt
    for a in range(len(phys)):
        for b in range(a + 1, len(phys)):
            i, j = phys[a], phys[b]
            d = p[j] - p[i]
            dist = math.hypot(*d)
            if 1e-6 < dist < 2 * MR:
                nrm = d / dist
                over = 2 * MR - dist
                p[i] -= nrm * over / 2; p[j] += nrm * over / 2
                rel = np.dot(v[j] - v[i], nrm)
                if rel < 0:
                    imp = 0.9 * rel * nrm
                    v[i] += imp; v[j] -= imp
                    if -rel > 180 and state[i] != "pit":
                        song.sfx(t, "tick", float((p[i, 0] - 540) / 470), min(0.4, 0.15 + -rel / 2000))
    for i in phys:
        collide_segments(i)
        if state[i] == "pit":
            pass
        d = p[i] - OBA
        dist = np.hypot(d[:, 0], d[:, 1])
        for k in np.where(dist < OBR + MR)[0]:
            nrm = d[k] / (dist[k] + 1e-6)
            p[i] = OBA[k] + nrm * (OBR[k] + MR)
            vn = np.dot(v[i], nrm)
            if vn < 0:
                if k < len(BUMP):
                    v[i] = v[i] - 2.0 * vn * nrm
                    spd = math.hypot(*v[i])
                    if spd < 430:
                        v[i] *= 430 / (spd + 1e-6)
                else:
                    v[i] = v[i] - 1.55 * vn * nrm
                ob_flash[k] = 1.0
                if t - hit_cool[i] > 0.06:
                    hit_cool[i] = t
                    song.note(t, float((p[i, 0] - 540) / 470), vel=0.85 if k < len(BUMP) else 0.6)
        for k in range(len(SPIN)):
            cx, cy, half, om, ph = SPIN[k]
            if abs(p[i, 1] - cy) > half + MR + 5:
                continue
            aa = ph + om * t
            A = np.array([cx - half * math.cos(aa), cy - half * math.sin(aa)])
            B = np.array([cx + half * math.cos(aa), cy + half * math.sin(aa)])
            ab = B - A
            u = np.clip(np.dot(p[i] - A, ab) / np.dot(ab, ab), 0, 1)
            q = A + ab * u
            dd = p[i] - q
            dst = math.hypot(*dd)
            if 1e-6 < dst < MR + 3:
                nrm = dd / dst
                p[i] = q + nrm * (MR + 3)
                vw = om * np.array([-(q[1] - cy), q[0] - cx])
                vr = v[i] - vw
                vn = np.dot(vr, nrm)
                if vn < 0:
                    vt = vr - vn * nrm
                    v[i] = vw + vt * 0.999 - 0.55 * vn * nrm
                    if -vn > 150 and t - hit_cool[i] > 0.08:
                        hit_cool[i] = t
                        song.note(t, float((p[i, 0] - 540) / 470), vel=min(1.0, 0.5 + -vn / 1400))
                        events.append((t, "spin", (float(q[0]), float(q[1]), int(colour[i]))))
        if p[i, 0] < XL + MR:
            p[i, 0] = XL + MR; v[i, 0] = abs(v[i, 0]) * 0.4
        if p[i, 0] > XR - MR:
            p[i, 0] = XR - MR; v[i, 0] = -abs(v[i, 0]) * 0.4
    # duel bookkeeping
    for d, ms in duel_marbles.items():
        if d in duel_winner and d in duel_tl:
            continue
        for i in ms:
            if state[i] != "race":
                continue
            # winner: drops through the open hole
            if d not in duel_winner and gate_open and H0 - 4 < p[i, 0] < H1 + 4 and p[i, 1] > r4y(p[i, 0]) + MR * 0.6:
                duel_winner[d] = i
                duel_tw[d] = t
                state[i] = "tube"
                lv = DUELS[d][0] + 1
                idx = DUELS[d][1] // 2
                tube_P[i] = tube_path(LEVELS[lv][idx])
                tube_s[i] = 0.0
                slot_of[i] = (lv, idx)
                shut_gate(i)
                gate_duel[0] = d
                song.sfx(t, "chime", 0.1, 0.9)
                song.sfx(t + 0.05, "whoosh", -0.4, 0.4)
                events.append((t, "win", (i, d)))
                for _ in range(16):
                    sparks.append([p[i, 0] + fx_rng.uniform(-30, 30), p[i, 1] + fx_rng.uniform(-30, 30), fx_rng.uniform(8, 18), t, COLS[colour[i]]])
            # loser: reaches the gate after it shut
            elif d in duel_winner and duel_winner[d] != i and d not in duel_tl and p[i, 0] > H0 - 10 and p[i, 1] > 1600:
                duel_tl[d] = t
            if d in duel_winner and duel_winner[d] != i and p[i, 0] > PIT_X0 + 2 and p[i, 1] > R4b[1] - 10:
                state[i] = "pit"
                out_t[i] = t
                if d not in duel_tl:
                    duel_tl[d] = t
                events.append((t, "out", (i,)))
                song.sfx(t, "whoosh", 0.8, 0.45)
    # loser that already left the course counts as out
    for d, ms in duel_marbles.items():
        if d in duel_winner:
            for i in ms:
                if i != duel_winner[d] and state[i] == "race" and p[i, 0] > PIT_X0 + 2 and p[i, 1] > R4b[1] - 10:
                    state[i] = "pit"; out_t[i] = t
                    events.append((t, "out", (i,)))
    # re-open the gate once the loser of the duel that shut it has passed it
    if not gate_open and gate_duel[0] is not None:
        d = gate_duel[0]
        los = [i for i in duel_marbles[d] if i != duel_winner[d]][0]
        if (state[los] == "pit" or p[los, 0] > H1 + 30) and t - gate_shut_t > 0.6:
            open_gate()
            events.append((t, "gate_open", 0))
    # a racer of an undecided duel must never meet a shut gate
    for d, ms in duel_marbles.items():
        if d not in duel_winner:
            for i in ms:
                if state[i] == "race" and not gate_open and p[i, 1] > 1600 and p[i, 0] > H0 - 60 and ("miss", d) not in start_t:
                    start_t[("miss", d)] = t
    # start the next duel: its pair settled in the box, previous duel decided -> on the next beat
    nd = duel_started + 1
    if nd < len(DUELS) and nd in duel_marbles and seg_on[START_BAR]:
        ms = duel_marbles[nd]
        ready = all(in_box(i) and math.hypot(*v[i]) < 60 for i in ms)
        prev_done = duel_started < 0 or duel_started in duel_winner
        if ready and prev_done:
            if "go_at" not in start_t:
                start_t["go_at"] = math.ceil(t / song.beat) * song.beat if t > 0.2 else 0.3
            if t >= start_t["go_at"]:
                start_t.pop("go_at")
                seg_on[START_BAR] = False
                bar_open_t = t
                duel_started = nd
                start_t[nd] = t
                for i in ms:
                    state[i] = "race"
                    v[i] += [rng.uniform(-25, 25), rng.uniform(-10, 10)]
                song.sfx(t, "whoosh", 0.7, 0.5)
                events.append((t, "start", (nd,)))
    # close the start bar again once the racers left the box
    if not seg_on[START_BAR] and duel_started in duel_marbles:
        if all(p[i, 0] < BOX_X - MR - 4 for i in duel_marbles[duel_started]):
            seg_on[START_BAR] = True
    # release the next pair once the box is empty and both of its slots are filled
    rd = duel_released + 1
    if rd < len(DUELS) and duel_started == duel_released and seg_on[START_BAR]:
        lv, a, b = DUELS[rd]
        if (lv, a) in occupant and (lv, b) in occupant and t - bar_open_t > 0.8:
            release(rd)

def tube_step(dt):
    global champion, champ_t, payoff_pending
    for i in range(NM):
        if state[i] != "tube":
            continue
        tube_s[i] += TUBE_V * dt
        L = path_len(tube_P[i])
        p[i] = path_at(tube_P[i], min(tube_s[i], L))
        if tube_s[i] >= L:
            lv, idx = slot_of[i]
            state[i] = "slot" if lv < 3 else "champ"
            occupant[(lv, idx)] = i
            lit[(lv, idx)] = int(colour[i])
            song.sfx(t, "tick", float((p[i, 0] - 540) / 470), 0.6)
            events.append((t, "arrive", (i, lv, idx)))
            if lv == 3:
                champion = i
                champ_t = t
                payoff_pending = song.next_bar(t + 0.15)

def do_payoff():
    global payoff_t
    payoff_t = t
    song.accent(t)
    song.sfx(t, "chime", 0.0, 1.0)
    song.sfx(t, "whoosh", 0.0, 0.7)
    for _ in range(160):
        a = fx_rng.uniform(0, 2 * math.pi)
        rr = fx_rng.uniform(40, 900)
        sparks.append([540 + rr * math.cos(a), 98 + abs(rr * math.sin(a)) * 1.8, fx_rng.uniform(10, 28), t, COLS[colour[champion]]])
    events.append((t, "payoff", 0))

# ---------------- drawing ----------------
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
ctx = cairo.Context(surf)
first = None
SPR = neon.SkinSprites(COLS + [GREY], MR, skin="orb")
STARS = [(fx_rng.uniform(0, W), fx_rng.uniform(0, H), fx_rng.uniform(0.6, 2.0), fx_rng.uniform(0.06, 0.25)) for _ in range(240)]
cur_col = [BASE_COL]

def tube(pts, rgb, alpha=1.0, width=5.0, glowk=1.0):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for w, a in [(34, 0.05), (18, 0.10), (9, 0.25)]:
        ctx.set_source_rgba(*rgb, a * alpha * glowk); ctx.set_line_width(w * width / 5)
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_source_rgba(*neon.mix(rgb, (1, 1, 1), 0.6), 0.92 * alpha); ctx.set_line_width(width)
    ctx.move_to(*pts[0])
    for q in pts[1:]:
        ctx.line_to(*q)
    ctx.stroke(); ctx.restore()

def glass_tube(P, rgb, alpha):
    """transparent glass pipe along the polyline P: faint fill + two thin glowing walls"""
    def path(w):
        ctx.set_line_width(w); ctx.move_to(*P[0])
        for q in P[1:]:
            ctx.line_to(*q)
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_BUTT); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_operator(cairo.OPERATOR_ADD)
    ctx.set_source_rgba(*rgb, 0.10 * alpha); path(2 * MR + 26); ctx.stroke()
    ctx.set_source_rgba(*rgb, 0.55 * alpha); path(2 * MR + 12); ctx.stroke()
    ctx.restore()
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_BUTT); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_source_rgba(0.0, 0.03, 0.07, 0.88); path(2 * MR + 7); ctx.stroke()
    ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source_rgba(*rgb, 0.05 * alpha); path(2 * MR + 7); ctx.stroke()
    ctx.restore()

def bracket_lines():
    """neon bracket tree; segments light up in the colour of the marble that came through."""
    def line(a, b, c, lit_k):
        mid_y = b[1] + (a[1] - b[1]) * 0.45
        pts = [(a[0], a[1] - MR - 6), (a[0], mid_y), (b[0], mid_y), (b[0], b[1] + MR + 6)]
        if lit_k is None:
            tube(pts, GREY, 0.45, 2.5, 0.6)
        else:
            tube(pts, COLS[lit_k], 0.95, 3.5, 1.2)
    for lv in range(3):
        for k, a in enumerate(LEVELS[lv]):
            b = LEVELS[lv + 1][k // 2]
            winner_here = lit.get((lv + 1, k // 2))
            # the line from this slot lights only if the marble from THIS slot advanced
            src = lit.get((lv, k))
            line(a, b, None, src if (winner_here is not None and winner_here == src) else None)

def slot_cup(x, y, c, open_k):
    # small neon cup under each bracket slot
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for w, a in [(14, 0.10), (6, 0.35)]:
        ctx.set_source_rgba(*c, a); ctx.set_line_width(w)
        ctx.new_path(); ctx.arc(x, y, MR + 7, 0.15 * math.pi + open_k * 0.3, 0.85 * math.pi - open_k * 0.3); ctx.stroke()
    ctx.restore()

def draw():
    global first
    neon.background(ctx, W, H, PAL)
    pr = progress()
    cc = cur_col[0]
    if payoff_t is not None:
        cc = neon.mix(cc, COLS[colour[champion]], min(1.0, (t - payoff_t) / 0.5))
    rg = cairo.RadialGradient(540, H * 0.55, 0, 540, H * 0.55, 1100)
    ga = 0.04 + 0.08 * pr + 0.02 * math.sin(t * 2.0)
    if payoff_t is not None:
        ga = 0.2 * math.exp(-(t - payoff_t) * 0.8) + 0.07
    rg.add_color_stop_rgba(0, *cc, ga); rg.add_color_stop_rgba(1, *cc, 0)
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(rg); ctx.paint(); ctx.restore()
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for x, y, rr, a in STARS:
        ctx.set_source_rgba(0.75, 0.85, 1.0, a * (0.7 + 0.3 * math.sin(t * 1.3 + x))); ctx.arc(x, y, rr, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    ctx.save()
    final = duel_started == 6 and champion is None
    shake = 16 * math.exp(-(t - payoff_t) * 6) if payoff_t is not None else (1.4 if final else 0.0)
    if shake > 0:
        ctx.translate(fx_rng.uniform(-shake, shake), fx_rng.uniform(-shake, shake))
    # glass tube (behind everything)
    tp = tube_path((540, RAIL_Y))
    glass_tube([tp[0], tp[1], tp[2], tp[3], (L0[-1][0] + 30, RAIL_Y)], TUBE_COL, 0.8)
    # bracket
    bracket_lines()
    for lv, L in enumerate(LEVELS):
        for k, (x, y) in enumerate(L):
            c = COLS[lit[(lv, k)]] if (lv, k) in lit else GREY
            rel = [e for e in events if e[1] == "release" and e[2] == (lv, k)]
            ok = 0.0
            if rel and t - rel[-1][0] < 0.5:
                ok = 1 - (t - rel[-1][0]) / 0.5
            if (lv, k) not in occupant:
                c = neon.mix(c, GREY, 0.55)
            slot_cup(x, y, c, ok)
    # course
    for k, (x0, y0, x1, y1) in enumerate(SEG):
        if k in (START_BAR, FLAP, LIP):
            continue
        tube([(x0, y0), (x1, y1)], cc, 1.0, 5.5)
    tube([(XL, 425), (XL, 1702)], neon.mix(cc, (0.4, 0.5, 0.8), 0.5), 0.45, 3.0)
    tube([(XR, 425), (XR, 1893)], neon.mix(cc, (0.4, 0.5, 0.8), 0.5), 0.45, 3.0)
    # start bar
    if seg_on[START_BAR]:
        x0, y0, x1, y1 = SEG[START_BAR]
        tube([(x0, y0), (x1, y1)], (1.0, 0.85, 0.4), 1.0, 5.0, 1.2)
    else:
        a = max(0.0, 1 - (t - bar_open_t) / 0.4)
        if a > 0:
            x0, y0, x1, y1 = SEG[START_BAR]
            tube([(x0, y0 - 60 * (1 - a)), (x1, y1 - 140 * (1 - a))], (1.0, 0.85, 0.4), a, 5.0)
    # flip gate
    gc_open = (0.55, 1.0, 0.75)
    if gate_open:
        x0, y0, x1, y1 = SEG[LIP]
        pulse = 1.0 + 0.3 * math.sin(t * 8)
        tube([(x0, y0), (x1, y1)], gc_open, 1.0, 5.5, pulse)
        # hole marker: soft glow over the hole
        hx = (H0 + H1) / 2
        gr = cairo.RadialGradient(hx, r4y(hx), 0, hx, r4y(hx), 60)
        gr.add_color_stop_rgba(0, *gc_open, 0.25); gr.add_color_stop_rgba(1, *gc_open, 0)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_source(gr); ctx.arc(hx, r4y(hx), 60, 0, 2 * math.pi); ctx.fill(); ctx.restore()
        if t - gate_shut_t < 1.2 and gate_shut_t > 0:
            pass
    else:
        age = t - gate_shut_t
        # the lip swings down onto the hole (pivot at the far end of the hole)
        k = min(1.0, age / 0.18)
        ang0 = -math.pi / 2
        sl = math.atan2(r4y(H1) - r4y(H0), H1 - H0) + math.pi
        a = ang0 + (sl - ang0 - 2 * math.pi if sl - ang0 > math.pi else sl - ang0) * k
        L = 74 + (math.hypot(H1 - H0, r4y(H1) - r4y(H0)) - 74) * k
        c = neon.mix((1.0, 0.3, 0.35), cc, min(1.0, max(0.0, age - 0.6) / 0.8))
        tube([(H1, r4y(H1)), (H1 + L * math.cos(a), r4y(H1) + L * math.sin(a))], c, 1.0, 5.5, 1.3)
    ctx.save(); ctx.set_source_rgba(1, 1, 1, 0.8)
    for x_ in (H0, H1):
        ctx.arc(x_, r4y(x_), 5, 0, 2 * math.pi); ctx.fill()
    ctx.restore()
    # obstacles
    for k, (x, y, R_) in enumerate(OBST):
        f = ob_flash[k]
        c = neon.mix(cc, (1, 1, 1), 0.5 * f)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        for w, a in ([(30, 0.06), (16, 0.12), (8, 0.3)] if R_ > 15 else [(18, 0.06), (8, 0.22)]):
            ctx.set_source_rgba(*c, a * (1 + 1.5 * f)); ctx.set_line_width(w)
            ctx.new_path(); ctx.arc(x, y, R_, 0, 2 * math.pi); ctx.stroke()
        gr = cairo.RadialGradient(x, y, 0, x, y, R_)
        gr.add_color_stop_rgba(0, *c, 0.10 + 0.35 * f); gr.add_color_stop_rgba(1, *c, 0.02)
        ctx.set_source(gr); ctx.arc(x, y, R_, 0, 2 * math.pi); ctx.fill()
        ctx.restore()
        ctx.save(); ctx.set_source_rgba(*neon.mix(c, (1, 1, 1), 0.65), 0.9); ctx.set_line_width(3.0 if R_ > 15 else 2.5)
        ctx.new_path(); ctx.arc(x, y, R_ * (1 + 0.12 * f), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    for k in range(len(SPIN)):
        cx, cy, half, om, ph = SPIN[k]
        aa = ph + om * t
        tube([(cx - half * math.cos(aa), cy - half * math.sin(aa)), (cx + half * math.cos(aa), cy + half * math.sin(aa))], cc, 1.0, 7.0, 1.3)
        ctx.save(); ctx.set_source_rgba(1, 1, 1, 0.9); ctx.arc(cx, cy, 7, 0, 2 * math.pi); ctx.fill(); ctx.restore()
    # hit flashes
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for et, kind, data in events[-80:]:
        if kind in ("hit", "spin") and 0 <= t - et < 0.3:
            a = 1 - (t - et) / 0.3
            x, y, c = data
            gr = cairo.RadialGradient(x, y, 0, x, y, 40)
            gr.add_color_stop_rgba(0, *COLS[c], 0.5 * a); gr.add_color_stop_rgba(1, *COLS[c], 0)
            ctx.set_source(gr); ctx.arc(x, y, 40, 0, 2 * math.pi); ctx.fill()
        if kind == "win" and 0 <= t - et < 0.6:
            a = 1 - (t - et) / 0.6
            hx = (H0 + H1) / 2
            ctx.set_source_rgba(*COLS[colour[data[0]]], 0.7 * a); ctx.set_line_width(5)
            ctx.new_path(); ctx.arc(hx, r4y(hx), 25 + 120 * (1 - a), 0, 2 * math.pi); ctx.stroke()
        if kind == "arrive" and 0 <= t - et < 0.6:
            a = 1 - (t - et) / 0.6
            i, lv, idx = data
            x, y = LEVELS[lv][idx]
            ctx.set_source_rgba(*COLS[colour[i]], 0.7 * a); ctx.set_line_width(4)
            ctx.new_path(); ctx.arc(x, y, MR + 6 + 50 * (1 - a), 0, 2 * math.pi); ctx.stroke()
    ctx.restore()
    # trails
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(NM):
        if state[i] not in ("race", "tube") or len(trail[i]) < 3:
            continue
        pts = trail[i]; n = len(pts)
        for k in range(1, n):
            if abs(pts[k][1] - pts[k - 1][1]) > 200 or abs(pts[k][0] - pts[k - 1][0]) > 200:
                continue
            a = (k / n) ** 1.6
            ctx.set_source_rgba(*COLS[colour[i]], 0.38 * a); ctx.set_line_width(MR * 1.3 * a)
            ctx.move_to(*pts[k - 1]); ctx.line_to(*pts[k]); ctx.stroke()
    ctx.restore()
    pts, cis = [], []
    for i in range(NM):
        ci = int(colour[i])
        if state[i] == "pit" and t - out_t[i] > 0.5:
            ci = len(COLS)
        pts.append(tuple(p[i])); cis.append(ci)
    SPR.draw(ctx, pts, cis)
    # the two racers of the current duel get a soft ring
    if duel_started in duel_marbles and duel_started not in duel_winner:
        for i in duel_marbles[duel_started]:
            x, y = p[i]
            k = 0.5 + 0.5 * math.sin(t * 9 + i)
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*COLS[colour[i]], 0.25 + 0.2 * k); ctx.set_line_width(3)
            ctx.new_path(); ctx.arc(x, y, MR * (1.5 + 0.15 * k), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    if champion is not None:
        x, y = p[champion]
        k = 0.5 + 0.5 * math.sin(t * 8)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_source_rgba(*COLS[colour[champion]], 0.4 + 0.3 * k); ctx.set_line_width(4)
        ctx.new_path(); ctx.arc(x, y, MR * (1.7 + 0.3 * k), 0, 2 * math.pi); ctx.stroke(); ctx.restore()
    live = [s for s in sparks if t - s[3] < 0.6]
    sparks[:] = live
    by = {}
    for x, y, sz, st_, c in live:
        a = 1 - (t - st_) / 0.6
        by.setdefault((c, round(a, 1)), []).append((x, y, sz * (0.6 + a)))
    for (c, a), q in by.items():
        neon.sparkles(ctx, q, neon.mix(c, (1, 1, 1), 0.4), alpha=a * 0.9)
    ctx.restore()
    if payoff_t is not None:
        dtp = t - payoff_t
        fa = max(0.0, 0.45 - dtp * 2.5)
        if fa > 0:
            ctx.set_source_rgba(*neon.mix(COLS[colour[champion]], (1, 1, 1), 0.7), fa); ctx.paint()
        if dtp < 1.4:
            a = 1 - dtp / 1.4
            ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
            ctx.set_source_rgba(*COLS[colour[champion]], 0.8 * a); ctx.set_line_width(4 + 18 * a)
            ctx.new_path(); ctx.arc(L3[0][0], L3[0][1], 40 + 2000 * dtp, 0, 2 * math.pi); ctx.stroke(); ctx.restore()
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
        physics_step(dt)
        tube_step(dt)
        if payoff_pending is not None and payoff_t is None and t >= payoff_pending:
            do_payoff()
        t += dt
    ob_flash *= 0.85
    for i in range(NM):
        trail[i].append((float(p[i, 0]), float(p[i, 1])))
        if len(trail[i]) > 12:
            trail[i].pop(0)
    # course colour follows the duel leader (lower on screen = ahead)
    if duel_started in duel_marbles and duel_started not in duel_winner:
        ms = duel_marbles[duel_started]
        lead = max(ms, key=lambda i: p[i, 1] + (0 if state[i] == "race" else 3000))
        target = neon.mix(COLS[colour[lead]], BASE_COL, 0.45)
    elif duel_started in duel_winner:
        target = neon.mix(COLS[colour[duel_winner[duel_started]]], BASE_COL, 0.3)
    else:
        target = BASE_COL
    cur_col[0] = neon.mix(cur_col[0], target, 0.05)
    if frame % 15 == 0:
        build_keys.append((t, progress()))
    if PREVIEW and any(abs(t - pt) < 0.5 / FPS for pt in PREVIEW):
        draw(); surf.flush(); surf.write_to_png(f"prev_{t:05.1f}.png")
    if os.environ.get("DEBUG") and frame % 30 == 0:
        print(round(t, 1), duel_started, duel_released, [(state[i][:2], int(p[i, 0]), int(p[i, 1])) for i in range(NM)])
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
res = []
for d in range(len(DUELS)):
    if d in duel_winner:
        w = duel_winner[d]
        res.append((d, round(start_t.get(d, -1), 1), round(duel_tw[d], 1), round(duel_tl.get(d, 99) - duel_tw[d], 2), int(colour[w])))
print("misses", [k for k in start_t if isinstance(k, tuple)])
print("seed", SEED, "duels (d, start, win_t, margin, winner colour)", res)
print("champion", champion is not None and int(colour[champion]), "arrive", champ_t and round(champ_t, 2),
      "payoff", payoff_t and round(payoff_t, 2), "duration", round(t, 2))
print("music", song.recipe_str())

if not SIM_ONLY or AUDIO_ONLY:
    bk = np.array(build_keys)
    def build(tt):
        return float(np.interp(tt, bk[:, 0], bk[:, 1]))
    song.render("audio.wav", t, build=build)
