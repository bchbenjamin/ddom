"""End-to-End Pipeline: Screenshot -> Forensic Visual Decomposition -> Blender -> Render.

Single command execution:
    python run_pipeline.py reference.png [--refine] [--heuristic] [--samples 16]
"""

import os
import sys
import argparse
import time
from PIL import Image

from scene_spec import SceneSpec
from vision_analyzer import get_vision_analyzer
from blender_generator import generate_scene_script
from renderer import BlenderRenderer
from refiner import analyze_image_mismatch, create_refinement_plan, apply_refinement_plan


def run_pipeline(
    image_path: str,
    output_dir: str = "output",
    force_heuristic: bool = False,
    refine: bool = False,
    samples: int = 16,
    width: int = 1024,
    height: int = 1024,
) -> dict:
    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(image_path):
        print(f"[Error] Reference image not found: {image_path}")
        sys.exit(1)

    print("=" * 60)
    print("SCREENSHOT -> BLENDER 3D RECONSTRUCTION PIPELINE")
    print("=" * 60)
    print(f"Reference Image: {image_path}")
    print(f"Output Directory: {output_dir}")

    # Inspect reference dimensions
    with Image.open(image_path) as img:
        ref_w, ref_h = img.size
        print(f"Image Resolution: {ref_w} x {ref_h}")

    # -------------------------------------------------------------
    # STEP 1: Forensic Visual Decomposition -> Scene Specification
    # -------------------------------------------------------------
    print("\n[Step 1/4] Analyzing scene (forensic visual decomposition)...")
    analyzer = get_vision_analyzer(force_heuristic=force_heuristic)
    scene_spec = analyzer.analyze(image_path)

    spec_path = os.path.join(output_dir, "scene_spec.json")
    scene_spec.save(spec_path)

    print(f"  ✓ Scene Type: {scene_spec.scene.type}")
    print(f"  ✓ Camera Position: {scene_spec.scene.camera.position} (FOV: {scene_spec.scene.camera.fov}°)")
    print(f"  ✓ Identified {len(scene_spec.objects)} object(s):")
    for obj in scene_spec.objects:
        print(f"    - [{obj.id}] {obj.class_name} ({obj.primitive}) at pos={obj.position} scale={obj.scale} color={obj.material.color} [{obj.evidence}, conf={obj.confidence:.2f}]")
    print(f"  ✓ Structured Scene Spec saved: {spec_path}")

    # -------------------------------------------------------------
    # STEP 2: Generate Executable Blender Scene Script
    # -------------------------------------------------------------
    print("\n[Step 2/4] Generating Blender scene script...")
    render_png_path = os.path.join(output_dir, "render.png")
    scene_blend_path = os.path.join(output_dir, "scene.blend")
    script_path = os.path.join(output_dir, "generated_scene.py")

    script_content = generate_scene_script(
        scene_spec_path=spec_path,
        output_render_path=render_png_path,
        output_blend_path=scene_blend_path,
        width=width,
        height=height,
    )
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    print(f"  ✓ Standalone Blender script saved: {script_path}")

    # -------------------------------------------------------------
    # STEP 3: Automatic Headless Blender Render
    # -------------------------------------------------------------
    print("\n[Step 3/4] Building scene and rendering in Blender...")
    renderer = BlenderRenderer()
    if not renderer.is_available():
        print(f"[Notice] Blender executable not found. Script saved to: {script_path}")
        print(f"To render manually: blender --background --python {script_path}")
        return {
            "scene_spec": spec_path,
            "script": script_path,
            "render": None,
            "blend": None,
        }

    success, msg = renderer.render_spec(
        scene_spec_path=spec_path,
        output_render_path=render_png_path,
        output_blend_path=scene_blend_path,
        width=width,
        height=height,
        samples=samples,
    )
    if not success:
        print(f"[Error] Render failed: {msg}")
        sys.exit(1)

    print(f"  ✓ Blender scene created: {scene_blend_path}")
    print(f"  ✓ Render complete: {render_png_path}")

    # -------------------------------------------------------------
    # STEP 4 (Optional): One-Shot Corrective Refinement
    # -------------------------------------------------------------
    refined_spec_path = None
    refined_render_path = None
    if refine:
        print("\n[Step 4/4] Performing optional one-shot refinement...")
        mismatch = analyze_image_mismatch(image_path, render_png_path)
        plan = create_refinement_plan(mismatch, scene_spec)

        fixes = plan.get("fixes", [])
        if fixes:
            print(f"  ✓ Identified {len(fixes)} corrective adjustment(s):")
            for f in fixes:
                print(f"    * Target [{f.get('target')}]: {f.get('change')} -> {f.get('reason')}")

            refined_spec = apply_refinement_plan(scene_spec, plan)
            refined_spec_path = os.path.join(output_dir, "refined_scene_spec.json")
            refined_spec.save(refined_spec_path)

            refined_render_path = os.path.join(output_dir, "render_refined.png")
            refined_blend_path = os.path.join(output_dir, "scene_refined.blend")

            print("  ✓ Re-rendering with applied fixes...")
            renderer.render_spec(
                scene_spec_path=refined_spec_path,
                output_render_path=refined_render_path,
                output_blend_path=refined_blend_path,
                width=width,
                height=height,
                samples=samples,
            )
            print(f"  ✓ Refined render saved: {refined_render_path}")
        else:
            print("  ✓ Visual match already within acceptable tolerance. No corrections needed.")

    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"PIPELINE COMPLETED IN {total_time:.1f} SECONDS")
    print("=" * 60)
    print(f"1. Scene Spec:    {spec_path}")
    print(f"2. Blender Scene: {scene_blend_path}")
    print(f"3. Render PNG:    {render_png_path}")
    if refined_render_path:
        print(f"4. Refined PNG:   {refined_render_path}")
    print("=" * 60)

    return {
        "scene_spec": spec_path,
        "script": script_path,
        "blend": scene_blend_path,
        "render": render_png_path,
        "refined_render": refined_render_path,
    }


def main():
    parser = argparse.ArgumentParser(description="Screenshot -> Blender 3D Reconstruction Pipeline")
    parser.add_argument("image", help="Path to reference screenshot/image")
    parser.add_argument("--output-dir", default="output", help="Directory for output files (default: output)")
    parser.add_argument("--refine", action="store_true", help="Perform at most one corrective refinement iteration")
    parser.add_argument("--heuristic", action="store_true", help="Force local deterministic heuristic vision analyzer (offline)")
    parser.add_argument("--samples", type=int, default=16, help="Blender Cycles render samples (default: 16)")
    parser.add_argument("--width", type=int, default=1024, help="Render width (default: 1024)")
    parser.add_argument("--height", type=int, default=1024, help="Render height (default: 1024)")

    args = parser.parse_args()
    run_pipeline(
        image_path=args.image,
        output_dir=args.output_dir,
        force_heuristic=args.heuristic,
        refine=args.refine,
        samples=args.samples,
        width=args.width,
        height=args.height,
    )


if __name__ == "__main__":
    main()
