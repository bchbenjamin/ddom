"""Screenshot → Blender: Forensic 3D Scene Reconstruction.

Design strictly adheres to Context/DESIGN.md:
- Pure Void Canvas: #000000 background, zero elevation, no panels/borders/cards
- Typography: Inter with weight 400 display headlines (-0.04em tracking), weight 200 body
- Color Palette: Bone White (#ffffff), Ash Gray (#9a9a9a), Silver Mist (#bdbdbd),
                 Electric Iris (#8052ff), Saffron Spark (#ffb829), Deep Verdant (#15846e)
- Hero Constellation Visualization: Animated organic brain-shape particle cloud of
  chromatic outlined triangles on pure black void canvas
- Primary Action CTA: Pill button #8052ff, 24px radius, uppercase tracking, subtle pulse
- Micro-animations: Forensic scanning sweep, glowing indicators, smooth floating elements
"""

import os
import json
import time
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

from run_pipeline import run_pipeline
from scene_spec import SceneSpec

st.set_page_config(
    page_title="DALA 3D — Screenshot → Blender",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------
# DESIGN SYSTEM STYLING & ANIMATIONS (Context/DESIGN.md)
# -------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;400;600;700&display=swap');

:root {
  --color-void: #000000;
  --color-bone-white: #ffffff;
  --color-ash-gray: #9a9a9a;
  --color-silver-mist: #bdbdbd;
  --color-electric-iris: #8052ff;
  --color-saffron-spark: #ffb829;
  --color-deep-verdant: #15846e;
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* Base Void Canvas */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #000000 !important;
    color: #ffffff !important;
    font-family: var(--font-sans) !important;
}

/* Sidebar Void Canvas */
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
    background-color: #000000 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
}

