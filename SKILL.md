---
name: keyframe-coach
description: Animate characters, creatures and props in Blender with the 12 principles of animation adapted for games (timing, arcs, overlap, loops, root motion, blending, export). Covers bipeds, quadrupeds, insects and spiders, recreating an animation from a reference video or GIF, rendering looping GIFs, and exporting to Unity, Unreal, Godot or Roblox. Includes an audit script that finds loop seams, foot sliding and quaternion flips. Use when the user wants to animate, block, polish, review, render or export an animation in Blender, or asks why an animation looks stiff, floaty, slidey or pops in-engine.
---

# Keyframe Coach

`SKILL_DIR` = the directory containing this file.

## Connector: MCP for Blender (official)

All Blender work goes through the official **MCP for Blender** server (tools `mcp__blender__*`). If they are deferred, load them in one ToolSearch call: `select:mcp__blender__get_addon_status,mcp__blender__get_scene_info,mcp__blender__execute_blender_code,mcp__blender__look`.

- Start with `get_addon_status`. "Could not connect" means Blender is not running or the add-on's server is off. Check `pgrep -a blender` first:
  - **Blender is running**: ask the user to click **Start MCP Server** in its sidebar (or Preferences → Add-ons → **Interface: MCP for Blender**). Never start a second Blender over their open one.
  - **Blender is not running**: launch it yourself with the server started, then call `get_addon_status` again:
    ```bash
    nohup blender --python-expr "import bpy, addon_utils
    m = next(m for m in addon_utils.modules() if m.bl_info.get('name') == 'MCP for Blender')
    addon_utils.enable(m.__name__, default_set=True)
    bpy.app.timers.register(lambda: bpy.ops.blendermcp.start_server() and None, first_interval=2)" > /tmp/blender_mcp.log 2>&1 &
    ```
    Add `/path/file.blend` before `--python-expr` to open a file. If the add-on is not installed, run `uvx mcp-for-blender install-addon` first.
  - **Still no connection** (no display, launch fails): fall back to headless `blender -b file.blend --python script.py`. Keep the same workflow: save the `.blend` after each step, run the audit headless (see Audit), and replace `look` with rendered stills (`blender -b file.blend -o //look_#### -f 1,5,9`) that you open with Read. Tell the user you switched to headless and why.
- If it reports `up_to_date: false`, run `uvx mcp-for-blender install-addon`, then restart Blender or disable/enable the add-on.
- `get_scene_info`: scene facts as text. Use `fields: ["animation", "details"]` for actions and bones, `fields: ["settings"]` for frame range and fps, `root`/`query` to find the armature.
- `execute_blender_code`: runs bpy in the live Blender. Print what you need; work in small steps.
- `look`: the only way to see the result (see Workflow step 7).
- Do not use the old third-party `blender-mcp` (ahujasid) tools such as `get_viewport_screenshot` or `get_object_info`.

## Step 0: mandatory questions (always, before any animation work)

First run `get_addon_status` and `get_scene_info` (read-only), then ask everything below with the AskUserQuestion tool in **one** call. Skip a question only if the user already answered it in this conversation. Do not guess or assume defaults.

1. **Export target**: Unity, Unreal, Godot, Roblox. Put "Other: another engine, or *none – render only*" in the question text.
   - **Skip this question** when the user only asks for a render (GIF, video, stills, turntable) and names no engine: that is **render-only mode**. In render-only mode skip `engines.md` and step 8; render instead, and run the audit with `engine=""`.
2. **Style**: Realistic, Stylized/cartoony, Blocky/rigid-part (Roblox-like, low-poly), Anime/snappy.
3. **Scene** (only when the open scene has objects or `bpy.data.is_dirty` is true): "Blender already has a scene open. Where should I work?"
   - **New scene in this file (Recommended)**: `bpy.ops.scene.new(type='EMPTY')`; their scene stays untouched.
   - **Save it, then start a new file**: `bpy.ops.wm.save_mainfile()` (ask for a path if it was never saved), then `bpy.ops.wm.read_homefile(use_empty=True)`.
   - **Work in the current scene**: edit what is there.

   Never call `read_factory_settings`, `read_homefile` or delete objects in the user's scene without this answer. A factory reset also stops the MCP server.

