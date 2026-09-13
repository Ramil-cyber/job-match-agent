"""Build the repository's technical-guide PDF from its Markdown source."""

from __future__ import annotations

import html
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = PROJECT_ROOT / "docs" / "TECHNICAL_GUIDE.md"
OUTPUT_PATH = PROJECT_ROOT / "docs" / "Job_Match_Agent_Technical_Guide.pdf"
ARCHITECTURE_PATH = PROJECT_ROOT / "assets" / "system-architecture.svg"

PAGE_WIDTH, PAGE_HEIGHT = LETTER
LEFT_MARGIN = 0.72 * inch
RIGHT_MARGIN = 0.72 * inch
TOP_MARGIN = 0.68 * inch
BOTTOM_MARGIN = 0.62 * inch
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

NAVY = colors.HexColor("#0B1220")
SLATE = colors.HexColor("#334155")
MUTED = colors.HexColor("#64748B")
BLUE = colors.HexColor("#2563EB")
CYAN = colors.HexColor("#0891B2")
CORAL = colors.HexColor("#E11D48")
WHITE = colors.white
LIGHT = colors.HexColor("#F8FAFC")
PALE_BLUE = colors.HexColor("#EFF6FF")
BORDER = colors.HexColor("#CBD5E1")
CODE_BACKGROUND = colors.HexColor("#F1F5F9")


def _register_fonts() -> tuple[str, str, str]:
    """Use Unicode fonts when available and safe built-in fallbacks otherwise."""

    font_locations = (
        Path("/usr/share/fonts/truetype/dejavu"),
        Path(
            "/opt/codex/runtimes/codex-primary-runtime/dependencies/"
            "native/libreoffice-headless/libreoffice/share/fonts/truetype"
        ),
    )
    for location in font_locations:
        regular = location / "DejaVuSans.ttf"
        bold = location / "DejaVuSans-Bold.ttf"
        mono = location / "DejaVuSansMono.ttf"
        if regular.is_file() and bold.is_file() and mono.is_file():
            pdfmetrics.registerFont(TTFont("GuideSans", regular))
            pdfmetrics.registerFont(TTFont("GuideSans-Bold", bold))
            pdfmetrics.registerFont(TTFont("GuideMono", mono))
            pdfmetrics.registerFontFamily(
                "GuideSans",
                normal="GuideSans",
                bold="GuideSans-Bold",
            )
            return "GuideSans", "GuideSans-Bold", "GuideMono"

    return "Helvetica", "Helvetica-Bold", "Courier"


