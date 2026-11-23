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

## 2026-11-21 (evening run) — numbers + research
Sources: Metricool analytics (brand 8158935); Know Your Meme "Weapon Ball Battles" (knowyourmeme.com/memes/weapon-ball-battles-earclacks);
BallEngine Shorts generator page (funcirclegames.pages.dev/youtube-shorts-generator); jimmylol "The bouncing ball project" devlog
(jimmylol.itch.io/the-bouncing-ball-project/devlog/853575/new-mode); integral-pixels "Ultimate Galton Board" (integral-pixels.itch.io/ultimate-galton-board).
- Numbers (IG): Merge Duel 2,271 views / 11 likes / 16.8 s avg / skip 31.0% → merge-ladder keeps the highest reach and now good watch time too.
  Black Hole 1,458 / 23 likes (best like-rate after Ring Escape) but 10.9 s avg and 42% skip → the rule is loved, the opener was too slow/empty.
  YouTube: Ring Escape 1,277, Ball x2 1,120, Merge Ladder 1,069, Hex Escape 1,033, Break Through 1,017, Black Hole 105 (new). TikTok: still 0 views on every post.
- Versus + escalation series are the big growth engine in ball battles: two circles, each hit upgrades the attacker (more damage / more spin), titles
  "A 🗡 VS 🛡 B" with emojis between the names, and tournament / "training arc" episodes that give a reason to follow. → use "X vs Y" titles and
  pick-a-side first comments; consider a recurring league format later (original names only).
- Vendor guidance from ball-sim generators: escalate (speed / size / count) so viewers don't drop mid-video; silent clips underperform; "rhythmic"
  modes play the next note of a melody on every collision; mode hooks are one-liners ("One ball becomes hundreds", "Break out through the rings").
- "Tiny difference → chaos" (many copies started 0.000001 apart) is its own satisfying genre with built-in comment bait ("which colour survives?").
  Learned while building One Survives: a ball in a round ring (even with gravity) is almost regular — the copies stay glued together for 30+ s and then
  leave all at once. Convex pegs inside the ring (Sinai-billiard style) make the split start within ~2 s and give a smooth spread of exits.
- Grow-on-every-wall-hit and Galton boards keep appearing as evergreen modes; Galton is "relaxing" rather than tense — would need a twist + payoff.

## 2026-11-22 (evening run) — numbers + research
Sources: Metricool analytics (brand 8158935); BallEngine Escape Mode help (funcirclegames.pages.dev/help/simulation-modes/escape-mode) and
viral sharing tips (funcirclegames.pages.dev/help/social-and-sharing/viral-sharing-tips); WaveSpeed bouncing-ball video maker
(wavespeed.ai/free-tools/bouncing-ball-video-maker); App Store "Idle Ball Escape: Smash Rings" (apps.apple.com/us/app/idle-ball-escape-smash-rings/id6759967969).
- Numbers (IG): Colour Gate flopped (250 views, 11.7 s avg, 42.7% skip) while Ring/Hex Escape hold ~2.2k and 17–20 s → the escape
  structure works, but the twist must be readable in the first second without explanation (colour cycling + matching gates wasn't).
  Pendulum Wave got reach (2,393) but the weakest watch time (9.9 s, 41.6% skip) → calm, non-escalating concepts lose viewers early.
  YouTube: Merge Duel 1,129, Colour Gate 493 (15 s avg). TikTok: still 0 views on every post.
- Escape tools keep adding variants: shrink mode (rings close in until they break), time trial (+5 s per ring), gap patterns
  (spiral / staggered / opposite), and "progressive break stages" — the break SOUND changes as more rings are gone. Our own twist
  today: every wall hit makes a ball bigger and it must still FIT the gap (too-big balls bounce off the gap edges) → 11-23 pm Grow Escape.
- Vendor viral tips map modes to goals: suspense = escape, visible progress = counters, build-up = spawner, payoff = breaker,
  calm = drawer/wave. Calm mechanics need a progress goal + payoff on top → 11-23 am Bell Curve: a Galton board (calm) with a
  dashed target curve to fill, a live counter, rising drop rate and a floor that gives way under the weight.
- Generators ship "ring escape", "split on every bounce" and "piano bounce" as their core scenes (notes on every bounce,
  seed-picking for a good run); the idle game "Idle Ball Escape" combines escape rings with GRAVITY → future escape variation:
  gravity + rotating rings, the ball has to bounce its way up and out.

## 2026-11-23 (early) — user feedback
- Grow Escape (escape variation: balls grow on every wall hit) was rejected before posting: "it's the same video with only the song changed".
  A rule tweak inside the same 12-ring look does NOT count as a new video for the user — escape variations need a clearly different
  arena/structure, or rest the family for a while. Replaced 18:00 with Gate Race (new marble-race family, scrolling course, elimination gates).
- The user liked Bell Curve (plinko): dense gravity piles, colour strata, a target to fill and a weight-driven payoff.

## 2026-11-23 (evening run) — numbers + research
Sources: Metricool analytics (brand 8158935); Ball Chaos – Visual Playground (apps.apple.com/us/app/ball-chaos-visual-playground/id6479562631);
ballsimulator.com "How to create viral bouncing ball videos" (ballsimulator.com/en/blog/how-to-create-viral-bouncing-ball-videos/);
kottke.org "The ball is its own video" (kottke.org/24/11/0045638-ive-seen-a-lot-of); jimmylol devlog (jimmylol.itch.io/the-bouncing-ball-project/devlog).
- Numbers (IG): Merge Spin 2,487 views / 18 likes / 19.3 s avg (2nd-best watch time after Ring Escape) and One Survives 2,642 views (best reach,
  13.6 s avg, 33% skip). Merge-ladder is now the most reliable family (4 posts, all 2.3–2.5k, 14.5–19.3 s). Pendulum Wave keeps the weakest
  watch time (9.9 s). YouTube still only reports up to 11-21 (Colour Gate 493). TikTok: 0 views on every post — the connection/account needs a look.
- Generator vendors now ship "Accumulation" (balls freeze in place and become part of the arena) and "Infinite Loop" (perfect loop = retention)
  as headline modes; apps add "Square Race" obstacle courses and "Music Square" (rhythm-synced motion). → our own take on accumulation:
  freezing balls grow a 6-fold mirrored SNOWFLAKE (diffusion-limited growth: drifting balls stick on touch, the crystal copies each one six ways);
  the arms naturally grow toward where the balls come from, so the vents decide the shape. Payoff = frost wedging: an arm touches the ring → ring splits.
- Learned while tuning Snowflake: with 12-fold copies, ~90 real freezes are enough to reach the ring — the launch rate must start very low
  (every other beat) or it's over in 30 s. A frozen copy that lands past the ring must be clamped onto the ring (not skipped), otherwise the
  crystal stalls just short of the wall and the payoff never comes.
- Merge variation that looks new: a TILTED sieve splitting the capsule (pegs with gaps): small balls rain through, big ones roll to the low end
  and pile up; a flat sieve clogged in ~20 s and stopped the sorting — tilt keeps the upper part open so the sorting stays visible to ~45 s.
  Two-stage payoff with a visible cause each: the sieve snaps under the packed top pile, the avalanche's impact breaks the floor on the next bar.
- Engagement idea from reviews of ball apps: viewers ask for "balls that split after escaping" and "a sound on every escape" → sound design per
  event (tick on freeze, chime every few) keeps dense moments readable.
