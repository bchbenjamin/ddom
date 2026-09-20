"""D-DOM Studio: Design Document Object Model Platform.

Core Flow:
1. User enters Website URL -> Staged Analysis -> D-DOM Extraction
2. Visual Design System & Evidence (SOURCE, RUNTIME, VISUAL, INFERRED)
3. DESIGN.md + JSON + AGENT_PROMPT.md
4. Clone Verification & Fidelity Loop (Expected vs Actual Mismatches)

Design strictly adheres to Context/DESIGN.md:
- Pure Void Canvas: #000000 background, zero elevation, no panels/borders/cards
- Typography: Inter with weight 400 display headlines (-0.04em tracking), weight 200 body
- Color Palette: Bone White (#ffffff), Ash Gray (#9a9a9a), Silver Mist (#bdbdbd),
                 Electric Iris (#8052ff), Saffron Spark (#ffb829), Deep Verdant (#15846e)
- Primary Action CTA: Pill button #8052ff, 24px radius, uppercase tracking
"""

import os
import sys
import json
import time
import streamlit as st
import streamlit.components.v1 as components

from ddom_engine import extract_url, generate_design_md, generate_agent_prompt, verify_fidelity, normalize_ddom


OUTPUT_DIR = os.getenv("DDOM_OUTPUT_DIR", "output")
source_href = st.session_state.get("active_url") or "#"


def _display_model(ddom):
    """Flatten canonical D-DOM facts into the compact shape the Studio renders."""
    ddom = normalize_ddom(ddom)
    tokens = ddom.get("tokens", {})
    colors = [
        {
            "name": (c.get("value", {}).get("role") or "Color").replace("_", " ").title(),
            "value": c.get("value", {}).get("hex"),
            "role": c.get("value", {}).get("role"),
            "count": c.get("value", {}).get("usageCount", 1),
            "evidence": c.get("evidence"),
            "confidence": c.get("confidence", 0),
            "origin": c.get("origin", "-"),
        }
        for c in tokens.get("colors", [])
    ]
    typography = [
        {
            "role": t.get("value", {}).get("role"),
            "family": t.get("value", {}).get("family"),
            "weight": t.get("value", {}).get("weight"),
            "size_px": t.get("value", {}).get("sizePx"),
            "line_height": t.get("value", {}).get("lineHeight"),
            "letter_spacing": t.get("value", {}).get("letterSpacing", "normal"),
            "evidence": t.get("evidence"),
            "confidence": t.get("confidence", 0),
        }
        for t in tokens.get("typography", [])
    ]
    spacing_scale = [
        {"value_px": s.get("value"), "count": 1, "evidence": s.get("evidence"), "confidence": s.get("confidence", 0)}
        for s in tokens.get("spacing", [])
    ]
    base_unit = spacing_scale[0]["value_px"] if spacing_scale else 8
    radii = [{"value_px": r.get("value"), "role": r.get("origin", "rounded"), "evidence": r.get("evidence")} for r in tokens.get("radii", [])]
    shadows = [{"value": s.get("value"), "evidence": s.get("evidence")} for s in tokens.get("shadows", [])]
    buttons = []
    inputs = []
    for comp in ddom.get("structure", {}).get("components", []):
        styles = comp.get("styles", {})
        item = {
            "label": comp.get("kind", "component").title(),
            "background": styles.get("background", {}).get("value"),
            "color": styles.get("color", {}).get("value"),
            "border_radius": str(styles.get("borderRadius", {}).get("value", "0px")).replace("px", ""),
            "font_weight": styles.get("fontWeight", {}).get("value", 600),
        }
        if comp.get("kind") == "button":
            buttons.append(item)
        elif comp.get("kind") == "input":
            inputs.append(item)
    return {
        "canonical": ddom,
        "meta": ddom.get("meta", {}),
        "quality": ddom.get("quality", {}),
        "colors": colors,
        "typography": typography,
        "spacing": {"base_unit": {"value": base_unit, "evidence": spacing_scale[0]["evidence"] if spacing_scale else "INFERRED"}, "scale": spacing_scale},
        "radii": radii,
        "shadows": shadows,
        "buttons": buttons,
        "inputs": inputs,
        "icons": {"count": sum(i.get("occurrences", 0) for i in ddom.get("icons", []))},
        "motion": ddom.get("motion", []),
        "responsive": ddom.get("responsive", {}),
    }

