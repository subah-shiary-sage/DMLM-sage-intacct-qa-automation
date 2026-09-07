"""
report.py — Standalone HTML regression report.

Reuses the CSS and section skeleton of the hand-built reports already in
Regression/ (stat cards, coverage table, per-scenario table, defects, remaining
work; light + dark via prefers-color-scheme) so generated output is visually
consistent with what's already there.

All counts come from the live status columns via workbook.count_statuses —
never from the workbook's cached Summary numbers, which go stale.
"""

from __future__ import annotations

import datetime as _dt
import html
from pathlib import Path
from typing import Iterable, Sequence

from openpyxl.workbook.workbook import Workbook

from . import workbook as wbmod
from .workbook import TestRow

DEFAULT_OUTPUT = Path("Regression/LME_Regression_Report.html")

# Copied verbatim from Regression/LME_Untested_Execution_Report.html so
# generated reports match the hand-built ones.
CSS = """
:root{--bd:#e3e6ea;--mut:#5b6770;--pass:#1f7a3d;--passbg:#e8f5ec;--fail:#b3261e;--failbg:#fdecea;--na:#5b6770;--nabg:#eef0f2;--tbt:#8a6100;--tbtbg:#fff6e0}
*{box-sizing:border-box}body{margin:0;padding:32px;font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1a1f24;background:#fff;max-width:1200px;margin-inline:auto}
h1{font-size:26px;margin:0 0 6px}h2{font-size:18px;margin:32px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--bd)}
.meta{color:var(--mut);margin:0 0 22px;font-size:14px}
.cards{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0 6px}
.card{flex:1 1 150px;border:1px solid var(--bd);border-radius:10px;padding:14px 16px;background:#fafbfc}
.card .n{font-size:28px;font-weight:650;line-height:1}.card .l{color:var(--mut);font-size:13px;margin-top:4px}
.card.pass{background:var(--passbg);border-color:#bfe3cb}.card.pass .n{color:var(--pass)}
.card.fail{background:var(--failbg);border-color:#f3c9c5}.card.fail .n{color:var(--fail)}
.card.tbt{background:var(--tbtbg);border-color:#f0dca8}.card.tbt .n{color:var(--tbt)}
.tablewrap{overflow-x:auto;border:1px solid var(--bd);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:14px;min-width:820px}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--bd);vertical-align:top}
th{background:#f5f7f9;font-weight:600}tr:last-child td{border-bottom:0}
td.pass{color:var(--pass);background:var(--passbg);font-weight:600;white-space:nowrap}
td.fail{color:var(--fail);background:var(--failbg);font-weight:600;white-space:nowrap}
td.na{color:var(--na);background:var(--nabg);font-weight:600;white-space:nowrap}
td.tbt{color:var(--tbt);background:var(--tbtbg);font-weight:600;white-space:nowrap}
ul{padding-left:20px}li{margin:6px 0}code{background:#eef0f2;padding:1px 5px;border-radius:4px;font-size:13px}
.banner{border:1px solid #f0dca8;background:var(--tbtbg);color:var(--tbt);border-radius:10px;padding:12px 16px;margin:0 0 18px;font-weight:600}
@media(prefers-color-scheme:dark){body{background:#15181b;color:#e6e9ec}th{background:#1e2226}.card{background:#1b1f23;border-color:#2c3238}
.tablewrap,td,th{border-color:#2c3238}h2{border-color:#2c3238}code{background:#22272b}
.card.pass{background:#12301d;border-color:#1f5133}.card.fail{background:#331512;border-color:#5e2620}.card.tbt{background:#332a10;border-color:#5c4a17}
td.pass{background:#12301d;color:#7fd6a0}td.fail{background:#331512;color:#f3a49c}td.na{background:#22272b;color:#9aa5ae}td.tbt{background:#332a10;color:#e5c377}}
"""

_STATUS_CLASS = {
    wbmod.STATUS_PASSED: "pass",
    wbmod.STATUS_FAILED: "fail",
    wbmod.STATUS_UNTESTED: "na",
    wbmod.STATUS_TO_BE_TESTED: "tbt",
}


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _status_cell(status: str | None) -> str:
    label = (status or "").strip() or "—"
    return f'<td class="{_STATUS_CLASS.get(label, "na")}">{_esc(label)}</td>'