BODY_FONT, BOLD_FONT, MONO_FONT = _register_fonts()


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName=BOLD_FONT,
            fontSize=30,
            leading=35,
            textColor=WHITE,
            alignment=TA_LEFT,
            spaceAfter=16,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base["Normal"],
            fontName=BODY_FONT,
            fontSize=13,
            leading=19,
            textColor=colors.HexColor("#BAE6FD"),
            spaceAfter=20,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=base["Normal"],
            fontName=BODY_FONT,
            fontSize=9.2,
            leading=14,
            textColor=colors.HexColor("#E2E8F0"),
        ),
        "body": ParagraphStyle(
            "GuideBody",
            parent=base["BodyText"],
            fontName=BODY_FONT,
            fontSize=9.2,
            leading=13.4,
            textColor=SLATE,
            spaceAfter=7,
            allowWidows=0,
            allowOrphans=0,
        ),
        "section": ParagraphStyle(
            "GuideSection",
            parent=base["Heading1"],
            fontName=BOLD_FONT,
            fontSize=18,
            leading=22,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "subsection": ParagraphStyle(
            "GuideSubsection",
            parent=base["Heading2"],
            fontName=BOLD_FONT,
            fontSize=12.2,
            leading=15,
            textColor=BLUE,
            spaceBefore=10,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "minor": ParagraphStyle(
            "GuideMinor",
            parent=base["Heading3"],
            fontName=BOLD_FONT,
            fontSize=10.2,
            leading=13,
            textColor=CYAN,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "list": ParagraphStyle(
            "GuideList",
            parent=base["BodyText"],
            fontName=BODY_FONT,
            fontSize=8.9,
            leading=12.8,
            textColor=SLATE,
            leftIndent=17,
            bulletIndent=0,
            bulletFontName=BOLD_FONT,
            bulletFontSize=8.3,
            bulletColor=BLUE,
            spaceAfter=3,
            allowWidows=0,
            allowOrphans=0,
        ),
        "table_header": ParagraphStyle(
            "GuideTableHeader",
            parent=base["BodyText"],
            fontName=BOLD_FONT,
            fontSize=7.3,
            leading=9.5,
            textColor=WHITE,
        ),
        "table_cell": ParagraphStyle(
            "GuideTableCell",
            parent=base["BodyText"],
            fontName=BODY_FONT,
            fontSize=7.1,
            leading=9.5,
            textColor=SLATE,
        ),
        "code": ParagraphStyle(
            "GuideCode",
            parent=base["Code"],
            fontName=MONO_FONT,
            fontSize=7.2,
            leading=10.2,
            textColor=NAVY,
            leftIndent=8,
            rightIndent=8,
            borderColor=BORDER,
            borderWidth=0.5,
            borderPadding=8,
            backColor=CODE_BACKGROUND,
            spaceBefore=3,
            spaceAfter=8,
        ),
        "callout": ParagraphStyle(
            "GuideCallout",
            parent=base["BodyText"],
            fontName=BODY_FONT,
            fontSize=8.7,
            leading=12.8,
            textColor=colors.HexColor("#1E3A8A"),
        ),
        "contents": ParagraphStyle(
            "GuideContents",
            parent=base["BodyText"],
            fontName=BODY_FONT,
            fontSize=9.4,
            leading=14,
            textColor=SLATE,
            leftIndent=12,
            firstLineIndent=-12,
            spaceAfter=3,
        ),
        "caption": ParagraphStyle(
            "GuideCaption",
            parent=base["BodyText"],
            fontName=BODY_FONT,
            fontSize=7.5,
            leading=10,
            alignment=TA_CENTER,
            textColor=MUTED,
            spaceAfter=8,
        ),
    }


STYLES = _build_styles()


def _inline_markdown(text: str) -> str:
    """Convert the small inline-Markdown subset used by this guide."""

    clean = html.escape(text.strip(), quote=True)
    clean = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<link href="\2" color="#2563EB">\1</link>',
        clean,
    )
    clean = re.sub(
        r"`([^`]+)`",
        rf'<font name="{MONO_FONT}" color="#0F766E">\1</font>',
        clean,
    )
    clean = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", clean)
    return clean


def _add_arrow(
    drawing: Drawing,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color=BLUE,
) -> None:
    drawing.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.5))
    if abs(y2 - y1) >= abs(x2 - x1):
        direction = -1 if y2 < y1 else 1
        drawing.add(
            Polygon(
                [x2, y2, x2 - 4, y2 - 7 * direction, x2 + 4, y2 - 7 * direction],
                fillColor=color,
                strokeColor=color,
            )
        )
    else:
        direction = 1 if x2 > x1 else -1
        drawing.add(
            Polygon(
                [x2, y2, x2 - 7 * direction, y2 - 4, x2 - 7 * direction, y2 + 4],
                fillColor=color,
                strokeColor=color,
            )
        )


def _add_box(
    drawing: Drawing,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    subtitle: str,
    *,
    fill,
    title_color=NAVY,
) -> None:
    drawing.add(
        Rect(
            x,
            y,
            width,
            height,
            rx=8,
            ry=8,
            fillColor=fill,
            strokeColor=BORDER,
            strokeWidth=1,
        )
    )
    drawing.add(
        String(
            x + width / 2,
            y + height - 19,
            title,
            fontName=BOLD_FONT,
            fontSize=9,
            fillColor=title_color,
            textAnchor="middle",
        )
    )
    drawing.add(
        String(
            x + width / 2,
            y + 14,
            subtitle,
            fontName=BODY_FONT,
            fontSize=6.8,
            fillColor=MUTED,
            textAnchor="middle",
        )
    )


