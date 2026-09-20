"""D-DOM: Design Document Object Model - Interactive MVP Application.

Inputs:
- Public Website URL (or Screenshot Image)
- Optional Clone / Generated URL for Fidelity Verification

Outputs:
- Structured Evidence-Tagged D-DOM JSON (`ddom.json`)
- Agent Context Document (`DESIGN.md`)
- Fidelity Comparison Report & Mismatches (Source vs Clone)
"""

import os
import json
import streamlit as st
import streamlit.components.v1 as components

from ddom_analyzer import analyze_url, analyze_image
from ddom_generator import generate_design_md
from ddom_comparator import compare_ddom

st.set_page_config(
    page_title="D-DOM — Design Document Object Model",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------
# STYLING (Void Dark Theme)
# -------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;400;600;700&display=swap');

:root {
  --color-void: #000000;
  --color-electric-iris: #8052ff;
  --color-saffron-spark: #ffb829;
  --color-deep-verdant: #15846e;
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #000000 !important;
    color: #ffffff !important;
    font-family: var(--font-sans) !important;
}

[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
    background-color: #000000 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
}

[data-testid="stVerticalBlock"] > div, .stCard, [data-testid="stExpander"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

h1, .dala-display {
    font-family: var(--font-sans) !important;
    font-weight: 400 !important;
    font-size: 64px !important;
    line-height: 1.05 !important;
    letter-spacing: -2.5px !important;
    color: #ffffff !important;
    margin-bottom: 16px !important;
}

h2, .dala-heading {
    font-family: var(--font-sans) !important;
    font-weight: 400 !important;
    font-size: 36px !important;
    line-height: 1.15 !important;
    letter-spacing: -1.2px !important;
    color: #ffffff !important;
}

h3, .dala-subheading {
    font-family: var(--font-sans) !important;
    font-weight: 400 !important;
    font-size: 24px !important;
    line-height: 1.2 !important;
    color: #ffffff !important;
}

p, .dala-body, [data-testid="stMarkdownContainer"] p {
    font-family: var(--font-sans) !important;
    font-weight: 200 !important;
    font-size: 17px !important;
    line-height: 1.6 !important;
    color: #bdbdbd !important;
}

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

.dala-label {
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.35px !important;
    color: #9a9a9a !important;
}

/* Primary Action Button */
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
    transition: all 0.25s ease !important;
    cursor: pointer !important;
}

.stButton > button:hover {
    box-shadow: 0 0 35px rgba(128, 82, 255, 0.65) !important;
    transform: translateY(-2px) !important;
}

/* Download buttons */
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
    transition: all 0.2s ease !important;
}

.stDownloadButton > button:hover {
    border-color: #8052ff !important;
    color: #8052ff !important;
    background-color: rgba(128, 82, 255, 0.08) !important;
}

[data-baseweb="input"] > div, .stTextInput > div > div {
    background-color: #0a0a0a !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 14px !important;
    color: #ffffff !important;
}

.metric-card {
    background-color: #080808;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
}
.metric-value {
    font-size: 38px;
    font-weight: 600;
    color: #8052ff;
}
.metric-title {
    font-size: 13px;
    font-weight: 600;
    color: #9a9a9a;
    text-transform: uppercase;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# TOP NAV
# -------------------------------------------------------------
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0 24px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.07); margin-bottom: 32px;">
    <div style="display: flex; align-items: center; gap: 14px;">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polygon points="12,2 22,20 2,20" fill="#8052ff" />
            <polygon points="12,8 18,18 6,18" fill="#15846e" />
        </svg>
        <span style="font-size: 20px; font-weight: 600; color: #ffffff; letter-spacing: 0.5px;">D-DOM</span>
    </div>
    <div style="display: flex; gap: 24px; align-items: center;">
        <span class="dala-label">DESIGN DOCUMENT OBJECT MODEL</span>
        <span class="dala-tag" style="margin-bottom: 0;">MVP v0.1</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------