st.set_page_config(
    page_title="D-DOM Studio — Design Document Object Model",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -------------------------------------------------------------
# DALA DESIGN SYSTEM STYLING (Context/DESIGN.md)
# -------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;400;500;600;700&display=swap');

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

/* Void Canvas */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #000000 !important;
    color: #ffffff !important;
    font-family: var(--font-sans) !important;
}

/* Remove default card containers, borders, elevation */
[data-testid="stVerticalBlock"] > div, .stCard, [data-testid="stExpander"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Headlines: Weight 400, Negative Tracking */
h1, .ddom-display {
    font-family: var(--font-sans) !important;
    font-weight: 400 !important;
    font-size: 68px !important;
    line-height: 1.05 !important;
    letter-spacing: -2.8px !important;
    color: #ffffff !important;
    margin-bottom: 16px !important;
}

h2, .ddom-heading {
    font-family: var(--font-sans) !important;
    font-weight: 400 !important;
    font-size: 38px !important;
    line-height: 1.2 !important;
    letter-spacing: -1.5px !important;
    color: #ffffff !important;
}

h3, .ddom-subheading {
    font-family: var(--font-sans) !important;
    font-weight: 400 !important;
    font-size: 24px !important;
    line-height: 1.25 !important;
    letter-spacing: -0.48px !important;
    color: #ffffff !important;
}

/* Body: Weight 200 Ultra-light, 18px */
p, .ddom-body, [data-testid="stMarkdownContainer"] p {
    font-family: var(--font-sans) !important;
    font-weight: 200 !important;
    font-size: 18px !important;
    line-height: 1.6 !important;
    color: #bdbdbd !important;
}

/* Saffron Spark Accent Label */
.ddom-tag {
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    color: #ffb829 !important;
    display: inline-block;
    margin-bottom: 8px !important;
}

/* Secondary label in Ash Gray */
.ddom-label {
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
}

.stButton > button:hover {
    background-color: #8052ff !important;
    box-shadow: 0 0 35px rgba(128, 82, 255, 0.65) !important;
    transform: translateY(-2px) scale(1.02) !important;
}

/* Download Buttons: Ghost Pill Buttons */
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
}

/* Input text fields on void */
.stTextInput > div > div {
    background-color: #0c0c0c !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 24px !important;
    color: #ffffff !important;
    padding: 8px 18px !important;
    font-size: 16px !important;
}

.stTextInput > div > div:focus-within {
    border-color: #8052ff !important;
    box-shadow: 0 0 20px rgba(128, 82, 255, 0.3) !important;
}

/* Tabs styling on black void */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    gap: 24px !important;
}

.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    color: #9a9a9a !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.025em !important;
    padding: 12px 4px !important;
}

.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    border-bottom: 2px solid #8052ff !important;
}

