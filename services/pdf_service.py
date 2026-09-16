"""
PDF Invoice Generation Service using ReportLab
Generates clean, professional, branded retail and tax invoices.
"""
import os
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from config import Config

def generate_invoice_pdf(invoice, output_path=None):
    """
    Generates a professional PDF for an Invoice model instance.
    Returns: filepath string if saved, or BytesIO buffer if output_path is None.
    """
    buffer = BytesIO() if output_path is None else output_path

    # Page setup
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B')
    )
    
    subtitle_style = ParagraphStyle(
        'InvoiceSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B')
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0F172A')
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    bold_body = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    elements = []

    # 1. Header: Store Info & Tax Invoice Title
    header_data = [
        [
            Paragraph(f"<b>{Config.SHOP_NAME}</b><br/>{Config.SHOP_TAGLINE}<br/>{Config.SHOP_ADDRESS}<br/>Phone: {Config.SHOP_PHONE} | GST: {Config.SHOP_GST}", subtitle_style),
            Paragraph("<b>TAX INVOICE</b><br/><font size='8' color='#64748B'>ORIGINAL FOR RECIPIENT</font>", title_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[340, 180])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=15))

    # 2. Meta: Invoice Details & Customer Info
    cust_name = invoice.customer.name if invoice.customer else "Walk-in Customer"
    cust_phone = invoice.customer.phone if invoice.customer else "N/A"
    cust_addr = invoice.customer.address if invoice.customer and invoice.customer.address else "Over the counter"
    cust_email = invoice.customer.email if invoice.customer and invoice.customer.email else ""

    cashier_name = invoice.cashier.full_name if invoice.cashier else "Staff"

    meta_data = [
        [
            Paragraph(f"<b>Billed To:</b><br/><b>{cust_name}</b><br/>Phone: {cust_phone}<br/>{cust_addr}" + (f"<br/>Email: {cust_email}" if cust_email else ""), body_style),
            Paragraph(
                f"<b>Invoice #:</b> {invoice.invoice_number}<br/>"
                f"<b>Date:</b> {invoice.created_at.strftime('%d-%b-%Y %I:%M %p')}<br/>"
                f"<b>Payment Mode:</b> {invoice.payment_mode}<br/>"
                f"<b>Status:</b> {invoice.payment_status}<br/>"
                f"<b>Billed By:</b> {cashier_name}",
                body_style
            )
        ]
    ]
    meta_table = Table(meta_data, colWidths=[320, 200])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    # 3. Itemized Table
    table_rows = [
        [
            Paragraph("<b>#</b>", bold_body),
            Paragraph("<b>Item Description / Specs</b>", bold_body),
            Paragraph("<b>Type</b>", bold_body),
            Paragraph("<b>Qty</b>", bold_body),
            Paragraph("<b>Rate (₹)</b>", bold_body),
            Paragraph("<b>Total (₹)</b>", bold_body)
        ]
    ]

    for idx, item in enumerate(invoice.items, 1):
        desc = item.item_name
        if item.imei:
            desc += f"<br/><font size='7.5' color='#64748B'>IMEI: {item.imei}</font>"

        table_rows.append([
            Paragraph(str(idx), body_style),
            Paragraph(desc, body_style),
            Paragraph(item.item_type.capitalize(), body_style),
            Paragraph(str(item.quantity), body_style),
            Paragraph(f"{item.unit_price:,.2f}", body_style),
            Paragraph(f"{item.total_price:,.2f}", bold_body)
        ])

    items_table = Table(table_rows, colWidths=[25, 235, 65, 35, 80, 80])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2F6')),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 10))

    # 4. Totals & Payment Summary
    totals_data = [
        ["Subtotal:", f"₹ {invoice.subtotal:,.2f}"],
        [f"GST / Tax ({invoice.tax_rate}%):", f"+ ₹ {invoice.tax_amount:,.2f}"]
    ]
    if invoice.discount_amount and invoice.discount_amount > 0:
        totals_data.append(["Special Discount:", f"- ₹ {invoice.discount_amount:,.2f}"])
    if invoice.exchange_discount and invoice.exchange_discount > 0:
        totals_data.append(["Exchange Old Phone Bonus:", f"- ₹ {invoice.exchange_discount:,.2f}"])

    totals_data.append(["Grand Total Payable:", f"₹ {invoice.final_total:,.2f}"])

    totals_table = Table(totals_data, colWidths=[150, 100])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#0F172A')),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#0F172A')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))

    # Wrap in right-aligned wrapper table
    wrapper_data = [
        [
            Paragraph(
                "<b>Terms & Warranty Policy:</b><br/>"
                "• 1 Year standard manufacturer warranty on smart mobile handsets.<br/>"
                "• Original invoice and matching IMEI are required for warranty claims.<br/>"
                "• Accessories carry 7-day replacement warranty for manufacturing defects.<br/>"
                "• Physical and water damage are not covered under standard warranty.",
                subtitle_style
            ),
            totals_table
        ]
    ]
    wrapper_table = Table(wrapper_data, colWidths=[270, 250])
    wrapper_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (0, 0), 8),
    ]))
    elements.append(wrapper_table)
    elements.append(Spacer(1, 25))

    # 5. Signatures & Footer
    footer_data = [
        [
            Paragraph("Customer Signature", subtitle_style),
            Paragraph("Authorized Signatory (MOBIXPRO)", ParagraphStyle('RSign', parent=subtitle_style, alignment=2))
        ]
    ]
    footer_table = Table(footer_data, colWidths=[260, 260])
    footer_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (0, 0), 0.5, colors.HexColor('#94A3B8')),
        ('LINEABOVE', (1, 0), (1, 0), 0.5, colors.HexColor('#94A3B8')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(KeepTogether([footer_table]))

    doc.build(elements)

    if output_path is None:
        buffer.seek(0)
        return buffer
    return output_path
