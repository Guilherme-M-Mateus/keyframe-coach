# Keyframe Coach

**A Claude Code skill that animates in Blender like a game animator would.**

Keyframe Coach teaches Claude the 12 principles of animation, adapted for games, and gives it a workflow to drive a live Blender through the official MCP for Blender connector: plan the timing, block the key poses, polish, audit, look at the result, and export to your engine or render a looping GIF.

![Human reference vs Claude without the skill vs Claude with Keyframe Coach](assets/compare-test1.gif)

<sub>Recreating a human-made walk cycle from a GIF. Same model (Claude Opus 5.5), same prompt, same fox.</sub>

---

## Contents

- [What it does](#what-it-does)
- [Results](#results)
- [Requirements](#requirements)
- [Install](#install)
- [Usage](#usage)
- [The audit script](#the-audit-script)
- [What's inside](#whats-inside)
- [Limitations](#limitations)
- [License](#license)

## What it does

- **Asks before it animates.** Export target (Unity, Unreal, Godot, Roblox, or render only), style (realistic, cartoony, blocky, anime), and where to work if you already have a scene open. It never wipes your scene without asking.
- **Animates like an animator.** Timing is planned in frames, then blocked pose-to-pose, then broken down onto arcs and polished with overlap, follow-through and easing.
- **Handles more than bipeds.** Built-in reference for quadrupeds (walk, trot, pace), insects (tripod and wave gaits) and spiders (tetrapod gait): footfall phases, duty factors, leg IK and tail carriage.
- **Matches a reference.** Give it a GIF or video and it measures the frame count, footfalls and stride first, matches the camera, then compares its render side by side with yours.
- **Checks its own work.** A read-only audit script finds loop seams, foot sliding, quaternion flips, scale keys your engine will drop, and missing overlap.
- **Looks at the result** from the side and from the gameplay camera, instead of trusting the numbers.
- **Exports correctly** for Unity, Unreal, Godot and Roblox (scale, leaf bones, loops, root motion, bone-scale support).

## Results

Two tests on Claude Opus 5.5, each run once with and once without the skill, using the same low-poly fox model.

### Test 1: recreate a human-made animation from a GIF

![Test 1 comparison](assets/compare-test1.gif)

| | No skill | With Keyframe Coach |
|---|---|---|
| Clip length | Guessed (24 frames) | Measured the reference (17 frames at 24 fps), made 16 |
| Tail carriage | Model's default, hanging down | Raised to match the reference |
| Framing and lighting | Close | Matched by comparing rendered frames with the reference |
| Paw contacts | Paws slide back at different speeds (found by the audit) | Constant slide on all four paws, front paws roll and curl |
| Turns | 13 | 44 |

### Test 2: a walk cycle from scratch, rendered as a looping GIF

![Test 2 comparison](assets/compare-test2.gif)

| | No skill | Keyframe Coach v1 | Keyframe Coach v2 |
|---|---|---|---|
| Staging | High camera, flat light | Three-quarter view, real shadows | Side-on, three-point light, IK-planted paws |
| Blender | Headless script | Fell back to headless, skipped the audit | Launched Blender itself, worked live, audited |
| Turns | 12 | 18 | 35 |

v2 is the current version: it adds render-only mode, launches Blender with the connector when it isn't running, protects your open scene, and fixes several false alarms in the audit.

**Honest take:** the skill clearly improves staging, reference matching and correctness (loops, contacts), at roughly 1.5–3× the turns. Neither version matches the human animator's stride and paw flick yet. These are single runs, not a benchmark.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- [Blender](https://www.blender.org/) 4.2 or newer (tested on 5.2)
- The official **MCP for Blender** add-on and connector:
  ```bash
  uvx mcp-for-blender install-addon
  ```
  Then in Blender: Preferences → Add-ons → enable **Interface: MCP for Blender** → **Start MCP Server**, and add the `blender` MCP server to Claude Code.
- `ffmpeg` (optional, for matching a reference video or GIF)

## Install

Clone into your Claude Code skills folder:

```bash
git clone https://github.com/Guilherme-M-Mateus/keyframe-coach ~/.claude/skills/keyframe-coach
```

Restart Claude Code. The skill shows up as `/keyframe-coach`.

## Usage

Invoke it directly:

```text
/keyframe-coach Make a run cycle for the wolf rig, root motion, exported for Unreal.
```

Or just ask; Claude loads it when the request fits:

```text
Animate this fox walking and render it as a looping GIF on a white floor.
Recreate the attack in this GIF on my character.
Why does my walk cycle slide in Unity?
```

## The audit script

`scripts/audit.py` is read-only and runs inside Blender, live or headless:

```python
import os
exec(open(os.path.expanduser("~/.claude/skills/keyframe-coach/scripts/audit.py")).read())
audit("Armature", engine="unity", loop=True)
```

```bash
blender -b walk.blend --python-expr "exec(open('scripts/audit.py').read()); audit('Armature', loop=True)"
```

Example output:

```text
Audit 'Fox_Walk' on root: frames 1-17 (first/last key) @ 24 fps, 91 curves
LOOP SEAM: 2 curves don't match start/end: pose.bones["b_LeftLeg02_016"].rotation_quaternion[3] ...
BAKED: every bone keyed on (almost) every frame; overlap/twinning checks skipped, judge offsets by eye
FEET checked: b_LeftFoot02_018, b_LeftHand_011, b_RightFoot02_022, b_RightHand_08 (in-place)
```

| Check | What it catches |
|---|---|
| Loop seam | Start and end don't match, or the motion snaps across the loop point |
| Foot slide | Planted feet drift (root motion), or slide unevenly (in place) |
| Foot speed mismatch | In-place feet sliding back at different speeds |
| Quaternion flip | A limb swinging the long way round between keys |
| Scale keys | Squash and stretch your engine (Roblox, Unity Humanoid) will drop |
| No overlap / twinning | Every bone keyed on the same frames; left and right mirrored |
| Constraints | IK and other constraints that need baking on export |
| Interpolation | Leftover linear or constant keys |

It finds feet automatically on bipeds, quadrupeds and many-legged rigs, and checks the keyed range, so a loop keyed 1–17 and rendered 1–16 is handled correctly.

## What's inside

```text
keyframe-coach/
├── SKILL.md              # Workflow, questions, connector setup, reference matching
├── references/
│   ├── principles.md     # The 12 principles for games, style dials, frame budgets
│   ├── legs.md           # 4-, 6- and 8-legged gaits, leg IK, body and tail (with sources)
│   └── engines.md        # Export settings for Unity, Unreal, Godot, Roblox
├── scripts/
│   └── audit.py          # Read-only animation audit
└── assets/               # README comparison GIFs
```

## Limitations

- Needs the official MCP for Blender connector. Without a display it falls back to headless Blender, which is slower to iterate.
- Roblox R15 and custom skinned rigs are untested; R6 rigs use the separate `roblox-blender-setup` skill.
- Motion quality still trails a human animator, especially stride length and secondary detail.
- Results above are single runs on one model.

## License

[MIT](LICENSE)
