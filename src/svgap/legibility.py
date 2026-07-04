from __future__ import annotations

from typing import Any

from svgap.validation import validate_report_payload


def explain_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if "functional" in payload and "structural" in payload:
        return explain_evaluation_report(validate_report_payload(payload))
    if "verdict" in payload and "semantics" in payload:
        return explain_adjudication_report(payload)
    raise ValueError("unsupported report type for explanation")


def explain_evaluation_report(report: dict[str, Any]) -> dict[str, Any]:
    answered: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    unanswered: list[dict[str, str]] = []
    next_evidence: list[str] = []
    functional = report["functional"]
    structural = report["structural"]

    if functional["status"] == "pass":
        answered.append(
            {
                "question": "Did the supplied functional oracle accept the candidate?",
                "answer": "yes",
                "evidence": functional.get("imported_from") or "executed functional commands",
            }
        )
    elif functional["status"] in {"fail", "compile_error"}:
        failed.append(
            {
                "question": "Did the supplied functional oracle accept the candidate?",
                "answer": functional["status"],
                "evidence": str(functional.get("stderr") or "")[-500:],
            }
        )
        next_evidence.append("Resolve the functional failure before making a production-readiness claim.")
    else:
        unanswered.append(
            {
                "question": "Did the supplied functional oracle accept the candidate?",
                "reason": functional["status"],
            }
        )
        next_evidence.append("Supply or successfully execute a content-bound functional result.")

    if structural["status"] == "pass":
        answered.append(
            {
                "question": "Did the configured structural backend emit a failing finding?",
                "answer": "no",
                "evidence": f"{structural['backend']} {structural['backend_version']}",
            }
        )
        next_evidence.append(
            "Review backend coverage before treating a structural pass as evidence beyond configured rules."
        )
    elif structural["status"] == "fail":
        for finding in structural["findings"]:
            failed.append(
                {
                    "question": f"Does the candidate satisfy {finding['rule_id']}?",
                    "answer": "no",
                    "evidence": finding["message"],
                }
            )
        next_evidence.append(
            "Review the finding, repair the candidate, run an independent backend, or attach an approved adjudication."
        )
    else:
        reasons = structural.get("diagnostics", []) or [structural["status"]]
        for reason in reasons:
            unanswered.append(
                {
                    "question": "Does the candidate satisfy the configured structural rules?",
                    "reason": reason,
                }
            )
        if structural["status"] == "unknown":
            next_evidence.append("Supply missing design intent or use a backend that covers the submitted structure.")
        else:
            next_evidence.append("Resolve the structural tool failure and rerun without converting it to pass.")

    return {
        "schema_version": "1.0",
        "candidate_id": report["candidate_id"],
        "answered": answered,
        "failed": failed,
        "unanswered": unanswered,
        "next_evidence": list(dict.fromkeys(next_evidence)),
        "claim_boundary": (
            "This explanation reports what configured evidence establishes. "
            "It is not silicon signoff or evidence about unconfigured properties."
        ),
    }


def explain_adjudication_report(report: dict[str, Any]) -> dict[str, Any]:
    required = {
        "candidate_id",
        "verdict",
        "semantics",
        "instrumenter",
        "seed_budget",
        "seeds_completed",
        "calibration",
    }
    if not required.issubset(report):
        raise ValueError("adjudication report is missing required fields")
    answered: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    unanswered: list[dict[str, str]] = []
    next_evidence: list[str] = []
    verdict = report["verdict"]
    semantics = report["semantics"]
    if verdict == "hazard_demonstrated":
        reproducer = report.get("reproducer") or {}
        failed.append(
            {
                "question": "Did any observed trace diverge under the declared semantics?",
                "answer": "yes",
                "evidence": f"seed={reproducer.get('seed')} semantics={semantics.get('name')}",
            }
        )
        next_evidence.append("Reproduce the recorded seed and inspect whether the declared semantics match the intended production requirement.")
    elif verdict == "no_divergence_observed":
        answered.append(
            {
                "question": "Was divergence observed within the executed seed budget?",
                "answer": "no",
                "evidence": f"{report['seeds_completed']}/{report['seed_budget']} seeds completed",
            }
        )
        next_evidence.append("Increase coverage or use an independent method; no observed divergence is not a safety proof.")
    else:
        unanswered.append(
            {
                "question": "Does the candidate diverge under the declared semantics?",
                "reason": "; ".join(report.get("diagnostics", [])) or "inconclusive",
            }
        )
        next_evidence.append("Resolve calibration, instrumentation, or observation failures before interpreting the candidate.")
    if report["instrumenter"].get("mode") == "mock_prerecorded":
        next_evidence.append(
            "Prerecorded mock traces demonstrate the protocol only and cannot support a candidate-level hazard claim."
        )
    return {
        "schema_version": "1.0",
        "candidate_id": report["candidate_id"],
        "answered": answered,
        "failed": failed,
        "unanswered": unanswered,
        "next_evidence": list(dict.fromkeys(next_evidence)),
        "claim_boundary": "Adjudication conclusions are conditional on the declared digital perturbation and observation semantics.",
    }


def render_explanation(explanation: dict[str, Any]) -> str:
    lines = [f"candidate   {explanation['candidate_id']}"]
    for heading, key in (("ANSWERED", "answered"), ("FAILED", "failed"), ("UNANSWERED", "unanswered")):
        lines.append(heading)
        items = explanation[key]
        if not items:
            lines.append("  none")
        for item in items:
            detail = item.get("answer") or item.get("reason", "")
            lines.append(f"  - {item['question']} {detail}".rstrip())
            if item.get("evidence"):
                lines.append(f"    evidence: {item['evidence']}")
    lines.append("NEXT EVIDENCE")
    for item in explanation["next_evidence"]:
        lines.append(f"  - {item}")
    lines.append("CLAIM BOUNDARY")
    lines.append(f"  {explanation['claim_boundary']}")
    return "\n".join(lines) + "\n"