def build_architecture_diagram(width: float = 720, height: float = 420) -> Drawing:
    """Create a scalable architecture diagram for Markdown and PDF."""

    drawing = Drawing(width, height)
    drawing.add(
        Rect(
            0,
            0,
            width,
            height,
            rx=12,
            ry=12,
            fillColor=LIGHT,
            strokeColor=BORDER,
            strokeWidth=1,
        )
    )
    drawing.add(
        String(
            width / 2,
            height - 28,
            "Job Match Agent system architecture",
            fontName=BOLD_FONT,
            fontSize=15,
            fillColor=NAVY,
            textAnchor="middle",
        )
    )

    margin = width * 0.055
    gap = width * 0.035
    box_width = (width - 2 * margin - 2 * gap) / 3
    box_height = height * 0.13
    top_y = height * 0.68
    core_y = height * 0.42
    service_y = height * 0.13

    interface_boxes = (
        ("Public portfolio", "Saved + protected live"),
        ("Private Streamlit", "Restricted owner workflow"),
        ("Command line", "Local file workflow"),
    )
    core_boxes = (
        ("Public controls", "Auth, input, quota"),
        ("Agent core", "Evidence-based analysis"),
        ("Output controls", "Validation, PDF, Markdown"),
    )
    service_boxes = (
        ("Google OIDC", "Verified identity"),
        ("Supabase", "Atomic quota counters"),
        ("OpenAI API", "Moderation + generation"),
    )

    centers: list[list[tuple[float, float]]] = []
    for row_index, (items, y, fill) in enumerate(
        (
            (interface_boxes, top_y, colors.HexColor("#DBEAFE")),
            (core_boxes, core_y, colors.HexColor("#E0F2FE")),
            (service_boxes, service_y, colors.HexColor("#FCE7F3")),
        )
    ):
        row_centers = []
        for column, (title, subtitle) in enumerate(items):
            x = margin + column * (box_width + gap)
            _add_box(
                drawing,
                x,
                y,
                box_width,
                box_height,
                title,
                subtitle,
                fill=fill,
                title_color=NAVY if row_index < 2 else colors.HexColor("#9F1239"),
            )
            row_centers.append((x + box_width / 2, y + box_height / 2))
        centers.append(row_centers)

    for column in range(3):
        top = centers[0][column]
        core = centers[1][column]
        _add_arrow(
            drawing,
            top[0],
            top[1] - box_height / 2,
            core[0],
            core[1] + box_height / 2,
        )

    public_core = centers[1][0]
    google = centers[2][0]
    supabase = centers[2][1]
    agent = centers[1][1]
    openai = centers[2][2]
    output = centers[1][2]
    _add_arrow(
        drawing,
        public_core[0],
        public_core[1] - box_height / 2,
        google[0],
        google[1] + box_height / 2,
        color=CYAN,
    )
    _add_arrow(
        drawing,
        public_core[0] + box_width * 0.25,
        public_core[1] - box_height / 2,
        supabase[0] - box_width * 0.25,
        supabase[1] + box_height / 2,
        color=CYAN,
    )
    _add_arrow(
        drawing,
        agent[0] + box_width * 0.25,
        agent[1] - box_height / 2,
        openai[0] - box_width * 0.25,
        openai[1] + box_height / 2,
        color=CORAL,
    )
    _add_arrow(
        drawing,
        agent[0] + box_width / 2,
        agent[1],
        output[0] - box_width / 2,
        output[1],
        color=BLUE,
    )

    drawing.add(
        String(
            width / 2,
            height * 0.055,
            "Secrets remain server-side; public failures stop before unmetered generation.",
            fontName=BODY_FONT,
            fontSize=7.2,
            fillColor=MUTED,
            textAnchor="middle",
        )
    )
    return drawing


def _table_column_widths(column_count: int) -> list[float]:
    ratios = {
        2: (0.30, 0.70),
        3: (0.23, 0.32, 0.45),
        4: (0.19, 0.20, 0.27, 0.34),
        5: (0.16, 0.17, 0.20, 0.22, 0.25),
    }.get(column_count)
    if ratios is None:
        ratios = tuple(1 / column_count for _ in range(column_count))
    return [CONTENT_WIDTH * ratio for ratio in ratios]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells
    )


def _markdown_table(lines: list[str]) -> LongTable:
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in lines
    ]
    rows = [row for row in rows if not _is_separator_row(row)]
    column_count = max(len(row) for row in rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rows]
    data = []
    for row_index, row in enumerate(normalized):
        style = STYLES["table_header"] if row_index == 0 else STYLES["table_cell"]
        data.append([Paragraph(_inline_markdown(cell), style) for cell in row])

    table = LongTable(
        data,
        colWidths=_table_column_widths(column_count),
        repeatRows=1,
        splitByRow=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 1), (-1, -1), WHITE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _is_special(line: str) -> bool:
    stripped = line.strip()
    return bool(
        not stripped
        or stripped.startswith("#")
        or stripped.startswith("```")
        or stripped.startswith("|")
        or stripped.startswith(">")
        or stripped.startswith("![")
        or re.match(r"^(?:-|\d+\.)\s+", stripped)
    )


