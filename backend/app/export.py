"""
Generic tabular export to CSV, HTML, or PDF. Both the audit log and the
detections endpoints hand this the same shape - a list of (key, label)
column definitions and a list of dict rows - so adding a new exportable
table later is just calling these three functions again, not writing a new
renderer.
"""
import csv
import html
import io
from datetime import datetime
from typing import Any

from fastapi import Response

Column = tuple[str, str]  # (dict key, display label)


def _cell(row: dict, key: str) -> str:
    value = row.get(key)
    if value is None:
        return ""
    return str(value)


def rows_to_csv_bytes(columns: list[Column], rows: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([label for _, label in columns])
    for row in rows:
        writer.writerow([_cell(row, key) for key, _ in columns])
    return buf.getvalue().encode("utf-8")


def rows_to_html_bytes(title: str, columns: list[Column], rows: list[dict]) -> bytes:
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    head_cells = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    body_rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(_cell(row, key))}</td>" for key, _ in columns) + "</tr>"
        for row in rows
    )
    doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, sans-serif; background: #14161A; color: #ECEEF1; padding: 24px; }}
  h1 {{ font-size: 18px; font-weight: 600; }}
  .meta {{ color: #8B92A0; font-size: 12px; margin-bottom: 16px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #2A2E36; }}
  th {{ color: #8B92A0; font-weight: 500; }}
  td {{ font-family: ui-monospace, monospace; }}
</style></head>
<body>
  <h1>{html.escape(title)}</h1>
  <div class="meta">Generated {generated_at} - {len(rows)} row(s)</div>
  <table><thead><tr>{head_cells}</tr></thead><tbody>{body_rows}</tbody></table>
</body></html>"""
    return doc.encode("utf-8")


def rows_to_pdf_bytes(title: str, columns: list[Column], rows: list[dict]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    elements = [
        Paragraph(title, styles["Heading2"]),
        Paragraph(f"Generated {generated_at} - {len(rows)} row(s)", styles["Normal"]),
        Spacer(1, 10),
    ]

    table_data = [[label for _, label in columns]]
    for row in rows:
        table_data.append([_cell(row, key) for key, _ in columns])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B1E24")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F4F4")]),
    ]))
    elements.append(table)
    doc.build(elements)
    return buf.getvalue()


def export_response(format: str, title: str, filename_stem: str, columns: list[Column], rows: list[dict]) -> Response:
    if format == "csv":
        return Response(
            content=rows_to_csv_bytes(columns, rows),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename_stem}.csv"'},
        )
    if format == "html":
        return Response(
            content=rows_to_html_bytes(title, columns, rows),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{filename_stem}.html"'},
        )
    if format == "pdf":
        return Response(
            content=rows_to_pdf_bytes(title, columns, rows),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename_stem}.pdf"'},
        )
    raise ValueError(f"Unsupported export format: {format}")
