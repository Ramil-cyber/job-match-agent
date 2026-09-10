import re
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PAGE_MARGIN = 0.65 * inch


def _clean_text(text: str) -> str:
    """Replace characters that may not display correctly in the PDF."""

    replacements = str.maketrans(
        {
            "\u00a0": " ",
            "\u2010": "-",
            "\u2011": "-",
            "\u2012": "-",
            "\u2013": "-",
            "\u2014": "-",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2022": "-",
            "\u2026": "...",
        }
    )

    return text.translate(replacements)


def _format_inline_markdown(text: str) -> str:
    """Convert simple Markdown formatting into ReportLab formatting."""

    safe_text = escape(_clean_text(text).strip(), quote=False)

    safe_text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<b>\1</b>",
        safe_text,
    )

    safe_text = re.sub(
        r"`(.+?)`",
        r'<font name="Courier">\1</font>',
        safe_text,
    )

    return safe_text


def _build_styles():
    """Create the fonts, colors, spacing, and sizes used in the PDF."""

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="PDFTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=16,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PDFHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1D4ED8"),
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PDFBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PDFList",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            leftIndent=14,
            firstLineIndent=-10,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PDFTableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PDFTableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor("#1F2937"),
        )
    )

    return styles


def _split_table_row(line: str) -> list[str]:
    """Split one Markdown table row into individual cells."""

    row = line.strip().strip("|")
    cells = re.split(r"(?<!\\)\|", row)

    return [cell.replace(r"\|", "|").strip() for cell in cells]


def _is_table_separator(cells: list[str]) -> bool:
    """Check whether a row is the Markdown table separator."""

    return all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def _build_table(table_lines: list[str], styles) -> Table:
    """Convert Markdown table lines into a formatted PDF table."""

    rows = [_split_table_row(line) for line in table_lines]

    if len(rows) > 1 and _is_table_separator(rows[1]):
        rows.pop(1)

    column_count = max(len(row) for row in rows)

    for row in rows:
        row.extend([""] * (column_count - len(row)))

    formatted_rows = []

    for row_number, row in enumerate(rows):
        cell_style = (
            styles["PDFTableHeader"] if row_number == 0 else styles["PDFTableCell"]
        )

        formatted_rows.append(
            [
                Paragraph(
                    _format_inline_markdown(cell),
                    cell_style,
                )
                for cell in row
            ]
        )

    available_width = LETTER[0] - (2 * PAGE_MARGIN)

    if column_count == 3:
        column_widths = [
            available_width * 0.32,
            available_width * 0.43,
            available_width * 0.25,
        ]
    else:
        column_widths = [available_width / column_count for _ in range(column_count)]

    table = Table(
        formatted_rows,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=True,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1E3A5F"),
                ),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F8FAFC"),
                    ],
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    return table


def _draw_footer(canvas, document) -> None:
    """Add the application name and page number to every page."""

    page_width, _ = canvas._pagesize

    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.line(
        PAGE_MARGIN,
        0.55 * inch,
        page_width - PAGE_MARGIN,
        0.55 * inch,
    )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(
        PAGE_MARGIN,
        0.35 * inch,
        "Job Match Agent",
    )
    canvas.drawRightString(
        page_width - PAGE_MARGIN,
        0.35 * inch,
        f"Page {canvas.getPageNumber()}",
    )
    canvas.restoreState()


def create_job_match_pdf(report_markdown: str) -> bytes:
    """Convert a Markdown job-match report into PDF bytes."""

    if not isinstance(report_markdown, str) or not report_markdown.strip():
        raise ValueError("The report cannot be empty.")

    styles = _build_styles()
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=0.75 * inch,
        title="Job Match Report",
        author="Job Match Agent",
    )

    story = []
    lines = report_markdown.splitlines()
    line_number = 0

    while line_number < len(lines):
        line = lines[line_number].strip()

        if not line:
            line_number += 1
            continue

        if line.startswith("|"):
            table_lines = []

            while line_number < len(lines) and lines[line_number].strip().startswith(
                "|"
            ):
                table_lines.append(lines[line_number].strip())
                line_number += 1

            story.append(_build_table(table_lines, styles))
            story.append(Spacer(1, 10))
            continue

        if line.startswith("# "):
            story.append(
                Paragraph(
                    _format_inline_markdown(line[2:]),
                    styles["PDFTitle"],
                )
            )

        elif line.startswith("## "):
            story.append(
                Paragraph(
                    _format_inline_markdown(line[3:]),
                    styles["PDFHeading"],
                )
            )

        elif re.match(r"^[-*]\s+", line):
            item_text = re.sub(r"^[-*]\s+", "", line)

            story.append(
                Paragraph(
                    f"- {_format_inline_markdown(item_text)}",
                    styles["PDFList"],
                )
            )

        elif numbered_item := re.match(r"^(\d+)\.\s+(.+)", line):
            number = numbered_item.group(1)
            item_text = numbered_item.group(2)

            story.append(
                Paragraph(
                    f"{number}. {_format_inline_markdown(item_text)}",
                    styles["PDFList"],
                )
            )

        elif line in {"---", "***", "___"}:
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=colors.HexColor("#CBD5E1"),
                    spaceBefore=4,
                    spaceAfter=8,
                )
            )

        else:
            story.append(
                Paragraph(
                    _format_inline_markdown(line),
                    styles["PDFBody"],
                )
            )

        line_number += 1

    document.build(
        story,
        onFirstPage=_draw_footer,
        onLaterPages=_draw_footer,
    )

    return buffer.getvalue()
