"""Procedural 3D Object Library for Blender (bpy).

Provides deterministic procedural generators for primitives and common furniture/props:
- cube / box
- cylinder
- sphere
- plane
- thin panel
- simple table
- simple chair
- simple sofa
- simple bed
- simple lamp
- simple monitor / TV
- simple cabinet / bookshelf
"""

import math
from typing import List, Tuple, Optional

try:
    import bpy
    import mathutils
except ImportError:
    bpy = None
    mathutils = None


def hex_to_rgb(hex_str: str) -> List[float]:
    """Convert hex color string (#RRGGBB) to linear RGB [r, g, b] in range [0, 1]."""
    if not isinstance(hex_str, str):
        return [0.8, 0.8, 0.8]
    hex_clean = hex_str.lstrip('#')
    if len(hex_clean) == 3:
        hex_clean = ''.join([c * 2 for c in hex_clean])
    if len(hex_clean) != 6:
        return [0.8, 0.8, 0.8]
    try:
        r = int(hex_clean[0:2], 16) / 255.0
        g = int(hex_clean[2:4], 16) / 255.0
        b = int(hex_clean[4:6], 16) / 255.0
        return [pow(r, 2.2), pow(g, 2.2), pow(b, 2.2)]
    except ValueError:
        return [0.8, 0.8, 0.8]


def get_or_create_material(
    name: str,
    color_linear: List[float],
    roughness: float = 0.5,
    metallic: float = 0.0,
    transmission: float = 0.0,
    emission_color: Optional[List[float]] = None,
    emission_strength: float = 0.0,
):
    """Create or reuse a Principled BSDF material in Blender."""
    if bpy is None:
        return None

    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True

    nodes = mat.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if not principled:
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")

    # Base Color: RGBA
    rgba = [color_linear[0], color_linear[1], color_linear[2], 1.0]
    principled.inputs["Base Color"].default_value = rgba

    if "Roughness" in principled.inputs:
        principled.inputs["Roughness"].default_value = roughness
    if "Metallic" in principled.inputs:
        principled.inputs["Metallic"].default_value = metallic
    if "Transmission Weight" in principled.inputs:
        principled.inputs["Transmission Weight"].default_value = transmission
    elif "Transmission" in principled.inputs:
        principled.inputs["Transmission"].default_value = transmission

    if emission_strength > 0 and emission_color:
        if "Emission Color" in principled.inputs:
            principled.inputs["Emission Color"].default_value = [
                emission_color[0], emission_color[1], emission_color[2], 1.0
            ]
        elif "Emission" in principled.inputs:
            principled.inputs["Emission"].default_value = [
                emission_color[0], emission_color[1], emission_color[2], 1.0
            ]
        if "Emission Strength" in principled.inputs:
            principled.inputs["Emission Strength"].default_value = emission_strength

    return mat


