# Screenshot → Blender: Forensic 3D Scene Reconstruction MVP

Converts a 2D reference screenshot into a structured scene specification (`scene_spec.json`), procedurally generates a 3D scene in Blender, renders it with Cycles, and optionally applies a 1-shot corrective refinement.

---

## 🏗️ Architecture

```
REFERENCE IMAGE
       ↓
VISION ANALYZER (Gemini / OpenAI / Deterministic Forensic CV)
       ↓
STRUCTURED SCENE SPEC (scene_spec.json)
       ↓
BLENDER GENERATOR (Procedural Geometry Library & PBR Materials)
       ↓
HEADLESS BLENDER (Cycles CPU Fast Denoiser)
       ↓
RENDERED 3D SCENE (render.png & scene.blend)
       ↓
LIGHTWEIGHT MISMATCH COMPARISON (Refinement Loop)
       ↓
REFINED 3D SCENE (render_refined.png & scene_refined.blend)
```

---

## 🚀 Quick Start

### 1. Requirements

Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

Blender 4.2+ executable should be available in `PATH` or `~/.local/bin/blender`.

### 2. Running the Pipeline (CLI)

Run the full end-to-end pipeline with automatic rendering and optional refinement:

```bash
# Basic run
python run_pipeline.py examples/reference_room.png

# With 1-shot corrective refinement
python run_pipeline.py examples/reference_room.png --refine

# Force offline deterministic heuristic analyzer (zero external API calls)
python run_pipeline.py examples/reference_room.png --heuristic --refine
```

### 3. Interactive Web UI

Launch the Streamlit interface:
```bash
streamlit run app.py
```
Open `http://localhost:8501` to upload images, view side-by-side renders, download `.blend` project files, and inspect `scene_spec.json`.

---

## 📁 Output Artifacts

Every run generates the following artifacts in the `output/` directory:

| Artifact | Description |
| :--- | :--- |
| `output/scene_spec.json` | Validated structured scene metadata, camera, lights, and objects |
| `output/generated_scene.py` | Self-contained, executable Blender Python script |
| `output/scene.blend` | Complete Blender project file (can be opened in Blender GUI) |
| `output/render.png` | Cycles-rendered 3D image |
| `output/refined_scene_spec.json` | Corrected scene specification (if `--refine` is enabled) |
| `output/render_refined.png` | Corrected render output (if `--refine` is enabled) |

---

## 📐 Structured Scene Specification (`scene_spec.json`)

The intermediate format strictly decouples visual analysis from 3D generation:

```json
{
  "scene": {
    "type": "room",
    "background": {
      "color": "#E0E5EC",
      "has_floor": true,
      "floor_color": "#D5D9E0",
      "floor_roughness": 0.35
    },
    "camera": {
      "type": "perspective",
      "position": [0.0, -4.5, 2.2],
      "target": [0.0, 0.0, 0.5],
      "fov": 45.0,
      "elevation_deg": 22.0
    },
    "lighting": {
      "type": "three_point",
      "key_light": {
        "position": [3.5, -3.0, 4.0],
        "intensity": 750.0,
        "color": "#FFF8ED"
      },
      "fill_light": {
        "position": [-3.5, -2.5, 2.5],
        "intensity": 300.0,
        "color": "#EBF2FF"
      },
      "rim_light": {
        "position": [0.0, 3.5, 3.0],
        "intensity": 250.0,
        "color": "#FFFFFF"
      },
      "ambient_strength": 0.25,
      "ambient_color": "#E0E5EC"
    }
  },
  "objects": [
    {
      "id": "object_01",
      "class": "table",
      "primitive": "table",
      "bbox_2d": [0.25, 0.35, 0.5, 0.45],
      "position": [0.0, 0.0, 0.0],
      "rotation": [0.0, 0.0, 0.0],
      "scale": [1.6, 0.9, 0.75],
      "material": {
        "color": "#966038",
        "roughness": 0.38,
        "metallic": 0.0
      },
      "confidence": 0.95,
      "evidence": "VISUAL",
      "relationship": "on_floor"
    }
  ]
}
```

---

## 🪑 Supported Procedural Primitives

The deterministic procedural generator in `object_library.py` supports:
- **Primitives**: `cube`, `cylinder`, `sphere`, `plane`, `thin_panel`
- **Furniture & Props**:
  - `table` (tabletop slab + 4 corner legs grounded at z=0)
  - `chair` (seat cushion + 4 legs + backrest)
  - `sofa` (cushioned base + backrest + dual armrests)
  - `bed` (frame + mattress + headboard + pillows)
  - `lamp` (ground disc + pole + lampshade cone)
  - `monitor` / `tv` (base stand + neck + screen panel)
  - `cabinet` / `bookshelf` (carcass body + inset dividers)

---

## 🎯 Intentionally Limited Scope (MVP)

1. **Procedural Approximations over Photogrammetry**: Objects use structured parametric primitives rather than heavy scanned mesh reconstruction.
2. **Deterministic Fallback**: Runs offline with zero external API calls if `GEMINI_API_KEY` is not provided.
3. **Single Refinement Iteration**: The corrective loop runs at most once to prevent infinite agentic cycles.
