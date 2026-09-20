"""Screenshot → Blender: Forensic 3D Scene Reconstruction.

Design strictly adheres to Context/DESIGN.md:
- Pure Void Canvas: #000000 background, zero elevation, no cards/borders/shadows
- Typography: Inter with weight 400 display headlines (-0.04em tracking), weight 200 body
- Color Palette: Bone White (#ffffff), Ash Gray (#9a9a9a), Silver Mist (#bdbdbd),
                 Electric Iris (#8052ff), Saffron Spark (#ffb829), Deep Verdant (#15846e)
- Primary CTA: Pill button #8052ff, 24px radius, uppercase tracking
"""

import os
import json
import time
from PIL import Image
import streamlit as st

from run_pipeline import run_pipeline
from scene_spec import SceneSpec

st.set_page_config(
    page_title="Screenshot → Blender",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject exact design tokens and typography from Context/DESIGN.md
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
  --font-sans: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
}

/* Void Canvas */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #000000 !important;
    color: #ffffff !important;
    font-family: var(--font-sans) !important;
}

/* Sidebar void canvas */
[data-testid="stSidebar"] {
    background-color: #000000 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

/* Remove default card containers, borders, elevation */
[data-testid="stVerticalBlock"] > div, .stCard, [data-testid="stExpander"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Headlines: Weight 400, Negative tracking */
h1, .dala-display {
    font-family: var(--font-sans) !important;
    font-weight: 400 !important;
    font-size: 64px !important;
    line-height: 1.1 !important;
    letter-spacing: -2.5px !important;
    color: #ffffff !important;
    margin-bottom: 12px !important;
}

h2, .dala-heading {
    font-family: var(--font-sans) !important;
    font-weight: 400 !important;
    font-size: 42px !important;
    line-height: 1.2 !important;
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

/* Body: Weight 200 Ultra-light, 18px */
p, .dala-body, [data-testid="stMarkdownContainer"] p {
    font-family: var(--font-sans) !important;
    font-weight: 200 !important;
    font-size: 18px !important;
    line-height: 1.5 !important;
    color: #bdbdbd !important;
}

/* Saffron Spark Accent Label */
.dala-tag {
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    color: #ffb829 !important;
    margin-bottom: 8px !important;
    display: inline-block;
}

/* Secondary label in Ash Gray */
.dala-label {
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 14px !important;
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
    padding: 12px 28px !important;
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.025em !important;
    box-shadow: none !important;
    transition: transform 0.15s ease, opacity 0.15s ease !important;
}

.stButton > button:hover {
    background-color: #8052ff !important;
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}

/* Download buttons styling: Pill buttons */
.stDownloadButton > button {
    background-color: transparent !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 24px !important;
    padding: 10px 22px !important;
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.025em !important;
}

.stDownloadButton > button:hover {
    border-color: #8052ff !important;
    color: #8052ff !important;
}

/* Form controls, inputs, select boxes on black void */
[data-baseweb="select"] > div, .stTextInput > div > div {
    background-color: #0d0d0d !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 12px !important;
    color: #ffffff !important;
}

[data-testid="stFileUploader"] {
    background-color: #050505 !important;
    border: 1px dashed rgba(255, 255, 255, 0.15) !important;
    border-radius: 18px !important;
    padding: 16px !important;
}

/* Status Box */
[data-testid="stStatusWidget"] {
    background-color: #080808 !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
}
</style>
""", unsafe_allow_html=True)

# Navigation Bar Lockup
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0 36px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
    <div style="display: flex; align-items: center; gap: 12px;">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polygon points="12,2 22,20 2,20" fill="#8052ff" />
            <polygon points="12,7 18,18 6,18" fill="#15846e" />
        </svg>
        <span style="font-size: 18px; font-weight: 600; color: #ffffff; letter-spacing: 0.5px;">DALA 3D</span>
    </div>
    <div style="display: flex; gap: 24px; align-items: center;">
        <span class="dala-label">SCREENSHOT → BLENDER</span>
        <span style="font-size: 12px; color: #8052ff; font-weight: 600; text-transform: uppercase;">MVP v1.0</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.markdown('<span class="dala-tag">PIPELINE SETTINGS</span>', unsafe_allow_html=True)
sample_rate = st.sidebar.slider("Blender Cycles Samples", min_value=8, max_value=32, value=16, step=4)
enable_refine = st.sidebar.checkbox("Enable 1-Shot Refinement", value=True)
force_heuristic = st.sidebar.checkbox("Force Heuristic Analyzer (Zero-Cost Offline)", value=False)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.markdown('<span class="dala-label">ABOUT ARCHITECTURE</span>', unsafe_allow_html=True)
st.sidebar.markdown("""
<p style="font-size: 14px; font-weight: 200; color: #9a9a9a; line-height: 1.6;">
Deconstructs 2D images into structured <code>scene_spec.json</code>, builds procedural geometry deterministically in Blender, and renders in Cycles.
</p>
""", unsafe_allow_html=True)

# Hero Section: Two-Column Layout following DESIGN.md
hero_left, hero_right = st.columns([1.1, 0.9], gap="large")

with hero_left:
    st.markdown('<span class="dala-tag">FORENSIC 3D RECONSTRUCTION</span>', unsafe_allow_html=True)
    st.markdown('<h1 class="dala-display">From pixels<br>to physical 3D.</h1>', unsafe_allow_html=True)
    st.markdown("""
    <p class="dala-body" style="max-width: 520px;">
    Provide a reference screenshot. The engine performs forensic visual decomposition, extracts a structured scene specification, and automatically generates grounded procedural geometry in Blender.
    </p>
    """, unsafe_allow_html=True)

# File Selection and Upload
sample_images = []
if os.path.exists("examples"):
    for f in os.listdir("examples"):
        if f.endswith((".png", ".jpg", ".jpeg")):
            sample_images.append(os.path.join("examples", f))

target_image_path = None

with hero_right:
    st.markdown('<span class="dala-label">REFERENCE INPUT</span>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload reference screenshot", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed")

    selected_sample = None
    if sample_images:
        use_sample = st.checkbox("Use benchmark sample scene", value=uploaded_file is None)
        if use_sample:
            selected_sample = st.selectbox("Benchmark scenes:", sample_images, label_visibility="collapsed")

    if uploaded_file is not None:
        os.makedirs("output/uploads", exist_ok=True)
        target_image_path = os.path.join("output/uploads", uploaded_file.name)
        with open(target_image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    elif selected_sample:
        target_image_path = selected_sample

    if target_image_path and os.path.exists(target_image_path):
        st.image(target_image_path, caption="Active Reference Image", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# Action CTA
col_btn, _ = st.columns([1, 2])
with col_btn:
    generate_clicked = st.button("Generate Blender Scene", type="primary")

if generate_clicked and target_image_path:
    status_widget = st.status("Reconstructing 3D scene from reference...", expanded=True)
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

        status_widget.write("✦ Procedural geometry created in Blender 4.2.")
        status_widget.write("✦ Automatic Cycles render complete.")
        if res.get("refined_render"):
            status_widget.write("✦ Corrective 1-shot refinement pass applied.")
        status_widget.update(label="Scene Reconstruction Complete", state="complete", expanded=False)

        # Visual Comparison Section (DESIGN.md spacious layout)
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<span class="dala-tag">VISUAL COMPARISON</span>', unsafe_allow_html=True)
        st.markdown('<h2 class="dala-heading">Reference vs. Generated Render</h2>', unsafe_allow_html=True)
        st.markdown("""
        <p class="dala-body" style="margin-bottom: 24px;">
        Comparing visible viewpoint, spatial alignment, material properties, and lighting balance.
        </p>
        """, unsafe_allow_html=True)

        num_cols = 3 if res.get("refined_render") else 2
        comp_cols = st.columns(num_cols, gap="medium")

        with comp_cols[0]:
            st.markdown('<span class="dala-label">REFERENCE IMAGE</span>', unsafe_allow_html=True)
            st.image(target_image_path, use_container_width=True)

        with comp_cols[1]:
            st.markdown('<span class="dala-label">BLENDER CYCLES RENDER</span>', unsafe_allow_html=True)
            if res.get("render") and os.path.exists(res["render"]):
                st.image(res["render"], use_container_width=True)

        if res.get("refined_render") and os.path.exists(res["refined_render"]):
            with comp_cols[2]:
                st.markdown('<span class="dala-label" style="color: #ffb829;">REFINED RENDER (1-SHOT FIX)</span>', unsafe_allow_html=True)
                st.image(res["refined_render"], use_container_width=True)

        # Artifacts and Inspection Section
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<span class="dala-tag">PROJECT ARTIFACTS</span>', unsafe_allow_html=True)
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

        # Structured Specification Display
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="dala-label">INTERMEDIATE SPECIFICATION (`scene_spec.json`)</span>', unsafe_allow_html=True)
        if res.get("scene_spec") and os.path.exists(res["scene_spec"]):
            with open(res["scene_spec"], "r") as f:
                spec_content = json.load(f)
            st.json(spec_content)

    except Exception as e:
        status_widget.update(label="Reconstruction Failed", state="error")
        st.error(f"Execution error: {e}")