def _join_parts(parts: List[bpy.types.Object], final_name: str, mat: Optional[bpy.types.Material]) -> bpy.types.Object:
    """Join multiple mesh objects into one single object and assign material."""
    if not parts:
        return None
    valid_parts = [p for p in parts if p is not None and p.name in bpy.data.objects]
    if not valid_parts:
        return None

    bpy.ops.object.select_all(action="DESELECT")
    for p in valid_parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = valid_parts[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    if len(valid_parts) > 1:
        bpy.ops.object.join()

    obj = bpy.context.view_layer.objects.active
    obj.name = final_name

    if mat:
        if not obj.data.materials:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

    return obj


def _apply_transforms(
    obj: bpy.types.Object,
    pos: List[float],
    rot_deg: List[float],
    scale: List[float]
):
    """Apply final position, Euler rotation (degrees converted to radians), and scale."""
    if obj is None:
        return
    obj.location = (pos[0], pos[1], pos[2])
    obj.rotation_euler = (
        math.radians(rot_deg[0]),
        math.radians(rot_deg[1]),
        math.radians(rot_deg[2]),
    )
    obj.scale = (scale[0], scale[1], scale[2])


# --- Procedural Geometry Generators ---

def create_cube(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Create a rectangular cuboid."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    _apply_transforms(obj, pos, rot, scale)
    return obj


def create_cylinder(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Create a cylinder."""
    bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    _apply_transforms(obj, pos, rot, scale)
    return obj


def create_sphere(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Create a UV sphere."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    if mat:
        obj.data.materials.append(mat)
    _apply_transforms(obj, pos, rot, scale)
    return obj


def create_plane(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Create a flat plane (rug, poster, floor pad)."""
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    _apply_transforms(obj, pos, rot, scale)
    return obj


def create_thin_panel(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Create a thin vertical or horizontal panel."""
    s = [scale[0], max(0.02, scale[1] * 0.1), scale[2]]
    return create_cube(name, pos, rot, s, mat)


def create_table(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Procedural Table: tabletop slab + 4 corner legs."""
    sx, sy, sz = scale[0], scale[1], scale[2]
    top_thickness = sz * 0.08
    leg_height = sz - top_thickness
    leg_thickness = min(sx, sy) * 0.08

    parts = []

    # Tabletop
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, 0, sz - (top_thickness / 2.0))
    )
    top = bpy.context.active_object
    top.scale = (sx, sy, top_thickness)
    parts.append(top)

    # 4 Legs
    inset_x = (sx / 2.0) - (leg_thickness / 2.0) * 1.2
    inset_y = (sy / 2.0) - (leg_thickness / 2.0) * 1.2
    leg_z = leg_height / 2.0

    for dx in (-inset_x, inset_x):
        for dy in (-inset_y, inset_y):
            bpy.ops.mesh.primitive_cube_add(
                size=1.0,
                location=(dx, dy, leg_z)
            )
            leg = bpy.context.active_object
            leg.scale = (leg_thickness, leg_thickness, leg_height)
            parts.append(leg)

    obj = _join_parts(parts, name, mat)
    _apply_transforms(obj, pos, rot, [1.0, 1.0, 1.0])
    return obj


def create_chair(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Procedural Chair: seat cushion, 4 legs, backrest."""
    sx, sy, sz = scale[0], scale[1], scale[2]
    seat_height = sz * 0.45
    seat_thick = sz * 0.08
    leg_height = seat_height - seat_thick
    leg_thick = min(sx, sy) * 0.08
    back_height = sz - seat_height
    back_thick = sy * 0.12

    parts = []

    # Seat
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, 0, seat_height - (seat_thick / 2.0))
    )
    seat = bpy.context.active_object
    seat.scale = (sx, sy, seat_thick)
    parts.append(seat)

    # 4 Legs
    inset_x = (sx / 2.0) - (leg_thick / 2.0) * 1.2
    inset_y = (sy / 2.0) - (leg_thick / 2.0) * 1.2
    leg_z = leg_height / 2.0

    for dx in (-inset_x, inset_x):
        for dy in (-inset_y, inset_y):
            bpy.ops.mesh.primitive_cube_add(
                size=1.0,
                location=(dx, dy, leg_z)
            )
            leg = bpy.context.active_object
            leg.scale = (leg_thick, leg_thick, leg_height)
            parts.append(leg)

    # Backrest
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, -(sy / 2.0) + (back_thick / 2.0), seat_height + (back_height / 2.0))
    )
    back = bpy.context.active_object
    back.scale = (sx * 0.95, back_thick, back_height)
    parts.append(back)

    obj = _join_parts(parts, name, mat)
    _apply_transforms(obj, pos, rot, [1.0, 1.0, 1.0])
    return obj


def create_sofa(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Procedural Sofa / Couch: base cushion, back cushion, left & right armrests."""
    sx, sy, sz = scale[0], scale[1], scale[2]
    base_h = sz * 0.4
    arm_w = sx * 0.12
    arm_h = sz * 0.65
    back_thick = sy * 0.25

    parts = []

    # Base cushion / seat
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, (back_thick / 2.0) * 0.3, base_h / 2.0)
    )
    base = bpy.context.active_object
    base.scale = (sx - (arm_w * 2.0), sy - back_thick * 0.5, base_h)
    parts.append(base)

    # Backrest
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, -(sy / 2.0) + (back_thick / 2.0), sz / 2.0)
    )
    back = bpy.context.active_object
    back.scale = (sx, back_thick, sz)
    parts.append(back)

    # Left armrest
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(-(sx / 2.0) + (arm_w / 2.0), 0, arm_h / 2.0)
    )
    left_arm = bpy.context.active_object
    left_arm.scale = (arm_w, sy, arm_h)
    parts.append(left_arm)

    # Right armrest
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=((sx / 2.0) - (arm_w / 2.0), 0, arm_h / 2.0)
    )
    right_arm = bpy.context.active_object
    right_arm.scale = (arm_w, sy, arm_h)
    parts.append(right_arm)

    obj = _join_parts(parts, name, mat)
    _apply_transforms(obj, pos, rot, [1.0, 1.0, 1.0])
    return obj


