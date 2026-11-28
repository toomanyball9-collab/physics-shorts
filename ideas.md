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

## 2026-11-24 (evening run) — numbers + research
Sources: Metricool analytics (brand 8158935); Jelle's Marble Runs wiki "Marble Survival 100" (jellesmarbleruns.fandom.com/wiki/Marble_Survival_100);
Know Your Meme "Treadmill Racing" (knowyourmeme.com/memes/subcultures/treadmill-racing); "Dot Battle – a Javascript physics toy"
(sheep.horse/2025/10/dot_battle_-_a_javascript_physics_toy.html).
- Numbers (IG): Gate Race (marble-race, 11-23 pm) = BEST average watch time so far (20.6 s, skip 30.9%, 2,480 views, 21 likes), ahead of
  Ring Escape (20.1 s). Bell Curve 2,364 views / 15.0 s / 39% skip (ok reach, average watch). One Survives keeps the best reach (2,774).
  → marble-race earns a variation; a clear "who's out next" elimination structure holds people. YouTube still only reports up to 11-21; TikTok 0 views.
- Elimination ladders keep audiences for months: Marble Survival 100 = one race a day, bottom two cut after each event, single elimination at the
  end, numbered "Race N" chapters. Treadmill racing titles state the stakes up front ("FIRST TO FALL OFF LOSES!", "Guess who wins").
  → 11-25 pm Lift Laps: a looping one-screen course, the last marble to finish each lap drops through a trapdoor; stakes readable at a glance.
- Physics battles with no narration ("Who will win?") let viewers work out the rules by watching, like a sports announcer (Dot Battle: colour
  armies, x2/+4 chutes, damage on contact). → 11-25 am Colour Cycle: three colours in a cycle (pink>gold>cyan>pink), explained only by a
  3-dot legend with arrows; contact converts.
- Learned while building: pong-wars-style territory painting is self-balancing (a small territory has more frontier per ball, so it paints and
  splits faster) — 4 teams never finished in 80 s, even with split-on-paint, pop-on-painted-tile and annihilation rules. Cyclic dominance on contact
  gives big swings (a colour can drop to 3 balls and come back) and a built-in plot twist: when one colour dies, the colour that beats the
  current LEADER takes everything (11-25 am seed: pink led 104-16 and still lost to cyan).
- Looping courses: a lift that only pushes marbles up must not overlap the "not yet in the lift" wall clamp, or marbles pile up at the entrance;
  open the trapdoor only once the last marble reaches the final ramp, otherwise faster marbles on the next lap fall through it.

## 2026-11-25 (evening run) — numbers + research
Sources: Metricool analytics (brand 8158935); ballsimulator.com "10 pro tips to make your bouncing ball videos go viral"
(ballsimulator.com/en/blog/10-pro-tips-to-make-your-bouncing-ball-videos-go-viral/) and "How to create viral bouncing ball videos"
(ballsimulator.com/en/blog/how-to-create-viral-bouncing-ball-videos/); Tellter BallTok (tellter.com/projects/balltok);
Bustle on bottle-rolling ASMR psychology (bustle.com/life/bottle-rolling-videos-tiktok-psychology-asmr); almanac.com/calendar/date/2026-11-26 (Thanksgiving).
- Numbers (IG): Merge Sieve 2,359 views / 17.8 s / 33% skip (merge-ladder stays the most reliable family); Snowflake 2,275 views / 20 likes but only
  11.7 s and 39% skip — like Pendulum Wave, a calm "growing art" build gets likes but loses viewers early. Gate Race keeps the best watch time (20.7 s).
  YouTube now reports up to 11-22 and ranks differently from IG: Merge Duel 1,395, Break Through 1,355 (an IG flop!), Pendulum 1,349. TikTok: still 0 views on every post.
- Three hooks named in the Bustle piece: non-human motion, uncertainty over whether the object BREAKS, and a promise of transformation.
  → 11-26 am Glass Floors puts a "will this one hold?" question on every floor (visible strength = glass thickness, heat/sag as the pile grows);
  11-26 pm Feast is pure transformation (four tiny orbs → one orb that fills the ring).
