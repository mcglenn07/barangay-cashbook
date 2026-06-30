"""Renders a cashbook period as a PDF matching the official barangay
cashbook layout (4 fund columns, beginning balance, totals, and two
signature blocks: Treasurer certification + Captain approval)."""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, legal
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def money(v):
    if v is None or v == 0:
        return ""
    return f"{v:,.2f}"


def build_period_pdf(barangay, period, opening, ledger, totals):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(legal),
        leftMargin=0.3 * inch,
        rightMargin=0.3 * inch,
        topMargin=0.3 * inch,
        bottomMargin=0.3 * inch,
        title=f"Cashbook - {barangay['name']} - {period['label']}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10, leading=12)
    bold_title_style = ParagraphStyle("boldtitle", parent=title_style, fontName="Helvetica-Bold", fontSize=13)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=10)
    small_bold = ParagraphStyle("smallbold", parent=small, fontName="Helvetica-Bold")

    story = []
    story.append(Paragraph(f"Municipality of {barangay['municipality']}", title_style))
    story.append(Paragraph(f"Province of {barangay['province']}", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("CASHBOOK", bold_title_style))
    story.append(Paragraph(f"Calendar Year: {period['calendar_year']}", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Barangay:</b> {barangay['name']}", small))
    story.append(Paragraph(f"<b>Barangay Treasurer:</b> {barangay['treasurer_name']}", small))
    story.append(Paragraph(f"<b>Barangay Captain:</b> {barangay['captain_name']}", small))
    story.append(Paragraph(f"<b>Period:</b> {period['label']}", small))
    story.append(Spacer(1, 8))

    # --- Build the table -----------------------------------------------
    header_row1 = [
        "Date", "Particulars", "Reference",
        "Cash in Local Treasury", "", "",
        "Cash in Bank", "", "",
        "Cash Advance", "", "",
        "Petty Cash", "", "",
    ]
    header_row2 = [
        "", "", "",
        "Collections", "Deposit", "Balance",
        "Deposit", "Check Issued", "Balance",
        "Receipt", "Disbursements", "Balance",
        "Receipt/\nReplenishment", "Payments", "Balance",
    ]

    data = [header_row1, header_row2]

    cell_style = ParagraphStyle("cell", parent=small, fontSize=6.5, leading=8)

    def cell(text):
        text = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(text, cell_style)

    data.append([
        "", cell("Beginning Balance"), "",
        "", "", money(opening["lt"]),
        "", "", money(opening["bank"]),
        "", "", money(opening["ca"]),
        "", "", money(opening["petty"]),
    ])

    for tx in ledger:
        if tx["is_cancelled"]:
            label = "CANCELLED" + (f" ({tx['particulars']})" if tx["particulars"] not in ("", "CANCELLED") else "")
            data.append([
                cell(tx["entry_date"]), cell(label),
                cell(tx["check_number"] or tx["reference"] or ""),
                "", "", "", "", "", "", "", "", "", "", "", "",
            ])
            continue
        data.append([
            cell(tx["entry_date"]),
            cell(tx["particulars"]),
            cell(tx["check_number"] or tx["reference"] or ""),
            money(tx["lt_collection"]), money(tx["lt_deposit"]), money(tx["lt_balance"]),
            money(tx["bank_deposit"]), money(tx["bank_check_issued"]), money(tx["bank_balance"]),
            money(tx["ca_receipt"]), money(tx["ca_disbursement"]), money(tx["ca_balance"]),
            money(tx["petty_receipt"]), money(tx["petty_payment"]), money(tx["petty_balance"]),
        ])

    data.append([
        "", "Total", "",
        money(totals["lt_collection"]), money(totals["lt_deposit"]), "",
        money(totals["bank_deposit"]), money(totals["bank_check_issued"]), "",
        money(totals["ca_receipt"]), money(totals["ca_disbursement"]), "",
        money(totals["petty_receipt"]), money(totals["petty_payment"]), "",
    ])

    col_widths = [0.65, 2.6, 0.75] + [0.65] * 12
    col_widths = [w * inch for w in col_widths]

    table = Table(data, colWidths=col_widths, repeatRows=2)

    n_rows = len(data)
    style = [
        ("SPAN", (0, 0), (0, 1)),
        ("SPAN", (1, 0), (1, 1)),
        ("SPAN", (2, 0), (2, 1)),
        ("SPAN", (3, 0), (5, 0)),
        ("SPAN", (6, 0), (8, 0)),
        ("SPAN", (9, 0), (11, 0)),
        ("SPAN", (12, 0), (14, 0)),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("ALIGN", (0, 0), (-1, 1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 1), colors.whitesmoke),
        ("ALIGN", (3, 2), (-1, -1), "RIGHT"),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f0f0f0")),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-BoldOblique"),
        ("BACKGROUND", (0, n_rows - 1), (-1, n_rows - 1), colors.HexColor("#f0f0f0")),
        ("FONTNAME", (0, n_rows - 1), (-1, n_rows - 1), "Helvetica-Bold"),
    ]
    table.setStyle(TableStyle(style))
    story.append(table)
    story.append(Spacer(1, 18))

    # --- Signature blocks -------------------------------------------------
    cert_style = ParagraphStyle("cert", parent=small, fontSize=8, leading=11)
    story.append(Paragraph("CERTIFICATION:", small_bold))
    story.append(Paragraph(
        "I hereby certify that the foregoing is a correct and complete record of all collections, "
        "deposits, remittances and balances of the accounts in the Cash-in-Local-Treasury, Cash in "
        "Bank, Cash Advances, and Petty Cash for the period stated above.",
        cert_style,
    ))
    story.append(Spacer(1, 22))

    sig_data = [
        [
            Paragraph(f"<b>{barangay['treasurer_name']}</b>", small),
            Paragraph(f"<b>{barangay['captain_name']}</b>", small),
        ],
        [
            Paragraph("Barangay Treasurer &mdash; Name and Signature", small),
            Paragraph("Barangay Captain &mdash; Approved/Noted by (Name and Signature)", small),
        ],
        [
            Paragraph(f"Date: {period['certified_date'] or '_____________'}", small),
            Paragraph(f"Date: {period['approved_date'] or '_____________'}", small),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[5 * inch, 5 * inch])
    sig_table.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (0, 1), 0.75, colors.black),
        ("LINEABOVE", (1, 1), (1, 1), 0.75, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 14),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 2),
    ]))
    story.append(sig_table)

    doc.build(story)
    buf.seek(0)
    return buf
