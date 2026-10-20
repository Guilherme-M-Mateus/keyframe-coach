# Read-only audit of an armature's active action. Usage (inside Blender):
#   exec(open(".../audit.py").read()); audit("Armature", engine="unity", loop=True)
# Also works headless: blender -b file.blend --python-expr "exec(open('.../audit.py').read()); audit('Armature', loop=True)"
import bpy, re, statistics

NO_SCALE = {"roblox"}  # targets that drop bone scale keys (Unity Humanoid too; warned separately)


def _fcurves(obj):
    ad = obj.animation_data
    act = ad.action
    try:
        from bpy_extras import anim_utils
        cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
        return act, (list(cb.fcurves) if cb else [])
    except (ImportError, AttributeError):  # Blender < 4.4
        return act, list(act.fcurves)


def _bone(fc):
    m = re.match(r'pose\.bones\["(.+?)"\]', fc.data_path)
    return m.group(1) if m else None


def _mirror(name):
    for a, b in ((".L", ".R"), ("_L", "_R"), ("_l", "_r"), ("Left", "Right"), ("left", "right")):
        if a in name:
            return name.replace(a, b)
    return None


def _key_range(fcs):
    xs = [k.co[0] for fc in fcs for k in fc.keyframe_points]
    return (int(round(min(xs))), int(round(max(xs)))) if xs else None


