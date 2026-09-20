from ddom_engine import normalize_ddom, verify_fidelity
from ddom_schema import DDOM, FidelityReport, MismatchItem


def compare_ddom(source_ddom: DDOM, clone_ddom: DDOM) -> FidelityReport:
    """Compare two canonical D-DOM objects using the shared fidelity loop."""
    report = verify_fidelity(source_ddom.to_dict(), clone_ddom.to_dict())
    return FidelityReport(
        fidelity=report["fidelity"],
        byCategory=report["byCategory"],
        mismatches=[
            MismatchItem(
                category=m["category"],
                target=m.get("target") or m.get("property", ""),
                expected=m["expected"],
                actual=m["actual"],
                suggestedFix=m.get("suggestedFix", ""),
            )
            for m in report["mismatches"]
        ],
    )


def compare_dicts(source_ddom: dict, clone_ddom: dict) -> dict:
    """Convenience function for callers that work with raw dictionaries."""
    return verify_fidelity(normalize_ddom(source_ddom), normalize_ddom(clone_ddom))
