# Many-legged locomotion: 4, 6 and 8 legs

Read this for any creature with four or more legs. Frame counts assume 30 fps (scale as in principles.md). Always prefer measured reference (a video, Muybridge plates) over these numbers.

## The method: phase and duty factor

Describe every gait with two numbers per leg, then key from them (by hand or by script):

- **Phase**: when in the cycle the foot lands, 0–1. Legs a quarter cycle apart have phases 0 and 0.25.
- **Duty factor**: the fraction of the cycle the foot is on the ground. A walk is above 0.5 (at least one foot of each pair is always down); running gaits drop below 0.5 and get an airborne moment.

For an in-place loop, every planted foot slides backward at the **same constant ground speed**: stride length ÷ (duty factor × cycle length). `audit.py` checks this (FOOT SLIDE, FOOT SPEED MISMATCH). Put a timeline marker on each foot's landing frame, and draw the footfall chart (one row per leg, filled where the foot is down) in your plan before keying.

## Four legs

### Gaits (phase of landing; LH = left hind, LF = left fore)

| Gait | LH | LF | RH | RF | Duty factor | Notes |
|---|---|---|---|---|---|---|
| Walk (lateral sequence) | 0 | 0.25 | 0.5 | 0.75 | 0.6–0.8 | Default for almost all quadrupeds: hind foot, then same-side forefoot, then the other side. Four even beats. |
| Walk (diagonal sequence) | 0 | 0.75 | 0.5 | 0.25 | 0.6–0.8 | Hind foot, then the *opposite* forefoot. Mostly primates; don't use it for a dog, cat or horse. |
| Trot | 0 | 0.5 | 0.5 | 0 | 0.35–0.5 | Diagonal pairs land together (LH + RF, RH + LF). Two beats; a short airborne moment at speed. |
| Pace | 0 | 0 | 0.5 | 0.5 | 0.4–0.5 | Same-side pairs together. Camels, giraffes, some dogs when tired; the body rolls side to side. |
| Canter / gallop | asymmetric | | | | < 0.4 | Feet land in a fast 3- or 4-beat sequence with a long airborne phase. Block it from reference (Muybridge), not from a table. |

Within a beat, offset paired feet by 1 frame instead of landing them on the exact same frame, unless it's a stylized trot.

### Timing and stride (starting points)

- **Cycle length** (all four feet once): small animals (cat, fox, small dog) walk in about 20–30 frames, medium and large dogs 28–36, a horse 32–42. A trot takes about 55–65% of the walk cycle. A human-made fox walk reference measured 17 frames at 24 fps (21 at 30 fps): small animals walk fast.
- **Stride**: at a normal walk each foot travels roughly one shoulder-to-hip length per cycle. AI-made walks consistently undershoot this, with short, careful steps; check the reach against reference.
- **Register**: foxes, cats and many dogs *direct register*: the hind paw lands in, or right next to, the print the forepaw just left. That is a quick check of stride and timing.

### Legs (digitigrade: dogs, cats, foxes; hooves work the same way)

- The joint that looks like a "backwards knee" is the **ankle (hock)** on the hind leg and the **wrist** on the foreleg. Hind: knee points forward, hock points back. Fore: elbow points back, wrist bends forward.
- **Forepaw**: on lift it peels from the back and **flicks up and back** as the wrist folds, then the leg reaches forward and the paw unfolds just before contact. The flick is the most visible detail of a good quadruped walk; don't skip it.
- **Hind paw**: lifts lower; the hock flexes and the paw stays closer to the ground on the swing.
- **IK**: give every leg IK a **pole target** (in front of the hind knee, behind the fore elbow) or the joints flip between frames. A 3-segment digitigrade leg is unstable as a single IK chain: use 2-bone IK on the upper two bones and key or drive the lowest bone (paw angle) separately, or use Rigify's `limbs.rear_paw` / `limbs.front_paw` rig types. Imported rigs (glTF, FBX) have guessed bone tails: aim each bone's tail at its child joint before adding IK, and set the IK `use_tail` to match.

### Body, head and tail

- **Hips and shoulders** each rise and fall twice per cycle (highest as a leg passes under them, lowest just after contact), the shoulders about a quarter cycle behind the hips. The hips also rock: the side whose hind leg is swinging drops slightly.
- **Spine**: bends sideways a little toward the forward foreleg in a walk; nearly rigid in a trot.
- **Head**: predators (fox, cat, dog) keep the head and eyes nearly level, countering the shoulder bob. Hoofed animals nod the head with each forefoot step.
- **Tail carriage** belongs to the species: a fox carries the brush out level or just below the back line, a cat often up, a dog's varies with mood. Set the carriage first, then add sway: side to side, each segment 1–3 frames behind the one before (follow-through). The rest pose of an imported model is rarely the right carriage.