- Vendor tips: start with the ball already moving toward the first obstacle (no slow intro), calibrate the climax so the peak lands inside the clip,
  rotate modes by weekday. "Expansion" (grow until it fills the frame) and "Accumulation" are standard modes — our twist on expansion is competitive:
  orbs eat leaves blown in on the beat and the clearly bigger orb swallows the smaller (agar-style), so viewers can pick a colour.
- Learned while building: with AREA-based growth the rivals' size ratio drifts back toward 1 (stalemates, nobody can swallow anyone); adding a fixed
  RADIUS per leaf + "bigger sweeps more" makes the leader pull away, so eliminations happen — and the early leader can still lose (11-26 pm seed:
  plum ate two rivals at 17 s, then got swallowed by cranberry at 43 s).
- Deep gravity piles (400 balls) need a position-based solver (8 projection passes + a little damping on resting contacts), otherwise the pile
  compresses and "boils"; a tiny random offset at the side walls stops impossible vertical columns of balls standing against a smooth wall.

## 2026-11-26 (evening run) — numbers + research
Sources: Metricool analytics (brand 8158935); "Majority Rules" marble race (cyanbeast01.itch.io/majority-rules); "Last Marble Wins"
(app.cinevva.com/arcade/last-marble-wins); Spin Striker app (apps.apple.com/us/app/-/id6749786592); "Viral YouTube Video Trends, November 2026"
(blog.mean.ceo/viral-youtube-video-trends-november-2026/).
- Numbers (IG): Lift Laps (marble-race) = BEST reach so far (3,306 views) and the LOWEST skip rate (28.4%), 18.0 s avg; Gate Race keeps the best
  watch time (20.7 s). Marble-race is now the strongest family on IG for both reach and holding people. Colour Cycle got the MOST likes ever (39,
  2,292 views) but only 12.7 s / 42.9% skip → "pick a side / who wins?" earns likes, the opener needs a faster first event.
  YouTube ranks calm loops differently: Snowflake 871 views, 13 likes, 3 comments and an average view of 85 s (people loop it). TikTok: still 0 views.
- Staged knockouts keep a field narrowing in visible steps (Majority Rules: 27 marbles, 6 legs with 2–3 qualifying slots each); "Last Marble Wins"
  inverts the race rule (the LAST to cross wins); Spin Striker's race mode = race to the bottom by breaking barriers, with a clean "simple view" for
  screen recording. → 11-27 am Knockout Duels: a physical 8-marble BRACKET, raced as 1-v-1 duels; a flip gate at the finish (the first marble falls
  through and knocks the flap shut, the second rolls over it into the pit), the winner rides a glass tube up into its next bracket slot.
- Hook rule of thumb for Shorts: one outcome, one tension point, one curiosity gap, and a payoff the visuals promise. → 11-27 pm Hot Potato (new
  family): one bomb, a visible fuse arc that always runs out on the beat (tension point), "who is holding it at zero?" (curiosity gap); touching
  passes it, the holder pops, survivors grow, 10 → 1.
- Learned while building: in a bracket every duel must start the moment the previous one is decided (not when its loser is gone), and the finish
  gate must stay shut until that loser has passed — otherwise either 4 s of dead time per duel or both racers of the next duel drop into the pit.
  Pegs closer than one marble-width to a wall trap marbles forever (keep wall gaps > 2·r + peg r).

## 2026-11-27 (evening run) — numbers + research
Sources: Metricool analytics (brand 8158935); BallEngine mode catalogue (ballengine.app/ball-simulator); ViralBalls "Ball Bouncing Simulator"
blog, 2026-03-10 (viralballs.com/en/blog/ball-bouncing-simulator-free-online-physics-sandbox); Loop Physics release "One ball becomes chaos"
(github.com/hthkrksy54-dotcom/Yt/releases/tag/sims-20261016-multiply-3).
- Numbers (IG): Lift Laps (marble-race) jumped to 5,061 views — twice any other post — with the lowest skip (27.2%) and 5 saves; Glass Floors
  (chain-reaction) got the MOST likes ever (47) with 18.6 s avg and 30.6% skip. The two best families right now: marble-race for reach,
  "will the glass hold?" for likes. YouTube still only reports up to 11-25 am; TikTok still reports 0 views on every post.
  → 11-28 am Glass Bridges combines both: a marble race where every glass bridge carries one marble fewer than are still racing (glowing pips);
  each marble that rolls over uses up a pip, the last one breaks through into a catch-bin.
