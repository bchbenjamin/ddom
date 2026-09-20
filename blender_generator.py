"""Blender Scene Generator.

Builds a complete 3D scene from scene_spec.json using Blender Python API (bpy):
- Clears default scene
- Sets world ambient lighting
- Adds floor/backdrop
- Sets up three-point lighting (Key, Fill, Rim)
- Places camera with accurate target look-at and FOV
- Generates procedural objects with PBR materials
- Configures render engine (Cycles fast CPU or EEVEE)
- Renders to PNG and saves .blend file
"""

import sys
import os
import json
import math
import argparse
from typing import Optional, Dict, Any

# Ensure project root is in sys.path when running inside Blender's python
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    import bpy
    import mathutils
    from object_library import hex_to_rgb, build_object_from_spec, get_or_create_material
except ImportError as e:
    bpy = None
    mathutils = None


def clear_scene():
    """Remove all existing objects, lights, cameras, and materials from scene."""
    if bpy is None:
        return
    # Deselect all, select all, delete
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # Purge unused data blocks
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.lights:
        if block.users == 0:
            bpy.data.lights.remove(block)
    for block in bpy.data.cameras:
        if block.users == 0:
            bpy.data.cameras.remove(block)


def setup_world(background_spec: dict, lighting_spec: dict):
    """Set up world ambient lighting and background color."""
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world

    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes.clear()

    bg_node = nodes.new(type="ShaderNodeBackground")
    out_node = nodes.new(type="ShaderNodeOutputWorld")

    # Ambient color & strength
    amb_color_hex = lighting_spec.get("ambient_color", background_spec.get("color", "#E8E8E8"))
    amb_rgb = hex_to_rgb(amb_color_hex)
    amb_strength = float(lighting_spec.get("ambient_strength", 0.25))

    bg_node.inputs["Color"].default_value = [amb_rgb[0], amb_rgb[1], amb_rgb[2], 1.0]
    bg_node.inputs["Strength"].default_value = max(0.05, amb_strength)

    world.node_tree.links.new(bg_node.outputs["Background"], out_node.inputs["Surface"])


def setup_floor_and_walls(background_spec: dict, mat_cache: dict):
    """Create floor plane and optional room walls."""
    has_floor = background_spec.get("has_floor", True)
    if has_floor:
        floor_color_hex = background_spec.get("floor_color", "#D0D0D0")
        floor_roughness = float(background_spec.get("floor_roughness", 0.4))
        mat = get_or_create_material(
            "Mat_Floor",
            hex_to_rgb(floor_color_hex),
            roughness=floor_roughness,
            metallic=0.0
        )
        bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0.0, 0.0, 0.0))
        floor = bpy.context.active_object
        floor.name = "Floor"
        floor.data.materials.append(mat)

    has_walls = background_spec.get("has_walls", False)
    if has_walls:
        wall_color_hex = background_spec.get("wall_color", "#F0F0F0")
        mat_wall = get_or_create_material(
            "Mat_Wall",
            hex_to_rgb(wall_color_hex),
            roughness=0.6,
            metallic=0.0
        )
        # Back wall
        bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0.0, 8.0, 10.0))
        back_wall = bpy.context.active_object
        back_wall.name = "BackWall"
        back_wall.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        back_wall.data.materials.append(mat_wall)

        # Side wall
        bpy.ops.mesh.primitive_plane_add(size=40.0, location=(-12.0, 0.0, 10.0))
        side_wall = bpy.context.active_object
        side_wall.name = "SideWall"
        side_wall.rotation_euler = (math.radians(90.0), 0.0, math.radians(90.0))
        side_wall.data.materials.append(mat_wall)


def setup_lighting(lighting_spec: dict):
    """Create Key, Fill, and Rim lights."""
    def _create_light(name: str, light_type: str, pos: list, energy: float, color_hex: str, size: float = 1.0):
        light_data = bpy.data.lights.new(name=name, type=light_type)
        light_data.energy = energy
        rgb = hex_to_rgb(color_hex)
        light_data.color = (rgb[0], rgb[1], rgb[2])
        if light_type == "AREA":
            light_data.size = size
        elif light_type == "POINT":
            light_data.shadow_soft_size = size * 0.2

        light_obj = bpy.data.objects.new(name=name, object_data=light_data)
        bpy.context.collection.objects.link(light_obj)
        light_obj.location = (pos[0], pos[1], pos[2])
        return light_obj

    # Key light
    key = lighting_spec.get("key_light", {})
    key_pos = key.get("position", [3.5, -3.5, 4.5])
    key_energy = float(key.get("intensity", 800.0))
    key_color = key.get("color", "#FFF9E6")
    _create_light("Light_Key", "AREA", key_pos, key_energy, key_color, size=2.0)

    # Fill light
    fill = lighting_spec.get("fill_light")
    if fill:
        fill_pos = fill.get("position", [-3.5, -2.5, 3.0])
        fill_energy = float(fill.get("intensity", 350.0))
        fill_color = fill.get("color", "#E8F0FF")
        _create_light("Light_Fill", "AREA", fill_pos, fill_energy, fill_color, size=3.0)

    # Rim / Back light
    rim = lighting_spec.get("rim_light")
    if rim:
        rim_pos = rim.get("position", [0.0, 4.0, 3.5])
        rim_energy = float(rim.get("intensity", 300.0))
        rim_color = rim.get("color", "#FFFFFF")
        _create_light("Light_Rim", "POINT", rim_pos, rim_energy, rim_color, size=1.5)


