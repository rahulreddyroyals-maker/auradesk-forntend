"""Static regression guard: no backend source file should log raw exception interpolation (f-string with {exc}) or obvious content variables — this is a cheap grep-based check, not a substitute for careful review, but it catches the exact regression pattern found and fixed in this security pass."""
import pathlib
import re

BACKEND_APP_DIR = pathlib.Path(__file__).resolve().parents[2] / "app"

# Patterns that indicate a raw exception or content variable is being
# interpolated directly into a print/log call — exactly the mistake
# fixed in voice_pipeline.py, tools.py, social.py, and
# followup_scheduler.py during this security pass.
RISKY_PATTERNS = [
    re.compile(r'print\(f".*\{exc\}"'),
    re.compile(r'print\(f".*\{.*message.*\}"', re.IGNORECASE),
    re.compile(r'print\(f".*\{.*content.*\}"', re.IGNORECASE),
    re.compile(r'print\(f".*\{.*reply.*\}"', re.IGNORECASE),
]


def test_no_raw_exception_or_content_interpolation_in_print_statements():
    violations = []
    for py_file in BACKEND_APP_DIR.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        if py_file.name == "safe_logging.py":
            # This module's own docstring documents the anti-pattern as
            # an example of what NOT to do — intentional, not a violation.
            continue
        text = py_file.read_text()
        for pattern in RISKY_PATTERNS:
            if pattern.search(text):
                violations.append(f"{py_file.relative_to(BACKEND_APP_DIR)}: matched {pattern.pattern}")

    assert not violations, "Found risky log interpolation patterns:\n" + "\n".join(violations)


def test_safe_logging_module_never_includes_str_of_exception():
    """redact_exception must return only the type name, never the exception's string representation (which can echo request/response bodies)."""
    from app.core.safe_logging import redact_exception

    exc = ValueError("this could theoretically contain a patient's message text")
    result = redact_exception(exc)
    assert result == "ValueError"
    assert "patient" not in result
