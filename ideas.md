# Ideas & learning log

Running notes from researching what works in ball / physics-simulation shorts. Add a dated section every run
(2–5 bullets: new formats seen, hooks, what drove views). Use them as inspiration for ORIGINAL concepts in our
neon style — never copy a specific video, its characters, names or melodies.

## 2026-11-18 — first research pass
Sources: knowyourmeme "Will the Ball Escape? / Ball Bouncing Brainrot", satisfyinglabs.com, tellter.com/projects/balltok,
YouTube "The cage SHRINKS every bounce..." (0sGLtcen3vo).

What drives views
- Escalation with an obvious end state (count / size / speed grows) + a question in the title ("Will it escape?", "until it's full").
- Sound synced to every bounce; a melody that becomes clearer as it speeds up is the biggest known hook (KYM examples 38M–67M views).
- Series framing ("Follow so you don't miss tomorrow's simulation", "Day N of …") and comment bait: named teams, "who wins?", "guess how many".
- Climax must land inside the clip (our payoff at 55–65 s fits), endings: escape, trap/cage breaking, survivor reveal.

Mechanics worth turning into our own concepts (family in brackets)
- Shrinking cage: each wall hit pulls the walls inward — "how long can it last?" [shrinking-arena]
- Ball grows / speeds up every bounce until it fills the arena [growing-ball]
- Escape spawns 2 new balls; regenerating rings that delay the escape [escape / ring-break] — done 11-18 (Ring Escape)
- Every ball–ball collision births a new ball until packed [wall-split variant]
- Spikes on the wall: balls stick and become obstacles, so each attempt takes a new route [new: sticky-spikes]
- Timed freeze: each ball has N seconds to escape, frozen balls become obstacles that reshape the arena [new: freeze-maze]
- Team battle with cut lines / territory, last colour standing wins — viewers pick a side [color-battle]
- Each bounce draws a glowing line from wall to ball until a web/mandala forms [trails]
- Black hole in the centre eats balls; only those that slip through a gap survive [orbits]
- Multiplier zones (x2 / x5 bands) on a spiral or ring [new: multiplier-zones]
- Merge ladder: two same-size balls merge into a bigger one, final giant ball breaks the container [new: merge-ladder]
- Crusher jaws squash balls which split; the trap breaks at the end [slicer variant]
- Bounces reveal a hidden picture / shape (keep it abstract or geometric, no logos/characters) [converge]

Title patterns that work: "[thing] [verb] every bounce…", "Can one ball …?", "until it's completely full",
"Which colour wins?", "Guess how many …", "Day N of …".

## 2026-11-18 — feedback from the user
- Rejected 'Shrinking Cage' (shape changed triangle→hexagon and balls appeared on hidden size thresholds): changes without a visible cause feel random. Every change needs a rule the viewer can see.
- Replaced with 'Merge Ladder' (dropper on the beat + same-size balls merge): both rules are obvious within 2 seconds.


## 2026-11-18 (evening run) — research + numbers
Sources: ballengine "viral growth blueprint" (funcirclegames.pages.dev/blog/viral-growth-blueprint-tiktok-satisfying-content),
ballengine Accumulate/spawner mode (funcirclegames.pages.dev/modes/spawner), korpi.ai/best-ai/ball-escape-ring,
kottke.org "Randomly bouncing balls arrange themselves into satisfying patterns", funcirclegames.pages.dev/help/simulation-modes/drawer-mode.
- Our first numbers: Ball x2 (11-17) on IG 154 views, avg watch 8.8 s of 65 s → most people leave in the first ~10 s.
  The first 10 s need a visible event every 1–2 s (first spawn/bounce inside 1 s, early events dense), not just a slow build.
- Spawner tools list the common "new ball" triggers: wall hit, balls touch, split, steady drop, escape, count to goal, merge numbers.
  "Balls touch → new ball" is the one we haven't done → 11-19 am Kiss Spawn (with a visible charge ring so growth stays readable).
- Retention diagnosis rule of thumb: drop in 1st second = hook, mid-video sag = pacing, drop before the end = payoff too late.
  Keep the payoff ≤ 62 s and make the 20–40 s stretch the busiest-changing part.
- "Drawer"/trail modes (ball path left as light) + "patterns from bouncing" are a separate satisfying genre: the art itself
  is the reward even before the climax → 11-19 pm String Orb (growing ball whose path draws a rosette).
- Caption hooks that keep showing up: "wait for the last bounce", "will it escape in time?", "which colour wins?", "wait for the overflow".

