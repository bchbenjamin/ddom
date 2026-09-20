"""Scene Refinement and Mismatch Analysis Module.

Performs at most ONE corrective iteration comparing reference image vs generated render:
- Identifies luminance / lighting mismatch
- Identifies color distribution mismatch
- Identifies framing and horizontal centroid offset
- Generates a structured correction plan (fixes)
- Applies fixes to SceneSpec deterministically
"""

import os
import json
import numpy as np
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional

from scene_spec import SceneSpec, rgb_to_hex, hex_to_rgb


def analyze_image_mismatch(ref_img_path: str, render_img_path: str) -> Dict[str, Any]:
    """Compare reference and render images using lightweight computer vision analysis."""
    ref = Image.open(ref_img_path).convert("RGB").resize((128, 128), Image.Resampling.BILINEAR)
    ren = Image.open(render_img_path).convert("RGB").resize((128, 128), Image.Resampling.BILINEAR)

    arr_ref = np.array(ref, dtype=np.float32) / 255.0
    arr_ren = np.array(ren, dtype=np.float32) / 255.0

    # 1. Luminance comparison
    lum_ref = np.mean(0.2126 * arr_ref[:, :, 0] + 0.7152 * arr_ref[:, :, 1] + 0.0722 * arr_ref[:, :, 2])
    lum_ren = np.mean(0.2126 * arr_ren[:, :, 0] + 0.7152 * arr_ren[:, :, 1] + 0.0722 * arr_ren[:, :, 2])
    lum_diff = float(lum_ref - lum_ren)

    # 2. Dominant color shift
    mean_color_ref = np.mean(arr_ref, axis=(0, 1))
    mean_color_ren = np.mean(arr_ren, axis=(0, 1))
    color_diff = (mean_color_ref - mean_color_ren).tolist()

    # 3. Horizontal centroid / mass balance (are objects too far left or right?)
    # Calculate difference from image border
    border_ref = np.median(arr_ref[0:15, :, :], axis=(0, 1))
    mask_ref = np.linalg.norm(arr_ref - border_ref, axis=2) > 0.15

    border_ren = np.median(arr_ren[0:15, :, :], axis=(0, 1))
    mask_ren = np.linalg.norm(arr_ren - border_ren, axis=2) > 0.15

    cols_ref = np.where(mask_ref)[1]
    cols_ren = np.where(mask_ren)[1]

    cx_ref = float(np.mean(cols_ref)) / 128.0 if len(cols_ref) > 0 else 0.5
    cx_ren = float(np.mean(cols_ren)) / 128.0 if len(cols_ren) > 0 else 0.5
    horizontal_shift = cx_ref - cx_ren

    # 4. Vertical coverage / size (are objects too small or too large?)
    area_ref = float(np.sum(mask_ref)) / (128.0 * 128.0)
    area_ren = float(np.sum(mask_ren)) / (128.0 * 128.0)
    area_ratio = (area_ref + 1e-4) / (area_ren + 1e-4)

    return {
        "luminance_difference": round(lum_diff, 3),
        "luminance_ref": round(float(lum_ref), 3),
        "luminance_render": round(float(lum_ren), 3),
        "color_shift_rgb": [round(c, 3) for c in color_diff],
        "horizontal_shift": round(float(horizontal_shift), 3),
        "area_ratio": round(float(area_ratio), 3),
    }


