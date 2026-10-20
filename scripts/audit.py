# Read-only audit of an armature's active action. Usage (inside Blender):
#   exec(open(".../audit.py").read()); audit("Armature", engine="unity", loop=True)
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


def audit(arm_name, engine="", loop=None, feet=None, in_place=None, eps=1e-3):
    obj = bpy.data.objects[arm_name]
    scene = bpy.context.scene
    if not (obj.animation_data and obj.animation_data.action):
        print(f"{arm_name}: no active action"); return
    act, fcs = _fcurves(obj)
    if act.use_frame_range:
        f0, f1 = int(act.frame_start), int(act.frame_end)
    else:
        f0, f1 = scene.frame_start, scene.frame_end
    engine = engine.lower()
    out = [f"Audit '{act.name}' on {arm_name}: frames {f0}-{f1} @ {scene.render.fps} fps, {len(fcs)} curves"]

    # Loop seams: value and slope at start must match end (Unity-style duplicated end frame)
    if loop:
        bad = []
        for fc in fcs:
            v0, v1 = fc.evaluate(f0), fc.evaluate(f1)
            s0, s1 = fc.evaluate(f0 + 1) - v0, v1 - fc.evaluate(f1 - 1)
            if abs(v0 - v1) > eps or abs(s0 - s1) > max(eps, 0.25 * abs(s0)):
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
    if len(multi) > 2 and len({frozenset(s) for s in multi.values()}) == 1:
        out.append("NO OVERLAP: every animated bone is keyed on the same frames; offset follow-through parts 1-3 frames")
    twins = [b for b in multi if _mirror(b) in multi and b < _mirror(b) and multi[b] == multi[_mirror(b)]]
    if twins:
        out.append(f"POSSIBLE TWINNING (L/R keyed on identical frames): {', '.join(twins[:8])}")

    # Constraints the engine won't evaluate
    cons = [pb.name for pb in obj.pose.bones if any(c.enabled and c.influence > 0 for c in pb.constraints)]
    if cons:
        out.append(f"CONSTRAINTS on {len(cons)} bones: make sure export bakes animation (Bake Animation / glTF sampling)")

    # Foot contact: planted feet should be still (root motion) or move at constant speed (in-place)
    feet = feet or [pb.name for pb in obj.pose.bones if re.search(r"foot|ankle|leg.?ik", pb.name, re.I)]
    if feet:
        zs = [b.head_local.z for b in obj.data.bones] + [b.tail_local.z for b in obj.data.bones]
        height = max(1e-6, (max(zs) - min(zs)) * max(obj.scale))
        cur = scene.frame_current
        track = {n: [] for n in feet}
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            for n in feet:
                pb = obj.pose.bones[n]  # IK chain end: the tail is the foot, the head is the knee
                pt = pb.tail if any(c.type == "IK" for c in pb.constraints) else pb.head
                track[n].append((obj.matrix_world @ pt).copy())
        scene.frame_set(cur)
        if in_place is None:
            in_place = max((ps[-1] - ps[0]).to_2d().length for ps in track.values()) < 0.1 * height
        for n, ps in track.items():
            zmin = min(p.z for p in ps)
            speeds = [((b - a).to_2d()).length for a, b, in zip(ps, ps[1:])
                      if a.z - zmin < 0.03 * height and b.z - zmin < 0.03 * height]
            if len(speeds) < 2:
                continue
            if in_place:
                mean = statistics.mean(speeds)
                if mean > 1e-3 * height and statistics.pstdev(speeds) / mean > 0.3:  # still feet are fine
                    out.append(f"FOOT SLIDE ({n}): contact speed uneven ({min(speeds):.3f}-{max(speeds):.3f}/frame); in-place feet should slide at constant speed")
            elif sum(speeds) > 0.02 * height:
                out.append(f"FOOT SLIDE ({n}): planted foot drifts {sum(speeds):.3f} units during contact")
        out.append(f"FEET checked: {', '.join(feet)} ({'in-place' if in_place else 'root motion'})")
    else:
        out.append("FEET: none detected; pass feet=[...] to check sliding")

    if len(out) == 1:
        out.append("No issues found.")
    print("\n".join(out))
    return out