def audit(arm_name, engine="", loop=None, feet=None, in_place=None, frames=None, eps=1e-3):
    obj = bpy.data.objects[arm_name]
    scene = bpy.context.scene
    if not (obj.animation_data and obj.animation_data.action):
        print(f"{arm_name}: no active action"); return
    act, fcs = _fcurves(obj)
    # Keyed range, not the scene range: a loop keyed 1-17 (17 == 1) is often rendered 1-16
    if frames:
        (f0, f1), src = frames, "given"
    elif act.use_frame_range:
        (f0, f1), src = (int(act.frame_start), int(act.frame_end)), "action range"
    elif _key_range(fcs):
        (f0, f1), src = _key_range(fcs), "first/last key"
    else:
        (f0, f1), src = (scene.frame_start, scene.frame_end), "scene range"
    engine = engine.lower()
    out = [f"Audit '{act.name}' on {arm_name}: frames {f0}-{f1} ({src}) @ {scene.render.fps} fps, {len(fcs)} curves"]
    if (f0, f1) != (scene.frame_start, scene.frame_end):
        out.append(f"NOTE: scene range is {scene.frame_start}-{scene.frame_end}; pass frames=(a, b) if the clip is not {f0}-{f1}")

    # Loop seams: value at start must match end (Unity-style duplicated end frame), and the bend
    # across the seam must be no sharper than the sharpest bend inside the clip
    if loop:
        bad = []
        for fc in fcs:
            vs = [fc.evaluate(f) for f in range(f0, f1 + 1)]
            v0, v1 = vs[0], vs[-1]
            kink = abs((vs[1] - v0) - (v1 - vs[-2])) if len(vs) > 2 else 0
            bend = max((abs(a - 2 * b + c) for a, b, c in zip(vs, vs[1:], vs[2:])), default=0)
            if abs(v0 - v1) > eps or kink > 2 * bend + eps:
                bad.append(f"{fc.data_path}[{fc.array_index}] (start {v0:.3f}/end {v1:.3f})")
        out.append(f"LOOP SEAM: {len(bad)} curves don't match start/end" + (": " + "; ".join(bad[:8]) if bad else ""))

    # Interpolation leftovers
    lin = sum(1 for fc in fcs for k in fc.keyframe_points if k.interpolation in {"LINEAR", "CONSTANT"})
    if lin:
        out.append(f"INTERPOLATION: {lin} linear/constant keys (fine if blocking or mechanical, otherwise ease them)")

    # Quaternion keys in opposite hemispheres make Blender blend the long way (limb snaps through rest)
    quats = {}
    for fc in fcs:
        if fc.data_path.endswith("rotation_quaternion"):
            quats.setdefault(fc.data_path, {})[fc.array_index] = fc
    flips = []
    for path, g in quats.items():
        if len(g) < 4:
            continue
        frames = sorted({k.co[0] for k in g[0].keyframe_points})
        qs = [[g[i].evaluate(f) for i in range(4)] for f in frames]
        if any(sum(a * b for a, b in zip(p, q)) < 0 for p, q in zip(qs, qs[1:])):
            flips.append(_bone(g[0]) or path)
    if flips:
        out.append(f"QUATERNION FLIP (limb swings the long way between keys; negate the later key): {', '.join(flips[:8])}")

    # Scale animation the target may drop
    scaled = sorted({_bone(fc) or fc.data_path for fc in fcs if fc.data_path.endswith("scale")
                     and len({round(k.co[1], 4) for k in fc.keyframe_points}) > 1})
    if scaled:
        tag = "WILL BE DROPPED" if engine in NO_SCALE else ("dropped by Unity Humanoid rigs" if engine == "unity" else "ok")
        out.append(f"SCALE KEYS ({tag}): {', '.join(scaled[:8])}")

    # Overlap / twinning: compare which frames each bone is keyed on
    keyset = {}
    for fc in fcs:
        b = _bone(fc)
        if b:
            keyset.setdefault(b, set()).update(round(k.co[0]) for k in fc.keyframe_points)
    multi = {b: s for b, s in keyset.items() if len(s) > 2}
    baked = multi and min(len(s) for s in multi.values()) >= 0.8 * (f1 - f0 + 1)
    if baked:
        out.append("BAKED: every bone keyed on (almost) every frame; overlap/twinning checks skipped, judge offsets by eye")
    elif len(multi) > 2 and len({frozenset(s) for s in multi.values()}) == 1:
        out.append("NO OVERLAP: every animated bone is keyed on the same frames; offset follow-through parts 1-3 frames")
    twins = [] if baked else [b for b in multi if _mirror(b) in multi and b < _mirror(b) and multi[b] == multi[_mirror(b)]]
    if twins:
        out.append(f"POSSIBLE TWINNING (L/R keyed on identical frames): {', '.join(twins[:8])}")

    # Constraints the engine won't evaluate
    cons = [pb.name for pb in obj.pose.bones if any(c.enabled and c.influence > 0 for c in pb.constraints)]
    if cons:
        out.append(f"CONSTRAINTS on {len(cons)} bones: make sure export bakes animation (Bake Animation / glTF sampling)")

    # Foot contact: planted feet should be still (root motion) or move at constant speed (in-place).
    # Auto-detect the END of each limb chain (toe/paw tip touches the ground, not the ankle that rolls).
    if not feet:
        limb = re.compile(r"foot|toe|ankle|paw|hoof|hand|leg.?ik|tarsus|claw", re.I)
        hits = {pb.name for pb in obj.pose.bones if limb.search(pb.name)}
        feet = [n for n in hits if not any(c.name in hits for c in obj.pose.bones[n].children_recursive)]
    if feet:
        zs = [b.head_local.z for b in obj.data.bones] + [b.tail_local.z for b in obj.data.bones]
        height = max(1e-6, (max(zs) - min(zs)) * max(obj.scale))
        cur = scene.frame_current
        track = {n: [] for n in feet}
        roots = [pb for pb in obj.pose.bones if pb.parent is None]
        root_xy = []
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            root_xy.append([(obj.matrix_world @ pb.head).to_2d() for pb in roots])
            for n in feet:
                pb = obj.pose.bones[n]
                # IK chain end: the IK tip (tail, or head with use_tail off). Otherwise the head (toe/paw joint): imported rigs
                # (glTF, FBX) store no tails, so Blender's guessed tail can point anywhere
                ik = next((c for c in pb.constraints if c.type == "IK"), None)
                pt = pb.tail if ik and ik.use_tail else pb.head
                track[n].append((obj.matrix_world @ pt).copy())
        scene.frame_set(cur)
        ground = min(p.z for ps in track.values() for p in ps)
        # A "foot" that never reaches the ground (a biped's hand) is not checked
        grounded = {n: ps for n, ps in track.items() if min(p.z for p in ps) - ground < 0.1 * height}
        if in_place is None:  # root motion = a root bone travels over the clip
            travel = max(((b - a).length for a, b in zip(root_xy[0], root_xy[-1])), default=0)
            in_place = travel < 0.1 * height
        for n, ps in grounded.items():
            zmin = min(p.z for p in ps)
            low = [p.z - zmin < 0.03 * height for p in ps]
            # contact runs, minus their first/last frame (plant and lift blend through the threshold)
            runs, run = [], []
            for i, c in enumerate(low):
                if c:
                    run.append(i)
                elif run:
                    runs.append(run); run = []
            if run:
                runs.append(run)
            speeds = [(ps[i + 1] - ps[i]).to_2d().length for r in runs for i in r[1:-2]]
            if len(speeds) < 2:
                continue
            if in_place:
                mean = statistics.mean(speeds)
                if mean > 1e-3 * height and statistics.pstdev(speeds) / mean > 0.3:  # still feet are fine
                    out.append(f"FOOT SLIDE ({n}): contact speed uneven ({min(speeds):.3f}-{max(speeds):.3f}/frame); in-place feet should slide at constant speed")
            elif sum(speeds) > 0.02 * height:
                out.append(f"FOOT SLIDE ({n}): planted foot drifts {sum(speeds):.3f} units during contact")
        if in_place and len(grounded) > 1:
            means = {n: statistics.mean([(ps[i + 1] - ps[i]).to_2d().length for i in range(len(ps) - 1)
                                         if ps[i].z - min(p.z for p in ps) < 0.03 * height] or [0]) for n, ps in grounded.items()}
            lo, hi = min(means.values()), max(means.values())
            if hi > 1e-3 * height and lo / hi < 0.7:
                out.append(f"FOOT SPEED MISMATCH: feet slide back at different speeds ({lo:.3f}-{hi:.3f}/frame); in-place feet must match the ground speed")
        skipped = sorted(set(feet) - set(grounded))
        out.append(f"FEET checked: {', '.join(sorted(grounded))} ({'in-place' if in_place else 'root motion'})"
                   + (f"; not touching ground, skipped: {', '.join(skipped)}" if skipped else ""))
    else:
        out.append("FEET: none detected; pass feet=[...] to check sliding")

    if len(out) == 1:
        out.append("No issues found.")
    print("\n".join(out))
    return out
