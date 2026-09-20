"""Blender Renderer Automation Module.

Orchestrates headless execution of Blender to build scenes and generate renders.
"""

import os
import sys
import shutil
import subprocess
import time
from typing import Optional, Dict, Any, Tuple


def find_blender_binary() -> Optional[str]:
    """Locate the Blender executable in PATH or common installation directories."""
    # 1. Direct path in PATH
    which_blender = shutil.which("blender")
    if which_blender:
        return which_blender

    # 2. Check known local paths
    candidates = [
        os.path.expanduser("~/.local/bin/blender"),
        os.path.expanduser("~/.local/opt/blender-4.2.0-linux-x64/blender"),
        "/usr/local/bin/blender",
        "/usr/bin/blender",
        "/opt/blender/blender",
        "/var/lib/snapd/snap/bin/blender",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c

    return None


class BlenderRenderer:
    def __init__(self, blender_path: Optional[str] = None):
        self.blender_path = blender_path or find_blender_binary()
        if not self.blender_path:
            print("[Warning] Blender executable not found in PATH or standard locations.")

    def is_available(self) -> bool:
        return self.blender_path is not None and os.path.exists(self.blender_path)

    def render_spec(
        self,
        scene_spec_path: str,
        output_render_path: str,
        output_blend_path: str,
        width: int = 1024,
        height: int = 1024,
        samples: int = 32,
        timeout_sec: int = 180,
    ) -> Tuple[bool, str]:
        """Execute Blender in headless background mode to build and render the scene.

        Returns (success: bool, message: str)
        """
        if not self.is_available():
            return False, f"Blender executable not found. Unable to render automatically."

        scene_spec_abs = os.path.abspath(scene_spec_path)
        output_render_abs = os.path.abspath(output_render_path)
        output_blend_abs = os.path.abspath(output_blend_path)

        os.makedirs(os.path.dirname(output_render_abs), exist_ok=True)
        os.makedirs(os.path.dirname(output_blend_abs), exist_ok=True)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        blender_gen_script = os.path.join(current_dir, "blender_generator.py")

        cmd = [
            self.blender_path,
            "--background",
            "--python",
            blender_gen_script,
            "--",
            "--spec", scene_spec_abs,
            "--output", output_render_abs,
            "--blend", output_blend_abs,
            "--width", str(width),
            "--height", str(height),
            "--samples", str(samples),
        ]

        print(f">>> Executing Blender headless render: {' '.join(cmd)}")
        t0 = time.time()
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec,
                cwd=current_dir
            )
            elapsed = time.time() - t0

            if result.returncode != 0:
                print(f"[Error] Blender returned code {result.returncode}")
                print(result.stderr[-1000:] if result.stderr else result.stdout[-1000:])
                return False, f"Blender execution failed with code {result.returncode}: {result.stderr[-300:]}"

            # Verify output files
            if not os.path.exists(output_render_abs) or os.path.getsize(output_render_abs) == 0:
                return False, "Render output PNG was not created or is empty."

            print(f">>> Render successfully finished in {elapsed:.1f}s: {output_render_abs}")
            return True, f"Render successful ({elapsed:.1f}s)"

        except subprocess.TimeoutExpired:
            return False, f"Blender rendering timed out after {timeout_sec}s."
        except Exception as e:
            return False, f"Unexpected error running Blender: {e}"
