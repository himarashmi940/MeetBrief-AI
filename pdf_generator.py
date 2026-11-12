
from io import BytesIO
import re
from xml.sax.saxutils import escape, quoteattr
from urllib.parse import urlparse

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    ListFlowable,
    ListItem,
    Table,
    TableStyle,
)
from reportlab.platypus.doctemplate import LayoutError


_NAVY = colors.HexColor("#243B64")
_BLUE = colors.HexColor("#3973A8")
_PALE_BLUE = colors.HexColor("#EAF1F8")
_LIGHT_BLUE = colors.HexColor("#C7D7E8")

_INLINE_MARKDOWN = re.compile(
    r"\[([^\]]+)\]\(([^)]+)\)"
    r"|\*\*(.+?)\*\*|__(.+?)__|`([^`]+)`"
    r"|(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!_)_([^_\n]+)_(?!_)"
)
_HEADING = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*#*\s*$")
_NUMBERED_HEADING = re.compile(r"^\s*\d+[.)]\s+(.+?)\s*$")
_BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_ORDERED_ITEM = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_HORIZONTAL_RULE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")


class PDFGenerationError(RuntimeError):
    """Raised when ReportLab cannot build the meeting report."""


def _format_inline_markdown(text):
    parts = []
    position = 0

    for match in _INLINE_MARKDOWN.finditer(text):
        parts.append(escape(text[position:match.start()]))
        if match.group(1) is not None:
            label, url = match.group(1), match.group(2).strip()
            parsed_url = urlparse(url)
            if parsed_url.scheme in ("http", "https") and parsed_url.netloc:
                parts.append(
                    f'<link href={quoteattr(url)} color="#3973A8">'
                    f"{escape(label)}</link>"
                )
            else:
                parts.append(escape(label))
        elif match.group(3) is not None or match.group(4) is not None:
            parts.append(f"<b>{escape(match.group(3) or match.group(4))}</b>")
        elif match.group(5) is not None:
            parts.append(f'<font name="Courier">{escape(match.group(5))}</font>')
        else:
            parts.append(f"<i>{escape(match.group(6) or match.group(7))}</i>")
        position = match.end()

    parts.append(escape(text[position:]))
    return "".join(parts)


def _heading_for_line(line):
    match = _HEADING.match(line)
    if match:
        return min(len(match.group(1)), 3), match.group(2).strip()

    match = _NUMBERED_HEADING.match(line)
    if match:
        text = match.group(1).strip()
        plain_text = text.replace("**", "").replace("__", "").strip()
        if len(plain_text) <= 100 and not plain_text.endswith((".", "!", "?")):
            return 2, text
    return None


def _list_item_for_line(line):
    match = _BULLET.match(line)
    if match:
        return match.group(1), "bullet", match.group(2), None

    match = _ORDERED_ITEM.match(line)
    if match:
        return match.group(1), "1", match.group(3), int(match.group(2))
    return None