def _consume_list(
    lines: list[str],
    index: int,
    *,
    ordered: bool,
) -> tuple[list[Paragraph], int]:
    items: list[Paragraph] = []
    marker = re.compile(r"^(?:\d+\.|-)\s+(.*)")
    while index < len(lines):
        stripped = lines[index].strip()
        match = marker.match(stripped)
        if not match:
            break
        current_is_ordered = bool(re.match(r"^\d+\.\s+", stripped))
        if current_is_ordered != ordered:
            break
        parts = [match.group(1)]
        index += 1
        while index < len(lines):
            continuation = lines[index].strip()
            if not continuation or _is_special(lines[index]):
                break
            parts.append(continuation)
            index += 1
        bullet = f"{len(items) + 1}." if ordered else "•"
        items.append(
            Paragraph(
                _inline_markdown(" ".join(parts)),
                STYLES["list"],
                bulletText=bullet,
            )
        )
        if index < len(lines) and not lines[index].strip():
            lookahead = index + 1
            if lookahead < len(lines):
                next_line = lines[lookahead].strip()
                next_is_same = (
                    bool(re.match(r"^\d+\.\s+", next_line))
                    if ordered
                    else next_line.startswith("- ")
                )
                if next_is_same:
                    index = lookahead
                    continue
            break

    return items, index


def _parse_markdown(lines: list[str]) -> list:
    story: list = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        if stripped.startswith("## "):
            story.append(Paragraph(_inline_markdown(stripped[3:]), STYLES["section"]))
            index += 1
            continue
        if stripped.startswith("### "):
            story.append(
                Paragraph(_inline_markdown(stripped[4:]), STYLES["subsection"])
            )
            index += 1
            continue
        if stripped.startswith("#### "):
            story.append(Paragraph(_inline_markdown(stripped[5:]), STYLES["minor"]))
            index += 1
            continue

        if stripped.startswith("!["):
            if "system-architecture.svg" in stripped:
                story.append(Spacer(1, 4))
                story.append(build_architecture_diagram(CONTENT_WIDTH, 290))
                story.append(
                    Paragraph(
                        "Figure 1. Interfaces, shared controls, and external services.",
                        STYLES["caption"],
                    )
                )
            index += 1
            continue

        if stripped.startswith("```"):
            index += 1
            code_lines: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            code = "\n".join(code_lines).replace("\t", "    ")
            story.append(
                XPreformatted(
                    escape(code),
                    STYLES["code"],
                )
            )
            continue

        if stripped.startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.append(_markdown_table(table_lines))
            story.append(Spacer(1, 8))
            continue

        if stripped.startswith(">"):
            callout_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                callout_lines.append(lines[index].strip().lstrip(">").strip())
                index += 1
            callout = Table(
                [[Paragraph(_inline_markdown(" ".join(callout_lines)), STYLES["callout"])]],
                colWidths=[CONTENT_WIDTH],
                hAlign="LEFT",
            )
            callout.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#93C5FD")),
                        ("LINEBEFORE", (0, 0), (0, -1), 4, BLUE),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.extend([callout, Spacer(1, 8)])
            continue

        if stripped.startswith("- "):
            flowables, index = _consume_list(lines, index, ordered=False)
            story.extend(flowables)
            story.append(Spacer(1, 4))
            continue
        if re.match(r"^\d+\.\s+", stripped):
            flowables, index = _consume_list(lines, index, ordered=True)
            story.extend(flowables)
            story.append(Spacer(1, 4))
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines) and not _is_special(lines[index]):
            paragraph_lines.append(lines[index].strip())
            index += 1
        story.append(
            Paragraph(_inline_markdown(" ".join(paragraph_lines)), STYLES["body"])
        )

    return story


