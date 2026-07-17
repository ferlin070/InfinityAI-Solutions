import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from src.core.config import logger


def generate_quotation_pdf(quotation: dict, items: list[dict]) -> str | None:
    try:
        tmp = tempfile.gettempdir()
        filename = f"quotation_{quotation['number']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(tmp, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4,
                                leftMargin=20*mm, rightMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "QuotationTitle", parent=styles["Heading1"],
            spaceAfter=6*mm, fontSize=18,
        )
        normal = styles["Normal"]

        elements = []
        elements.append(Paragraph(f"Quotation: {quotation['number']}", title_style))
        elements.append(Paragraph(f"Date: {datetime.now().strftime('%d %B %Y')}", normal))
        elements.append(Spacer(1, 10*mm))

        table_data = [["Item", "Qty", "Unit Price", "Total"]]
        for item in items:
            table_data.append([
                item.get("description", ""),
                str(item.get("qty", 1)),
                f"RM{item.get('unit_price', 0):.2f}",
                f"RM{item.get('line_total', 0):.2f}",
            ])

        col_widths = [80*mm, 20*mm, 35*mm, 35*mm]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D2A32")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D2D2")),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F6F5")]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 5*mm))

        elements.append(Paragraph(f"Subtotal: RM{quotation.get('subtotal', 0):.2f}", normal))
        elements.append(Paragraph(f"Tax (6%): RM{quotation.get('tax', 0):.2f}", normal))
        elements.append(Paragraph(f"<b>Total: RM{quotation.get('total', 0):.2f}</b>", styles["Heading4"]))

        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(
            "Quotation ini sah selama 14 hari dari tarikh dikeluarkan.",
            ParagraphStyle("Footer", parent=normal, fontSize=8, textColor=colors.gray),
        ))

        doc.build(elements)
        logger.info(f"PDF generated: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        return None