/* Remove default card containers, borders, elevation - elements float on void */
[data-testid="stVerticalBlock"] > div, .stCard, [data-testid="stExpander"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Monolithic Weight 400 Display Headings with Negative Tracking */
h1, .dala-display {
    font-family: var(--font-sans) !important;
    font-weight: 400 !important;
    font-size: 72px !important;
    line-height: 1.05 !important;
    letter-spacing: -3.12px !important;
    color: #ffffff !important;
    margin-bottom: 16px !important;
    animation: fadeInUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

h2, .dala-heading {
    font-family: var(--font-sans) !important;
    font-weight: 400 !important;
    font-size: 42px !important;
    line-height: 1.15 !important;
    letter-spacing: -1.68px !important;
    color: #ffffff !important;
}

h3, .dala-subheading {
    font-family: var(--font-sans) !important;
    font-weight: 400 !important;
    font-size: 27px !important;
    line-height: 1.2 !important;
    letter-spacing: -0.48px !important;
    color: #ffffff !important;
}

/* Ultra-light Weight 200 Body Text (18px) */
p, .dala-body, [data-testid="stMarkdownContainer"] p {
    font-family: var(--font-sans) !important;
    font-weight: 200 !important;
    font-size: 18px !important;
    line-height: 1.6 !important;
    color: #bdbdbd !important;
}

/* Saffron Spark Accent Label */
.dala-tag {
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.4px !important;
    color: #ffb829 !important;
    display: inline-block;
    margin-bottom: 8px !important;
}

/* Secondary label in Ash Gray */
.dala-label {
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.35px !important;
    color: #9a9a9a !important;
}

/* Primary Action Button: Electric Iris Pill */
.stButton > button, div.stButton > button:first-child {
    background-color: #8052ff !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 24px !important;
    padding: 14px 32px !important;
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.025em !important;
    box-shadow: 0 0 25px rgba(128, 82, 255, 0.35) !important;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    cursor: pointer !important;
}

.stButton > button:hover {
    background-color: #8052ff !important;
    box-shadow: 0 0 35px rgba(128, 82, 255, 0.65) !important;
    transform: translateY(-2px) scale(1.02) !important;
}

/* Download buttons: Ghost Pill Buttons */
.stDownloadButton > button {
    background-color: transparent !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 24px !important;
    padding: 10px 24px !important;
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.025em !important;
    transition: all 0.2s ease !important;
}

.stDownloadButton > button:hover {
    border-color: #8052ff !important;
    color: #8052ff !important;
    background-color: rgba(128, 82, 255, 0.08) !important;
    box-shadow: 0 0 15px rgba(128, 82, 255, 0.25) !important;
}

/* File Uploader styling on black void */
[data-testid="stFileUploader"] {
    background-color: #050505 !important;
    border: 1px dashed rgba(255, 255, 255, 0.15) !important;
    border-radius: 24px !important;
    padding: 20px !important;
    transition: border-color 0.2s ease !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: #8052ff !important;
}

/* Inputs, Selectboxes, Sliders */
[data-baseweb="select"] > div, .stTextInput > div > div {
    background-color: #0a0a0a !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 14px !important;
    color: #ffffff !important;
}

/* Status widget */
[data-testid="stStatusWidget"] {
    background-color: #080808 !important;
    border: 1px solid rgba(128, 82, 255, 0.25) !important;
    border-radius: 18px !important;
    box-shadow: 0 0 30px rgba(128, 82, 255, 0.1) !important;
}

/* Keyframe Animations */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes pulseGlow {
    0%, 100% {
        box-shadow: 0 0 15px rgba(128, 82, 255, 0.3);
    }
    50% {
        box-shadow: 0 0 30px rgba(128, 82, 255, 0.7);
    }
}

@keyframes scanSweep {
    0% {
        top: 0%;
        opacity: 0.8;
    }
    50% {
        top: 96%;
        opacity: 1;
    }
    100% {
        top: 0%;
        opacity: 0.8;
    }
}

.scan-container {
    position: relative;
    overflow: hidden;
    border-radius: 18px;
}

.scan-beam {
    position: absolute;
    left: 0;
    width: 100%;
    height: 3px;
    background: linear-gradient(90deg, transparent, #8052ff, #ffb829, transparent);
    box-shadow: 0 0 15px #8052ff;
    animation: scanSweep 3s ease-in-out infinite;
    pointer-events: none;
    z-index: 10;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# TOP NAVIGATION BAR (Context/DESIGN.md)
# -------------------------------------------------------------
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0 28px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.07); margin-bottom: 36px;">
    <div style="display: flex; align-items: center; gap: 14px;">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polygon points="12,2 22,20 2,20" fill="#8052ff" />
            <polygon points="12,8 18,18 6,18" fill="#15846e" />
        </svg>
        <span style="font-size: 20px; font-weight: 600; color: #ffffff; letter-spacing: 0.5px;">DALA</span>
    </div>
    <div style="display: flex; gap: 32px; align-items: center;">
        <span class="dala-label" style="letter-spacing: 0.025em;">SCREENSHOT → BLENDER</span>
        <span class="dala-tag" style="margin-bottom: 0;">MVP v1.0</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SIDEBAR CONTROLS
# -------------------------------------------------------------
st.sidebar.markdown('<span class="dala-tag">CONFIGURATION</span>', unsafe_allow_html=True)
sample_rate = st.sidebar.slider("Blender Cycles Samples", min_value=8, max_value=32, value=16, step=4)
enable_refine = st.sidebar.checkbox("Enable 1-Shot Refinement Loop", value=True)
force_heuristic = st.sidebar.checkbox("Force Offline Forensic Analyzer", value=False)

st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
st.sidebar.markdown('<span class="dala-label">PIPELINE STAGES</span>', unsafe_allow_html=True)
st.sidebar.markdown("""
<div style="margin-top: 12px; display: flex; flex-direction: column; gap: 14px;">
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #8052ff; display: inline-block;"></span>
        <span style="font-size: 14px; font-weight: 200; color: #ffffff;">Visual Decomposition</span>
    </div>
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #ffb829; display: inline-block;"></span>
        <span style="font-size: 14px; font-weight: 200; color: #ffffff;">Structured Spec (`scene_spec.json`)</span>
    </div>
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #15846e; display: inline-block;"></span>
        <span style="font-size: 14px; font-weight: 200; color: #ffffff;">Procedural 3D Mesh Generation</span>
    </div>
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #8052ff; display: inline-block;"></span>
        <span style="font-size: 14px; font-weight: 200; color: #ffffff;">Headless Blender Cycles Render</span>
    </div>
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #ffb829; display: inline-block;"></span>
        <span style="font-size: 14px; font-weight: 200; color: #ffffff;">1-Shot Corrective Refinement</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# HERO SECTION & ANIMATED CONSTELLATION (Context/DESIGN.md)
# -------------------------------------------------------------
hero_left, hero_right = st.columns([1.1, 0.9], gap="large")

with hero_left:
    st.markdown('<span class="dala-tag">FORENSIC VISUAL DECOMPOSITION</span>', unsafe_allow_html=True)
    st.markdown('<h1 class="dala-display">From pixels<br>to physical 3D.</h1>', unsafe_allow_html=True)
    st.markdown("""
    <p class="dala-body" style="max-width: 520px;">
    Provide a reference screenshot. The system extracts a validated 3D scene specification, builds procedural geometry deterministically in Blender, and renders it automatically.
    </p>
    """, unsafe_allow_html=True)

with hero_right:
    # Interactive Animated Particle Constellation Canvas from DESIGN.md
    components.html("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body, html {
                margin: 0;
                padding: 0;
                overflow: hidden;
                background-color: #000000;
            }
            canvas {
                display: block;
                width: 100%;
                height: 320px;
                background-color: #000000;
            }
        </style>
    </head>
    <body>
        <canvas id="constellationCanvas"></canvas>
        <script>
            const canvas = document.getElementById('constellationCanvas');
            const ctx = canvas.getContext('2d');

            function resize() {
                canvas.width = window.innerWidth * window.devicePixelRatio;
                canvas.height = 320 * window.devicePixelRatio;
                ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
            }
            resize();
            window.addEventListener('resize', resize);

            const colors = ['#8052ff', '#ffb829', '#15846e', '#38bdf8', '#f43f5e', '#a855f7'];
            const particles = [];
            const count = 110;

            const width = window.innerWidth;
            const height = 320;
            const cx = width * 0.48;
            const cy = height * 0.5;

            // Generate organic brain-cloud constellation
            for (let i = 0; i < count; i++) {
                const angle = Math.random() * Math.PI * 2;
                const side = Math.random() > 0.5 ? 1 : -1;
                const hx = cx + side * (35 + Math.random() * 85);
                const hy = cy + (Math.random() - 0.5) * 110;

                particles.push({
                    x: hx + (Math.random() - 0.5) * 40,
                    y: hy + (Math.random() - 0.5) * 40,
                    baseX: hx,
                    baseY: hy,
                    vx: (Math.random() - 0.5) * 0.45,
                    vy: (Math.random() - 0.5) * 0.45,
                    size: 3.5 + Math.random() * 4.5,
                    color: colors[Math.floor(Math.random() * colors.length)],
                    rot: Math.random() * Math.PI * 2,
                    rotSpeed: (Math.random() - 0.5) * 0.025,
                    phase: Math.random() * Math.PI * 2
                });
            }

            let t = 0;
            function animate() {
                t += 0.015;
                ctx.clearRect(0, 0, width, height);

                // Draw connector lines for nearby points
                for (let i = 0; i < particles.length; i++) {
                    for (let j = i + 1; j < particles.length; j++) {
                        const dx = particles[i].x - particles[j].x;
                        const dy = particles[i].y - particles[j].y;
                        const dist = Math.sqrt(dx * dx + dy * dy);
                        if (dist < 55) {
                            ctx.strokeStyle = `rgba(128, 82, 255, ${0.28 * (1 - dist / 55)})`;
                            ctx.lineWidth = 0.75;
                            ctx.beginPath();
                            ctx.moveTo(particles[i].x, particles[i].y);
                            ctx.lineTo(particles[j].x, particles[j].y);
                            ctx.stroke();
                        }
                    }
                }

                // Draw chromatic outlined triangular glyphs
                for (let p of particles) {
                    p.x += p.vx + Math.sin(t + p.phase) * 0.25;
                    p.y += p.vy + Math.cos(t + p.phase) * 0.25;
                    p.rot += p.rotSpeed;

                    ctx.save();
                    ctx.translate(p.x, p.y);
                    ctx.rotate(p.rot);

                    ctx.strokeStyle = p.color;
                    ctx.lineWidth = 1.2;
                    ctx.beginPath();
                    const r = p.size;
                    ctx.moveTo(0, -r);
                    ctx.lineTo(r * 0.866, r * 0.5);
                    ctx.lineTo(-r * 0.866, r * 0.5);
                    ctx.closePath();
                    ctx.stroke();

                    ctx.restore();
                }

                requestAnimationFrame(animate);
            }
            animate();
        </script>
    </body>
    </html>
    """, height=320)

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# REFERENCE IMAGE SELECTION & SCANNING
# -------------------------------------------------------------
sample_images = []
if os.path.exists("examples"):
    for f in os.listdir("examples"):
        if f.endswith((".png", ".jpg", ".jpeg")):
            sample_images.append(os.path.join("examples", f))

input_col1, input_col2 = st.columns([1, 1], gap="large")
target_image_path = None

with input_col1:
    st.markdown('<span class="dala-tag">STEP 1</span>', unsafe_allow_html=True)
    st.markdown('<h3 class="dala-subheading">Select Reference Image</h3>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload reference screenshot", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed")

    selected_sample = None
    if sample_images:
        use_sample = st.checkbox("Or select benchmark sample room", value=uploaded_file is None)
        if use_sample:
            selected_sample = st.selectbox("Benchmark rooms:", sample_images, label_visibility="collapsed")

    if uploaded_file is not None:
        os.makedirs("output/uploads", exist_ok=True)
        target_image_path = os.path.join("output/uploads", uploaded_file.name)
        with open(target_image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    elif selected_sample:
        target_image_path = selected_sample

with input_col2:
    if target_image_path and os.path.exists(target_image_path):
        st.markdown('<span class="dala-label">ACTIVE REFERENCE PREVIEW</span>', unsafe_allow_html=True)
        st.markdown("""
        <div class="scan-container">
            <div class="scan-beam"></div>
        </div>
        """, unsafe_allow_html=True)
        st.image(target_image_path, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# GENERATE CTA BUTTON
# -------------------------------------------------------------
btn_col, _ = st.columns([1, 2])
with btn_col:
    generate_clicked = st.button("Generate Blender Scene", type="primary")

if generate_clicked and target_image_path:
    status_widget = st.status("Reconstructing 3D scene...", expanded=True)
    try:
        status_widget.write("✦ Performing forensic visual decomposition...")
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        res = run_pipeline(
            image_path=target_image_path,
            output_dir=output_dir,
            force_heuristic=force_heuristic,
            refine=enable_refine,
            samples=sample_rate,
        )

        status_widget.write("✦ Procedural grounded 3D geometry assembled in Blender.")
        status_widget.write("✦ Headless Cycles render completed.")
        if res.get("refined_render"):
            status_widget.write("✦ Corrective 1-shot refinement pass applied.")
        status_widget.update(label="Scene Reconstruction Complete", state="complete", expanded=False)

        # -------------------------------------------------------------
        # VISUAL COMPARISON (Context/DESIGN.md)
        # -------------------------------------------------------------
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<span class="dala-tag">OUTPUT VERIFICATION</span>', unsafe_allow_html=True)
        st.markdown('<h2 class="dala-heading">Reference vs. Generated Render</h2>', unsafe_allow_html=True)
        st.markdown("""
        <p class="dala-body" style="margin-bottom: 32px;">
        Comparing visible viewpoint, spatial alignment, material properties, and lighting balance on black void.
        </p>
        """, unsafe_allow_html=True)

        num_cols = 3 if res.get("refined_render") else 2
        comp_cols = st.columns(num_cols, gap="large")

        with comp_cols[0]:
            st.markdown('<span class="dala-label">1. REFERENCE IMAGE</span>', unsafe_allow_html=True)
            st.image(target_image_path, use_container_width=True)

        with comp_cols[1]:
            st.markdown('<span class="dala-label">2. BLENDER CYCLES RENDER</span>', unsafe_allow_html=True)
            if res.get("render") and os.path.exists(res["render"]):
                st.image(res["render"], use_container_width=True)

        if res.get("refined_render") and os.path.exists(res["refined_render"]):
            with comp_cols[2]:
                st.markdown('<span class="dala-label" style="color: #ffb829;">3. REFINED RENDER (1-SHOT)</span>', unsafe_allow_html=True)
                st.image(res["refined_render"], use_container_width=True)

        # -------------------------------------------------------------
        # ARTIFACTS & DOWNLOADS
        # -------------------------------------------------------------
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<span class="dala-tag">DELIVERABLES</span>', unsafe_allow_html=True)
        st.markdown('<h3 class="dala-subheading">Download Scene & Source Files</h3>', unsafe_allow_html=True)

        d1, d2, d3 = st.columns(3, gap="medium")

        with d1:
            if res.get("blend") and os.path.exists(res["blend"]):
                with open(res["blend"], "rb") as f:
                    st.download_button(
                        label="Download .blend File",
                        data=f,
                        file_name="scene.blend",
                        mime="application/x-blender",
                    )
        with d2:
            if res.get("render") and os.path.exists(res["render"]):
                with open(res["render"], "rb") as f:
                    st.download_button(
                        label="Download Render PNG",
                        data=f,
                        file_name="render.png",
                        mime="image/png",
                    )
        with d3:
            if res.get("script") and os.path.exists(res["script"]):
                with open(res["script"], "rb") as f:
                    st.download_button(
                        label="Download Python Script",
                        data=f,
                        file_name="generated_scene.py",
                        mime="text/plain",
                    )

        # -------------------------------------------------------------
        # STRUCTURED SPECIFICATION INSPECTOR
        # -------------------------------------------------------------
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="dala-label">INTERMEDIATE SPECIFICATION (`scene_spec.json`)</span>', unsafe_allow_html=True)
        if res.get("scene_spec") and os.path.exists(res["scene_spec"]):
            with open(res["scene_spec"], "r") as f:
                spec_content = json.load(f)
            st.json(spec_content)

    except Exception as e:
        status_widget.update(label="Reconstruction Failed", state="error")
        st.error(f"Execution error: {e}")