st.sidebar.markdown('<span class="dala-tag">ANALYSIS MODE</span>', unsafe_allow_html=True)
input_mode = st.sidebar.radio("Input Source:", ["Public Website URL", "Screenshot Image"], index=0)
enable_fidelity = st.sidebar.checkbox("Enable Fidelity Verification Loop", value=True)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.markdown('<span class="dala-label">EVIDENCE HIERARCHY</span>', unsafe_allow_html=True)
st.sidebar.markdown("""
<div style="margin-top: 12px; display: flex; flex-direction: column; gap: 12px;">
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #8052ff;"></span>
        <span style="font-size: 13px; color: #ffffff;"><b>SOURCE</b> (Extracted CSS/HTML)</span>
    </div>
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #ffb829;"></span>
        <span style="font-size: 13px; color: #ffffff;"><b>RUNTIME</b> (DOM Measured)</span>
    </div>
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #15846e;"></span>
        <span style="font-size: 13px; color: #ffffff;"><b>VISUAL</b> (Pixel Decomposition)</span>
    </div>
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #9a9a9a;"></span>
        <span style="font-size: 13px; color: #ffffff;"><b>INFERRED</b> (Geometric Fallback)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# HERO
# -------------------------------------------------------------
hero_left, hero_right = st.columns([1.2, 0.8], gap="large")

with hero_left:
    st.markdown('<span class="dala-tag">MEASURABLE DESIGN FOR AI AGENTS</span>', unsafe_allow_html=True)
    st.markdown('<h1 class="dala-display">Extract design facts.<br>Verify fidelity.</h1>', unsafe_allow_html=True)
    st.markdown("""
    <p class="dala-body" style="max-width: 580px;">
    D-DOM converts web interfaces into evidence-tagged design tokens and generates exact context for AI agents. Run automated fidelity loops to compare target designs against generated clones.
    </p>
    """, unsafe_allow_html=True)

with hero_right:
    # Particle canvas
    components.html("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body, html { margin: 0; padding: 0; overflow: hidden; background-color: #000000; }
            canvas { display: block; width: 100%; height: 260px; background-color: #000000; }
        </style>
    </head>
    <body>
        <canvas id="canvas"></canvas>
        <script>
            const canvas = document.getElementById('canvas');
            const ctx = canvas.getContext('2d');
            function resize() {
                canvas.width = window.innerWidth * window.devicePixelRatio;
                canvas.height = 260 * window.devicePixelRatio;
                ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
            }
            resize();
            window.addEventListener('resize', resize);
            const colors = ['#8052ff', '#ffb829', '#15846e', '#38bdf8'];
            const particles = [];
            for (let i = 0; i < 70; i++) {
                particles.push({
                    x: Math.random() * window.innerWidth * 0.4,
                    y: Math.random() * 260,
                    vx: (Math.random() - 0.5) * 0.5,
                    vy: (Math.random() - 0.5) * 0.5,
                    size: 3 + Math.random() * 4,
                    color: colors[Math.floor(Math.random() * colors.length)]
                });
            }
            function animate() {
                ctx.clearRect(0, 0, window.innerWidth, 260);
                for (let i = 0; i < particles.length; i++) {
                    for (let j = i + 1; j < particles.length; j++) {
                        const dx = particles[i].x - particles[j].x;
                        const dy = particles[i].y - particles[j].y;
                        const dist = Math.sqrt(dx * dx + dy * dy);
                        if (dist < 60) {
                            ctx.strokeStyle = `rgba(128, 82, 255, ${0.3 * (1 - dist / 60)})`;
                            ctx.lineWidth = 0.8;
                            ctx.beginPath();
                            ctx.moveTo(particles[i].x, particles[i].y);
                            ctx.lineTo(particles[j].x, particles[j].y);
                            ctx.stroke();
                        }
                    }
                }
                for (let p of particles) {
                    p.x += p.vx; p.y += p.vy;
                    if (p.x < 0 || p.x > window.innerWidth * 0.4) p.vx *= -1;
                    if (p.y < 0 || p.y > 260) p.vy *= -1;
                    ctx.fillStyle = p.color;
                    ctx.fillRect(p.x - p.size/2, p.y - p.size/2, p.size, p.size);
                }
                requestAnimationFrame(animate);
            }
            animate();
        </script>
    </body>
    </html>
    """, height=260)

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# INPUT SECTION
# -------------------------------------------------------------
in_col1, in_col2 = st.columns([1, 1], gap="large")