## 2026-11-18 (evening) — user feedback
- Said the 2nd video of the day felt lower quality than the 1st; asked for a slicer: a blade moving repeatedly inside the circle, every cut splits a ball into two smaller ones, start BIG.
- Built 'Blade Cut' (replaces 11-19 pm String Orb). Learned: cut rate is driven by pieces crossing the blade, not blade speed → tune piece speed + blade energy; an energy-based pendulum that eventually loops over the top gives a natural visible escalation.
- User on Blade Cut v1: 'too out of place, badly made'. What was wrong: grey stick blade that didn't match the neon look, rainbow generation colours (noise), 470 crumbs, pieces piling up along the blade. v3 fixes: neon laser blade in the same glow language as the ring, one colour family (blue→mint), ONE big hero ball at the start (like Ring Escape's single ball), visible half-disc split animation, no pile-ups. Benchmark the user likes: Ring Escape — clean structure, one clear rule, few elements, steady escalation.
- Research: viral 'A spinning paddle doubles every ball it touches' short (youtube.com/shorts/pY7NhfIRwP0); ViralBalls' 10 modes (classic rings, accumulation/freeze, multiply, lines, paint %, target order, grow, shatter HP walls, colour match, portals) — viralballs.com/en.
- User: drop the slicer entirely ('too awkward'); make videos with the feel of Ring Escape (13 neon rings). Their favourite so far = Ring Escape. Lean on its structure (one ball, nested neon layers, escape → break → +2 balls, zoom out, sealed final layer bursts) and vary arena shape / palette / music / twist. Made Hex Escape for 11-19 18:00.

## 2026-11-19 (evening run) — numbers + research
Sources: Metricool analytics (brand 8158935); YouTube Shorts "What happened in the end? 😳" (youtube.com/shorts/P0H8Pv7aAFw),
"sounds familiar 🤔" (youtube.com/shorts/e6ZImW6HeWc), "What sound are balls making?" (youtube.com/shorts/lDoadSgwjlk),
"Can the Ball Beat the Shrinking Circle?" (youtube.com/shorts/CPw2d5chCtg); ballengine trail mode (main-copy.funcirclegames.pages.dev/modes/trail).
- IG numbers (~36–46 h): Ring Escape 2,218 views / 36 likes / avg watch 20.2 s / skip 29.7%; Merge Ladder 2,358 views / 8 likes / 14.6 s / skip 37.2%;
  Ball x2 158 views / 8.9 s / skip 40.6%. Escape = ~4.5x the likes per view and +40% watch time; merge reaches as many people.
  → keep escape as the quality benchmark, but merge-ladder earns a variation too. TikTok still reports 0 views for all posts (check the account).
- Lowest skip rate = structure visible in frame 1 (13 rings) + motion in the first second. Every opener should show the whole "machine" at once
  and have a first event (swallow / merge / escape) inside ~1 s.
- Title trend on ball sims: mystery questions that invite comments ("What happened in the end? 😳", "Sounds familiar 🤔", "Do you know this one?")
  and versus framing ("Can the ball beat …?"). Use "vs" + a question; ask viewers to pick a side in the first comment.
- Trail modes: short coloured trails make curved paths (gravity) readable; long rainbow trails on many balls wash out to grey → keep trails short, per-ball colour.
- New this run: [orbits] Black Hole (horizon grows with every swallowed ball, r ∝ M; tide tears the ring) and a merge-ladder variation
  with two teams that can't merge with each other (Merge Duel, "teal or amber?").

## 2026-11-19 (late) — user feedback
- The zigzag crack strokes on the heated wall (Merge Duel capsule bottom, Black Hole ring, also used in Merge Ladder / Break Through) look cheap and alien to the neon look — never show them again. Tension = red heat + glow pulse + shake only. Re-rendered both 11-20 videos without them (DRAW_CRACKS = False).

## 2026-11-20 (evening run) — numbers + research
Sources: Metricool analytics (brand 8158935); BallEngine escape-mode help (funcirclegames.pages.dev/help/simulation-modes/escape-mode);
UMD LecDem "Animation highlight: pendulum waves" (lecdem.physics.umd.edu/tools-and-resources/lecdem-blog/460-animation-highlight-pendulum-waves-blog.html);
Wolfram "Pendulum Waves" (demonstrations.wolfram.com/PendulumWaves/).
- Numbers (IG, 1–3 days): Ring Escape 2,233 views / 37 likes / 20.2 s avg / skip 29.7%; Hex Escape 2,207 / 10 / 17.6 s / 31.1%;
  Merge Ladder 2,386 / 9 / 14.5 s / 37.4%; Break Through 226 / 2 / 11.4 s / 42.9% (flop). YouTube finally reports: Ball x2 1,074 views
  (8 s avg), Ring Escape 813 views (16 s avg). Escape is consistently the best for watch time; ring-break (bricks) didn't land — rest it.
  TikTok still reports 0 views on every post → the account/connection needs checking.
- Escape tools now ship gap patterns (spiral, staggered, opposite), alternating rotation, shrink mode and time-trial clocks. Our own new
  twist instead: COLOUR GATES — the ball changes colour on every bounce and can only pass the gate of its own colour (near misses on the
  wrong colour are the tension). → 11-21 am Colour Gate.
- Pendulum waves: periods chosen so ball n makes exactly (K+n) swings in one cycle → patterns (wave, snakes, 2/3/4 interleaved groups,
  chaos) and a guaranteed full realignment at the cycle time. Perfect for our rules: every change has a visible cause, the payoff is pure
  physics and can be placed exactly on a bar, and the video loops by itself. → 11-21 pm Pendulum Wave (top ball's period = 1 bar).
- Escape-mode presets suggest 10–15 rings with large gaps for "quick breakout", 30–50 rings with small gaps for long tense runs — our
  12 rings + slow-opening gaps sit in the quick-breakout zone, which matches the 55–65 s payoff.