def generate(
    wb: Workbook,
    *,
    output_path: Path = DEFAULT_OUTPUT,
    module_name: str = "",
    environment_line: str = "",
    executed_rows: Sequence[TestRow] = (),
    defects: Sequence[dict] = (),
    skipped: Sequence[TestRow] = (),
    remaining_notes: Iterable[str] = (),
    run_timestamp: str | None = None,
    dry_run: bool = False,
) -> Path:
    """
    Write the report and return its path.

    ``defects`` entries are dicts with keys: bug_no, title, area, status,
    screenshot (all optional except title).
    """
    output_path = Path(output_path)
    stamp = run_timestamp or _dt.datetime.now().isoformat(timespec="seconds")

    coverage: list[tuple[str, dict]] = [
        (name, wbmod.count_statuses(wb, name)) for name in wbmod.SUMMARY_SHEET_ORDER
    ]
    tot_items = tot_pass = tot_fail = tot_open = 0
    for _, c in coverage:
        tot_items += sum(c[s] for s in wbmod.VALID_STATUSES) + c["(blank)"]
        tot_pass += c[wbmod.STATUS_PASSED]
        tot_fail += c[wbmod.STATUS_FAILED]
        tot_open += c[wbmod.STATUS_UNTESTED] + c[wbmod.STATUS_TO_BE_TESTED]

    out: list[str] = []
    title = f"LME regression report{' — ' + module_name if module_name else ''}"
    out.append(f"<h1>{_esc(title)}</h1>")

    meta_bits = [f"Generated {_esc(stamp)}"]
    if environment_line:
        meta_bits.append(_esc(environment_line))
    if module_name:
        meta_bits.append(f"Module: <code>{_esc(module_name)}</code>")
    out.append(f'<p class="meta">{" &middot; ".join(meta_bits)}</p>')

    if dry_run:
        out.append(
            '<p class="banner">DRY RUN — no JIRA comment was posted and the '
            "workbook was not saved. Re-run with <code>--live</code> to commit.</p>"
        )

    # ── stat cards ────────────────────────────────────────────────────────────
    out.append('<div class="cards">')
    out.append(f'<div class="card"><div class="n">{tot_items}</div><div class="l">Total scenarios</div></div>')
    out.append(f'<div class="card pass"><div class="n">{tot_pass}</div><div class="l">Passed</div></div>')
    out.append(f'<div class="card fail"><div class="n">{tot_fail}</div><div class="l">Failed</div></div>')
    out.append(f'<div class="card tbt"><div class="n">{tot_open}</div><div class="l">Untested / To be tested</div></div>')
    out.append(f'<div class="card"><div class="n">{len(executed_rows)}</div><div class="l">Executed this run</div></div>')
    out.append("</div>")

    # ── coverage ──────────────────────────────────────────────────────────────
    out.append("<h2>Coverage by checklist</h2>")
    out.append('<div class="tablewrap"><table><thead><tr>'
               "<th>Checklist / area</th><th>Test items</th><th>Passed</th>"
               "<th>Failed</th><th>Untested / To be tested</th></tr></thead><tbody>")
    for name, c in coverage:
        items = sum(c[s] for s in wbmod.VALID_STATUSES) + c["(blank)"]
        open_ = c[wbmod.STATUS_UNTESTED] + c[wbmod.STATUS_TO_BE_TESTED]
        out.append(
            f"<tr><td>{_esc(name)}</td><td>{items}</td><td>{c[wbmod.STATUS_PASSED]}</td>"
            f"<td>{c[wbmod.STATUS_FAILED]}</td><td>{open_}</td></tr>"
        )
    out.append(
        f"<tr><th>TOTAL</th><th>{tot_items}</th><th>{tot_pass}</th>"
        f"<th>{tot_fail}</th><th>{tot_open}</th></tr>"
    )
    out.append("</tbody></table></div>")

    # ── executed this run ─────────────────────────────────────────────────────
    out.append(f"<h2>Scenarios executed ({len(executed_rows)})</h2>")
    if executed_rows:
        out.append('<div class="tablewrap"><table><thead><tr>'
                   "<th>Sheet</th><th>SL</th><th>Objective</th><th>Status</th>"
                   "<th>Evidence</th></tr></thead><tbody>")
        for row in executed_rows:
            out.append(
                f"<tr><td>{_esc(row.sheet)}</td><td>{_esc(row.sl_no)}</td>"
                f"<td>{_esc(row.objective)}</td>{_status_cell(row.status)}"
                f"<td>{_esc(row.comment)}</td></tr>"
            )
        out.append("</tbody></table></div>")
    else:
        out.append("<p>No scenarios were executed in this run.</p>")

    # ── defects ───────────────────────────────────────────────────────────────
    out.append(f"<h2>Defects raised ({len(defects)})</h2>")
    if defects:
        out.append('<div class="tablewrap"><table><thead><tr>'
                   "<th>Bug</th><th>Area</th><th>Title</th><th>Status</th>"
                   "<th>Screenshot</th></tr></thead><tbody>")
        for d in defects:
            out.append(
                f"<tr><td>{_esc(d.get('bug_no', '—'))}</td><td>{_esc(d.get('area'))}</td>"
                f"<td>{_esc(d.get('title'))}</td><td>{_esc(d.get('status', ''))}</td>"
                f"<td>{_esc(d.get('screenshot', ''))}</td></tr>"
            )
        out.append("</tbody></table></div>")
    else:
        out.append("<p>No new defects were raised in this run.</p>")

    # ── could not confirm ─────────────────────────────────────────────────────
    if skipped:
        out.append(f"<h2>Not confirmed — needs a manual look ({len(skipped)})</h2>")
        out.append(
            "<p>Automation could not reach a verdict on these. They are left open "
            "rather than marked Passed or Failed, and no bug was filed for them.</p>"
        )
        out.append('<div class="tablewrap"><table><thead><tr>'
                   "<th>Sheet</th><th>SL</th><th>Objective</th><th>Reason</th>"
                   "</tr></thead><tbody>")
        for row in skipped:
            out.append(
                f"<tr><td>{_esc(row.sheet)}</td><td>{_esc(row.sl_no)}</td>"
                f"<td>{_esc(row.objective)}</td><td>{_esc(row.comment)}</td></tr>"
            )
        out.append("</tbody></table></div>")

    # ── remaining work ────────────────────────────────────────────────────────
    notes = list(remaining_notes)
    if notes:
        out.append("<h2>Remaining work</h2><ul>")
        out.extend(f"<li>{_esc(n)}</li>" for n in notes)
        out.append("</ul>")

    doc = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_esc(title)}</title><style>{CSS}</style></head><body>"
        + "\n".join(out)
        + "</body></html>"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(doc, encoding="utf-8")
    return output_path