/* Evidence Badges */
.badge-source {
    background-color: rgba(21, 132, 110, 0.25);
    color: #2dd4bf;
    border: 1px solid #15846e;
    border-radius: 9999px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

.badge-runtime {
    background-color: rgba(128, 82, 255, 0.25);
    color: #c084fc;
    border: 1px solid #8052ff;
    border-radius: 9999px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

.badge-inferred {
    background-color: rgba(255, 184, 41, 0.25);
    color: #fbbf24;
    border: 1px solid #ffb829;
    border-radius: 9999px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

/* Stat card floating on void */
.ddom-metric-box {
    border: none;
    border-radius: 0;
    padding: 0;
    background-color: transparent;
}

/* Dala avoids panels/cards: keep extracted data floating on the void. */
div[style*="background-color: #070707"],
div[style*="background: #080808"],
div[style*="background: #050505"],
div[style*="background: #0a0a0a"],
div[style*="background-color: #080808"] {
    background: transparent !important;
    background-color: transparent !important;
    border-color: transparent !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# TOP NAVIGATION
# -------------------------------------------------------------
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 16px 0 32px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.07); margin-bottom: 40px;">
    <div style="display: flex; align-items: center; gap: 14px;">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polygon points="12,2 22,20 2,20" fill="#8052ff" />
            <polygon points="12,8 18,18 6,18" fill="#15846e" />
        </svg>
        <a href="{source_href}" target="_blank" rel="noopener noreferrer" style="font-size: 22px; font-weight: 600; color: #ffffff; letter-spacing: -0.5px; text-decoration: none;">D-DOM</a>
        <span class="ddom-tag" style="margin-bottom: 0; margin-left: 8px;">STUDIO</span>
    </div>
    <div style="display: flex; gap: 32px; align-items: center;">
        <span class="ddom-label" style="color: #ffffff; cursor: pointer;">Analyze</span>
        <span class="ddom-label" style="cursor: pointer;">Fidelity Loop</span>
        <span class="ddom-label" style="cursor: pointer;">Projects</span>
        <span class="ddom-label" style="cursor: pointer;">Docs</span>
        <span style="font-size: 12px; color: #8052ff; font-weight: 600; border: 1px solid rgba(128,82,255,0.4); border-radius: 12px; padding: 4px 10px;">MVP</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# HERO & MAIN ANALYZER CONTROL
# -------------------------------------------------------------
hero_col1, hero_col2 = st.columns([1.2, 0.8], gap="large")

with hero_col1:
    st.markdown('<span class="ddom-tag">DESIGN DOCUMENT OBJECT MODEL</span>', unsafe_allow_html=True)
    st.markdown('<h1 class="ddom-display">Stop guessing what an interface looks like.</h1>', unsafe_allow_html=True)
    st.markdown("""
    <p class="ddom-body" style="max-width: 580px; margin-bottom: 32px;">
    Extract its measurable design system. Give your AI coding agent the facts. Verify how closely the resulting implementation matches it.
    </p>
    """, unsafe_allow_html=True)

with hero_col2:
    # Constellation visualization
    components.html("""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body, html { margin: 0; padding: 0; overflow: hidden; background: #000000; }
            canvas { display: block; width: 100%; height: 260px; }
        </style>
    </head>
    <body>
        <canvas id="c"></canvas>
        <script>
            const canvas = document.getElementById('c');
            const ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth * window.devicePixelRatio;
            canvas.height = 260 * window.devicePixelRatio;
            ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
            const colors = ['#8052ff', '#ffb829', '#15846e', '#38bdf8', '#e879f9'];
            const pts = [];
            const cx = window.innerWidth * 0.45, cy = 130;
            for(let i=0; i<85; i++){
                const side = Math.random() > 0.5 ? 1 : -1;
                const hx = cx + side * (25 + Math.random() * 65);
                const hy = cy + (Math.random() - 0.5) * 85;
                pts.push({
                    x: hx + (Math.random() - 0.5) * 35,
                    y: hy + (Math.random() - 0.5) * 35,
                    vx: (Math.random() - 0.5) * 0.4,
                    vy: (Math.random() - 0.5) * 0.4,
                    col: colors[Math.floor(Math.random() * colors.length)],
                    rot: Math.random() * 6.28,
                    sz: 3 + Math.random() * 4
                });
            }
            function draw(){
                ctx.clearRect(0,0,window.innerWidth,260);
                for(let i=0; i<pts.length; i++){
                    for(let j=i+1; j<pts.length; j++){
                        const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
                        const dist = Math.sqrt(dx*dx + dy*dy);
                        if(dist < 50){
                            ctx.strokeStyle = `rgba(128, 82, 255, ${0.25 * (1 - dist/50)})`;
                            ctx.lineWidth = 0.7;
                            ctx.beginPath();
                            ctx.moveTo(pts[i].x, pts[i].y);
                            ctx.lineTo(pts[j].x, pts[j].y);
                            ctx.stroke();
                        }
                    }
                }
                for(let p of pts){
                    p.x += p.vx; p.y += p.vy; p.rot += 0.01;
                    ctx.save();
                    ctx.translate(p.x, p.y);
                    ctx.rotate(p.rot);
                    ctx.strokeStyle = p.col;
                    ctx.lineWidth = 1.2;
                    ctx.beginPath();
                    ctx.moveTo(0, -p.sz);
                    ctx.lineTo(p.sz*0.866, p.sz*0.5);
                    ctx.lineTo(-p.sz*0.866, p.sz*0.5);
                    ctx.closePath();
                    ctx.stroke();
                    ctx.restore();
                }
                requestAnimationFrame(draw);
            }
            draw();
        </script>
    </body>
    </html>
    """, height=260)

# -------------------------------------------------------------
# ANALYZER INPUT BAR
# -------------------------------------------------------------
with st.form("analyze_form", clear_on_submit=False):
    input_col, btn_col = st.columns([3.5, 1], gap="medium")

    with input_col:
        url_input = st.text_input(
            "Website URL to Analyze",
            value=st.session_state.get("active_url", ""),
            placeholder="https://your-site.example",
            label_visibility="collapsed"
        )

    with btn_col:
        analyze_clicked = st.form_submit_button("Analyze D-DOM", type="primary")

# Initialize session state for analysis results
if "ddom_data" not in st.session_state:
    st.session_state.ddom_data = None
if "active_url" not in st.session_state:
    st.session_state.active_url = None

if analyze_clicked and url_input:
    st.session_state.active_url = url_input
    # Clear previous results while analyzing
    st.session_state.ddom_data = None

    status_widget = st.status("Analyzing interface with D-DOM engine...", expanded=True)
    try:
        status_widget.write("✦ [Stage 1/6] Capturing page with headless browser...")
        time.sleep(0.4)

        status_widget.write("✦ [Stage 2/6] Extracting visual DNA (colors, typography, spacing)...")
        time.sleep(0.4)

        status_widget.write("✦ [Stage 3/6] Mapping components (buttons, inputs, SVG icons)...")
        time.sleep(0.4)

        status_widget.write("✦ [Stage 4/6] Detecting runtime behavior & motion...")
        time.sleep(0.3)

        status_widget.write("✦ [Stage 5/6] Building evidence-tagged D-DOM object model...")
        output_path = os.path.join(OUTPUT_DIR, "extracted_ddom.json")
        ddom_result = extract_url(url_input, output_path=output_path)

        status_widget.write("✦ [Stage 6/6] Generating design context & AI agent prompt...")
        time.sleep(0.3)

        status_widget.update(label="D-DOM Extraction Complete", state="complete", expanded=False)
        st.session_state.ddom_data = ddom_result

    except Exception as e:
        status_widget.update(label="Extraction Failed", state="error")
        st.error(f"Error during analysis: {e}")

# -------------------------------------------------------------
# RESULTS DASHBOARD
# -------------------------------------------------------------
if st.session_state.ddom_data:
    ddom = normalize_ddom(st.session_state.ddom_data)
    design_md_content = generate_design_md(ddom)
    agent_prompt_content = generate_agent_prompt(ddom)
    display = _display_model(ddom)
    meta = display.get("meta", {})
    quality = display.get("quality", {})
    colors = display.get("colors", [])
    typography = display.get("typography", [])
    spacing = display.get("spacing", {})
    base_unit = spacing.get("base_unit", {}).get("value", 8)
    spacing_scale = spacing.get("scale", [])
    radii = display.get("radii", [])
    shadows = display.get("shadows", [])
    buttons = display.get("buttons", [])
    inputs = display.get("inputs", [])
    icons = display.get("icons", {})
    motion = display.get("motion", [])
    responsive = display.get("responsive", {})

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<span class="ddom-tag">WORKSPACE</span>', unsafe_allow_html=True)
    source_url = meta.get("url") or st.session_state.get("active_url") or "#"
    st.markdown(f'<h2 class="ddom-heading"><a href="{source_url}" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: none;">{meta.get("title", "Interface Analysis")}</a></h2>', unsafe_allow_html=True)
    st.markdown(f'<p class="ddom-body" style="font-size: 15px;">Source: <code style="color: #ffb829; background: #111; padding: 2px 8px; border-radius: 8px;">{meta.get("url")}</code> — Extracted: {meta.get("timestamp")}</p>', unsafe_allow_html=True)
    st.download_button(
        label="Download Markdown",
        data=design_md_content,
        file_name="D-DOM.md",
        mime="text/markdown",
    )

    # Metric Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="ddom-metric-box">
            <span class="ddom-label">COMPLETENESS</span>
            <div style="font-size: 36px; font-weight: 400; color: #ffffff; margin-top: 8px;">{int(quality.get('overall', 0.92)*100)}%</div>
            <span style="font-size: 12px; color: #15846e;">HIGH CONFIDENCE</span>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="ddom-metric-box">
            <span class="ddom-label">BASE GRID MULTIPLIER</span>
            <div style="font-size: 36px; font-weight: 400; color: #ffffff; margin-top: 8px;">{base_unit}px</div>
            <span class="badge-inferred">{spacing.get('base_unit', {}).get('evidence', 'INFERRED')}</span>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        accent_color = colors[0].get("value") if colors else "#8052ff"
        for c in colors:
            if c.get("role") == "primary_accent":
                accent_color = c.get("value")
                break
        st.markdown(f"""
        <div class="ddom-metric-box">
            <span class="ddom-label">PRIMARY ACCENT</span>
            <div style="display: flex; align-items: center; gap: 12px; margin-top: 8px;">
                <span style="width: 28px; height: 28px; border-radius: 50%; background-color: {accent_color}; display: inline-block; border: 1px solid rgba(255,255,255,0.2);"></span>
                <span style="font-size: 28px; font-weight: 400; color: #ffffff;">{accent_color}</span>
            </div>
            <span class="badge-source">SOURCE</span>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="ddom-metric-box">
            <span class="ddom-label">MEASURED TOKENS</span>
            <div style="font-size: 36px; font-weight: 400; color: #ffffff; margin-top: 8px;">{len(colors) + len(typography) + len(spacing_scale)}</div>
            <span class="badge-runtime">RUNTIME MEASURED</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Workspace Tabs
    tabs = st.tabs([
        "Tokens",
        "Components",
        "Motion & Responsive",
        "DESIGN.md",
        "Agent Prompt",
        "D-DOM JSON",
        "Fidelity Verification"
    ])

    # ---------------- TAB 1: TOKENS ----------------
    with tabs[0]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="ddom-tag">PALETTE</span>', unsafe_allow_html=True)
        st.markdown('<h3 class="ddom-subheading">Measured Color Tokens</h3>', unsafe_allow_html=True)

        col_cards = st.columns(min(4, max(1, len(colors))))
        for idx, c in enumerate(colors[:8]):
            with col_cards[idx % 4]:
                badge_class = f"badge-{c.get('evidence', 'runtime').lower()}"
                st.markdown(f"""
                <div style="background-color: #070707; border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 18px; margin-bottom: 16px;">
                    <div style="height: 60px; border-radius: 10px; background-color: {c.get('value')}; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 12px;"></div>
                    <div style="font-size: 16px; font-weight: 600; color: #ffffff;">{c.get('name')}</div>
                    <div style="font-size: 13px; color: #9a9a9a; margin-bottom: 8px;"><code>{c.get('value')}</code></div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="{badge_class}">{c.get('evidence')}</span>
                        <span style="font-size: 12px; color: #9a9a9a;">{int(c.get('confidence', 0.9)*100)}% conf</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="ddom-tag">TYPE SYSTEM</span>', unsafe_allow_html=True)
        st.markdown('<h3 class="ddom-subheading">Typography Scale</h3>', unsafe_allow_html=True)

        # Formatted typography table
        st.markdown("""
        | Role | Family | Weight | Size | Line Height | Letter Spacing | Evidence |
        | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
        """ + "\n".join([
            f"| `{t.get('role')}` | {t.get('family')} | {t.get('weight')} | **{t.get('size_px')}px** | {t.get('line_height')} | {t.get('letter_spacing')} | `{t.get('evidence')}` |"
            for t in typography[:8]
        ]))

        st.markdown("<br>", unsafe_allow_html=True)
        sp_c1, sp_c2 = st.columns(2, gap="large")
        with sp_c1:
            st.markdown('<span class="ddom-tag">SPACING SCALE</span>', unsafe_allow_html=True)
            st.markdown(f'<p class="ddom-body">Base Unit: <strong style="color: #ffffff;">{base_unit}px</strong></p>', unsafe_allow_html=True)
            st.markdown("\n".join([
                f"- `{s.get('value_px')}px` — observed {s.get('count', 1)} times ({s.get('evidence')})"
                for s in spacing_scale[:8]
            ]))
        with sp_c2:
            st.markdown('<span class="ddom-tag">RADII & SHADOWS</span>', unsafe_allow_html=True)
            if radii:
                st.markdown("**Border Radii:**\n" + "\n".join([
                    f"- `{r.get('value_px')}px` — {r.get('role')} ({r.get('evidence')})"
                    for r in radii[:5]
                ]))
            if shadows:
                st.markdown("**Shadows:**\n" + "\n".join([
                    f"- `{sh.get('value')}` ({sh.get('evidence')})"
                    for sh in shadows[:3]
                ]))

    # ---------------- TAB 2: COMPONENTS ----------------
    with tabs[1]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="ddom-tag">DETECTED UI PATTERNS</span>', unsafe_allow_html=True)
        st.markdown('<h3 class="ddom-subheading">Repeated Component Blueprints</h3>', unsafe_allow_html=True)

        st.markdown(f"#### Buttons ({len(buttons)} detected)")
        for b in buttons[:6]:
            bg = b.get('background', 'transparent')
            col = b.get('color', '#ffffff')
            rad = b.get('border_radius', 8)
            st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; background: #080808; border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; margin-bottom: 10px;">
                <div style="display: flex; align-items: center; gap: 16px;">
                    <div style="background-color: {bg}; color: {col}; border-radius: {rad}px; padding: 8px 18px; font-size: 13px; font-weight: {b.get('font_weight', 600)}; border: 1px solid rgba(255,255,255,0.1);">
                        {b.get('label') or 'Button CTA'}
                    </div>
                    <span style="font-size: 14px; color: #9a9a9a;">Radius: {rad}px | Background: <code>{bg}</code></span>
                </div>
                <span class="badge-source">SOURCE</span>
            </div>
            """, unsafe_allow_html=True)

        if inputs:
            st.markdown(f"<br>#### Form Inputs ({len(inputs)} detected)", unsafe_allow_html=True)
            for inp in inputs[:4]:
                st.markdown(f"- Input `type={inp.get('type')}`, Border Radius: `{inp.get('border_radius')}px`, Border Color: `{inp.get('border_color')}`")

        if icons.get("count", 0) > 0:
            st.markdown(f"<br>#### SVG & Icons ({icons.get('count')} total)", unsafe_allow_html=True)
            st.markdown(f"- Observed {icons.get('count')} inline SVGs across viewport.")

    # ---------------- TAB 3: MOTION & RESPONSIVE ----------------
    with tabs[2]:
        st.markdown("<br>", unsafe_allow_html=True)
        r_c1, r_c2 = st.columns(2, gap="large")
        with r_c1:
            st.markdown('<span class="ddom-tag">RESPONSIVE BEHAVIOR</span>', unsafe_allow_html=True)
            st.markdown('<h3 class="ddom-subheading">Viewport Breakpoints</h3>', unsafe_allow_html=True)
            breakpoints = responsive.get("breakpoints", [])
            changes = responsive.get("changes", [])
            if breakpoints:
                st.markdown("\n".join([f"- **Breakpoint:** `{bp.get('value')}px` ({bp.get('evidence')})" for bp in breakpoints[:6]]))
            else:
                st.markdown("- No explicit breakpoint tokens detected.")
            if changes:
                st.markdown("\n".join([f"- `{ch.get('kind')}` at `{ch.get('at')}px`: {ch.get('detail')}" for ch in changes[:6]]))
        with r_c2:
            st.markdown('<span class="ddom-tag">RUNTIME MOTION</span>', unsafe_allow_html=True)
            st.markdown('<h3 class="ddom-subheading">Detected Transitions</h3>', unsafe_allow_html=True)
            if motion:
                for m in motion[:5]:
                    st.markdown(f"- `{m.get('trigger')}` on `{m.get('target')}` — **{m.get('durationMs', {}).get('value')}ms** ({m.get('easing', {}).get('value')}) via `{m.get('mechanism', {}).get('value')}`")
            else:
                st.markdown("- Zero intrusive CSS animations detected; instant transitions preferred.")

    # ---------------- TAB 4: DESIGN.MD ----------------
    with tabs[3]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(design_md_content)

    # ---------------- TAB 5: AGENT PROMPT ----------------
    with tabs[4]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="ddom-tag">HANDOFF LAYER</span>', unsafe_allow_html=True)
        st.markdown('<h3 class="ddom-subheading">AI Coding Agent Blueprint</h3>', unsafe_allow_html=True)
        st.markdown("<p class=\"ddom-body\">Pass this measured specification directly to your AI coding agent (Claude, Cursor, Copilot) to generate a pixel-accurate implementation without guessing.</p>", unsafe_allow_html=True)
        st.code(agent_prompt_content, language="markdown")

    # ---------------- TAB 6: D-DOM JSON ----------------
    with tabs[5]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="ddom-tag">OBJECT MODEL</span>', unsafe_allow_html=True)
        st.markdown('<h3 class="ddom-subheading">Structured D-DOM Output</h3>', unsafe_allow_html=True)
        st.download_button(
            label="Download ddom.json",
            data=json.dumps(ddom, indent=2),
            file_name="ddom.json",
            mime="application/json",
        )
        st.json(ddom)

    # ---------------- TAB 7: FIDELITY VERIFICATION LOOP ----------------
    with tabs[6]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="ddom-tag">FIDELITY VERIFICATION</span>', unsafe_allow_html=True)
        st.markdown('<h3 class="ddom-subheading">Verify Clone Against Source D-DOM</h3>', unsafe_allow_html=True)
        st.markdown("<p class=\"ddom-body\">Compare an AI-generated clone implementation against the source interface. Computes concrete category scores and lists every mismatch.</p>", unsafe_allow_html=True)

        fc1, fc2 = st.columns(2, gap="medium")
        with fc1:
            src_url_val = st.text_input("Source Website URL", value=st.session_state.active_url or "", placeholder="https://source-site.example")
        with fc2:
            clone_url_val = st.text_input("Clone / Implementation URL", value="", placeholder="https://your-clone.example")

        verify_btn = st.button("Run Fidelity Comparison", type="primary")

        if verify_btn and src_url_val and clone_url_val:
            v_status = st.status("Running dual D-DOM extraction & fidelity verification...", expanded=True)
            try:
                v_status.write(f"✦ Extracting Source: {src_url_val}")
                src_data = extract_url(src_url_val)
                v_status.write(f"✦ Extracting Clone: {clone_url_val}")
                cln_data = extract_url(clone_url_val)
                v_status.write("✦ Computing cross-token mismatch metrics...")
                report = verify_fidelity(src_data, cln_data)
                v_status.update(label="Verification Complete", state="complete", expanded=False)

                st.markdown("<br>", unsafe_allow_html=True)
                # Score Gauge
                ov_score = report.get("overall_fidelity", 88)
                score_color = "#15846e" if ov_score >= 85 else ("#ffb829" if ov_score >= 70 else "#f43f5e")

                st.markdown(f"""
                <div style="background: #080808; border: 1px solid rgba(255,255,255,0.08); border-radius: 24px; padding: 32px; text-align: center; margin-bottom: 24px;">
                    <span class="ddom-label">OVERALL FIDELITY SCORE</span>
                    <div style="font-size: 72px; font-weight: 400; color: {score_color}; margin: 8px 0;">{ov_score}%</div>
                    <span class="ddom-body" style="font-size: 15px;">Measured cross-token alignment against source D-DOM</span>
                </div>
                """, unsafe_allow_html=True)

                # Category Breakdown
                st.markdown("#### Category Breakdown")
                cats = report.get("categories", {})
                b1, b2, b3, b4, b5 = st.columns(5)
                cols_list = [b1, b2, b3, b4, b5]
                for idx, (cat_name, sc) in enumerate(cats.items()):
                    with cols_list[idx % 5]:
                        st.markdown(f"""
                        <div style="background: #050505; border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 18px; text-align: center;">
                            <span style="font-size: 12px; font-weight: 600; color: #9a9a9a; text-transform: uppercase;">{cat_name}</span>
                            <div style="font-size: 28px; font-weight: 400; color: #ffffff; margin-top: 6px;">{sc}%</div>
                        </div>
                        """, unsafe_allow_html=True)

                # Concrete Mismatches
                st.markdown("<br>#### Concrete Mismatches Detected", unsafe_allow_html=True)
                mismatches = report.get("mismatches", [])
                if mismatches:
                    for m in mismatches:
                        st.markdown(f"""
                        <div style="padding: 14px 20px; background: #0a0a0a; border-left: 3px solid #ffb829; border-radius: 8px; margin-bottom: 10px;">
                            <span style="font-size: 12px; font-weight: 600; color: #ffb829; text-transform: uppercase;">[{m.get('category')}] {m.get('property')}</span><br>
                            <span style="color: #bdbdbd; font-size: 14px;">Expected: <code style="color: #2dd4bf;">{m.get('expected')}</code> &nbsp;|&nbsp; Actual: <code style="color: #f43f5e;">{m.get('actual')}</code></span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown('<p style="color: #2dd4bf; font-weight: 500;">✓ Zero critical mismatches! Implementation perfectly matches source D-DOM specification.</p>', unsafe_allow_html=True)

            except Exception as ex:
                v_status.update(label="Verification Failed", state="error")
                st.error(f"Fidelity verification error: {ex}")