def _draw_cover_page(canvas, document) -> None:
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    canvas.setFillColor(BLUE)
    canvas.rect(0, PAGE_HEIGHT - 18, PAGE_WIDTH * 0.72, 18, fill=1, stroke=0)
    canvas.setFillColor(CORAL)
    canvas.rect(PAGE_WIDTH * 0.72, PAGE_HEIGHT - 18, PAGE_WIDTH * 0.28, 18, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#334155"))
    canvas.setLineWidth(0.7)
    canvas.line(LEFT_MARGIN, 0.9 * inch, PAGE_WIDTH - RIGHT_MARGIN, 0.9 * inch)
    canvas.setFont(BODY_FONT, 7.5)
    canvas.setFillColor(colors.HexColor("#94A3B8"))
    canvas.drawString(LEFT_MARGIN, 0.62 * inch, "Ramil-cyber/job-match-agent")
    canvas.drawRightString(
        PAGE_WIDTH - RIGHT_MARGIN,
        0.62 * inch,
        "Technical documentation",
    )
    canvas.restoreState()


def _draw_body_page(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(
        LEFT_MARGIN,
        PAGE_HEIGHT - 0.45 * inch,
        PAGE_WIDTH - RIGHT_MARGIN,
        PAGE_HEIGHT - 0.45 * inch,
    )
    canvas.setFont(BODY_FONT, 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        LEFT_MARGIN,
        PAGE_HEIGHT - 0.32 * inch,
        "JOB MATCH AGENT  /  TECHNICAL GUIDE",
    )
    canvas.line(
        LEFT_MARGIN,
        0.43 * inch,
        PAGE_WIDTH - RIGHT_MARGIN,
        0.43 * inch,
    )
    canvas.drawString(LEFT_MARGIN, 0.25 * inch, "Verified September 12, 2026")
    canvas.drawRightString(
        PAGE_WIDTH - RIGHT_MARGIN,
        0.25 * inch,
        f"Page {document.page}",
    )
    canvas.restoreState()


def _cover_story() -> list:
    facts = Table(
        [
            [
                Paragraph("3 / 10 / 100", STYLES["cover_subtitle"]),
                Paragraph("49 tests", STYLES["cover_subtitle"]),
                Paragraph("8/8 benchmark", STYLES["cover_subtitle"]),
            ],
            [
                Paragraph("Account / daily / total quotas", STYLES["cover_meta"]),
                Paragraph("Automated suite", STYLES["cover_meta"]),
                Paragraph("Fictional scenario", STYLES["cover_meta"]),
            ],
        ],
        colWidths=[CONTENT_WIDTH / 3] * 3,
        hAlign="LEFT",
    )
    facts.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#172554")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#334155")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#334155")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return [
        Spacer(1, 1.05 * inch),
        Paragraph("Job Match Agent", STYLES["cover_title"]),
        Paragraph("Technical Guide", STYLES["cover_title"]),
        Paragraph(
            "Architecture • Security • Deployment • Testing • Operations",
            STYLES["cover_subtitle"],
        ),
        Spacer(1, 0.18 * inch),
        Paragraph(
            "A complete engineering reference for the OpenAI-only resume and "
            "job-description matching system, including its saved portfolio, "
            "protected public workflow, private interface, command-line path, "
            "and fail-closed cost controls.",
            STYLES["cover_meta"],
        ),
        Spacer(1, 0.4 * inch),
        facts,
        Spacer(1, 0.35 * inch),
        Paragraph(
            "Architecture baseline: v3.0.0 and subsequent repository organization",
            STYLES["cover_meta"],
        ),
        Paragraph("Last verified: September 12, 2026", STYLES["cover_meta"]),
        PageBreak(),
    ]


def _contents_story(section_titles: list[str]) -> list:
    items = [
        Paragraph("Contents", STYLES["section"]),
        Paragraph(
            "This PDF is generated from docs/TECHNICAL_GUIDE.md. The Markdown "
            "version remains the editable source.",
            STYLES["body"],
        ),
        Spacer(1, 6),
    ]
    for title in section_titles:
        items.append(Paragraph(_inline_markdown(title), STYLES["contents"]))
    items.append(PageBreak())
    return items


def build_pdf() -> tuple[Path, int]:
    """Generate the architecture SVG and technical-guide PDF."""

    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(f"Technical guide not found: {SOURCE_PATH}")

    source_lines = SOURCE_PATH.read_text(encoding="utf-8").splitlines()
    section_titles = [
        line[3:].strip() for line in source_lines if line.startswith("## ")
    ]
    first_section = next(
        index for index, line in enumerate(source_lines) if line.startswith("## ")
    )

    ARCHITECTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    renderSVG.drawToFile(
        build_architecture_diagram(),
        str(ARCHITECTURE_PATH),
        showBoundary=False,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=LETTER,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title="Job Match Agent Technical Guide",
        author="Ramil Mammadov",
        subject="Architecture, security, deployment, testing, and operations",
        creator="scripts/build_technical_guide_pdf.py",
    )
    story = _cover_story()
    story.extend(_contents_story(section_titles))
    story.extend(_parse_markdown(source_lines[first_section:]))
    document.build(
        story,
        onFirstPage=_draw_cover_page,
        onLaterPages=_draw_body_page,
    )

    pdf_data = OUTPUT_PATH.read_bytes()
    page_count = len(re.findall(rb"/Type\s*/Page(?!s)\b", pdf_data))
    if page_count < 5:
        raise RuntimeError("The generated technical guide is unexpectedly short.")
    if not pdf_data.startswith(b"%PDF-"):
        raise RuntimeError("The generated file is not a valid PDF.")
    return OUTPUT_PATH, page_count


def main() -> None:
    output_path, page_count = build_pdf()
    print(
        f"Technical guide PDF created: {output_path.relative_to(PROJECT_ROOT)} "
        f"({page_count} pages)"
    )


if __name__ == "__main__":
    main()
