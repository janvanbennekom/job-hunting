"""Render aggregate-only public status HTML."""

from __future__ import annotations

from html import escape

from jobhunter.application.display_labels import (
    label_eligibility_status,
    label_lifecycle_status,
)
from jobhunter.application.review.dtos import DashboardSummaryView


def render_public_status_html(summary: DashboardSummaryView) -> str:
    lifecycle_rows = _table_rows(
        summary.by_lifecycle,
        lambda code: label_lifecycle_status(code),
    )
    eligibility_rows = _table_rows(
        summary.by_eligibility,
        lambda code: label_eligibility_status(code),
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>JobHunter — Status</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      line-height: 1.5;
    }}
    body {{
      margin: 0;
      background: #0f172a;
      color: #e2e8f0;
      padding: 2rem 1rem;
    }}
    main {{
      max-width: 52rem;
      margin: 0 auto;
    }}
    h1 {{ font-size: 1.75rem; margin-bottom: 0.25rem; }}
    .lead {{ color: #94a3b8; margin-bottom: 2rem; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    .metric {{
      background: #1e293b;
      border-radius: 0.5rem;
      padding: 1rem;
      text-align: center;
    }}
    .metric .value {{ font-size: 1.75rem; font-weight: 700; }}
    .metric .label {{ color: #94a3b8; font-size: 0.875rem; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 1.5rem;
      background: #1e293b;
      border-radius: 0.5rem;
      overflow: hidden;
    }}
    th, td {{
      padding: 0.6rem 1rem;
      text-align: left;
      border-bottom: 1px solid #334155;
    }}
    th {{ color: #94a3b8; font-weight: 600; }}
    .footnote {{ color: #64748b; font-size: 0.875rem; margin-top: 2rem; }}
    a {{ color: #60a5fa; }}
  </style>
</head>
<body>
  <main>
    <h1>JobHunter</h1>
    <p class="lead">Automated discovery and assessment of international consultancy opportunities.</p>
    <div class="metrics">
      {_metric(summary.total_opportunities, "Opportunities")}
      {_metric(summary.actionable_count, "Actionable")}
      {_metric(summary.production_assessed_count, "Assessed")}
      {_metric(summary.production_ranked_count, "Ranked")}
    </div>
    <h2>Lifecycle</h2>
    <table>
      <thead><tr><th>Status</th><th>Count</th></tr></thead>
      <tbody>{lifecycle_rows}</tbody>
    </table>
    <h2>Eligibility</h2>
    <table>
      <thead><tr><th>Status</th><th>Count</th></tr></thead>
      <tbody>{eligibility_rows}</tbody>
    </table>
    <p class="footnote">Statistics reflect the current JobHunter opportunity database.
      Operator access: <a href="/app/">sign in</a>.</p>
  </main>
</body>
</html>"""


def _metric(value: int, label: str) -> str:
    return (
        f'<div class="metric"><div class="value">{int(value)}</div>'
        f'<div class="label">{escape(label)}</div></div>'
    )


def _table_rows(
    counts: dict[str, int],
    label_fn,
) -> str:
    if not counts:
        return '<tr><td colspan="2">No data yet.</td></tr>'
    rows = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    parts: list[str] = []
    for code, count in rows:
        label = escape(label_fn(code))
        parts.append(f"<tr><td>{label}</td><td>{int(count)}</td></tr>")
    return "\n".join(parts)
