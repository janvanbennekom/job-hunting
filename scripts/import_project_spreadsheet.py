"""Import professional project data from the structured XLSX workbook."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        import os

        os.environ.setdefault(key.strip(), value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import Project / ExperienceTypes worksheets into PostgreSQL."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("docs/2 model_instances - postgres.xlsx"),
        help="Path to the project spreadsheet (default: docs/2 model_instances - postgres.xlsx)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes (default: dry-run only)",
    )
    parser.add_argument(
        "--purge-spreadsheet-assignments",
        action="store_true",
        help=(
            "Delete assignments and assignment-capability links owned by this "
            "spreadsheet source (keeps ProfileDocument and Capabilities). "
            "Use before re-import when assignment identity rules change."
        ),
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    _load_env(root / ".env")

    if not args.source.exists():
        print(f"Source workbook not found: {args.source}", file=sys.stderr)
        return 1

    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )
    from jobhunter.infrastructure.importers.project_spreadsheet import (
        ProjectSpreadsheetImporter,
        purge_spreadsheet_assignments,
    )

    engine = create_engine_from_settings()
    session_factory = create_session_factory(engine)
    try:
        with session_scope(session_factory) as session:
            if args.purge_spreadsheet_assignments:
                purge = purge_spreadsheet_assignments(session, args.source)
                print(
                    f"Purge source: {purge.source_reference}\n"
                    f"ProfileDocument id: {purge.profile_document_id}\n"
                    f"ProfileDocuments kept: {purge.profile_documents}\n"
                    f"Capabilities kept: {purge.capabilities}\n"
                    f"Assignments deleted: {purge.assignments_deleted}\n"
                    f"AssignmentCapabilities deleted: "
                    f"{purge.assignment_capabilities_deleted}"
                )
                if not args.apply:
                    return 0
            importer = ProjectSpreadsheetImporter(session)
            report = importer.run(args.source, apply=args.apply)
            for line in report.summary_lines():
                print(line)
            if report.has_errors():
                return 1
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
