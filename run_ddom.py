"""D-DOM CLI Command Line Orchestrator.

Usage:
    python run_ddom.py <url>
    python run_ddom.py --source <source_url> --clone <clone_url>
"""

import sys
import os
import json
import argparse
from ddom_engine import extract_url, generate_design_md, generate_agent_prompt, verify_fidelity


def main():
    parser = argparse.ArgumentParser(description="D-DOM: Design Document Object Model CLI")
    parser.add_argument("url", nargs="?", help="Website URL to extract D-DOM from")
    parser.add_argument("--source", help="Source website URL for fidelity comparison")
    parser.add_argument("--clone", help="Clone website URL for fidelity comparison")
    parser.add_argument("--outdir", default="output", help="Output directory (default: output)")

    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    if args.source and args.clone:
        print("=" * 65)
        print("D-DOM FIDELITY VERIFICATION ENGINE")
        print("=" * 65)
        print(f"Source URL: {args.source}")
        print(f"Clone URL:  {args.clone}\n")

        print(">>> Extracting Source D-DOM...")
        src_path = os.path.join(args.outdir, "source_ddom.json")
        src_ddom = extract_url(args.source, src_path)

        print(">>> Extracting Clone D-DOM...")
        cln_path = os.path.join(args.outdir, "clone_ddom.json")
        cln_ddom = extract_url(args.clone, cln_path)

        print(">>> Comparing Design Systems & Computing Fidelity...")
        report = verify_fidelity(src_ddom, cln_ddom)
        rep_path = os.path.join(args.outdir, "fidelity_report.json")
        with open(rep_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print("\n" + "=" * 65)
        print(f"OVERALL FIDELITY SCORE: {report['overall_fidelity']}%")
        print("=" * 65)
        for cat, sc in report["categories"].items():
            print(f"  {cat.ljust(15)} : {sc}%")
        
        if report["mismatches"]:
            print("\nMismatches Detected:")
            for m in report["mismatches"]:
                print(f"  [{m['category']}] {m['property']}: Expected '{m['expected']}' != Actual '{m['actual']}'")
        else:
            print("\nNo critical design token mismatches detected!")

        print(f"\nReport saved to: {rep_path}")
        return

    if not args.url:
        parser.error("A target URL is required.")
    target_url = args.url
    print("=" * 65)
    print("D-DOM EXTRACTION STUDIO")
    print("=" * 65)
    print(f"Target URL: {target_url}\n")

    print("[Stage 1/6] Capturing page with headless browser...")
    print("[Stage 2/6] Extracting visual DNA (colors, typography, spacing)...")
    print("[Stage 3/6] Mapping UI components (buttons, inputs, icons)...")
    print("[Stage 4/6] Detecting runtime behavior & motion...")
    print("[Stage 5/6] Building evidence-tagged D-DOM object model...")

    ddom_file = os.path.join(args.outdir, "ddom.json")
    ddom = extract_url(target_url, ddom_file)

    print("[Stage 6/6] Generating design context & AI agent prompt...")
    design_md = generate_design_md(ddom)
    design_file = os.path.join(args.outdir, "DESIGN.md")
    with open(design_file, "w", encoding="utf-8") as f:
        f.write(design_md)

    agent_prompt = generate_agent_prompt(ddom)
    agent_file = os.path.join(args.outdir, "AGENT_PROMPT.md")
    with open(agent_file, "w", encoding="utf-8") as f:
        f.write(agent_prompt)

    print("\n" + "=" * 65)
    print("EXTRACTION COMPLETE")
    print("=" * 65)
    print(f"1. D-DOM JSON:    {ddom_file}")
    print(f"2. DESIGN.md:     {design_file}")
    print(f"3. Agent Prompt:  {agent_file}")
    print("=" * 65)


if __name__ == "__main__":
    main()
