"""D-DOM CLI Orchestrator: Web / Screenshot -> D-DOM -> DESIGN.md -> Fidelity Loop.

Usage:
    # Single website analysis
    python run_ddom_cli.py https://example.com

    # Fidelity verification (source vs clone)
    python run_ddom_cli.py https://example.com --clone https://my-clone.vercel.app
"""

import os
import sys
import argparse
from ddom_analyzer import analyze_url, analyze_image
from ddom_generator import generate_design_md
from ddom_comparator import compare_ddom


def run_ddom_pipeline(source: str, clone: str = None, output_dir: str = "output"):
    os.makedirs(output_dir, exist_ok=True)
    print("=" * 60)
    print("D-DOM — DESIGN DOCUMENT OBJECT MODEL PIPELINE")
    print("=" * 60)
    
    if source.startswith("http://") or source.startswith("https://"):
        print(f"[Step 1/3] Extracting D-DOM from Website URL: {source}...")
        ddom_source = analyze_url(source)
    else:
        print(f"[Step 1/3] Extracting D-DOM from Image File: {source}...")
        ddom_source = analyze_image(source)

    source_json_path = os.path.join(output_dir, "ddom.json")
    ddom_source.save(source_json_path)
    print(f"  ✓ Extracted {len(ddom_source.tokens.colors)} color token(s)")
    print(f"  ✓ Extracted {len(ddom_source.tokens.typography)} typography token(s)")
    print(f"  ✓ Saved D-DOM JSON: {source_json_path}")

    print("\n[Step 2/3] Generating AGENT context (DESIGN.md)...")
    design_md = generate_design_md(ddom_source)
    design_md_path = os.path.join(output_dir, "DESIGN.md")
    with open(design_md_path, "w", encoding="utf-8") as f:
        f.write(design_md)
    print(f"  ✓ Saved DESIGN.md: {design_md_path}")

    fidelity_report = None
    if clone:
        print(f"\n[Step 3/3] Running Fidelity Verification Loop against Clone: {clone}...")
        ddom_clone = analyze_url(clone)
        clone_json_path = os.path.join(output_dir, "ddom_clone.json")
        ddom_clone.save(clone_json_path)
        
        fidelity_report = compare_ddom(ddom_source, ddom_clone)
        print(f"  ✓ Overall Fidelity Score: {fidelity_report.fidelity}%")
        print(f"  ✓ Category Breakdown: {fidelity_report.byCategory}")
        if fidelity_report.mismatches:
            print(f"  ✓ Found {len(fidelity_report.mismatches)} mismatch(es):")
            for m in fidelity_report.mismatches:
                print(f"    - [{m.category}] target='{m.target}' expected='{m.expected}' actual='{m.actual}' | fix='{m.suggestedFix}'")
        else:
            print("  ✓ 100% Fidelity Match! No mismatches found.")
    else:
        print("\n[Step 3/3] Single target extraction complete (no clone URL specified).")

    print("=" * 60)
    print("D-DOM PIPELINE COMPLETED")
    print("=" * 60)
    print(f"1. D-DOM JSON: {source_json_path}")
    print(f"2. DESIGN.md:  {design_md_path}")
    if fidelity_report:
        print(f"3. Fidelity Score: {fidelity_report.fidelity}%")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="D-DOM Extraction and Fidelity Verification CLI")
    parser.add_argument("source", help="Website URL (e.g. https://example.com) or local image file path")
    parser.add_argument("--clone", default=None, help="Generated / Clone Website URL for Fidelity Verification")
    parser.add_argument("--output-dir", default="output", help="Output directory for artifacts")

    args = parser.parse_args()
    run_ddom_pipeline(source=args.source, clone=args.clone, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
