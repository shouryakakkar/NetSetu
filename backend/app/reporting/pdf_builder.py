"""
PDF Report Builder using ReportLab.

Report structure:
  1. Cover Page       — device info, scan date, compliance score gauge
  2. Executive Summary — framework, control counts, severity breakdown table
  3. Findings Matrix  — sortable table: ID | Severity | Title | Status | Actual
  4. Remediation Runbook — FAIL/WARN items with exact CLI commands
  5. Appendix          — normalized JSON snapshot
"""
from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import KeepTogether


# ── Colour palette ────────────────────────────────────────────────────────────
C_PRIMARY    = colors.HexColor("#1e3a5f")   # Dark navy
C_SECONDARY  = colors.HexColor("#2563eb")   # Electric blue
C_SUCCESS    = colors.HexColor("#16a34a")   # Green
C_FAIL       = colors.HexColor("#dc2626")   # Red
C_WARN       = colors.HexColor("#d97706")   # Amber
C_NA         = colors.HexColor("#6b7280")   # Gray
C_CRITICAL   = colors.HexColor("#7c3aed")   # Purple
C_HIGH       = colors.HexColor("#dc2626")
C_MEDIUM     = colors.HexColor("#d97706")
C_LOW        = colors.HexColor("#2563eb")
C_BG_LIGHT   = colors.HexColor("#f1f5f9")
C_BG_HEADER  = colors.HexColor("#1e293b")
C_WHITE      = colors.white
C_BLACK      = colors.black


def _severity_color(severity: str) -> Any:
    return {
        "CRITICAL": C_CRITICAL,
        "HIGH": C_HIGH,
        "MEDIUM": C_MEDIUM,
        "LOW": C_LOW,
    }.get(severity.upper(), C_BLACK)


def _status_color(status: str) -> Any:
    return {
        "PASS": C_SUCCESS,
        "FAIL": C_FAIL,
        "WARN": C_WARN,
        "N/A": C_NA,
    }.get(status.upper(), C_BLACK)


# ── Styles ────────────────────────────────────────────────────────────────────
def _build_styles() -> dict:
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("title", fontSize=28, textColor=C_WHITE, alignment=TA_CENTER, spaceAfter=6, fontName="Helvetica-Bold"),
        "subtitle": ParagraphStyle("subtitle", fontSize=13, textColor=colors.HexColor("#94a3b8"), alignment=TA_CENTER, spaceAfter=4, fontName="Helvetica"),
        "section_header": ParagraphStyle("section_header", fontSize=15, textColor=C_PRIMARY, fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=8, borderPad=4),
        "body": ParagraphStyle("body", fontSize=9, textColor=C_BLACK, fontName="Helvetica", spaceAfter=4, leading=14),
        "code": ParagraphStyle("code", fontSize=8, textColor=colors.HexColor("#1e293b"), fontName="Courier", spaceAfter=4, backColor=C_BG_LIGHT, leading=12),
        "caption": ParagraphStyle("caption", fontSize=8, textColor=C_NA, fontName="Helvetica", alignment=TA_CENTER),
        "score_big": ParagraphStyle("score_big", fontSize=56, textColor=C_WHITE, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "score_label": ParagraphStyle("score_label", fontSize=11, textColor=colors.HexColor("#cbd5e1"), alignment=TA_CENTER, fontName="Helvetica"),
    }
    return styles


# ── Score gauge (simple colored text) ─────────────────────────────────────────
def _score_color(score: float) -> Any:
    if score >= 80:   return C_SUCCESS
    if score >= 60:   return C_WARN
    return C_FAIL


# ── Cover Page ────────────────────────────────────────────────────────────────
def _cover_page(story: list, meta: dict, styles: dict) -> None:
    score = meta.get("score", 0.0)

    # Full-width dark banner using a Table as background block
    cover_data = [
        [Paragraph("NetSetu", styles["title"])],
        [Paragraph("AI-Driven Multi-Vendor Configuration Audit Report", styles["subtitle"])],
        [Paragraph(f"{score:.1f}%", ParagraphStyle("score_num", fontSize=56, leading=64, spaceAfter=8, textColor=_score_color(score), alignment=TA_CENTER, fontName="Helvetica-Bold"))],
        [Paragraph("Compliance Score", ParagraphStyle("score_label", fontSize=12, leading=16, textColor=colors.HexColor("#cbd5e1"), alignment=TA_CENTER, fontName="Helvetica-Bold"))],
        [Spacer(1, 20)],
    ]
    cover_table = Table(cover_data, colWidths=[17 * cm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_BG_HEADER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 20))

    # Device metadata table
    meta_rows = [
        ["Device Hostname", meta.get("hostname", "Unknown")],
        ["Detected Vendor", meta.get("vendor", "Unknown")],
        ["Framework", meta.get("framework", "—").upper()],
        ["Scan Date", meta.get("scan_date", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))],
        ["Total Controls", str(meta.get("total_controls", "—"))],
        ["Audited By", meta.get("audited_by", "System")],
    ]
    meta_table = Table(meta_rows, colWidths=[6 * cm, 11 * cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), C_BG_LIGHT),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_WHITE, C_BG_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(meta_table)
    story.append(PageBreak())