source_url = ""
clone_url = ""
uploaded_file = None

with in_col1:
    st.markdown('<span class="dala-tag">STEP 1</span>', unsafe_allow_html=True)
    if input_mode == "Public Website URL":
        st.markdown('<h3 class="dala-subheading">Source Target URL</h3>', unsafe_allow_html=True)
        source_url = st.text_input("Source Website URL", value="https://example.com", placeholder="https://example.com")
    else:
        st.markdown('<h3 class="dala-subheading">Upload Reference Screenshot</h3>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload reference image", type=["png", "jpg", "jpeg", "webp"])

with in_col2:
    if enable_fidelity:
        st.markdown('<span class="dala-tag">FIDELITY LOOP</span>', unsafe_allow_html=True)
        st.markdown('<h3 class="dala-subheading">Generated / Clone URL (Optional)</h3>', unsafe_allow_html=True)
        clone_url = st.text_input("Clone / Generated URL to verify", value="", placeholder="https://my-clone-site.vercel.app")
    else:
        st.markdown('<span class="dala-label">MODE</span>', unsafe_allow_html=True)
        st.info("Single page analysis mode selected.")

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# ACTION BUTTON & EXECUTION
# -------------------------------------------------------------
btn_col, _ = st.columns([1, 2])
with btn_col:
    analyze_clicked = st.button("Analyze & Generate D-DOM", type="primary")

if analyze_clicked:
    status_widget = st.status("Analyzing interface...", expanded=True)
    try:
        os.makedirs("output", exist_ok=True)
        
        # 1. Analyze Source Target
        status_widget.write("✦ Fetching and extracting evidence-tagged D-DOM tokens...")
        if input_mode == "Public Website URL" and source_url:
            source_ddom = analyze_url(source_url)
        elif uploaded_file is not None:
            temp_path = os.path.join("output", uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            source_ddom = analyze_image(temp_path)
        else:
            source_ddom = analyze_url("https://example.com")

        # Save artifacts
        source_json_path = os.path.join("output", "ddom.json")
        source_ddom.save(source_json_path)

        design_md_content = generate_design_md(source_ddom)
        design_md_path = os.path.join("output", "DESIGN.md")
        with open(design_md_path, "w", encoding="utf-8") as f:
            f.write(design_md_content)

        # 2. Run Fidelity Verification Loop if Clone URL is provided
        fidelity_report = None
        if enable_fidelity and clone_url.strip():
            status_widget.write("✦ Analyzing Clone URL for fidelity comparison...")
            clone_ddom = analyze_url(clone_url.strip())
            clone_json_path = os.path.join("output", "ddom_clone.json")
            clone_ddom.save(clone_json_path)
            
            status_widget.write("✦ Computing category-weighted fidelity score and mismatches...")
            fidelity_report = compare_ddom(source_ddom, clone_ddom)

        status_widget.update(label="D-DOM Analysis Complete", state="complete", expanded=False)

        # -------------------------------------------------------------
        # RESULTS DISPLAY
        # -------------------------------------------------------------
        st.markdown("<br>", unsafe_allow_html=True)
        
        if fidelity_report:
            st.markdown('<span class="dala-tag">FIDELITY VERIFICATION LOOP</span>', unsafe_allow_html=True)
            st.markdown(f'<h2 class="dala-heading">Overall Match: <span style="color:#8052ff;">{fidelity_report.fidelity}%</span></h2>', unsafe_allow_html=True)
            
            # Metrics Row
            m_cols = st.columns(len(fidelity_report.byCategory))
            for i, (cat_name, score) in enumerate(fidelity_report.byCategory.items()):
                with m_cols[i]:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">{cat_name}</div>
                        <div class="metric-value">{score}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
            if fidelity_report.mismatches:
                st.markdown('<h3 class="dala-subheading">Detected Mismatches & Suggested Fixes</h3>', unsafe_allow_html=True)
                mismatch_data = [m.model_dump() for m in fidelity_report.mismatches]
                st.dataframe(mismatch_data, use_container_width=True)
            else:
                st.success("Perfect fidelity! No mismatches detected between source and clone.")
            st.markdown("<br><hr style='border-color: rgba(255,255,255,0.1);'><br>", unsafe_allow_html=True)

        # Extracted Design Summary Cards
        st.markdown('<span class="dala-tag">EXTRACTED DESIGN SUMMARY</span>', unsafe_allow_html=True)
        st.markdown('<h2 class="dala-heading">D-DOM Design Tokens</h2>', unsafe_allow_html=True)
        
        s_col1, s_col2, s_col3 = st.columns(3, gap="large")
        
        with s_col1:
            st.markdown('<span class="dala-label">COLOR PALETTE</span>', unsafe_allow_html=True)
            for c in source_ddom.tokens.colors[:6]:
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                    <div style="width: 24px; height: 24px; border-radius: 6px; background-color: {c.value}; border: 1px solid #333;"></div>
                    <div>
                        <strong style="color:#fff;">{c.value}</strong> <span style="color:#9a9a9a;">({c.name or 'color'})</span>
                        <br><small style="color:#8052ff;">{c.evidence} • conf {c.confidence:.2f}</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        with s_col2:
            st.markdown('<span class="dala-label">TYPOGRAPHY HIERARCHY</span>', unsafe_allow_html=True)
            for t in source_ddom.tokens.typography[:4]:
                st.markdown(f"""
                <div style="margin-bottom: 8px;">
                    <strong style="color:#fff;"><{t.element}></strong>: {t.fontWeight or '400'} / {t.fontSize or '16px'}
                    <br><small style="color:#ffb829;">{t.fontFamily}</small>
                </div>
                """, unsafe_allow_html=True)
                
        with s_col3:
            st.markdown('<span class="dala-label">STRUCTURE & COMPONENTS</span>', unsafe_allow_html=True)
            for r in source_ddom.structure.regions:
                st.markdown(f"• Region: `{r.name}` (count: {r.count})")
            for comp in source_ddom.structure.components:
                st.markdown(f"• Component: `{comp.name}` (count: {comp.count})")

        # Downloads and Previews
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<span class="dala-tag">DELIVERABLES</span>', unsafe_allow_html=True)
        st.markdown('<h3 class="dala-subheading">Download D-DOM Artifacts</h3>', unsafe_allow_html=True)

        d1, d2 = st.columns(2, gap="medium")

        with d1:
            with open(source_json_path, "rb") as f:
                st.download_button(
                    label="Download ddom.json",
                    data=f,
                    file_name="ddom.json",
                    mime="application/json",
                )

        with d2:
            with open(design_md_path, "rb") as f:
                st.download_button(
                    label="Download DESIGN.md",
                    data=f,
                    file_name="DESIGN.md",
                    mime="text/markdown",
                )

        st.markdown("<br>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["DESIGN.md Preview", "ddom.json Preview"])
        
        with tab1:
            st.markdown(design_md_content)

        with tab2:
            st.json(source_ddom.to_dict())

    except Exception as e:
        status_widget.update(label="Analysis Failed", state="error")
        st.error(f"Execution error: {e}")
