#!/usr/bin/env python3
"""
security-scan.py

AST-based security scanner for Python files and regex-based scanner for
JS/TS files. Reports findings with file path, line number, severity,
and description.
"""

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    line: int
    severity: str  # HIGH, MEDIUM, LOW
    description: str

    def __str__(self) -> str:
        return f"  [{self.severity}] {self.file}:{self.line} - {self.description}"


@dataclass
class ScanResults:
    findings: List[Finding] = field(default_factory=list)

    def add(self, file: str, line: int, severity: str, description: str) -> None:
        self.findings.append(Finding(file, line, severity, description))

    def summary(self) -> dict:
        counts: dict = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Python AST visitor
# ---------------------------------------------------------------------------

DANGEROUS_CALLS = {
    "eval":          ("HIGH",   "Use of eval() can execute arbitrary code"),
    "exec":          ("HIGH",   "Use of exec() can execute arbitrary code"),
    "os.system":     ("HIGH",   "os.system() is vulnerable to shell injection"),
    "pickle.loads":  ("HIGH",   "pickle.loads() can deserialize malicious objects"),
    "pickle.load":   ("HIGH",   "pickle.load() can deserialize malicious objects"),
}


class SecurityVisitor(ast.NodeVisitor):
    """Walk a Python AST looking for dangerous patterns."""

    def __init__(self, filepath: str, results: ScanResults) -> None:
        self.filepath = filepath
        self.results = results

    # -- dangerous function calls ------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = self._resolve_name(node.func)
        if name in DANGEROUS_CALLS:
            severity, desc = DANGEROUS_CALLS[name]
            self.results.add(self.filepath, node.lineno, severity, desc)

        # subprocess with shell=True
        if name in ("subprocess.call", "subprocess.run", "subprocess.Popen"):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.results.add(
                        self.filepath, node.lineno, "HIGH",
                        f"{name}() called with shell=True -- risk of shell injection",
                    )

        # SQLAlchemy text() without bind parameters
        if name == "text" or name == "sqlalchemy.text":
            if node.args and isinstance(node.args[0], ast.JoinedStr):
                self.results.add(
                    self.filepath, node.lineno, "HIGH",
                    "SQL text() with f-string -- use bind parameters instead",
                )

        self.generic_visit(node)

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _resolve_name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts = []
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value  # type: ignore[assignment]
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return ".".join(reversed(parts))
        return ""


# ---------------------------------------------------------------------------
# Regex-based scanners
# ---------------------------------------------------------------------------

HARDCODED_SECRET_RE = re.compile(
    r"""(?:API_KEY|SECRET|PASSWORD|TOKEN|PRIVATE_KEY)\s*=\s*["'][^"']{4,}["']""",
    re.IGNORECASE,
)

JS_DANGEROUS_PATTERNS = [
    (re.compile(r"dangerouslySetInnerHTML"), "MEDIUM", "dangerouslySetInnerHTML can lead to XSS"),
    (re.compile(r"""javascript\s*:"""), "HIGH", "javascript: URL is an XSS vector"),
]


def scan_python_file(filepath: str, results: ScanResults) -> None:
    """Run AST and regex checks on a single Python file."""
    try:
        source = Path(filepath).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    # AST checks
    try:
        tree = ast.parse(source, filename=filepath)
        SecurityVisitor(filepath, results).visit(tree)
    except SyntaxError:
        pass  # skip files that cannot be parsed

    # Hardcoded secrets (regex)
    for lineno, line in enumerate(source.splitlines(), start=1):
        if HARDCODED_SECRET_RE.search(line):
            results.add(filepath, lineno, "MEDIUM", "Possible hardcoded secret detected")


def scan_js_ts_file(filepath: str, results: ScanResults) -> None:
    """Run regex checks on a single JS/TS file."""
    try:
        source = Path(filepath).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    for lineno, line in enumerate(source.splitlines(), start=1):
        for pattern, severity, description in JS_DANGEROUS_PATTERNS:
            if pattern.search(line):
                results.add(filepath, lineno, severity, description)

        if HARDCODED_SECRET_RE.search(line):
            results.add(filepath, lineno, "MEDIUM", "Possible hardcoded secret detected")


# ---------------------------------------------------------------------------
# Directory walker
# ---------------------------------------------------------------------------

PYTHON_EXTENSIONS = {".py"}
JS_TS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}


def scan_directory(directory: str, results: ScanResults) -> None:
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            filepath = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1]

            if ext in PYTHON_EXTENSIONS:
                scan_python_file(filepath, results)
            elif ext in JS_TS_EXTENSIONS:
                scan_js_ts_file(filepath, results)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Lightweight security scanner for Python and JS/TS files.")
    parser.add_argument("directory", help="Root directory to scan")
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"ERROR: {args.directory} is not a valid directory", file=sys.stderr)
        sys.exit(2)

    results = ScanResults()
    scan_directory(args.directory, results)

    # -- Report ------------------------------------------------------------
    print("=" * 60)
    print("  Security Scan Results")
    print("=" * 60)

    if not results.findings:
        print("\n  No findings. All clear!\n")
        sys.exit(0)

    for finding in sorted(results.findings, key=lambda f: (f.severity, f.file, f.line)):
        print(finding)

    summary = results.summary()
    print("\n" + "-" * 60)
    print("  Summary")
    print("-" * 60)
    print(f"  HIGH:   {summary['HIGH']}")
    print(f"  MEDIUM: {summary['MEDIUM']}")
    print(f"  LOW:    {summary['LOW']}")
    print(f"  TOTAL:  {sum(summary.values())}")
    print("-" * 60)

    if summary["HIGH"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
