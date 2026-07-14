#!/usr/bin/env python3
"""Canary retrieval checks for critical intents.

Fails with exit code 1 when expected source files are not present in top-k retrieval.
Use this in CI after indexing to detect retrieval drift.
"""

from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.retrieval.semantic_search import retrieval_diagnostics


@dataclass(frozen=True)
class CanaryCase:
    name: str
    project_id: str
    audience: str
    query: str
    expected_source_substrings: tuple[str, ...]
    expected_chunk_prefix: str | None = None
    k: int = 8


CASES = (
    CanaryCase(
        name="tb_definition_general",
        project_id="tb",
        audience="general",
        query="what is tb",
        expected_source_substrings=("FAQ.md",),
        expected_chunk_prefix="general_",
    ),
    CanaryCase(
        name="tb_register_patient_clinicians",
        project_id="tb",
        audience="clinicians",
        query="How can i register a patient",
        expected_source_substrings=("02-nurse-user-manual.md",),
        expected_chunk_prefix="clinicians_",
    ),
)


def _contains_expected(sources: list[str], expected_substrings: tuple[str, ...]) -> bool:
    for src in sources:
        for expected in expected_substrings:
            if expected in src:
                return True
    return False


def main() -> int:
    failures: list[str] = []

    for case in CASES:
        diag = retrieval_diagnostics(
            case.query,
            project_id=case.project_id,
            audience=case.audience,
            k=case.k,
        )
        top_sources = diag.get("top_source_files", [])
        top_chunk_ids = diag.get("top_chunk_ids", [])
        ok = _contains_expected(top_sources, case.expected_source_substrings)
        prefix_ok = True
        if case.expected_chunk_prefix and top_chunk_ids:
            prefix_ok = any(str(chunk_id).startswith(case.expected_chunk_prefix) for chunk_id in top_chunk_ids)

        print(f"\n[CANARY] {case.name}")
        print(f"  query: {case.query}")
        print(f"  audience: {case.audience}")
        print(f"  top_chunk_ids: {top_chunk_ids}")
        print(f"  top_sources: {top_sources}")
        print(f"  expected_any: {case.expected_source_substrings}")
        print(f"  expected_prefix: {case.expected_chunk_prefix}")
        print(f"  status: {'PASS' if ok and prefix_ok else 'FAIL'}")

        if not ok or not prefix_ok:
            failures.append(case.name)

    if failures:
        print(f"\nCanary retrieval checks failed: {', '.join(failures)}")
        return 1

    print("\nAll canary retrieval checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
