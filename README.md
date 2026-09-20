# Screenshot → Blender: Forensic 3D Scene Reconstruction MVP

Converts a 2D reference screenshot into a structured scene specification (`scene_spec.json`), procedurally generates a grounded 3D scene in Blender, renders it with Cycles, and optionally applies a 1-shot corrective refinement.

---

## 🏗️ System Architecture

```text
REFERENCE IMAGE
       ↓
VISION ANALYZER (Gemini / OpenAI / Offline Forensic Heuristic)
       ↓
STRUCTURED SCENE SPEC (output/scene_spec.json)
       ↓
BLENDER GENERATOR (output/generated_scene.py)
       ↓
HEADLESS BLENDER (Cycles Fast CPU/GPU Denoiser)
       ↓
RENDERED 3D SCENE (output/render.png & output/scene.blend)
       ↓
LIGHTWEIGHT MISMATCH COMPARISON (Refinement Loop)
       ↓
REFINED 3D SCENE (output/render_refined.png & output/scene_refined.blend)
```

---

## 🚀 Getting Started

### 1. Prerequisites

* **Python**: Version `3.10` or newer
* **Blender**: Version `4.0` or newer (Blender 4.2 LTS recommended)
* **Git**: Installed and configured

#### Installing Blender Headless

* **Linux (Fedora / RHEL / Ubuntu / Debian)**:
  ```bash
  # Download official portable Blender 4.2 LTS
  mkdir -p ~/.local/opt && cd ~/.local/opt
  curl -fSL https://download.blender.org/release/Blender4.2/blender-4.2.0-linux-x64.tar.xz -o blender.tar.xz
  tar -xf blender.tar.xz
  ln -sf ~/.local/opt/blender-4.2.0-linux-x64/blender ~/.local/bin/blender
  rm blender.tar.xz

  # Verify installation
  blender --version
  ```

* **macOS**:
  ```bash
  brew install --cask blender
  # Ensure /Applications/Blender.app/Contents/MacOS/Blender is in your PATH
  sudo ln -sf /Applications/Blender.app/Contents/MacOS/Blender /usr/local/bin/blender
  ```

* **Windows**:
  Download and install from [blender.org](https://www.blender.org/download/), then add `C:\Program Files\Blender Foundation\Blender 4.2` to your system `PATH`.

---

### 2. Repository Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/bchbenjamin/ddom.git
   cd ddom
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

### 3. API Key Configuration (Optional)

The system is designed with a **three-tier vision analyzer hierarchy**:

1. **Google Gemini** (Recommended for multimodal reasoning):
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"
   ```
2. **OpenAI GPT-4o**:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```
3. **Deterministic Offline Heuristic Analyzer** *(Zero-cost fallback)*:
   If no API key is set, the system automatically uses the local computer-vision forensic analyzer. It uses Pillow + NumPy color clustering, bounding box segmentation, and 3D geometric projection. **No API keys or internet connection required.**

---

### 4. Running the Interactive Web UI

Launch the Streamlit web interface designed according to the `Dala` design system (pure black `#000000` void canvas, interactive 60fps HTML5 constellation particle simulation, Electric Iris CTA buttons, and real-time scanning feedback):

```bash
streamlit run app.py
```

* Open your browser at the deployed AWS endpoint or `http://127.0.0.1:8501` for local testing.
* Upload any screenshot or pick an included benchmark scene.
* Configure render sample rates and 1-shot refinement toggle.
* Click **Generate Blender Scene**.
* Inspect the side-by-side comparison and download `.blend` project files or renders directly.

---

### 5. Running via Command Line (CLI)

Run the full end-to-end pipeline with a single terminal command:

```bash
# Basic run with automatic scene building and rendering
python run_pipeline.py examples/reference_room.png

# Run with 1-shot corrective refinement enabled
python run_pipeline.py examples/reference_room.png --refine

# Force offline deterministic heuristic mode (zero external API calls)
python run_pipeline.py examples/reference_room.png --heuristic --refine

# Custom resolution and sample settings
python run_pipeline.py examples/reference_room.png --samples 24 --width 1024 --height 1024 --refine
```

---

## 📁 Output Deliverables

All generated files are written to the [`output/`](file:///mnt/WindowsDrive/Fedora/Projects/wemakedevs/output) directory:

| Artifact | File Path | Description |
| :--- | :--- | :--- |
| **Scene Spec** | `output/scene_spec.json` | Validated intermediate JSON scene specification |
| **Blender Script** | `output/generated_scene.py` | Self-contained, executable Blender Python code |
| **Blender Scene** | `output/scene.blend` | Native Blender project file (can be opened in Blender GUI) |
| **Cycles Render** | `output/render.png` | High-fidelity Cycles-rendered PNG output |
| **Refined Spec** | `output/refined_scene_spec.json` | Parameter-corrected scene specification *(if `--refine` enabled)* |
| **Refined Blend** | `output/scene_refined.blend` | Updated Blender project file *(if `--refine` enabled)* |
| **Refined Render** | `output/render_refined.png` | Corrected render output *(if `--refine` enabled)* |

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

## 🪑 Supported Procedural Library

The deterministic procedural library in [`object_library.py`](file:///mnt/WindowsDrive/Fedora/Projects/wemakedevs/object_library.py) constructs properly grounded, clean 3D geometry:

* **Geometric Primitives**: `cube`, `cylinder`, `sphere`, `plane`, `thin_panel`
* **Procedural Furniture & Props**:
  * `table` (tabletop slab + 4 corner legs grounded at `z=0`)
  * `chair` (seat cushion + 4 legs + backrest)
  * `sofa` (cushioned base + backrest + dual armrests)
  * `bed` (frame + mattress + headboard + pillows)
  * `lamp` (ground disc + pole + lampshade cone + point light)
  * `monitor` / `tv` (base stand + neck + screen panel)
  * `cabinet` / `bookshelf` (carcass body + inset dividers)

---

## 🛠️ Project Structure

```text
ddom/
├── app.py                  # Streamlit Web UI (Dala dark design system & animations)
├── blender_generator.py    # Blender Python scene assembly and Cycles configuration
├── object_library.py       # Procedural 3D geometry library and PBR material engine
├── refiner.py              # Visual mismatch analyzer and 1-shot corrective planner
├── renderer.py             # Headless Blender process execution & validation
├── run_pipeline.py         # End-to-end CLI orchestrator
├── scene_spec.py           # Pydantic schema validation and JSON serialization
├── vision_analyzer.py      # Forensic visual decomposition (Gemini, OpenAI, Heuristic)
├── examples/               # Benchmark reference images and scenes
│   ├── reference_room.png
│   ├── reference_room.blend
│   └── reference_room_spec.json
├── output/                 # Generated deliverables (.blend, .png, .json)
├── requirements.txt        # Python package dependencies
├── LICENSE                 # MIT License
└── README.md               # Documentation & Quick Start
```

---

## 🎯 Intentionally Limited Scope (MVP)

1. **Procedural Geometry over Photogrammetry**: Focuses on structured parametric primitives matching the reference viewpoint rather than high-density scanned mesh reconstruction.
2. **Deterministic Camera Alignment**: Prioritizes visible framing and perspective matching over recovering occluded surfaces.
3. **Bounded Refinement Loop**: Capped at at most one corrective iteration to guarantee determinism and avoid infinite agentic cycles.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