## Six legs (insects)

- **Alternating tripod** (the standard insect walk): legs are two sets of three: L1 + R2 + L3, and R1 + L2 + R3 (1 = front, 3 = hind). One set is planted while the other swings. Phases 0 and 0.5, duty factor about 0.5.
- **Wave (metachronal) gait** for slow or careful walking: one leg at a time lifts, in a wave from back to front on each side (L3 → L2 → L1, then the right side, half a cycle later). Duty factor 0.7–0.85. Use it for heavy, creeping or cautious creatures.
- Legs in a set don't move exactly together: offset them by 1–2 frames.
- **Roles**: front legs reach forward and pull, middle legs point sideways, hind legs push from behind the body. The body stays nearly level, with a small side-to-side yaw.
- **Timing**: real insects step far too fast to read. Pick the speed for readability: about 8–16 frames per cycle for a dog-sized creature, slower for bigger ones.
- Exceptions: camel spiders (solifuges) hold the front pair up like feelers and walk in tripods on the rest.

## Eight legs (spiders, scorpions)

- **Alternating tetrapod**: two sets of four: L1 + R2 + L3 + R4, and R1 + L2 + R3 + L4. One set is planted while the other swings. Phases 0 and 0.5, duty factor about 0.5 at speed, higher when slow.
- Offset the legs within a set by a frame or two, and let the back legs trail a little: identical timing on every leg looks mechanical.
- Exceptions: harvestmen (daddy longlegs) hold the second pair up as feelers and walk on the other six in tripods.
- The body sits low, with the knees above it. The abdomen lags the cephalothorax by 1–3 frames (follow-through) and settles after stops.
- A contact shadow under each foot makes it much easier to read which legs are down; check it in the gameplay camera.

## Sources

- [Animating Four-Legged Beasts (Game Developer)](https://www.gamedeveloper.com/art/animating-four-legged-beasts): footfall order for walk, trot, canter and gallop.
- [Animating Quadruped Characters in The Flame in The Flood (GDC 2016)](https://gdcvault.com/play/1023209/Animating-Quadruped-Characters-in-The): game quadruped locomotion, foot sliding, blending gaits.
- [Rune Skovbo Johansen, semi-procedural locomotion (GDC 2009)](https://blog.runevision.com/2009/03/locomotion-system-gdc-2009-slides.html): foot placement on varied ground.
- Muybridge photo reference: [The Attitudes of Animals in Motion (Project Gutenberg)](https://gutenberg.org/files/37743/37743-h/37743-h.htm), [National Gallery of Art plates](https://www.nga.gov/collection/art-object-page.167069.html).
- Hildebrand's gait framework (duty factor, lateral and diagonal sequence): [Cartmill et al. 2002, Support polygons and symmetrical gaits in mammals](https://www.originalwisdom.com/wp-content/uploads/bsk-pdf-manager/2019/10/Cartmill-et-al_2002_Support-polygons-and-symmetrical-gaits-in-mammals.pdf), [eLife: Work minimization accounts for footfall phasing in slow quadrupedal gaits](https://elifesciences.org/articles/29495).
- [Simplified Models of Terrestrial Arthropod Gaits (Wolfram)](https://demonstrations.wolfram.com/SimplifiedModelsOfTerrestrialArthropodGaits/): tripod and tetrapod leg sets, exceptions.
- [Tripod gait, biology to IK (Hackster)](https://www.hackster.io/HiwonderRobot/tripod-gait-for-hexapod-robots-biology-to-inverse-kinematic-1d94b0), [Project Leptan tripod GIF](https://project-leptan-docs.readthedocs.io/en/latest/Overview.html), [stick-insect gait diagrams (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3755227).
- [Real-Time Approximation of Convincing Spider Behavior (SIGGRAPH 2014 poster)](https://history.siggraph.org/wp-content/uploads/2022/12/2014-Poster-84-Herbst_Real-Time-Approximation-of-Convincing-Spider-Behavior.pdf), [Spider animation tutorial (Highend3D)](https://highend3d.com/tutorials/spider-animations-tutorial), [Polycount thread on spider leg timing](https://polycount.com/discussion/comment/2182240).
- Richard Williams, *The Animator's Survival Kit*: quadruped and spider walk pages.