def create_pdf_report(company, meeting_date, briefing, sources=None):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=48,
        leftMargin=48,
        topMargin=48,
        bottomMargin=48,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=23,
        leading=28,
        alignment=TA_CENTER,
        textColor=_NAVY,
        spaceAfter=5,
    )

    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#60758C"),
        spaceAfter=18,
    )

    heading_styles = {
        1: ParagraphStyle(
            "BriefHeading1",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=_NAVY,
            spaceBefore=14,
            spaceAfter=7,
            keepWithNext=True,
        ),
        2: ParagraphStyle(
            "BriefHeading2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=_BLUE,
            spaceBefore=11,
            spaceAfter=5,
            keepWithNext=True,
        ),
        3: ParagraphStyle(
            "BriefHeading3",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=_NAVY,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
    }
    body_style = ParagraphStyle(
        "BriefBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#263746"),
        spaceAfter=7,
        splitLongWords=1,
    )
    meta_label_style = ParagraphStyle(
        "MetaLabel",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=_NAVY,
        spaceAfter=0,
    )
    meta_value_style = ParagraphStyle(
        "MetaValue",
        parent=body_style,
        spaceAfter=0,
    )
    empty_style = ParagraphStyle(
        "EmptyBrief",
        parent=body_style,
        textColor=colors.HexColor("#60758C"),
        italic=True,
    )

    story = []

    story.append(Paragraph("MeetBrief AI", title_style))
    story.append(Paragraph(
        "Intelligent Meeting Preparation Report",
        subtitle_style,
    ))

    metadata = Table(
        [
            [
                Paragraph("Company / Person", meta_label_style),
                Paragraph(escape(str(company or "Not provided")), meta_value_style),
            ],
            [
                Paragraph("Meeting Date", meta_label_style),
                Paragraph(escape(str(meeting_date or "Not provided")), meta_value_style),
            ],
        ],
        colWidths=[115, doc.width - 115],
        hAlign="LEFT",
    )
    metadata.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), _PALE_BLUE),
        ("BACKGROUND", (1, 0), (1, -1), colors.white),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, _LIGHT_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, _LIGHT_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(metadata)
    story.append(Spacer(1, 16))
    story.append(Paragraph("Meeting Briefing", heading_styles[1]))

    lines = str(briefing or "").splitlines()
    if not any(line.strip() for line in lines):
        story.append(Paragraph("No briefing content was provided.", empty_style))
    else:
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if not line:
                index += 1
                continue

            if _HORIZONTAL_RULE.match(line):
                story.append(Spacer(1, 3))
                story.append(HRFlowable(
                    width="100%",
                    thickness=0.8,
                    color=_LIGHT_BLUE,
                    spaceBefore=3,
                    spaceAfter=8,
                ))
                index += 1
                continue

            heading = _heading_for_line(line)
            if heading:
                level, text = heading
                story.append(Paragraph(
                    _format_inline_markdown(text),
                    heading_styles[level],
                ))
                index += 1
                continue

            list_item = _list_item_for_line(lines[index])
            if list_item:
                first_item = list_item
                items = []
                while index < len(lines):
                    current_item = _list_item_for_line(lines[index])
                    if not current_item or current_item[1] != first_item[1]:
                        break
                    items.append(ListItem(Paragraph(
                        _format_inline_markdown(current_item[2]),
                        body_style,
                    )))
                    index += 1
                indent = min(len(first_item[0].expandtabs(4)), 24)
                story.append(ListFlowable(
                    items,
                    bulletType=first_item[1],
                    start=first_item[3],
                    leftIndent=18 + indent,
                    bulletIndent=5 + indent,
                    bulletFontName="Helvetica",
                    bulletFontSize=8,
                    bulletColor=_BLUE,
                    bulletOffsetY=1,
                    spaceBefore=1,
                    spaceAfter=7,
                ))
                continue

            paragraph_lines = [line]
            index += 1
            while index < len(lines) and lines[index].strip():
                candidate = lines[index].strip()
                if (
                    _HORIZONTAL_RULE.match(candidate)
                    or _heading_for_line(candidate)
                    or _list_item_for_line(lines[index])
                ):
                    break
                paragraph_lines.append(candidate)
                index += 1
            story.append(Paragraph(
                _format_inline_markdown(" ".join(paragraph_lines)),
                body_style,
            ))

    valid_sources = []
    for source in sources or []:
        if not isinstance(source, dict):
            continue
        url = source.get("url")
        if not isinstance(url, str):
            continue
        parsed_url = urlparse(url)
        if parsed_url.scheme in ("http", "https") and parsed_url.netloc:
            valid_sources.append(source)
    if valid_sources:
        story.append(Spacer(1, 8))
        story.append(HRFlowable(
            width="100%",
            thickness=0.8,
            color=_LIGHT_BLUE,
            spaceBefore=3,
            spaceAfter=8,
        ))
        story.append(Paragraph("Research Sources", heading_styles[2]))
        for source in valid_sources:
            title = source.get("title") or source["url"]
            story.append(Paragraph(
                f'<link href={quoteattr(source["url"])} color="#3973A8">'
                f'{escape(str(title))}</link>'
                f' <font color="#60758C">({escape(source["url"])})</font>',
                body_style,
            ))

    story.append(Spacer(1, 14))

    story.append(Paragraph(
        "Generated by MeetBrief AI",
        ParagraphStyle(
            "Footer",
            parent=styles["Italic"],
            fontSize=8,
            textColor=colors.HexColor("#60758C"),
            alignment=TA_CENTER,
        ),
    ))

    try:
        doc.build(story)
    except (LayoutError, OSError, TypeError, ValueError) as error:
        raise PDFGenerationError(
            "The meeting briefing was created, but the PDF report could not be generated."
        ) from error

    buffer.seek(0)

    return buffer
