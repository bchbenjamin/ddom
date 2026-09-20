from typing import Dict, List
from ddom_schema import DDOM, FidelityReport, MismatchItem


def compare_ddom(source_ddom: DDOM, clone_ddom: DDOM) -> FidelityReport:
    """Deterministically compare source D-DOM and clone D-DOM to compute fidelity score and mismatches."""
    mismatches: List[MismatchItem] = []
    by_category: Dict[str, float] = {}

    # 1. Colors Comparison
    source_colors = [c.value.upper() for c in source_ddom.tokens.colors]
    clone_colors = [c.value.upper() for c in clone_ddom.tokens.colors]
    
    color_matches = 0
    total_source_colors = max(1, len(source_colors))
    
    for sc in source_colors:
        if sc in clone_colors:
            color_matches += 1
        else:
            mismatches.append(MismatchItem(
                category="colors",
                target="theme-color",
                expected=sc,
                actual=clone_colors[0] if clone_colors else "none",
                suggestedFix=f"add CSS color rule: {sc}"
            ))
            
    by_category["colors"] = round((color_matches / total_source_colors) * 100.0, 1)

    # 2. Typography Comparison
    source_typo_map = {t.element: t for t in source_ddom.tokens.typography if t.element}
    clone_typo_map = {t.element: t for t in clone_ddom.tokens.typography if t.element}
    
    typo_matches = 0
    total_typo_targets = max(1, len(source_typo_map))
    
    for tag, src_t in source_typo_map.items():
        exp_weight = src_t.fontWeight or "400"
        exp_size = src_t.fontSize or "16px"
        exp_str = f"{exp_weight} / {exp_size}"
        
        if tag in clone_typo_map:
            cl_t = clone_typo_map[tag]
            act_weight = cl_t.fontWeight or "400"
            act_size = cl_t.fontSize or "16px"
            act_str = f"{act_weight} / {act_size}"
            
            if exp_weight == act_weight and exp_size == act_size:
                typo_matches += 1
            else:
                typo_matches += 0.5
                mismatches.append(MismatchItem(
                    category="typography",
                    target=tag,
                    expected=exp_str,
                    actual=act_str,
                    suggestedFix=f"font-weight: {exp_weight}; font-size: {exp_size};"
                ))
        else:
            mismatches.append(MismatchItem(
                category="typography",
                target=tag,
                expected=exp_str,
                actual="not specified",
                suggestedFix=f"add selector '{tag}' with font-weight:{exp_weight}; font-size:{exp_size};"
            ))
            
    by_category["typography"] = round((typo_matches / total_typo_targets) * 100.0, 1)

    # 3. Spacing Scale Comparison
    src_spacing = set(s.value for s in source_ddom.tokens.spacing)
    cl_spacing = set(s.value for s in clone_ddom.tokens.spacing)
    
    common_spacing = src_spacing.intersection(cl_spacing)
    spacing_score = (len(common_spacing) / max(1, len(src_spacing))) * 100.0
    by_category["spacing"] = round(spacing_score, 1)
    
    missing_spacing = src_spacing - cl_spacing
    for ms in missing_spacing:
        mismatches.append(MismatchItem(
            category="spacing",
            target="spacing-scale",
            expected=ms,
            actual="missing",
            suggestedFix=f"include spacing token {ms} in padding/margin scale"
        ))

    # 4. Component Structure Comparison
    src_comps = {c.name: c.count for c in source_ddom.structure.components}
    cl_comps = {c.name: c.count for c in clone_ddom.structure.components}
    
    comp_matches = 0
    total_src_comps = max(1, len(src_comps))
    
    for c_name, count in src_comps.items():
        if c_name in cl_comps:
            if cl_comps[c_name] == count:
                comp_matches += 1
            else:
                comp_matches += 0.5
                mismatches.append(MismatchItem(
                    category="components",
                    target=c_name,
                    expected=f"count: {count}",
                    actual=f"count: {cl_comps[c_name]}",
                    suggestedFix=f"adjust element count for {c_name} to match expected {count}"
                ))
        else:
            mismatches.append(MismatchItem(
                category="components",
                target=c_name,
                expected=f"count: {count}",
                actual="missing",
                suggestedFix=f"implement component `{c_name}`"
            ))
            
    by_category["components"] = round((comp_matches / total_src_comps) * 100.0, 1)

    # 5. Icons & Responsive
    src_icons = sum(i.count for i in source_ddom.icons)
    cl_icons = sum(i.count for i in clone_ddom.icons)
    icon_score = 100.0 if (src_icons == cl_icons or (src_icons > 0 and cl_icons > 0)) else 50.0
    by_category["icons"] = round(icon_score, 1)
    if src_icons > 0 and cl_icons == 0:
        mismatches.append(MismatchItem(
            category="icons",
            target="svg-icons",
            expected=f"{src_icons} icons",
            actual="0 icons",
            suggestedFix="add SVG iconography elements"
        ))

    # Overall weighted fidelity calculation
    weights = {
        "colors": 0.25,
        "typography": 0.30,
        "spacing": 0.15,
        "components": 0.20,
        "icons": 0.10
    }
    
    total_score = sum(by_category[cat] * weights[cat] for cat in weights if cat in by_category)
    fidelity_score = round(total_score, 1)

    return FidelityReport(
        fidelity=fidelity_score,
        byCategory=by_category,
        mismatches=mismatches
    )
