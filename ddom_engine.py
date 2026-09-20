"""D-DOM Core Engine.

Keeps the product contract in one place:
- browser extraction returns canonical D-DOM v0.1
- markdown and agent prompts are rendered from canonical facts
- fidelity verification compares two D-DOM documents category-by-category
"""

from __future__ import annotations

import datetime as _dt
import ipaddress
import json
import os
import re
import socket
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


EVIDENCE_CONFIDENCE = {"SOURCE": 0.95, "RUNTIME": 0.9, "VISUAL": 0.7, "INFERRED": 0.55}


def fact(value: Any, evidence: str = "SOURCE", confidence: Optional[float] = None, origin: Optional[str] = None) -> Dict[str, Any]:
    item = {
        "value": value,
        "evidence": evidence,
        "confidence": round(float(confidence if confidence is not None else EVIDENCE_CONFIDENCE.get(evidence, 0.8)), 3),
    }
    if origin:
        item["origin"] = origin
    return item


def extract_url(url: str, output_path: Optional[str] = None, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
    """Execute the browser extractor and return canonical D-DOM JSON."""
    url = _normalize_and_validate_url(url)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    extractor_script = os.path.join(current_dir, "extractor.js")
    default_output_dir = os.getenv("DDOM_OUTPUT_DIR", os.path.join(current_dir, "output"))
    temp_output = output_path or os.path.join(default_output_dir, "temp_ddom.json")
    os.makedirs(os.path.dirname(temp_output), exist_ok=True)

    cmd = ["node", extractor_script, url, temp_output]
    if screenshot_path:
        cmd.append(screenshot_path)

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90, cwd=current_dir)
        if proc.returncode != 0:
            print(f"[Warning] Node extractor stderr: {proc.stderr}")
            ddom = _fallback_python_extract(url)
        else:
            with open(temp_output, "r", encoding="utf-8") as f:
                ddom = json.load(f)
    except Exception as exc:
        print(f"[Notice] Browser extraction error ({exc}), running deterministic fallback...")
        ddom = _fallback_python_extract(url)

    ddom = normalize_ddom(ddom, source_url=url)
    with open(temp_output, "w", encoding="utf-8") as f:
        json.dump(ddom, f, indent=2)
    return ddom


