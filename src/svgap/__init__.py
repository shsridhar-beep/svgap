"""SV-Gap: production-readiness evaluation for generated RTL.

Public library surface:

    import svgap

    report = svgap.evaluate("path/to/manifest.toml")
    if report.gap_member:
        ...

Everything exported here follows the same contract as the CLI: setup errors
raise, measurement outcomes (``unknown``, ``tool_error``) are reported, and a
structural ``pass`` means no configured finding - not verified safety.
"""

from svgap.api import evaluate
from svgap.backends.registry import BackendError, discover_backends, load_backend
from svgap.functional import run_functional
from svgap.manifest import Manifest, ManifestError, load_manifest
from svgap.model import CheckResult, EvaluationReport, Finding, FunctionalResult
from svgap.pilot import materialize_candidate
from svgap.resources import taskpack_metadata, taskpack_root
from svgap.study import summarize_reports
from svgap.validation import ReportValidationError, validate_report_payload

__version__ = "0.3.0a9"

__all__ = [
    "BackendError",
    "CheckResult",
    "EvaluationReport",
    "Finding",
    "FunctionalResult",
    "Manifest",
    "ManifestError",
    "ReportValidationError",
    "discover_backends",
    "evaluate",
    "load_backend",
    "load_manifest",
    "materialize_candidate",
    "run_functional",
    "summarize_reports",
    "taskpack_metadata",
    "taskpack_root",
    "validate_report_payload",
    "__version__",
]