def create_bed(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Procedural Bed: frame + mattress + headboard + pillows."""
    sx, sy, sz = scale[0], scale[1], scale[2]
    frame_h = sz * 0.3
    mattress_h = sz * 0.35
    headboard_h = sz * 0.95
    headboard_thick = sy * 0.08

    parts = []

    # Bedframe base
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, 0, frame_h / 2.0)
    )
    frame = bpy.context.active_object
    frame.scale = (sx, sy, frame_h)
    parts.append(frame)

    # Mattress
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, 0, frame_h + (mattress_h / 2.0))
    )
    mattress = bpy.context.active_object
    mattress.scale = (sx * 0.94, sy * 0.94, mattress_h)
    parts.append(mattress)

    # Headboard
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, -(sy / 2.0) + (headboard_thick / 2.0), headboard_h / 2.0)
    )
    headboard = bpy.context.active_object
    headboard.scale = (sx, headboard_thick, headboard_h)
    parts.append(headboard)

    # Pillows
    pillow_w = sx * 0.38
    pillow_l = sy * 0.22
    pillow_h = sz * 0.15
    pillow_z = frame_h + mattress_h + (pillow_h / 2.0)
    pillow_y = -(sy / 2.0) + headboard_thick + (pillow_l / 2.0) * 1.1

    for px in (-sx * 0.22, sx * 0.22):
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(px, pillow_y, pillow_z)
        )
        p = bpy.context.active_object
        p.scale = (pillow_w, pillow_l, pillow_h)
        parts.append(p)

    obj = _join_parts(parts, name, mat)
    _apply_transforms(obj, pos, rot, [1.0, 1.0, 1.0])
    return obj


def create_lamp(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Procedural Lamp: base disc + pole + lampshade cone."""
    sx, sy, sz = scale[0], scale[1], scale[2]
    rad = min(sx, sy) / 2.0
    base_h = sz * 0.05
    pole_h = sz * 0.65
    shade_h = sz * 0.35

    parts = []

    # Base
    bpy.ops.mesh.primitive_cylinder_add(
        radius=rad,
        depth=base_h,
        location=(0, 0, base_h / 2.0)
    )
    parts.append(bpy.context.active_object)

    # Pole
    bpy.ops.mesh.primitive_cylinder_add(
        radius=rad * 0.12,
        depth=pole_h,
        location=(0, 0, base_h + (pole_h / 2.0))
    )
    parts.append(bpy.context.active_object)

    # Lampshade (truncated cone / cylinder)
    bpy.ops.mesh.primitive_cone_add(
        radius1=rad * 0.95,
        radius2=rad * 0.6,
        depth=shade_h,
        location=(0, 0, base_h + pole_h + (shade_h / 2.0))
    )
    parts.append(bpy.context.active_object)

    obj = _join_parts(parts, name, mat)
    _apply_transforms(obj, pos, rot, [1.0, 1.0, 1.0])
    return obj


def create_monitor(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Procedural Monitor / TV: flat base + neck + screen panel."""
    sx, sy, sz = scale[0], scale[1], scale[2]
    base_w = sx * 0.4
    base_d = sy * 0.5
    base_h = sz * 0.04
    stand_h = sz * 0.3
    screen_h = sz * 0.65
    screen_thick = sy * 0.1

    parts = []

    # Base stand
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, 0, base_h / 2.0)
    )
    b = bpy.context.active_object
    b.scale = (base_w, base_d, base_h)
    parts.append(b)

    # Stand neck
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, 0, base_h + (stand_h / 2.0))
    )
    neck = bpy.context.active_object
    neck.scale = (base_w * 0.2, screen_thick * 0.8, stand_h)
    parts.append(neck)

    # Screen panel
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, 0, base_h + stand_h * 0.5 + (screen_h / 2.0))
    )
    screen = bpy.context.active_object
    screen.scale = (sx, screen_thick, screen_h)
    parts.append(screen)

    obj = _join_parts(parts, name, mat)
    _apply_transforms(obj, pos, rot, [1.0, 1.0, 1.0])
    return obj


def create_cabinet(name: str, pos: List[float], rot: List[float], scale: List[float], mat=None):
    """Procedural Cabinet / Bookshelf / Credenza."""
    sx, sy, sz = scale[0], scale[1], scale[2]
    parts = []

    # Main carcass
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, 0, sz / 2.0)
    )
    body = bpy.context.active_object
    body.scale = (sx, sy, sz)
    parts.append(body)

    # Inset / door lines (procedural detail)
    door_line_w = sx * 0.015
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(0, (sy / 2.0) * 1.01, sz / 2.0)
    )
    line = bpy.context.active_object
    line.scale = (door_line_w, sy * 0.05, sz * 0.85)
    parts.append(line)

    obj = _join_parts(parts, name, mat)
    _apply_transforms(obj, pos, rot, [1.0, 1.0, 1.0])
    return obj


# Generator dispatch dictionary
OBJECT_GENERATORS = {
    "cube": create_cube,
    "box": create_cube,
    "cylinder": create_cylinder,
    "sphere": create_sphere,
    "ball": create_sphere,
    "plane": create_plane,
    "thin_panel": create_thin_panel,
    "panel": create_thin_panel,
    "table": create_table,
    "desk": create_table,
    "coffee_table": create_table,
    "chair": create_chair,
    "stool": create_chair,
    "sofa": create_sofa,
    "couch": create_sofa,
    "bed": create_bed,
    "lamp": create_lamp,
    "floor_lamp": create_lamp,
    "desk_lamp": create_lamp,
    "monitor": create_monitor,
    "tv": create_monitor,
    "screen": create_monitor,
    "cabinet": create_cabinet,
    "shelf": create_cabinet,
    "bookshelf": create_cabinet,
    "credenza": create_cabinet,
    "nightstand": create_cabinet,
}


def build_object_from_spec(obj_spec_data: dict, mat_cache: dict) -> Optional[bpy.types.Object]:
    """Instantiate a 3D object in Blender from an ObjectSpec dictionary."""
    if bpy is None:
        raise RuntimeError("Blender 'bpy' is not available in current environment")

    obj_id = obj_spec_data.get("id", "object_00")
    prim = obj_spec_data.get("primitive", "cube").lower().strip()
    class_name = (obj_spec_data.get("class") or obj_spec_data.get("class_name", "cube")).lower().strip()

    # Find generator by primitive or class_name
    gen_func = OBJECT_GENERATORS.get(prim)
    if gen_func is None:
        gen_func = OBJECT_GENERATORS.get(class_name, create_cube)

    # Material
    mat_data = obj_spec_data.get("material", {})
    color_hex = mat_data.get("color", "#A0A0A0")
    color_linear = hex_to_rgb(color_hex)
    roughness = float(mat_data.get("roughness", 0.5))
    metallic = float(mat_data.get("metallic", 0.0))
    transmission = float(mat_data.get("transmission", 0.0))
    em_color = hex_to_rgb(mat_data.get("emission_color", "#000000"))
    em_strength = float(mat_data.get("emission_strength", 0.0))

    mat_key = f"{color_hex}_{roughness:.2f}_{metallic:.2f}_{transmission:.2f}"
    if mat_key not in mat_cache:
        mat_cache[mat_key] = get_or_create_material(
            f"Mat_{obj_id}_{mat_key}",
            color_linear,
            roughness,
            metallic,
            transmission,
            em_color,
            em_strength,
        )
    mat = mat_cache[mat_key]

    pos = obj_spec_data.get("position", [0.0, 0.0, 0.0])
    rot = obj_spec_data.get("rotation", [0.0, 0.0, 0.0])
    scale = obj_spec_data.get("scale", [1.0, 1.0, 1.0])

    return gen_func(obj_id, pos, rot, scale, mat)
