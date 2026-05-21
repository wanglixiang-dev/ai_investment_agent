from app.db.models import ResearchReportRecord


def format_report_as_markdown(record: ResearchReportRecord) -> str:
    lines = [
        f"# Investment Research Report: {record.ticker}",
        "",
        "## Metadata",
        "",
        f"- Report ID: {record.id}",
        f"- Ticker: {record.ticker}",
        f"- Horizon: {record.horizon}",
        f"- Risk Level: {record.risk_level}",
        f"- Created At: {record.created_at.isoformat()}",
        "",
        "## Executive Report",
        "",
        record.final_report.strip(),
        "",
        "## Data Sources",
        "",
        *_format_list(record.data_sources),
        "",
        "## Workflow Trace",
        "",
        *_format_steps(record.steps),
    ]

    if record.errors:
        lines.extend(
            [
                "",
                "## Errors",
                "",
                *_format_list(record.errors),
            ]
        )

    return "\n".join(lines).strip() + "\n"


def _format_list(values: list[str]) -> list[str]:
    if not values:
        return ["- None"]

    return [f"- {value}" for value in values]


def _format_steps(steps: list[dict]) -> list[str]:
    if not steps:
        return ["- No workflow steps recorded."]

    return [
        f"- `{step.get('name', 'unknown')}`: {step.get('status', 'unknown')} - "
        f"{step.get('message', '')}"
        for step in steps
    ]