Then read `references/engines.md` (the target's section only) and the matching style row in `references/principles.md`. For any creature with four or more legs, also read `references/legs.md` (gaits, footfall phases, leg IK, body and tail). For Roblox R6 rigs, also load the `roblox-blender-setup` skill and follow it for the rig and export steps. If the user gave a reference video or GIF, follow **Matching a reference** below.

Ask these too when they matter and are not obvious from the request: is the clip a **loop** (walk, run, idle) or a **one-shot** (attack, jump)? **In-place or root motion**? Is it **player-triggered** (needs fast startup) or **AI/cinematic**?

## Workflow

1. **Inspect**: `mcp__blender__get_addon_status`, then `mcp__blender__get_scene_info` (with `fields: ["animation", "details", "settings"]`), then find the armature, its actions, the frame range and fps.
2. **Plan timing**: write down the key poses and the frame number of each before keying. For attacks, list startup, active and recovery frames. For four or more legs, write the footfall chart (phase and duty factor per leg) from `references/legs.md`. Use `references/principles.md` for frame counts.
3. **Block** (pose-to-pose): key only the main poses, all on the same frames, with stepped/constant interpolation so the timing reads.
4. **Breakdowns**: add in-betweens that put the limbs on arcs. Check with Motion Paths.
5. **Spline and polish**: switch to Bezier, then offset the overlapping parts (head, arms, tail, cloth) by 1–3 frames, add overshoot and settle, and fix the easing.
6. **Audit**: run `scripts/audit.py` (below) and fix what it reports.
7. **Look**: `mcp__blender__look` with `mode: "frames"` and `frames: [...]` on the key frames, once with `view: [1, 0, 0.1]` (side) and once with `view: "camera"` (gameplay angle). Use `shading: "xray"` to see bones and `max_size: 512` for quick checks.
8. **Export** using the target's settings in `references/engines.md` (render-only mode: render the clip instead).

Blender 5.x: `action.fcurves` is gone. Read curves through `bpy_extras.anim_utils.action_get_channelbag_for_slot(action, obj.animation_data.action_slot)`.

## Audit

`scripts/audit.py` reads the animation data and reports concrete problems: loop seams that don't match, foot sliding, leftover linear keys, scale keys the engine will drop, every bone keyed on the same frames (no overlap), and left/right twinning. It changes nothing. Run it with `mcp__blender__execute_blender_code`:

```python
exec(open("<SKILL_DIR>/scripts/audit.py").read())
audit("Armature", engine="unity", loop=True)   # feet=["foot.L","foot.R"] if auto-detect misses
```

Headless: `blender -b file.blend --python-expr "exec(open('<SKILL_DIR>/scripts/audit.py').read()); audit('Armature', loop=True)"`.

It audits the **keyed** range (first to last key), not the scene range, so a loop keyed 1–17 with 17 = 1 and rendered 1–16 is checked correctly. Pass `frames=(a, b)` if the clip is something else. It finds feet automatically (the last foot/toe/paw/hand/hoof bone of each leg, skipping limbs that never touch the ground), so quadrupeds and many-legged rigs work too. Run it without `feet=` first; pass `feet=` only if it reports none, and then name the bone whose joint touches the ground (the paw/toe bone, not the ankle or wrist). When every frame is keyed (a baked or scripted clip) it skips the overlap and twinning checks and says so.

Treat its output as hints, not verdicts: a linear key on a mechanical motion or a held pose on purpose is fine. Tell the user what it found and what you will change before changing it.

## Matching a reference (video or GIF)

When the user wants an existing animation recreated, the reference is the spec: measure it before keying, and compare against it at the end.

1. **Extract and measure.** `ffmpeg -i ref.gif ref/f%03d.png`, then `ffprobe -v error -select_streams v -count_frames -show_entries stream=nb_read_frames,avg_frame_rate,width,height -of csv=p=0 ref.gif`. For GIFs, trust `avg_frame_rate` (frame delay), not `r_frame_rate`. View the frames with Read.
2. **Write down a spec table** before keying:
   - cycle length in frames (where the pose repeats) and fps
   - for each foot: the frame it lands and lifts (footfall order, how long it stays down)
   - stride length compared to body length, and how high the paws lift
   - body bob (how many per cycle), head and tail carriage, any flick or roll of the paws
   - camera angle and height, focal length guess, light and shadow direction, background colours
3. **Match the clip length exactly**: same frame count and fps. For a loop of N frames, key 1…N+1 with N+1 = 1 and render 1…N.
4. **Match the camera and lighting first.** Render one still of the rest pose and compare it with a reference frame before animating, so later comparisons line up.
5. **Key the contacts on the reference's frame numbers**, then the passing poses, then the body, head and tail.
6. **Compare side by side** (both clips with the same frame count), at the same frames:
   ```bash
   ffmpeg -v error -y -i ref.gif -i out.gif -filter_complex "[0:v]select='not(mod(n,2))',scale=240:-1,tile=8x1[a];[1:v]select='not(mod(n,2))',scale=240:-1,tile=8x1[b];[a][b]vstack" -frames:v 1 compare.png
   ```
   Fix the biggest difference first, usually in this order: stride length and leg reach, contact timing, body bob, then head, tail and paws. Repeat until the strips match.
7. **Report what still differs** (for example "shorter stride than the reference") instead of calling it a match.