def _normalize_and_validate_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported.")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not supported.")
    if not parsed.hostname:
        raise ValueError("URL must include a hostname.")
    try:
        for info in socket.getaddrinfo(parsed.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                raise ValueError("Refusing to analyze private, local, link-local, or reserved addresses.")
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve hostname: {parsed.hostname}") from exc
    return url


def _fallback_python_extract(url: str) -> Dict[str, Any]:
    warnings: List[str] = ["Browser extraction unavailable; used low-confidence HTML fallback."]
    try:
        import requests

        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (D-DOM Engine)"})
        html = resp.text
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else "Extracted Page"
    except Exception:
        html = ""
        title = "Extracted Page"
        warnings.append("Fallback could not fetch page HTML.")

    hex_colors = list(dict.fromkeys(re.findall(r"#[0-9a-fA-F]{6}\b", html)))[:8] or ["#000000", "#ffffff"]
    captured = _dt.datetime.now(_dt.timezone.utc).isoformat()
    colors = [fact({"hex": c.lower(), "role": "custom", "usageCount": 1}, "SOURCE", 0.75, "html/css text") for c in hex_colors]
    typography = [
        fact(
            {
                "family": "system-ui",
                "fallbackStack": ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
                "sizePx": 16,
                "weight": 400,
                "lineHeight": "1.5",
                "role": "body",
            },
            "INFERRED",
            0.55,
            "fallback baseline",
        )
    ]
    ddom = {
        "schemaVersion": "0.1",
        "id": _run_id(url),
        "source": {"kind": "website", "url": url, "capturedAt": captured, "viewports": [{"name": "desktop", "width": 1280, "height": 900}]},
        "tokens": {
            "colors": colors,
            "typography": typography,
            "spacing": [fact(v, "INFERRED", 0.5, "fallback scale") for v in [4, 8, 16, 24, 32]],
            "radii": [fact(0, "INFERRED", 0.5, "fallback baseline")],
            "shadows": [],
            "borders": [],
        },
        "structure": {"regions": [], "components": []},
        "motion": [],
        "interactions": [],
        "responsive": {"breakpoints": [], "changes": []},
        "icons": [],
        "warnings": warnings,
        "meta": {"url": url, "title": title, "timestamp": captured, "generator": "D-DOM v0.1 Python Fallback"},
    }
    ddom["quality"] = _quality_report(colors, typography, ddom["tokens"]["spacing"], [], [], ddom["source"]["viewports"])
    return ddom


def normalize_ddom(data: Dict[str, Any], source_url: Optional[str] = None) -> Dict[str, Any]:
    """Accept either legacy or canonical D-DOM and return canonical v0.1."""
    canonical = data if data.get("schemaVersion") == "0.1" and "source" in data and "structure" in data else _legacy_to_canonical(data, source_url)
    canonical.setdefault("schemaVersion", "0.1")
    canonical.setdefault("id", _run_id(canonical.get("source", {}).get("url", source_url or "unknown")))
    canonical.setdefault("warnings", [])
    canonical.setdefault("motion", [])
    canonical.setdefault("interactions", [])
    canonical.setdefault("icons", [])
    canonical.setdefault("responsive", {"breakpoints": [], "changes": []})
    canonical.setdefault("structure", {"regions": [], "components": []})
    canonical.setdefault("tokens", {})
    for key in ["colors", "typography", "spacing", "radii", "shadows", "borders"]:
        canonical["tokens"].setdefault(key, [])
    canonical["quality"] = _quality_report(
        canonical["tokens"]["colors"],
        canonical["tokens"]["typography"],
        canonical["tokens"]["spacing"],
        canonical.get("motion", []),
        canonical.get("structure", {}).get("components", []),
        canonical.get("source", {}).get("viewports", []),
    )
    canonical.setdefault("meta", {
        "url": canonical.get("source", {}).get("url"),
        "title": canonical.get("source", {}).get("url") or "Interface Analysis",
        "timestamp": canonical.get("source", {}).get("capturedAt"),
        "generator": "D-DOM v0.1 Core",
    })
    return canonical


def _legacy_to_canonical(data: Dict[str, Any], source_url: Optional[str]) -> Dict[str, Any]:
    meta = data.get("meta", {})
    tokens = data.get("tokens", {})
    captured = meta.get("timestamp") or _dt.datetime.now(_dt.timezone.utc).isoformat()
    url = source_url or meta.get("url") or data.get("url") or ""

    colors = [
        fact({"hex": c.get("value", "#000000"), "role": c.get("role"), "usageCount": int(c.get("count", 1))}, c.get("evidence", "RUNTIME"), c.get("confidence", 0.9), c.get("origin"))
        for c in tokens.get("colors", [])
    ]
    typography = []
    for t in tokens.get("typography", []):
        family = t.get("family") or t.get("fontFamily") or "system-ui"
        typography.append(fact(
            {
                "family": family,
                "fallbackStack": _fallback_stack(family),
                "sizePx": float(t.get("size_px") or str(t.get("fontSize", "16")).replace("px", "") or 16),
                "weight": int(t.get("weight") or t.get("fontWeight") or 400),
                "lineHeight": t.get("line_height") or t.get("lineHeight") or "normal",
                "letterSpacing": t.get("letter_spacing", "normal"),
                "role": t.get("role") or t.get("element") or "body",
            },
            t.get("evidence", "RUNTIME"),
            t.get("confidence", 0.9),
            t.get("origin"),
        ))

    spacing_source = tokens.get("spacing", {})
    spacing = [fact(s.get("value_px"), s.get("evidence", "RUNTIME"), s.get("confidence", 0.9), s.get("origin")) for s in spacing_source.get("scale", [])] if isinstance(spacing_source, dict) else []
    if not spacing and isinstance(spacing_source, list):
        spacing = [fact(int(str(s.get("value", "0")).replace("px", "")), s.get("evidence", "SOURCE"), s.get("confidence", 0.9), s.get("origin")) for s in spacing_source]
    radii = [fact(r.get("value_px"), r.get("evidence", "RUNTIME"), r.get("confidence", 0.9), r.get("role")) for r in tokens.get("border_radii", tokens.get("radii", []))]
    shadows = [fact(s.get("value"), s.get("evidence", "RUNTIME"), s.get("confidence", 0.9), s.get("origin")) for s in tokens.get("shadows", [])]

    legacy_components = data.get("components", {})
    components = []
    for kind, items in [("button", legacy_components.get("buttons", [])), ("input", legacy_components.get("inputs", []))]:
        for idx, item in enumerate(items):
            components.append({
                "id": f"{kind}_{idx + 1}",
                "kind": kind,
                "occurrences": 1,
                "exemplarSelector": item.get("selector", kind),
                "styles": {
                    "background": fact(str(item.get("background") or item.get("bg") or ""), item.get("evidence", "SOURCE"), item.get("confidence", 0.9)),
                    "color": fact(str(item.get("color") or ""), item.get("evidence", "SOURCE"), item.get("confidence", 0.9)),
                    "borderRadius": fact(f"{item.get('border_radius', 0)}px", item.get("evidence", "SOURCE"), item.get("confidence", 0.9)),
                },
            })

    icons = []
    icon_info = legacy_components.get("icons", {})
    if icon_info.get("count", 0):
        icons.append({"id": "icons_inline_svg", "format": "inline-svg", "sizePx": fact(24, "RUNTIME", 0.8, "inline svg average"), "family": fact("unknown", "INFERRED", 0.45), "occurrences": icon_info.get("count", 0)})

    motion = []
    for idx, m in enumerate(data.get("motion", [])):
        motion.append({
            "id": f"motion_{idx + 1}",
            "trigger": "hover",
            "target": m.get("target", "*"),
            "from": {},
            "to": {m.get("property", "transition"): m.get("duration", "")},
            "durationMs": fact(_duration_ms(m.get("duration", "0s")), m.get("evidence", "RUNTIME"), m.get("confidence", 0.9)),
            "easing": fact(m.get("timing_function") or m.get("timing") or "ease", m.get("evidence", "RUNTIME"), m.get("confidence", 0.9)),
            "mechanism": fact("css-transition", "RUNTIME", 0.9),
        })

    responsive = {"breakpoints": [], "changes": []}
    if data.get("responsive"):
        resp = data["responsive"]
        responsive["breakpoints"].append(fact(375, "RUNTIME", 0.9, "mobile viewport"))
        if resp.get("has_mobile_menu"):
            responsive["changes"].append({"at": 375, "kind": "nav-collapse", "selector": "nav/header", "detail": "mobile menu trigger detected"})

    return {
        "schemaVersion": "0.1",
        "id": _run_id(url),
        "source": {"kind": "website", "url": url, "capturedAt": captured, "viewports": [{"name": "desktop", "width": 1280, "height": 900}, {"name": "mobile", "width": 375, "height": 667}]},
        "tokens": {"colors": colors, "typography": typography, "spacing": spacing, "radii": radii, "shadows": shadows, "borders": []},
        "structure": {"regions": [], "components": components},
        "motion": motion,
        "interactions": [],
        "responsive": responsive,
        "icons": icons,
        "warnings": data.get("warnings", []),
        "meta": meta,
    }


def generate_design_md(ddom: Dict[str, Any]) -> str:
    ddom = normalize_ddom(ddom)
    source = ddom["source"]
    tokens = ddom["tokens"]
    quality = ddom["quality"]
    source_url = source.get("url") or ""
    source_link = f"[{source_url}]({source_url})" if source_url else "unknown"
    lines = [
        "# D-DOM Design Reference",
        "",
        f"> Captured {source.get('capturedAt')} from {source_link}. Values are evidence-tagged as source, runtime, visual, or inferred.",
        "",
        "## Source",
        f"- Kind: `{source.get('kind', 'website')}`",
        f"- URL: {source_link}",
        f"- Captured at: `{source.get('capturedAt')}`",
        "- Viewports: " + (
            ", ".join(
                f"`{viewport.get('name', 'viewport')}` {viewport.get('width')}x{viewport.get('height')}"
                for viewport in source.get("viewports", [])
            ) or "none recorded"
        ),
        "",
        "## Quality",
        f"- Overall: `{quality['overall']:.2f}`",
        f"- Source/RUNTIME evidence share: `{quality['sourceEvidenceShare']:.2f}`",
        f"- Responsive coverage: `{quality['responsiveCoverage']:.2f}`",
        "",
        "## Colors",
        "| Role | Hex | Usage | Evidence | Confidence |",
        "| :--- | :--- | ---: | :--- | ---: |",
    ]
    for c in tokens["colors"]:
        value = c["value"]
        lines.append(f"| {value.get('role') or 'custom'} | `{value.get('hex')}` | {value.get('usageCount', 1)} | {c['evidence'].lower()} | {c['confidence']:.2f} |")
    lines.extend(["", "## Typography", "| Role | Family | Weight | Size | Line Height | Evidence |", "| :--- | :--- | ---: | ---: | :--- | :--- |"])
    for t in tokens["typography"]:
        v = t["value"]
        lines.append(f"| {v.get('role', 'text')} | {v.get('family')} | {v.get('weight')} | {v.get('sizePx')}px | {v.get('lineHeight')} | {t['evidence'].lower()} |")
    lines.extend(["", "## Spacing, Radii, Shadows"])
    lines.append("- Spacing scale: " + (", ".join(f"`{s['value']}px` ({s['evidence'].lower()}, {s['confidence']:.2f})" for s in tokens["spacing"]) or "none detected"))
    lines.append("- Radii: " + (", ".join(f"`{r['value']}px` ({r['evidence'].lower()}, {r['confidence']:.2f})" for r in tokens["radii"]) or "`0px` inferred"))
    lines.append("- Shadows: " + (", ".join(f"`{s['value']}` ({s['evidence'].lower()}, {s['confidence']:.2f})" for s in tokens["shadows"]) or "none detected"))
    if tokens["borders"]:
        lines.extend(["", "## Borders", "| Width | Style | Color | Evidence | Confidence |", "| ---: | :--- | :--- | :--- | ---: |"])
        for b in tokens["borders"]:
            v = b["value"]
            lines.append(f"| {v.get('widthPx')}px | {v.get('style')} | `{v.get('color')}` | {b['evidence'].lower()} | {b['confidence']:.2f} |")
    lines.extend(["", "## Structure"])
    for region in ddom["structure"].get("regions", []):
        lines.append(f"- Region `{region['value'].get('role')}` at `{region['value'].get('selector')}` ({region['evidence'].lower()})")
    for comp in ddom["structure"].get("components", []):
        lines.append(f"- Component `{comp['kind']}` x{comp['occurrences']} exemplar `{comp['exemplarSelector']}`")
        for name, wrapped in comp.get("styles", {}).items():
            lines.append(f"  - `{name}`: `{wrapped.get('value')}` ({wrapped.get('evidence', '').lower()}, {wrapped.get('confidence', 0):.2f})")
    lines.extend(["", "## Motion"])
    if ddom["motion"]:
        for m in ddom["motion"]:
            lines.append(f"- `{m['trigger']}` on `{m['target']}`: {m['durationMs']['value']}ms, {m['easing']['value']} via {m['mechanism']['value']} ({m['mechanism']['evidence'].lower()})")
            if m.get("from"):
                lines.append(f"  - from: `{json.dumps(m['from'], ensure_ascii=False)}`")
            if m.get("to"):
                lines.append(f"  - to: `{json.dumps(m['to'], ensure_ascii=False)}`")
    else:
        lines.append("- No measurable motion records detected.")
    lines.extend(["", "## Interactions"])
    if ddom["interactions"]:
        for interaction in ddom["interactions"]:
            lines.append(f"- `{interaction['state']}` on `{interaction['target']}` ({interaction['evidence'].lower()}, {interaction['confidence']:.2f})")
            lines.append(f"  - delta: `{json.dumps(interaction.get('styleDelta', {}), ensure_ascii=False)}`")
    else:
        lines.append("- No interaction state deltas detected.")
    lines.extend(["", "## Responsive"])
    for bp in ddom["responsive"].get("breakpoints", []):
        lines.append(f"- Breakpoint `{bp['value']}px` ({bp['evidence'].lower()})")
    for change in ddom["responsive"].get("changes", []):
        lines.append(f"- At `{change['at']}px`, `{change['selector']}`: {change['kind']} - {change['detail']}")
    lines.extend(["", "## Icons"])
    if ddom["icons"]:
        for icon in ddom["icons"]:
            lines.append(f"- `{icon['id']}`: {icon['format']} x{icon['occurrences']}, family `{icon['family']['value']}`, size `{icon['sizePx']['value']}px` ({icon['family']['evidence'].lower()})")
            if icon.get("viewBox"):
                lines.append(f"  - viewBox: `{icon['viewBox']}`")
            if icon.get("stroke"):
                lines.append(f"  - stroke: `{json.dumps(icon['stroke'], ensure_ascii=False)}`")
    else:
        lines.append("- No SVG or icon-font records detected.")
    lines.extend(["", "## Implementation Rules", "- Prefer measured values over aesthetic guesses.", "- Treat inferred values as lower-confidence hints.", "- Re-run `verify_clone` after implementation and fix category mismatches first."])
    if ddom.get("warnings"):
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {w}" for w in ddom["warnings"])
    lines.extend([
        "",
        "## Complete D-DOM JSON",
        "",
        "This appendix is intentionally complete so coding agents can use every fact the extractor found.",
        "",
        "```json",
        json.dumps(ddom, indent=2, ensure_ascii=False),
        "```",
    ])
    return "\n".join(lines)


def generate_agent_prompt(ddom: Dict[str, Any]) -> str:
    ddom = normalize_ddom(ddom)
    tokens = ddom["tokens"]
    css_lines = [":root {"]
    for c in tokens["colors"][:10]:
        v = c["value"]
        role = (v.get("role") or "color").replace("_", "-")
        css_lines.append(f"  --{role}: {v.get('hex')}; /* {c['evidence']} conf {c['confidence']:.2f} */")
    if tokens["spacing"]:
        css_lines.append(f"  --space-base: {tokens['spacing'][0]['value']}px;")
    if tokens["radii"]:
        css_lines.append(f"  --radius-primary: {tokens['radii'][0]['value']}px;")
    css_lines.append("}")
    prompt = ["# D-DOM Agent Blueprint", "", "Build from measured D-DOM facts. Do not invent colors, spacing, type, icon families, or motion values.", "", "## CSS Tokens", "```css", *css_lines, "```", "", "## Typography"]
    for t in tokens["typography"][:8]:
        v = t["value"]
        prompt.append(f"- {v.get('role')}: {v.get('family')}, {v.get('weight')} weight, {v.get('sizePx')}px, line-height {v.get('lineHeight')} ({t['evidence']})")
    prompt.extend(["", "## Components"])
    for comp in ddom["structure"].get("components", [])[:10]:
        prompt.append(f"- Implement `{comp['kind']}` matching exemplar `{comp['exemplarSelector']}` and styles: {_style_summary(comp.get('styles', {}))}")
    prompt.extend(["", "## Verification", "After building, run D-DOM `verify_clone` and fix every mismatch in descending category impact."])
    return "\n".join(prompt)


def verify_fidelity(source_ddom: Dict[str, Any], clone_ddom: Dict[str, Any]) -> Dict[str, Any]:
    source = normalize_ddom(source_ddom)
    clone = normalize_ddom(clone_ddom)
    mismatches: List[Dict[str, str]] = []
    color_score = _score_colors(source, clone, mismatches)
    type_score = _score_typography(source, clone, mismatches)
    spacing_score = _score_simple_values("spacing", source["tokens"]["spacing"], clone["tokens"]["spacing"], mismatches, "px")
    radii_score = _score_simple_values("radii", source["tokens"]["radii"], clone["tokens"]["radii"], mismatches, "px")
    component_score = _score_components(source, clone, mismatches)
    motion_score = _score_motion(source, clone, mismatches)
    responsive_score = _score_responsive(source, clone, mismatches)
    icon_score = _score_icons(source, clone, mismatches)
    by_category = {
        "colors": color_score,
        "typography": type_score,
        "spacing": round((spacing_score * 0.65 + radii_score * 0.35), 1),
        "components": component_score,
        "motion": motion_score,
        "responsive": responsive_score,
        "icons": icon_score,
    }
    weights = {"colors": 0.22, "typography": 0.22, "spacing": 0.14, "components": 0.18, "motion": 0.08, "responsive": 0.08, "icons": 0.08}
    fidelity = round(sum(by_category[k] * weights[k] for k in weights), 1)
    return {"fidelity": fidelity, "byCategory": by_category, "mismatches": mismatches[:30], "overall_fidelity": fidelity, "categories": {k.title(): v for k, v in by_category.items()}}


def _score_colors(source: Dict[str, Any], clone: Dict[str, Any], mismatches: List[Dict[str, str]]) -> float:
    src = [(c["value"].get("role") or c["value"].get("hex"), c["value"].get("hex")) for c in source["tokens"]["colors"]]
    cln_hex = [c["value"].get("hex") for c in clone["tokens"]["colors"]]
    if not src:
        return 100.0
    matches = 0
    for role, hex_value in src:
        nearest = min((_hex_distance(hex_value, h), h) for h in cln_hex)[1] if cln_hex else "missing"
        if nearest != "missing" and _hex_distance(hex_value, nearest) <= 18:
            matches += 1
        else:
            mismatches.append({"category": "colors", "target": str(role), "property": str(role), "expected": str(hex_value), "actual": str(nearest), "suggestedFix": f"Use color {hex_value} for {role}."})
    return round(matches / len(src) * 100, 1)


def _score_typography(source: Dict[str, Any], clone: Dict[str, Any], mismatches: List[Dict[str, str]]) -> float:
    src = source["tokens"]["typography"][:8]
    cln = clone["tokens"]["typography"][:12]
    if not src:
        return 100.0
    matches = 0
    for item in src:
        sv = item["value"]
        best = None
        for cand in cln:
            cv = cand["value"]
            if abs(float(cv.get("sizePx", 0)) - float(sv.get("sizePx", 0))) <= 2:
                best = cv
                break
        if best and int(best.get("weight", 0)) == int(sv.get("weight", 0)):
            matches += 1
        else:
            actual = f"{best.get('weight')} / {best.get('sizePx')}px" if best else "missing"
            mismatches.append({"category": "typography", "target": sv.get("role", "text"), "property": sv.get("role", "text"), "expected": f"{sv.get('weight')} / {sv.get('sizePx')}px", "actual": actual, "suggestedFix": f"Set {sv.get('role')} to font-weight {sv.get('weight')} and font-size {sv.get('sizePx')}px."})
    return round(matches / len(src) * 100, 1)


def _score_simple_values(category: str, src_items: List[Dict[str, Any]], clone_items: List[Dict[str, Any]], mismatches: List[Dict[str, str]], suffix: str) -> float:
    src = [float(i["value"]) for i in src_items if isinstance(i.get("value"), (int, float))]
    cln = [float(i["value"]) for i in clone_items if isinstance(i.get("value"), (int, float))]
    if not src:
        return 100.0
    matches = 0
    for value in src:
        if any(abs(value - c) <= 2 for c in cln):
            matches += 1
        else:
            mismatches.append({"category": category, "target": f"{category}-scale", "property": f"{category}-scale", "expected": f"{value:g}{suffix}", "actual": "missing", "suggestedFix": f"Add {value:g}{suffix} to the {category} scale."})
    return round(matches / len(src) * 100, 1)


def _score_components(source: Dict[str, Any], clone: Dict[str, Any], mismatches: List[Dict[str, str]]) -> float:
    src_counts = _component_counts(source)
    cln_counts = _component_counts(clone)
    if not src_counts:
        return 100.0
    matches = 0
    for kind, count in src_counts.items():
        actual = cln_counts.get(kind, 0)
        if actual == count:
            matches += 1
        elif actual > 0:
            matches += 0.5
            mismatches.append({"category": "components", "target": kind, "property": "occurrences", "expected": str(count), "actual": str(actual), "suggestedFix": f"Adjust `{kind}` count and styling to match the source."})
        else:
            mismatches.append({"category": "components", "target": kind, "property": "occurrences", "expected": str(count), "actual": "0", "suggestedFix": f"Implement `{kind}` components."})
    return round(matches / len(src_counts) * 100, 1)


def _score_motion(source: Dict[str, Any], clone: Dict[str, Any], mismatches: List[Dict[str, str]]) -> float:
    if not source["motion"]:
        return 100.0
    if not clone["motion"]:
        mismatches.append({"category": "motion", "target": "motion-records", "property": "records", "expected": str(len(source["motion"])), "actual": "0", "suggestedFix": "Recreate measured hover/load/scroll transitions."})
        return 0.0
    return round(min(len(source["motion"]), len(clone["motion"])) / len(source["motion"]) * 100, 1)


def _score_responsive(source: Dict[str, Any], clone: Dict[str, Any], mismatches: List[Dict[str, str]]) -> float:
    src_changes = source["responsive"].get("changes", [])
    cln_kinds = {c.get("kind") for c in clone["responsive"].get("changes", [])}
    if not src_changes:
        return 100.0
    matches = sum(1 for c in src_changes if c.get("kind") in cln_kinds)
    if matches < len(src_changes):
        mismatches.append({"category": "responsive", "target": "breakpoint-behavior", "property": "changes", "expected": ", ".join(c.get("kind", "") for c in src_changes), "actual": ", ".join(cln_kinds) or "none", "suggestedFix": "Match breakpoint layout changes and navigation collapse behavior."})
    return round(matches / len(src_changes) * 100, 1)


def _score_icons(source: Dict[str, Any], clone: Dict[str, Any], mismatches: List[Dict[str, str]]) -> float:
    src_count = sum(int(i.get("occurrences", 0)) for i in source.get("icons", []))
    cln_count = sum(int(i.get("occurrences", 0)) for i in clone.get("icons", []))
    if src_count == 0:
        return 100.0
    if cln_count == 0:
        mismatches.append({"category": "icons", "target": "iconography", "property": "count", "expected": str(src_count), "actual": "0", "suggestedFix": "Use inline SVG icons with matching size/stroke style."})
        return 0.0
    return round(min(src_count, cln_count) / max(src_count, cln_count) * 100, 1)


def _quality_report(colors: List[Dict[str, Any]], typography: List[Dict[str, Any]], spacing: List[Dict[str, Any]], motion: List[Dict[str, Any]], components: List[Dict[str, Any]], viewports: List[Dict[str, Any]]) -> Dict[str, Any]:
    sections = [bool(colors), bool(typography), bool(spacing), bool(components), bool(viewports)]
    all_facts = [*colors, *typography, *spacing]
    trusted = [f for f in all_facts if f.get("evidence") in {"SOURCE", "RUNTIME"}]
    source_share = len(trusted) / max(1, len(all_facts))
    motion_conf = sum(m.get("durationMs", {}).get("confidence", 0) for m in motion) / max(1, len(motion)) if motion else 0
    completeness = sum(sections) / len(sections)
    responsive = min(1.0, len(viewports) / 2) if viewports else 0
    component_coverage = min(1.0, len(components) / 6) if components else 0
    weights = {"extractionCompleteness": 0.3, "sourceEvidenceShare": 0.25, "responsiveCoverage": 0.15, "motionConfidence": 0.1, "componentCoverage": 0.2}
    overall = completeness * weights["extractionCompleteness"] + source_share * weights["sourceEvidenceShare"] + responsive * weights["responsiveCoverage"] + motion_conf * weights["motionConfidence"] + component_coverage * weights["componentCoverage"]
    return {"extractionCompleteness": round(completeness, 3), "sourceEvidenceShare": round(source_share, 3), "responsiveCoverage": round(responsive, 3), "motionConfidence": round(motion_conf, 3), "componentCoverage": round(component_coverage, 3), "overall": round(overall, 3), "weights": weights}


def _run_id(url: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", url or "run").strip("_").lower()[:36]
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"run_{clean}_{stamp}"


def _fallback_stack(family: str) -> List[str]:
    lowered = family.lower()
    if "inter" in lowered:
        return ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"]
    if "serif" in lowered and "sans" not in lowered:
        return ["Georgia", "Times New Roman", "serif"]
    return ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"]


def _duration_ms(value: str) -> int:
    value = str(value or "0s").split(",")[0].strip()
    try:
        if value.endswith("ms"):
            return int(float(value[:-2]))
        if value.endswith("s"):
            return int(float(value[:-1]) * 1000)
    except ValueError:
        return 0
    return 0


def _style_summary(styles: Dict[str, Dict[str, Any]]) -> str:
    parts = [f"{key}={wrapped.get('value')}" for key, wrapped in styles.items() if wrapped.get("value")]
    return ", ".join(parts) or "measured source styles"


def _component_counts(ddom: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for comp in ddom["structure"].get("components", []):
        counts[comp["kind"]] = counts.get(comp["kind"], 0) + int(comp.get("occurrences", 1))
    return counts


def _hex_distance(a: str, b: str) -> float:
    def rgb(hex_value: str) -> Tuple[int, int, int]:
        hex_value = (hex_value or "#000000").strip().lstrip("#")
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        return int(hex_value[0:2], 16), int(hex_value[2:4], 16), int(hex_value[4:6], 16)

    ar, ag, ab = rgb(a)
    br, bg, bb = rgb(b)
    return ((ar - br) ** 2 + (ag - bg) ** 2 + (ab - bb) ** 2) ** 0.5