- Generator catalogues now list "multiplier gates flood the arena until the glass breaks", "glass tower" and "balls battle down to one winner"
  as headline modes — every mode is sold with a definite end point ("until …", "down to one …"). → 11-28 pm Multiplier Rain (new
  multiplier-gates family): three sliding neon gates with PIPS instead of text labels (x2 / x3 / x2); a ball that falls through takes the gate's
  colour, through all three = gold (x12); the very first ball goes through the gates so the multiplying is clear inside 1 s; the tank fills
  with colour strata and the floor gives way under the weight.
- Mode lists keep the same core (escape rings, accumulate, multiply, HP-brick shatter, colour match, portals, increasing bounciness);
  portals and colour-match are the least used → candidates for a future original twist (e.g. portals that swap two marbles mid-race).
- Loop Physics posts every few hours with one-line hooks ("One ball becomes chaos – every bounce adds another"), every bounce playing the next
  note of a public-domain melody, and a "What would you change?" call to action → first comments that ask viewers to change a rule.
- Learned while building: collapsing a whole bridge drops the tight pack too (3–4 marbles fell at once on the first bridge) — only the spot under
  the extra marble should give way (a marble-sized hole, the rest of the glass stays). In the position-based solver, moving a freshly split ball
  sideways must also move its previous position, otherwise the shift turns into a huge sideways speed (clones flew across the tank).

## 2026-11-28 (evening run) — numbers + research
Sources: Metricool analytics (brand 8158935); Suika++ devlog "a new mode with an enclosing space, variable strength drops and shape swapping"
(itch.io/devlog/628090/suika-a-new-mode-with-an-enclosing-space-variable-strength-drops-and-shape-swapping); Balls Royale devlog "New version,
new game mode" (darkcodelight.itch.io/balls-royale/devlog/863797/new-version-new-game-mode); Tabcut "marble racing for the TikTok Creativity
Program" (tabcut.com/blog/post/i-found-the-perfect-niche-for-tiktok-creativity-program-marble-racing).
- Numbers (IG): Knockout Duels (marble bracket) = BEST average watch time ever (24.3 s, skip 28.7%, 3,343 views, 3 saves); Lift Laps keeps
  climbing (6,057 views). Hot Potato got the HIGHEST skip so far (44.9%, 13.0 s) — like Colour Cycle and Pendulum, zero-gravity ring battles
  lose people in the first 3 s even with an elimination hook; gravity machines/courses hold. YouTube: Glass Floors 1,219 / 11 likes, Gate Race
  now 1,133 (was 13). TikTok: still 0 views on every post. Marble-race is at 4 of the last 14 → rests tomorrow.
- Suika++ adds pressure from the ARENA itself (the floor keeps rising unless you merge fast). Our own take: the arena wears out under the
  balls — every bounce makes the tile thinner (thickness = bounces left, red = last one), last ball still bouncing wins → 11-29 pm Last Bounce
  (new floor-survival family, three floors, bounce period locked to 2 beats so the landings are the melody).
- Obstacle-course and marble-race creators stack small sound cues (countdown before the start, a bounce SFX on every hit) and keep the music
  original/royalty-free — matches our rule: notes on bounces, sfx for actions, own music engine.
- Chain-reaction variation for the morning (Glass Floors had the most likes): shishi-odoshi tipping cups with VISIBLE counterweights — a cup
  tips when the balls out-weigh its counterweight (real torque), pours into the next cup, swings back; the basin has the biggest one → 11-29 am
  Tipping Cups.
- Learned while building: the lever pivot must sit BELOW the load (with the pivot at mid-height a cup finds a half-tipped balance and never
  pours), the counterweight hangs a little below the pivot so an empty cup always swings back, and a flared outer wall pours at ~60°. Feed
  every cup near its outer lip, otherwise the stream hits the back of the tipped cup and flies off. For moving walls decide the side per wall
  from the ball's previous position (polygon membership pushed balls in the open top out through the wall). Wear-based eliminations cluster
  at the end; a thin top floor + thicker lower floors spreads the falls, and the landing test must also catch balls pushed into a floor by a
  collision (they fell through solid tiles).