# ── Executive Summary ─────────────────────────────────────────────────────────
def _executive_summary(story: list, meta: dict, styles: dict) -> None:
    story.append(Paragraph("Executive Summary", styles["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY))
    story.append(Spacer(1, 10))

    passed = meta.get("passed", 0)
    failed = meta.get("failed", 0)
    warned = meta.get("warned", 0)
    na = meta.get("not_applicable", 0)
    total = meta.get("total_controls", passed + failed + warned + na)

    summary_data = [
        ["Metric", "Value"],
        ["Framework", meta.get("framework", "—").upper()],
        ["Total Controls Evaluated", str(total)],
        ["✓ Passed", str(passed)],
        ["✗ Failed", str(failed)],
        ["⚠ Warnings", str(warned)],
        ["— Not Applicable", str(na)],
        ["Compliance Score", f"{meta.get('score', 0):.1f}%"],
    ]
    t = Table(summary_data, colWidths=[9 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_BG_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        # Color specific rows
        ("TEXTCOLOR", (1, 3), (1, 3), C_SUCCESS),   # Passed
        ("TEXTCOLOR", (1, 4), (1, 4), C_FAIL),      # Failed
        ("TEXTCOLOR", (1, 5), (1, 5), C_WARN),      # Warnings
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
        ("FONTNAME", (0, 7), (-1, 7), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(PageBreak())


# ── Findings Matrix ───────────────────────────────────────────────────────────
def _findings_matrix(story: list, findings: list[dict], styles: dict) -> None:
    story.append(Paragraph("Compliance Findings", styles["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY))
    story.append(Spacer(1, 10))

    header = ["Control ID", "Sev", "Title", "Status", "Expected", "Actual"]
    rows = [header]
    for f in findings:
        rows.append([
            f.get("control_id", ""),
            f.get("severity", ""),
            Paragraph(f.get("title", ""), ParagraphStyle("cell", fontSize=8, fontName="Helvetica", leading=11)),
            f.get("status", ""),
            str(f.get("expected", ""))[:30],
            str(f.get("actual", ""))[:30],
        ])

    col_widths = [2.8 * cm, 1.5 * cm, 6.0 * cm, 1.5 * cm, 2.5 * cm, 2.7 * cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), C_BG_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_BG_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]
    # Color severity and status cells per row
    for i, f in enumerate(findings, start=1):
        sev_col = _severity_color(f.get("severity", ""))
        stat_col = _status_color(f.get("status", ""))
        style_cmds += [
            ("TEXTCOLOR", (1, i), (1, i), sev_col),
            ("FONTNAME", (1, i), (1, i), "Helvetica-Bold"),
            ("TEXTCOLOR", (3, i), (3, i), stat_col),
            ("FONTNAME", (3, i), (3, i), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style_cmds))
    story.append(t)
    story.append(PageBreak())


# ── Remediation Runbook ───────────────────────────────────────────────────────
def _remediation_runbook(story: list, findings: list[dict], styles: dict) -> None:
    story.append(Paragraph("Remediation Runbook", styles["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY))
    story.append(Spacer(1, 10))

    action_items = [f for f in findings if f.get("status") in ("FAIL", "WARN")]
    if not action_items:
        story.append(Paragraph("✓ No remediation required — all controls passed.", styles["body"]))
        return

    for idx, f in enumerate(action_items, 1):
        block = []
        sev_color = _severity_color(f.get("severity", ""))
        header_text = f"[{f.get('severity', '')}] {f.get('control_id', '')} — {f.get('title', '')}"
        block.append(Paragraph(header_text, ParagraphStyle(
            "finding_hdr", fontSize=10, fontName="Helvetica-Bold",
            textColor=sev_color, spaceBefore=10, spaceAfter=4,
        )))
        block.append(Paragraph(
            f"<b>Status:</b> {f.get('status', '')} | "
            f"<b>Expected:</b> {f.get('expected', '')} | "
            f"<b>Actual:</b> {f.get('actual', '')}",
            ParagraphStyle("finding_meta", fontSize=8, fontName="Helvetica", textColor=C_NA, spaceAfter=4),
        ))
        cli = f.get("remediation_hint", "Manual remediation required.")
        block.append(Paragraph("<b>CLI Fix:</b>", styles["body"]))
        block.append(Paragraph(cli.replace("\n", "<br/>"), styles["code"]))
        block.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#e2e8f0")))
        story.append(KeepTogether(block))


# ── Appendix ──────────────────────────────────────────────────────────────────
def _appendix(story: list, normalized_json: dict, styles: dict) -> None:
    story.append(PageBreak())
    story.append(Paragraph("Appendix — Normalized Configuration JSON", styles["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY))
    story.append(Spacer(1, 8))
    json_str = json.dumps(normalized_json, indent=2, default=str)
    # Split into chunks to avoid single-cell overflow
    chunk_size = 2000
    for i in range(0, len(json_str), chunk_size):
        story.append(Paragraph(json_str[i:i + chunk_size].replace("\n", "<br/>").replace(" ", "&nbsp;"), styles["code"]))


# ── Public entry point ────────────────────────────────────────────────────────

def build_pdf(
    meta: dict,
    findings: list[dict],
    normalized_json: dict | None = None,
) -> bytes:
    """
    Build a complete compliance audit PDF and return it as bytes.

    Args:
        meta:           dict with keys: hostname, vendor, framework, scan_date,
                        score, total_controls, passed, failed, warned,
                        not_applicable, audited_by
        findings:       list of finding dicts (from compliance engine)
        normalized_json: optional normalized config snapshot for appendix
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Compliance Audit — {meta.get('hostname', 'Device')}",
        author="NetSetu",
        subject=f"{meta.get('framework', '').upper()} Compliance Report",
    )

    styles = _build_styles()
    story: list = []

    _cover_page(story, meta, styles)
    _executive_summary(story, meta, styles)
    _findings_matrix(story, findings, styles)
    _remediation_runbook(story, findings, styles)
    if normalized_json:
        _appendix(story, normalized_json, styles)

    doc.build(story)
    return buffer.getvalue()
