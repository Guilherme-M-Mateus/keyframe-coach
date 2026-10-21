# Self-check for audit.py on synthetic rigs. Run: blender -b --factory-startup --python tests/test_audit.py
import bpy, math, os, sys

exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "keyframe-coach", "scripts", "audit.py")).read())
N = 20  # cycle length; keyed 1..N+1 (N+1 = 1), scene renders 1..N


def rig(foot_pose, body_x=lambda f: 0.0):
    """body: vertical 1-unit bone (gives the rig its height). foot: 0.2-unit bone lying on the floor along +Y.
    foot_pose(f) -> (location, heel_lift_angle); the angle pivots the foot about its toe (tail)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, N
    arm = bpy.data.objects.new("Rig", bpy.data.armatures.new("Rig"))
    scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for name, head, tail in (("body", (0, 0, 0), (0, 0, 1)), ("foot", (0, 0, 0), (0, 0.2, 0))):
        b = arm.data.edit_bones.new(name)
        b.head, b.tail = head, tail
    bpy.ops.object.mode_set(mode="POSE")
    foot, body = arm.pose.bones["foot"], arm.pose.bones["body"]
    foot.rotation_mode = "XYZ"
    for f in range(1, N + 2):
        (x, y, z), a = foot_pose(f)
        # rotate by -a about X, then shift so the toe stays at (x, y + 0.2, z)
        foot.rotation_euler = (-a, 0, 0)
        foot.location = (x, y + 0.2 - 0.2 * math.cos(a), z + 0.2 * math.sin(a))
        body.location = (body_x(f), 0, 0)
        for pb in (foot, body):
            pb.keyframe_insert("location", frame=f)
        foot.keyframe_insert("rotation_euler", frame=f)
    return arm


def skin(arm, z):
    """one-vertex paw mesh skinned to the foot, at height z (the rig has no bone there)"""
    me = bpy.data.meshes.new("Paw")
    me.from_pydata([(0, 0.1, z)], [], [])
    m = bpy.data.objects.new("Paw", me)
    bpy.context.scene.collection.objects.link(m)
    m.vertex_groups.new(name="foot").add([0], 1.0, "REPLACE")
    m.modifiers.new("Armature", "ARMATURE").object = arm
    return arm


def run(arm, **kw):
    return "\n".join(audit(arm.name, feet=["foot"], **kw))


def gait(contact_y, swing_lift=0.3):
    """first 60% of the cycle on the floor at contact_y(u), then an arc back to the start."""
    def pose(f):
        u = ((f - 1) % N) / N
        if u < 0.6:
            return (0, contact_y(u), 0), 0.0
        s = (u - 0.6) / 0.4
        return (0, contact_y(0.6) + (contact_y(0) - contact_y(0.6)) * s, swing_lift * math.sin(math.pi * s)), 0.0
    return pose


# In place: constant backward slide during contact is correct
assert "FOOT SLIDE" not in run(rig(gait(lambda u: -u)), loop=True, in_place=True)
# In place: a foot that stops mid-contact slides unevenly
assert "FOOT SLIDE" in run(rig(gait(lambda u: -min(u, 0.3))), loop=True, in_place=True)
# Root motion: a planted foot that holds still is fine
assert "FOOT SLIDE" not in run(rig(lambda f: ((0, 0, 0), 0.0)), in_place=False)
# Root motion: a foot that stays on the floor but slides is caught
assert "FOOT SLIDE" in run(rig(lambda f: ((0, 0.02 * f, 0), 0.0)), in_place=False)
# Root motion: heel-off roll (toe planted, ankle rising) is not a slide
assert "FOOT SLIDE" not in run(rig(lambda f: ((0, 0, 0), math.radians(3 * f))), in_place=False)
# A swing that dips under the floor (rest height) is caught
assert "FOOT BELOW FLOOR" in run(rig(gait(lambda u: -u, swing_lift=-0.1)), loop=True, in_place=True)
assert "FOOT BELOW FLOOR" not in run(rig(gait(lambda u: -u)), loop=True, in_place=True)
# ...also when only the skinned paw (not the bone) goes under
assert "FOOT BELOW FLOOR (foot): lowest point (skinned mesh) 0.100" in run(skin(rig(gait(lambda u: -u)), -0.1), loop=True, in_place=True)
assert "FOOT BELOW FLOOR" not in run(skin(rig(gait(lambda u: -u)), 0.0), loop=True, in_place=True)
# Loop keyed 1..N+1 with N+1 = 1: no seam even though the scene ends at N
assert "LOOP SEAM" not in run(rig(gait(lambda u: -u), lambda f: math.sin(2 * math.pi * (f - 1) / N)), loop=True)
# Sampled loop whose sharpest frame sits on the seam (a bounce, like a paw landing on frame 1) is not a seam pop
assert "LOOP SEAM" not in run(rig(gait(lambda u: -u), lambda f: abs(math.sin(math.pi * (f - 1) / N))), loop=True)


def hand_keyed(keys, cycles=False):
    """rig whose body x is hand-keyed (Bezier, auto-clamped handles) at {frame: value}"""
    arm = rig(gait(lambda u: -u))
    fc = next(fc for fc in _fcurves(arm)[1] if fc.data_path.startswith('pose.bones["body"].location') and fc.array_index == 0)
    fc.keyframe_points.clear()
    for f, v in keys.items():
        fc.keyframe_points.insert(f, v)
    if cycles:
        fc.modifiers.new("CYCLES")
    fc.update()
    return arm


# Hand-keyed loop passing through the seam mid-motion: flat end handles stop it there (hitch), Cycles fixes it
assert "LOOP SEAM" in run(hand_keyed({1: 0, 6: 1, 11: 0, 16: -1, 21: 0}), loop=True)
assert "LOOP SEAM" not in run(hand_keyed({1: 0, 6: 1, 11: 0, 16: -1, 21: 0}, cycles=True), loop=True)
# Hand-keyed loop whose seam is a turning point: flat handles are right there
assert "LOOP SEAM" not in run(hand_keyed({1: 1, 11: -1, 21: 1}), loop=True)
# Baked clip: overlap/twinning skipped (key timing means nothing there)
assert "OVERLAP/TWINNING not checked" in run(rig(gait(lambda u: -u)), loop=True)
# Scripted clip keyed every 2 frames: also skipped
arm = rig(gait(lambda u: -u))
for fc in _fcurves(arm)[1]:
    for k in [k for k in fc.keyframe_points if int(k.co[0]) % 2 == 0][::-1]:
        fc.keyframe_points.remove(k)
assert "OVERLAP/TWINNING not checked" in run(arm, loop=True)
# Hand-blocked keys (every 5 frames) are still checked
arm = rig(gait(lambda u: -u))
for fc in _fcurves(arm)[1]:
    for k in [k for k in fc.keyframe_points if (int(k.co[0]) - 1) % 5][::-1]:
        fc.keyframe_points.remove(k)
assert "OVERLAP/TWINNING not checked" not in run(arm, loop=True)


def legged(n):
    """n-legged rig: a spine plus two-bone legs reaching the floor; returns (rig, foot names)"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm = bpy.data.objects.new("Rig", bpy.data.armatures.new("Rig"))
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    spine = arm.data.edit_bones.new("spine")
    spine.head, spine.tail = (0, -0.5, 0.6), (0, 0.5, 0.6)
    for i in range(n):
        x, y = (-0.2, 0.2)[i % 2], -0.4 + 0.8 * (i // 2) / max(1, n // 2 - 1)
        up = arm.data.edit_bones.new(f"upper{i}")
        up.head, up.tail, up.parent = (x, y, 0.6), (x * 2, y, 0.3), spine
        lo = arm.data.edit_bones.new(f"lower{i}")
        lo.head, lo.tail, lo.parent = (x * 2, y, 0.3), (x * 2, y, 0.0), up
    tail = arm.data.edit_bones.new("tail")  # hangs to the floor in rest pose, lifted in the clip
    tail.head, tail.tail, tail.parent = (0, -0.5, 0.6), (0, -0.6, 0.0), spine
    bpy.ops.object.mode_set(mode="POSE")
    arm.pose.bones["tail"].rotation_mode = "XYZ"
    arm.pose.bones["tail"].rotation_euler = (0, 0, 0)
    arm.pose.bones["tail"].rotation_euler.x = math.radians(-80)
    for f in (1, 11):
        arm.pose.bones["spine"].keyframe_insert("location", frame=f)
        arm.pose.bones["tail"].keyframe_insert("rotation_euler", frame=f)
    return arm, sorted(f"lower{i}" for i in range(n))


# Feet come from the caller; a passed bone that never reaches the floor (a lifted tail) is called out and skipped
arm, lows = legged(4)
out = "\n".join(audit(arm.name, feet=lows + ["tail"]))
assert "FOOT NOT ON FLOOR (tail): lowest point (bone ends) stays" in out and f"FEET checked: {', '.join(lows)} " in out
assert "FEET: not checked" in "\n".join(audit(arm.name))
print("test_audit: all checks passed")
sys.exit(0)