def setup_camera(camera_spec: dict):
    """Position camera, set FOV/focal length, and look at target."""
    cam_data = bpy.data.cameras.new(name="MainCamera")

    fov = float(camera_spec.get("fov", 45.0))
    focal_length = camera_spec.get("focal_length")
    if focal_length and focal_length > 0:
        cam_data.lens = focal_length
    else:
        cam_data.angle = math.radians(fov)

    cam_obj = bpy.data.objects.new(name="MainCamera", object_data=cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    cam_pos = camera_spec.get("position", [0.0, -4.5, 2.2])
    target_pos = camera_spec.get("target", [0.0, 0.0, 0.5])

    cam_obj.location = (cam_pos[0], cam_pos[1], cam_pos[2])

    # Direct camera to look at target
    loc = mathutils.Vector(cam_pos)
    target_vec = mathutils.Vector(target_pos)
    direction = target_vec - loc
    if direction.length > 0.001:
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam_obj.rotation_euler = rot_quat.to_euler()

    return cam_obj


def configure_render_settings(output_path: str, width: int = 1024, height: int = 1024, samples: int = 32):
    """Configure render resolution, Cycles CPU settings, and output format."""
    scene = bpy.context.scene
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = os.path.abspath(output_path)

    # Use Cycles CPU with fast settings for reliable headless execution
    scene.render.engine = 'CYCLES'
    try:
        scene.cycles.device = 'CPU'
        scene.cycles.samples = samples
        scene.cycles.preview_samples = 16
        scene.cycles.use_denoising = True
    except AttributeError:
        pass


def build_scene(spec_dict: Dict[str, Any], output_render_path: str, output_blend_path: Optional[str] = None,
                width: int = 1024, height: int = 1024, samples: int = 32):
    """Complete scene generation pipeline from spec dictionary."""
    print(">>> Initializing Blender Scene Construction...")
    clear_scene()

    scene_data = spec_dict.get("scene", {})
    bg_data = scene_data.get("background", {})
    lighting_data = scene_data.get("lighting", {})
    camera_data = scene_data.get("camera", {})
    objects_data = spec_dict.get("objects", [])

    mat_cache = {}

    # 1. World ambient
    setup_world(bg_data, lighting_data)

    # 2. Floor & walls
    setup_floor_and_walls(bg_data, mat_cache)

    # 3. Lights
    setup_lighting(lighting_data)

    # 4. Camera
    setup_camera(camera_data)

    # 5. Objects
    print(f">>> Building {len(objects_data)} procedural objects...")
    for idx, obj_spec in enumerate(objects_data):
        try:
            build_object_from_spec(obj_spec, mat_cache)
        except Exception as e:
            print(f"[Warning] Failed to build object {obj_spec.get('id', idx)}: {e}")

    # 6. Render setup
    configure_render_settings(output_render_path, width=width, height=height, samples=samples)

    # 7. Save .blend file if requested
    if output_blend_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_blend_path)), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(output_blend_path))
        print(f">>> Scene saved to .blend: {output_blend_path}")

    # 8. Render
    print(f">>> Rendering scene to: {output_render_path}")
    os.makedirs(os.path.dirname(os.path.abspath(output_render_path)), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print(">>> Render complete!")


def generate_scene_script(scene_spec_path: str, output_render_path: str, output_blend_path: str,
                          width: int = 1024, height: int = 1024) -> str:
    """Generate standalone python code that can be executed directly by Blender."""
    script_content = f'''# Autogenerated Blender scene builder
import sys
import os
import json

# Add project root to sys.path
repo_dir = r"{current_dir}"
if repo_dir not in sys.path:
    sys.path.insert(0, repo_dir)

from blender_generator import build_scene

spec_file = r"{os.path.abspath(scene_spec_path)}"
output_render = r"{os.path.abspath(output_render_path)}"
output_blend = r"{os.path.abspath(output_blend_path)}"

with open(spec_file, "r", encoding="utf-8") as f:
    spec_data = json.load(f)

build_scene(
    spec_data,
    output_render_path=output_render,
    output_blend_path=output_blend,
    width={width},
    height={height},
    samples=32
)
'''
    return script_content


if __name__ == "__main__" and bpy is not None:
    # Running inside Blender CLI
    # Arguments after '--' are user arguments
    argv = sys.argv
    if "--" in argv:
        user_args = argv[argv.index("--") + 1:]
    else:
        user_args = []

    parser = argparse.ArgumentParser(description="Blender Scene Generator")
    parser.add_argument("--spec", required=True, help="Path to scene_spec.json")
    parser.add_argument("--output", default="output/render.png", help="Path to output render PNG")
    parser.add_argument("--blend", default="output/scene.blend", help="Path to output .blend file")
    parser.add_argument("--width", type=int, default=1024, help="Render width")
    parser.add_argument("--height", type=int, default=1024, help="Render height")
    parser.add_argument("--samples", type=int, default=32, help="Render samples")

    args = parser.parse_args(user_args)

    with open(args.spec, "r", encoding="utf-8") as f:
        spec_data = json.load(f)

    build_scene(
        spec_data,
        output_render_path=args.output,
        output_blend_path=args.blend,
        width=args.width,
        height=args.height,
        samples=args.samples
    )