def create_refinement_plan(mismatch: Dict[str, Any], spec: SceneSpec) -> Dict[str, Any]:
    """Generate a compact list of targeted parameter corrections based on mismatch metrics."""
    fixes = []

    # 1. Lighting correction
    lum_diff = mismatch.get("luminance_difference", 0.0)
    if abs(lum_diff) > 0.02:
        factor = 1.0 + (lum_diff * 1.5)
        factor = max(0.6, min(1.8, factor))
        fixes.append({
            "target": "lighting",
            "change": "adjust_intensity",
            "factor": round(factor, 2),
            "reason": f"Render is {'darker' if lum_diff > 0 else 'brighter'} than reference ({lum_diff:+.3f})"
        })

    # 2. Horizontal framing correction
    h_shift = mismatch.get("horizontal_shift", 0.0)
    if abs(h_shift) > 0.003:
        cam_dx = round(-h_shift * 2.2, 2)
        fixes.append({
            "target": "camera",
            "change": "shift_target",
            "delta": [cam_dx, 0.0, 0.0],
            "reason": f"Center of mass offset ({h_shift:+.3f})"
        })

    # 3. Framing distance / scale correction
    area_ratio = mismatch.get("area_ratio", 1.0)
    if area_ratio > 1.08:
        fixes.append({
            "target": "camera",
            "change": "zoom",
            "focal_length_delta": 4.0,
            "reason": "Objects occupy less frame than reference"
        })
    elif area_ratio < 0.95:
        fixes.append({
            "target": "camera",
            "change": "zoom",
            "focal_length_delta": -4.0,
            "reason": "Objects occupy slightly more frame than reference"
        })

    # 4. Color tint balance
    color_shift = mismatch.get("color_shift_rgb", [0, 0, 0])
    if any(abs(c) > 0.02 for c in color_shift) and spec.objects:
        primary_obj = spec.objects[0]
        cur_rgb = hex_to_rgb(primary_obj.material.color)
        new_rgb = [
            max(0.0, min(1.0, cur_rgb[0] + color_shift[0] * 0.4)),
            max(0.0, min(1.0, cur_rgb[1] + color_shift[1] * 0.4)),
            max(0.0, min(1.0, cur_rgb[2] + color_shift[2] * 0.4)),
        ]
        fixes.append({
            "target": primary_obj.id,
            "change": "adjust_color",
            "new_color": rgb_to_hex(new_rgb),
            "reason": "Color distribution tint adjustment"
        })

    return {"fixes": fixes, "mismatch_analysis": mismatch}


def apply_refinement_plan(spec: SceneSpec, plan: Dict[str, Any]) -> SceneSpec:
    """Apply the refinement fixes deterministically to create an updated SceneSpec."""
    refined = spec.model_copy(deep=True)
    fixes = plan.get("fixes", [])

    for fix in fixes:
        target = fix.get("target")
        change = fix.get("change")

        if target == "lighting" and change == "adjust_intensity":
            factor = fix.get("factor", 1.0)
            refined.scene.lighting.key_light.intensity *= factor
            if refined.scene.lighting.fill_light:
                refined.scene.lighting.fill_light.intensity *= factor
            if refined.scene.lighting.rim_light:
                refined.scene.lighting.rim_light.intensity *= factor

        elif target == "camera":
            if change == "shift_target":
                delta = fix.get("delta", [0, 0, 0])
                refined.scene.camera.target[0] += delta[0]
                refined.scene.camera.position[0] += delta[0] * 0.7
            elif change == "zoom":
                delta_fl = fix.get("focal_length_delta", 0.0)
                fl = refined.scene.camera.focal_length or 50.0
                refined.scene.camera.focal_length = max(24.0, min(90.0, fl + delta_fl))

        else:
            # Match object ID
            for obj in refined.objects:
                if obj.id == target:
                    if change == "adjust_color":
                        new_color = fix.get("new_color")
                        if new_color:
                            obj.material.color = new_color
                    elif change == "move":
                        delta = fix.get("delta", [0, 0, 0])
                        obj.position = [
                            obj.position[0] + delta[0],
                            obj.position[1] + delta[1],
                            obj.position[2] + delta[2],
                        ]
                    elif change == "scale":
                        factor = fix.get("factor", [1, 1, 1])
                        if isinstance(factor, list) and len(factor) == 3:
                            obj.scale = [
                                obj.scale[0] * factor[0],
                                obj.scale[1] * factor[1],
                                obj.scale[2] * factor[2],
                            ]

    return refined
