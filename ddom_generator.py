from ddom_schema import DDOM


def generate_design_md(ddom: DDOM) -> str:
    """Generate concise human-readable DESIGN.md from structured D-DOM object."""
    lines = []
    lines.append("# Design System")
    lines.append("")
    lines.append(f"**Source**: `{ddom.source.url}` ({ddom.source.kind.upper()})")
    lines.append(f"**Viewport**: `{ddom.source.viewport.width}x{ddom.source.viewport.height}` | **Captured**: `{ddom.source.capturedAt}`")
    lines.append("")
    
    # Evidence section
    lines.append("## Evidence")
    lines.append("- **SOURCE**: Deterministically extracted from source code / CSS tokens.")
    lines.append("- **RUNTIME**: Measured from browser layout rendering pipeline.")
    lines.append("- **VISUAL**: Forensic pixel-level spatial decomposition.")
    lines.append("- **INFERRED**: Algorithmic estimation / geometric pattern matching.")
    lines.append("")
    
    # Colors section
    lines.append("## Colors")
    if ddom.tokens.colors:
        for c in ddom.tokens.colors:
            name_str = f" — {c.name}" if c.name else ""
            origin_str = f" ({c.origin})" if c.origin else ""
            lines.append(f"- `{c.value}`{name_str} — **{c.evidence}** — confidence {c.confidence:.2f}{origin_str}")
    else:
        lines.append("*No explicit color tokens detected.*")
    lines.append("")
    
    # Typography section
    lines.append("## Typography")
    if ddom.tokens.typography:
        for t in ddom.tokens.typography:
            elem = f"`{t.element}`: " if t.element else ""
            details = f"{t.fontWeight or '400'} / {t.fontSize or '16px'} / {t.fontFamily or 'Inter, sans-serif'}"
            lines.append(f"- {elem}{details} — **{t.evidence}** — confidence {t.confidence:.2f}")
    else:
        lines.append("*No explicit typography tokens detected.*")
    lines.append("")
    
    # Spacing section
    lines.append("## Spacing")
    if ddom.tokens.spacing:
        vals = ", ".join([f"`{s.value}`" for s in ddom.tokens.spacing])
        ev = ddom.tokens.spacing[0].evidence if ddom.tokens.spacing else "SOURCE"
        conf = ddom.tokens.spacing[0].confidence if ddom.tokens.spacing else 0.95
        lines.append(f"Observed spacing scale: {vals} — **{ev}** — confidence {conf:.2f}")
    else:
        lines.append("*No explicit spacing scale detected.*")
    lines.append("")
    
    # Border Radii & Shadows
    if ddom.tokens.radii:
        radii_vals = ", ".join([f"`{r.value}`" for r in ddom.tokens.radii])
        lines.append(f"**Border Radii Scale**: {radii_vals}")
    if ddom.tokens.shadows:
        shadow_vals = "; ".join([f"`{sh.value}`" for sh in ddom.tokens.shadows])
        lines.append(f"**Box Shadows**: {shadow_vals}")
    if ddom.tokens.radii or ddom.tokens.shadows:
        lines.append("")

    # Components section
    lines.append("## Components")
    if ddom.structure.components or ddom.structure.regions:
        for r in ddom.structure.regions:
            lines.append(f"- **Region**: `{r.name}` (count: {r.count}) — **{r.evidence}** — confidence {r.confidence:.2f}")
        for comp in ddom.structure.components:
            lines.append(f"- **Component**: `{comp.name}` (count: {comp.count}, type: `{comp.type}`) — **{comp.evidence}** — confidence {comp.confidence:.2f}")
    else:
        lines.append("*No major reusable components detected.*")
    lines.append("")
    
    # Motion section
    lines.append("## Motion")
    if ddom.motion:
        for m in ddom.motion:
            duration_str = f" ({m.duration})" if m.duration else ""
            lines.append(f"- `{m.name}`{duration_str} — **{m.evidence}** — confidence {m.confidence:.2f}")
    else:
        lines.append("None observed.")
    lines.append("")
    
    # Responsive section
    lines.append("## Responsive")
    if ddom.responsive:
        for r in ddom.responsive:
            lines.append(f"- Breakpoint `{r.breakpoint}` — **{r.evidence}** — confidence {r.confidence:.2f}")
    else:
        lines.append("None observed.")
    lines.append("")
    
    # Iconography section
    lines.append("## Iconography")
    if ddom.icons:
        for ico in ddom.icons:
            lines.append(f"- `{ico.type.upper()}` icons detected (count: {ico.count}) — **{ico.evidence}** — confidence {ico.confidence:.2f}")
    else:
        lines.append("None observed.")
    lines.append("")

    return "\n".join(lines)
