"""
Notification Service for MOBIX
Handles Email (SMTP with HTML template + PDF attachment) and
WhatsApp notification deep-links/API dispatch for Billing and Repair updates.
"""
import smtplib
import urllib.parse
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from config import Config
from services.pdf_service import generate_invoice_pdf

def build_whatsapp_invoice_message(invoice, host_url=None):
    """Formats an attractive WhatsApp message for retail billing with direct PDF bill attachment link."""
    cust_name = invoice.customer.name if invoice.customer else "Valued Customer"
    item_lines = []
    for item in invoice.items:
        imei_note = f"\n   ↳ *IMEI:* `{item.imei}`" if item.imei else ""
        item_lines.append(f"📱 *{item.item_name}* x{item.quantity}\n   ↳ Price: ₹{item.total_price:,.2f}{imei_note}")

    items_text = "\n\n".join(item_lines) if item_lines else "• Mobile Device & Accessories"
    
    base = host_url.rstrip('/') if host_url else "http://127.0.0.1:5000"
    pdf_url = f"{base}/pos/receipt/{invoice.invoice_number}/pdf"
    view_url = f"{base}/pos/receipt/{invoice.invoice_number}"

    msg = (
        f"🧾 *TAX INVOICE & WARRANTY SLIP — {Config.SHOP_NAME}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Dear *{cust_name}*,\n"
        f"Thank you for purchasing with us! Your official purchase bill & brand warranty record has been registered.\n\n"
        f"📋 *Invoice No:* #{invoice.invoice_number}\n"
        f"📅 *Date:* {invoice.created_at.strftime('%d-%b-%Y %I:%M %p')}\n"
        f"💳 *Payment Mode:* {invoice.payment_mode} ({invoice.payment_status})\n\n"
        f"🛍️ *PURCHASED PRODUCTS & IMEI:*\n{items_text}\n\n"
        f"💰 *Subtotal:* ₹{invoice.subtotal:,.2f}\n"
        f"📊 *GST ({invoice.tax_rate}%):* ₹{invoice.tax_amount:,.2f}\n"
    )
    if invoice.discount_amount > 0:
        msg += f"🏷️ *Discount:* -₹{invoice.discount_amount:,.2f}\n"
    if invoice.exchange_discount > 0:
        msg += f"🔄 *Old Phone Exchange Credit:* -₹{invoice.exchange_discount:,.2f}\n"

    if invoice.payment_mode == 'EMI' and invoice.emi_account:
        msg += f"🗓️ *EMI Plan:* {invoice.emi_account.tenure_months} Months @ ₹{invoice.emi_account.emi_amount:,.2f}/mo (Down Payment: ₹{invoice.emi_account.down_payment:,.2f})\n"

    msg += (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 *FINAL BILL TOTAL:* *₹{invoice.final_total:,.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📄 *ATTACHED OFFICIAL BILL (PDF FORMAT):*\n"
        f"📥 *Click to Download & Open PDF Bill:* {pdf_url}\n"
        f"🌐 *View Interactive Digital Receipt:* {view_url}\n\n"
        f"🛡️ *Warranty Policy:* Retain this digital bill & IMEI for official brand warranty claims.\n"
        f"📞 *Customer Support:* {Config.SHOP_PHONE}\n"
        f"📍 *Store Address:* {Config.SHOP_ADDRESS}\n\n"
        f"✨ *Thank you for shopping at {Config.SHOP_NAME}!*"
    )
    return msg

def get_whatsapp_url(phone, message_text):
    """Generates a universal WhatsApp click-to-chat web/mobile URL."""
    clean_phone = ''.join(filter(str.isdigit, str(phone)))
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone  # Default Indian country code if 10 digits
    encoded = urllib.parse.quote(message_text)
    return f"https://wa.me/{clean_phone}?text={encoded}"

def build_whatsapp_repair_message(ticket):
    """Formats an update message for mobile repair tracking."""
    cust_name = ticket.customer.name if ticket.customer else "Customer"
    status_emoji = {
        'Received': '📥',
        'Diagnosing': '🔍',
        'Repairing': '🛠️',
        'Ready': '✅',
        'Delivered': '🤝'
    }.get(ticket.status, '🔧')

    msg = (
        f"🔧 *{Config.SHOP_NAME} — Repair Update*\n\n"
        f"Hello *{cust_name}*,\n"
        f"Your device repair status has been updated:\n\n"
        f"📋 *Ticket #:* {ticket.ticket_no}\n"
        f"📱 *Device:* {ticket.brand} {ticket.model}\n"
        f"{status_emoji} *Current Status:* *{ticket.status.upper()}*\n"
        f"💵 *Estimated Cost:* ₹{ticket.estimated_cost:,.2f}\n"
    )
    if ticket.status in ('Ready', 'Delivered'):
        msg += f"🎉 *Final Amount Due:* ₹{max(0.0, (ticket.final_cost or ticket.estimated_cost) - ticket.advance_paid):,.2f}\n"
        msg += f"🛡️ *Repair Warranty:* {ticket.warranty_days} Days\n"
    
    if ticket.technician_notes:
        msg += f"📝 *Technician Note:* {ticket.technician_notes}\n"

    msg += f"\n📞 *Contact Us:* {Config.SHOP_PHONE}"
    return msg

def send_email_invoice(invoice, recipient_email=None):
    """
    Dispatches a professional HTML invoice with PDF attachment via Gmail SMTP.
    Lists purchased mobiles (with IMEI numbers) and accessories, tax breakdown,
    and warranty credentials.
    """
    owner_email = (Config.MAIL_USERNAME or '').strip()
    cust_email = invoice.customer.email.strip() if (invoice.customer and invoice.customer.email) else None
    to_email = (recipient_email or cust_email or owner_email).strip() if (recipient_email or cust_email or owner_email) else None

    if not to_email:
        return False, "No recipient or store email configured."

    cust_name = invoice.customer.name if invoice.customer else "Valued Customer"
    cust_phone = invoice.customer.phone if invoice.customer else "N/A"

    # Build itemized rows for Mobiles and Accessories
    items_html = []
    items_text = []
    for item in invoice.items:
        is_mobile = (item.item_type == 'mobile' or item.imei)
        icon = "📱" if is_mobile else "🎧"
        type_badge = "Mobile Handset" if is_mobile else "Accessory"
        
        imei_html = f'<div style="font-size: 11px; color: #6366f1; margin-top: 3px; font-family: monospace;"><b>IMEI:</b> {item.imei}</div>' if item.imei else ''
        imei_txt = f" (IMEI: {item.imei})" if item.imei else ""

        items_html.append(f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 12px 10px; vertical-align: top;">
                <span style="font-size: 16px; margin-right: 6px;">{icon}</span>
                <strong>{item.item_name}</strong>
                <span style="display: inline-block; font-size: 10px; background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">{type_badge}</span>
                {imei_html}
            </td>
            <td style="padding: 12px 10px; text-align: center; vertical-align: top; font-weight: 600;">{item.quantity}</td>
            <td style="padding: 12px 10px; text-align: right; vertical-align: top; color: #475569;">₹{item.unit_price:,.2f}</td>
            <td style="padding: 12px 10px; text-align: right; vertical-align: top; font-weight: 700; color: #0f172a;">₹{item.total_price:,.2f}</td>
        </tr>
        """)
        items_text.append(f"- {icon} {item.item_name} x{item.quantity}{imei_txt}: ₹{item.total_price:,.2f}")

    items_table_rows = "\n".join(items_html) if items_html else "<tr><td colspan='4' style='padding: 10px;'>Mobile Devices & Accessories</td></tr>"
    items_plain_text = "\n".join(items_text) if items_text else "- Mobile Devices & Accessories"

    # Discounts & Credits
    discounts_html = []
    if invoice.discount_amount > 0:
        discounts_html.append(f"""
        <tr>
            <td colspan="3" style="padding: 6px 10px; text-align: right; color: #e11d48;">Discount:</td>
            <td style="padding: 6px 10px; text-align: right; font-weight: 600; color: #e11d48;">-₹{invoice.discount_amount:,.2f}</td>
        </tr>
        """)
    if invoice.exchange_discount > 0:
        discounts_html.append(f"""
        <tr>
            <td colspan="3" style="padding: 6px 10px; text-align: right; color: #059669;">Old Device Trade-In Credit:</td>
            <td style="padding: 6px 10px; text-align: right; font-weight: 600; color: #059669;">-₹{invoice.exchange_discount:,.2f}</td>
        </tr>
        """)

    # Linked EMI Details
    emi_html = ""
    if invoice.payment_mode == 'EMI' and invoice.emi_account:
        emi_html = f"""
        <div style="background: #fffbeb; border: 1px solid #fef3c7; border-left: 4px solid #f59e0b; padding: 14px; border-radius: 6px; margin: 18px 0;">
            <div style="font-weight: bold; color: #b45309; font-size: 13px;">🗓️ Smart Store EMI Activated</div>
            <div style="font-size: 12px; color: #78350f; margin-top: 4px;">
                <strong>Tenure:</strong> {invoice.emi_account.tenure_months} Months &nbsp;|&nbsp;
                <strong>Down Payment:</strong> ₹{invoice.emi_account.down_payment:,.2f} &nbsp;|&nbsp;
                <strong>Monthly EMI:</strong> ₹{invoice.emi_account.emi_amount:,.2f}/month
            </div>
        </div>
        """

    subject = f"🧾 Tax Invoice #{invoice.invoice_number} — {Config.SHOP_NAME}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 20px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
        <div style="max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
            
            <!-- Branded Header -->
            <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 28px 24px; color: #ffffff;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">{Config.SHOP_NAME}</h1>
                        <p style="margin: 4px 0 0; font-size: 12px; opacity: 0.9;">{Config.SHOP_TAGLINE}</p>
                    </div>
                </div>
                <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.2); font-size: 12px; display: flex; justify-content: space-between;">
                    <span><b>Invoice:</b> #{invoice.invoice_number}</span>
                    <span><b>Date:</b> {invoice.created_at.strftime('%d-%b-%Y %I:%M %p')}</span>
                </div>
            </div>

            <!-- Main Body -->
            <div style="padding: 24px;">
                <p style="font-size: 15px; margin-top: 0;">Dear <strong>{cust_name}</strong>,</p>
                <p style="font-size: 13.5px; color: #475569; line-height: 1.5;">
                    Thank you for shopping at <strong>{Config.SHOP_NAME}</strong>! Your purchase transaction has been completed successfully. Below is your official tax invoice and product warranty record.
                </p>

                <!-- Customer Details Box -->
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin: 16px 0; font-size: 12.5px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                        <div><b>Customer:</b> {cust_name}</div>
                        <div><b>Phone:</b> {cust_phone}</div>
                        <div><b>Payment Mode:</b> {invoice.payment_mode} ({invoice.payment_status})</div>
                        <div><b>GSTIN:</b> {Config.SHOP_GST}</div>
                    </div>
                </div>

                <!-- Products Table -->
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 13px;">
                    <thead>
                        <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1; color: #334155;">
                            <th style="padding: 10px; text-align: left;">Item Description</th>
                            <th style="padding: 10px; text-align: center; width: 50px;">Qty</th>
                            <th style="padding: 10px; text-align: right; width: 90px;">Rate</th>
                            <th style="padding: 10px; text-align: right; width: 100px;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_table_rows}
                    </tbody>
                    <tfoot>
                        <tr>
                            <td colspan="3" style="padding: 10px; text-align: right; color: #64748b; border-top: 2px solid #e2e8f0;">Subtotal:</td>
                            <td style="padding: 10px; text-align: right; font-weight: 600; border-top: 2px solid #e2e8f0;">₹{invoice.subtotal:,.2f}</td>
                        </tr>
                        <tr>
                            <td colspan="3" style="padding: 6px 10px; text-align: right; color: #64748b;">GST ({invoice.tax_rate}%):</td>
                            <td style="padding: 6px 10px; text-align: right; font-weight: 600;">₹{invoice.tax_amount:,.2f}</td>
                        </tr>
                        {"".join(discounts_html)}
                        <tr style="background: #f0fdf4; border-top: 2px solid #10b981; border-bottom: 2px solid #10b981;">
                            <td colspan="3" style="padding: 12px 10px; text-align: right; font-size: 15px; font-weight: 800; color: #047857;">Final Paid Total:</td>
                            <td style="padding: 12px 10px; text-align: right; font-size: 17px; font-weight: 800; color: #047857;">₹{invoice.final_total:,.2f}</td>
                        </tr>
                    </tfoot>
                </table>

                {emi_html}

                <!-- Warranty Notice -->
                <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 14px; margin: 20px 0; font-size: 12px; color: #1e40af;">
                    <div style="font-weight: 700; margin-bottom: 4px;">🛡️ Official Warranty & Device Registration</div>
                    <div>
                        Mobile IMEI numbers and serials listed on this bill are officially registered for manufacturer warranty.
                        A printable copy of your invoice is attached to this email as a PDF document (<strong>{invoice.invoice_number}.pdf</strong>).
                    </div>
                </div>

                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />

                <!-- Footer -->
                <div style="font-size: 11.5px; color: #64748b; text-align: center; line-height: 1.6;">
                    <strong>{Config.SHOP_NAME}</strong><br/>
                    {Config.SHOP_ADDRESS}<br/>
                    📞 Phone: {Config.SHOP_PHONE} &nbsp;|&nbsp; ✉️ Email: {Config.SHOP_EMAIL} &nbsp;|&nbsp; GSTIN: {Config.SHOP_GST}<br/>
                    <span style="color: #94a3b8;">This is an automated purchase invoice generated at checkout.</span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    plain_content = f"""
{Config.SHOP_NAME} - Tax Invoice #{invoice.invoice_number}
==================================================
Date: {invoice.created_at.strftime('%d-%b-%Y %I:%M %p')}
Customer: {cust_name} ({cust_phone})
Payment Mode: {invoice.payment_mode} ({invoice.payment_status})

PURCHASED ITEMS:
{items_plain_text}

Subtotal: ₹{invoice.subtotal:,.2f}
GST ({invoice.tax_rate}%): ₹{invoice.tax_amount:,.2f}
Final Total: ₹{invoice.final_total:,.2f}

Official PDF bill attached: {invoice.invoice_number}.pdf
Store: {Config.SHOP_NAME}, {Config.SHOP_ADDRESS}
Phone: {Config.SHOP_PHONE}
    """

    # Dispatch via Gmail SMTP
    clean_password = (Config.MAIL_PASSWORD or '').replace(' ', '').strip()
    mail_user = (Config.MAIL_USERNAME or '').strip()

    if mail_user and clean_password:
        try:
            msg = MIMEMultipart('mixed')
            msg['From'] = Config.MAIL_DEFAULT_SENDER
            msg['To'] = to_email
            msg['Subject'] = subject

            # Determine BCC recipients: always keep store owner archive informed
            recipients = [to_email]
            if owner_email and owner_email != to_email:
                recipients.append(owner_email)

            # Alternate plain/HTML body container
            alt_part = MIMEMultipart('alternative')
            alt_part.attach(MIMEText(plain_content, 'plain', 'utf-8'))
            alt_part.attach(MIMEText(html_content, 'html', 'utf-8'))
            msg.attach(alt_part)

            # Generate and attach PDF
            try:
                pdf_buffer = generate_invoice_pdf(invoice)
                pdf_data = pdf_buffer.getvalue() if hasattr(pdf_buffer, 'getvalue') else pdf_buffer.read()
                pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename=f"{invoice.invoice_number}.pdf")
                msg.attach(pdf_attachment)
            except Exception as pdf_err:
                print(f"[MAIL] PDF generation warning: {pdf_err}")

            with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=20) as server:
                if Config.MAIL_USE_TLS:
                    server.starttls()
                server.login(mail_user, clean_password)
                server.send_message(msg, from_addr=Config.MAIL_DEFAULT_SENDER, to_addrs=recipients)

            return True, f"Official purchase bill successfully emailed to {to_email} via Gmail."
        except Exception as e:
            err_msg = f"Email delivery failed: {str(e)}"
            print(f"[MAIL ERROR] {err_msg}")
            return False, err_msg
    else:
        return True, f"[SIMULATION] Invoice email prepared for {to_email} with PDF attachment."



def build_whatsapp_preorder_confirmation(booking, host_url=None):
    """Formats an attractive WhatsApp message confirming a flagship pre-booking & token advance."""
    cust_name = booking.customer.name if booking.customer else "Valued Customer"
    base = host_url.rstrip('/') if host_url else "http://127.0.0.1:5000"
    pass_url = f"{base}/prebook/pass/{booking.booking_no}"
    receipt_url = f"{base}/preorders/receipt/{booking.id}"

    msg = (
        f"📱 *FLAGSHIP PRE-ORDER CONFIRMATION — {Config.SHOP_NAME}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Dear *{cust_name}*,\n"
        f"Congratulations! Your priority pre-booking for the upcoming flagship launch has been secured.\n\n"
        f"📋 *Booking ID:* `{booking.booking_no}`\n"
        f"🏆 *Queue Rank:* *#{booking.queue_priority} (Priority VIP Allocation)*\n"
        f"📲 *Device:* *{booking.brand} {booking.model}*\n"
        f"🎨 *Variant / Color:* {booking.variant}\n"
    )
    if booking.expected_price and booking.expected_price > 0:
        msg += f"💵 *Estimated Price:* ₹{booking.expected_price:,.2f}\n"

    msg += (
        f"💰 *Token Advance Paid:* *₹{booking.token_advance:,.2f}* ({booking.payment_mode})\n"
        f"💳 *Remaining Balance:* ₹{booking.remaining_balance:,.2f} (due upon delivery)\n"
        f"📅 *Booked On:* {booking.created_at.strftime('%d-%b-%Y %I:%M %p')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 *LIVE DIGITAL BOOKING PASS & QUEUE TRACKER:*\n"
        f"📲 *View Live Status:* {pass_url}\n"
        f"📄 *Printable Advance Voucher:* {receipt_url}\n\n"
        f"✨ *Next Steps:* When the shipment arrives, the system will allocate your priority unit and notify you immediately for store pickup.\n\n"
        f"📞 *Customer Support:* {Config.SHOP_PHONE}\n"
        f"📍 *Store Address:* {Config.SHOP_ADDRESS}\n"
        f"Thank you for choosing *{Config.SHOP_NAME}*!"
    )
    return msg


def build_whatsapp_stock_arrival_alert(booking, host_url=None):
    """Formats an alert informing the customer that their pre-ordered flagship has arrived and is ready for pickup."""
    cust_name = booking.customer.name if booking.customer else "Customer"
    imei_text = f"\n🔍 *Reserved Device IMEI:* `{booking.allocated_mobile.imei_1}`" if booking.allocated_mobile else ""
    base = host_url.rstrip('/') if host_url else "http://127.0.0.1:5000"
    pass_url = f"{base}/prebook/pass/{booking.booking_no}"

    msg = (
        f"🎉 *YOUR FLAGSHIP HAS ARRIVED! — {Config.SHOP_NAME}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Dear *{cust_name}*,\n"
        f"Exciting news! Your pre-booked smartphone is now in stock and reserved exclusively for you!\n\n"
        f"📋 *Booking ID:* `{booking.booking_no}` (Queue #{booking.queue_priority})\n"
        f"📱 *Handset:* *{booking.brand} {booking.model}* ({booking.variant}){imei_text}\n"
        f"💰 *Token Advance Deducted:* -₹{booking.token_advance:,.2f}\n"
        f"💵 *Final Balance Payable:* *₹{booking.remaining_balance:,.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏰ *Pickup Notice:* Please visit our showroom within *48 Hours* to complete POS billing and pick up your brand new handset.\n"
        f"🎫 *Show this digital pass at the counter:* {pass_url}\n\n"
        f"📞 *Helpline:* {Config.SHOP_PHONE}\n"
        f"📍 *Store Address:* {Config.SHOP_ADDRESS}"
    )
    return msg


def build_whatsapp_lost_sale_alert(lost_sale, mobile, host_url=None):
    """Alerts a customer that a previously requested out-of-stock model has just arrived."""
    msg = (
        f"🔔 *PRODUCT IN-STOCK ALERT — {Config.SHOP_NAME}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Hello *{lost_sale.customer_name}*,\n"
        f"You previously requested the *{lost_sale.brand} {lost_sale.model}*.\n\n"
        f"✨ Fresh stock has just arrived at our store!\n"
        f"📱 *Model:* {mobile.brand} {mobile.model} ({mobile.ram}/{mobile.storage}) - {mobile.color}\n"
        f"💰 *Price:* ₹{mobile.selling_price:,.2f}\n"
        f"🛡️ *Warranty:* {mobile.warranty_months} Months Official Warranty\n\n"
        f"⚡ Units are limited. Reply to this message or visit our store today to reserve your device!\n\n"
        f"📞 *Call Us:* {Config.SHOP_PHONE}\n"
        f"📍 *Store Address:* {Config.SHOP_ADDRESS}"
    )
    return msg


def _send_smtp_multipart_mail(to_email, subject, plain_content, html_content, attachment_bytes=None, attachment_filename=None):
    """
    Internal helper to dispatch branded multipart HTML/Plain emails via Gmail SMTP with optional attachments.
    """
    owner_email = (Config.MAIL_USERNAME or '').strip()
    clean_password = (Config.MAIL_PASSWORD or '').replace(' ', '').strip()
    mail_user = (Config.MAIL_USERNAME or '').strip()

    if not to_email:
        return False, "No recipient email provided."

    if mail_user and clean_password:
        try:
            msg = MIMEMultipart('mixed')
            msg['From'] = Config.MAIL_DEFAULT_SENDER
            msg['To'] = to_email
            msg['Subject'] = subject

            # BCC store owner copy
            recipients = [to_email]
            if owner_email and owner_email != to_email:
                recipients.append(owner_email)

            alt_part = MIMEMultipart('alternative')
            alt_part.attach(MIMEText(plain_content, 'plain', 'utf-8'))
            alt_part.attach(MIMEText(html_content, 'html', 'utf-8'))
            msg.attach(alt_part)

            if attachment_bytes and attachment_filename:
                pdf_attachment = MIMEApplication(attachment_bytes, _subtype="pdf")
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename=attachment_filename)
                msg.attach(pdf_attachment)

            with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=20) as server:
                if Config.MAIL_USE_TLS:
                    server.starttls()
                server.login(mail_user, clean_password)
                server.send_message(msg, from_addr=Config.MAIL_DEFAULT_SENDER, to_addrs=recipients)

            return True, f"Email dispatched successfully to {to_email} via Gmail."
        except Exception as e:
            err_msg = f"Email delivery failed: {str(e)}"
            print(f"[MAIL ERROR] {err_msg}")
            return False, err_msg
    else:
        return True, f"[SIMULATION] Email prepared for {to_email} (Subject: {subject})"


def send_email_preorder_confirmation(booking, recipient_email=None, host_url=None):
    """
    Dispatches a branded HTML Pre-Order Confirmation email via Gmail SMTP
    to the customer upon reserving an upcoming flagship mobile device.
    """
    cust_name = booking.customer.name if booking.customer else "Valued Customer"
    cust_phone = booking.customer.phone if booking.customer else "N/A"
    cust_email = booking.customer.email.strip() if (booking.customer and booking.customer.email) else None
    to_email = (recipient_email or cust_email or '').strip()

    if not to_email:
        return False, "No recipient email address available for pre-order confirmation."

    base = (host_url or "http://127.0.0.1:5000").rstrip('/')
    pass_url = f"{base}/prebook/pass/{booking.booking_no}"
    expected_delivery_str = booking.expected_delivery_date.strftime('%d %B %Y') if booking.expected_delivery_date else "To be announced upon shipment arrival"

    subject = f"📱 Pre-Order Confirmed: {booking.brand} {booking.model} (Pass #{booking.booking_no}) — {Config.SHOP_NAME}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 20px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
        <div style="max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
            
            <!-- Branded Header -->
            <div style="background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%); padding: 28px 24px; color: #ffffff;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">{Config.SHOP_NAME}</h1>
                        <p style="margin: 4px 0 0; font-size: 12px; opacity: 0.9;">Flagship Mobile Pre-Order & Priority Queue</p>
                    </div>
                </div>
                <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.2); font-size: 12px; display: flex; justify-content: space-between;">
                    <span><b>Booking Pass:</b> #{booking.booking_no}</span>
                    <span><b>Booked On:</b> {booking.created_at.strftime('%d-%b-%Y %I:%M %p')}</span>
                </div>
            </div>

            <!-- Main Body -->
            <div style="padding: 24px;">
                <p style="font-size: 15px; margin-top: 0;">Dear <strong>{cust_name}</strong>,</p>
                <p style="font-size: 13.5px; color: #475569; line-height: 1.5;">
                    Congratulations! Your pre-order for the <strong>{booking.brand} {booking.model}</strong> has been confirmed and registered in our priority store allocation queue.
                </p>

                <!-- Priority Rank Highlight Card -->
                <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(168, 85, 247, 0.08)); border: 1.5px solid rgba(99, 102, 241, 0.3); border-radius: 10px; padding: 16px 20px; margin: 18px 0; display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #4f46e5; letter-spacing: 0.5px;">Official Allocation Priority</div>
                        <div style="font-size: 20px; font-weight: 800; color: #1e1b4b; margin-top: 2px;">
                            VIP Queue Position: #{booking.queue_priority}
                        </div>
                    </div>
                    <span style="background: #4f46e5; color: #ffffff; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700;">
                        ✓ Confirmed
                    </span>
                </div>

                <!-- Pre-Order Details Table -->
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 13px;">
                    <tbody>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 10px; color: #64748b; width: 40%;">Handset Model</td>
                            <td style="padding: 10px; font-weight: 700; color: #0f172a;">📱 {booking.brand} {booking.model}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 10px; color: #64748b;">Selected Variant</td>
                            <td style="padding: 10px; font-weight: 600; color: #334155;">🎨 {booking.variant}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 10px; color: #64748b;">Estimated Retail Price</td>
                            <td style="padding: 10px; font-weight: 600; color: #334155;">₹{booking.expected_price:,.2f}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0; background: #f0fdf4;">
                            <td style="padding: 10px; color: #15803d; font-weight: 600;">Token Advance Paid</td>
                            <td style="padding: 10px; font-weight: 800; color: #15803d;">₹{booking.token_advance:,.2f} ({booking.payment_mode} • {booking.payment_status})</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 10px; color: #64748b;">Estimated Balance Payable</td>
                            <td style="padding: 10px; font-weight: 700; color: #0f172a;">₹{booking.remaining_balance:,.2f} (Due at Pickup)</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; color: #64748b;">Expected Availability</td>
                            <td style="padding: 10px; font-weight: 600; color: #334155;">📅 {expected_delivery_str}</td>
                        </tr>
                    </tbody>
                </table>

                <!-- Digital Booking Pass CTA -->
                <div style="text-align: center; margin: 26px 0 20px;">
                    <a href="{pass_url}" style="display: inline-block; background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%); color: #ffffff; text-decoration: none; padding: 13px 28px; border-radius: 8px; font-weight: 700; font-size: 14px; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35);">
                        🎫 View Live Digital Booking Pass
                    </a>
                    <div style="font-size: 11.5px; color: #64748b; margin-top: 8px;">Track your live queue position anytime on your mobile phone</div>
                </div>

                <!-- Next Steps Info Box -->
                <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 14px; margin: 20px 0; font-size: 12.5px; color: #1e40af;">
                    <div style="font-weight: 700; margin-bottom: 4px;">⚡ What Happens Next?</div>
                    <div>
                        As soon as the new stock shipment arrives at our store, our auto-allocation system will reserve your phone based on your queue position and send an immediate <strong>Stock Arrived Gmail alert</strong> to notify you for pickup.
                    </div>
                </div>

                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />

                <!-- Footer -->
                <div style="font-size: 11.5px; color: #64748b; text-align: center; line-height: 1.6;">
                    <strong>{Config.SHOP_NAME}</strong><br/>
                    {Config.SHOP_ADDRESS}<br/>
                    📞 Phone: {Config.SHOP_PHONE} &nbsp;|&nbsp; ✉️ Email: {Config.SHOP_EMAIL}<br/>
                    <span style="color: #94a3b8;">This is an automated pre-booking confirmation from MOBIX ERP.</span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    plain_content = f"""
{Config.SHOP_NAME} — Pre-Order Confirmed
==================================================
Booking Pass: #{booking.booking_no}
Queue Position: #{booking.queue_priority}
Date: {booking.created_at.strftime('%d-%b-%Y %I:%M %p')}

Dear {cust_name},
Your pre-order for the {booking.brand} {booking.model} has been confirmed.

PRE-ORDER SUMMARY:
- Handset: {booking.brand} {booking.model} ({booking.variant})
- Estimated Price: ₹{booking.expected_price:,.2f}
- Token Advance Paid: ₹{booking.token_advance:,.2f} ({booking.payment_mode})
- Balance Remaining: ₹{booking.remaining_balance:,.2f}
- Expected Delivery: {expected_delivery_str}

LIVE DIGITAL PASS:
{pass_url}

When your handset arrives in stock, you will receive an automatic Stock Arrival notification via Gmail!

Store: {Config.SHOP_NAME}, {Config.SHOP_ADDRESS}
Phone: {Config.SHOP_PHONE}
    """

    return _send_smtp_multipart_mail(to_email, subject, plain_content, html_content)


def send_email_stock_arrival(booking, recipient_email=None, host_url=None):
    """
    Dispatches a high-priority HTML Stock Arrived notification email via Gmail SMTP
    alerting the customer that their pre-ordered mobile has arrived in stock and is reserved for pickup.
    """
    cust_name = booking.customer.name if booking.customer else "Valued Customer"
    cust_phone = booking.customer.phone if booking.customer else "N/A"
    cust_email = booking.customer.email.strip() if (booking.customer and booking.customer.email) else None
    to_email = (recipient_email or cust_email or '').strip()

    if not to_email:
        return False, "No recipient email address available for stock arrival alert."

    base = (host_url or "http://127.0.0.1:5000").rstrip('/')
    pass_url = f"{base}/prebook/pass/{booking.booking_no}"
    allocated_imei = booking.allocated_mobile.imei_1 if (booking.allocated_mobile and booking.allocated_mobile.imei_1) else "Assigned In-Stock Unit"

    subject = f"🎉 Stock Arrived & Ready for Pickup: {booking.brand} {booking.model} (Pass #{booking.booking_no}) — {Config.SHOP_NAME}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 20px; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
        <div style="max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
            
            <!-- Branded Header -->
            <div style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); padding: 28px 24px; color: #ffffff;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">{Config.SHOP_NAME}</h1>
                        <p style="margin: 4px 0 0; font-size: 12px; opacity: 0.9;">🎉 Stock Arrived & Reserved for Pickup</p>
                    </div>
                </div>
                <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.2); font-size: 12px; display: flex; justify-content: space-between;">
                    <span><b>Booking Pass:</b> #{booking.booking_no}</span>
                    <span><b>Queue Rank:</b> #{booking.queue_priority} (Allocated)</span>
                </div>
            </div>

            <!-- Main Body -->
            <div style="padding: 24px;">
                <p style="font-size: 15px; margin-top: 0;">Dear <strong>{cust_name}</strong>,</p>
                <p style="font-size: 13.5px; color: #475569; line-height: 1.5;">
                    Great news! Fresh shipment has arrived, and your pre-ordered <strong>{booking.brand} {booking.model}</strong> has officially been <strong>allocated and reserved exclusively for you</strong>!
                </p>

                <!-- Stock Arrival Announcement Card -->
                <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(5, 150, 105, 0.08)); border: 1.5px solid rgba(16, 185, 129, 0.35); border-radius: 10px; padding: 16px 20px; margin: 18px 0; display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: #059669; letter-spacing: 0.5px;">Stock Status</div>
                        <div style="font-size: 20px; font-weight: 800; color: #065f46; margin-top: 2px;">
                            Device In Stock & Ready for Pickup!
                        </div>
                    </div>
                    <span style="background: #10b981; color: #ffffff; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700;">
                        Ready
                    </span>
                </div>

                <!-- Allocated Device Details Table -->
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 13px;">
                    <tbody>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 10px; color: #64748b; width: 40%;">Reserved Handset</td>
                            <td style="padding: 10px; font-weight: 700; color: #0f172a;">📱 {booking.brand} {booking.model} ({booking.variant})</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 10px; color: #64748b;">Allocated Device IMEI</td>
                            <td style="padding: 10px; font-weight: 700; color: #4f46e5; font-family: monospace;">{allocated_imei}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0; background: #f0fdf4;">
                            <td style="padding: 10px; color: #15803d; font-weight: 600;">Advance Credited</td>
                            <td style="padding: 10px; font-weight: 800; color: #15803d;">-₹{booking.token_advance:,.2f} (Deducted from Bill)</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 10px; color: #64748b; font-weight: 600;">Final Balance Payable at Store</td>
                            <td style="padding: 10px; font-weight: 800; font-size: 15px; color: #0f172a;">₹{booking.remaining_balance:,.2f}</td>
                        </tr>
                    </tbody>
                </table>

                <!-- Pickup Instructions Box -->
                <div style="background: #fffbeb; border: 1.5px solid #fef3c7; border-left: 4px solid #f59e0b; border-radius: 8px; padding: 16px; margin: 20px 0;">
                    <div style="font-weight: 800; color: #b45309; font-size: 13.5px; margin-bottom: 6px;">
                        ⏰ 48-Hour Priority Reservation Window
                    </div>
                    <div style="font-size: 12.5px; color: #78350f; line-height: 1.5;">
                        Your handset is reserved under your name. Please visit our showroom within <strong>48 Hours</strong> to inspect your new device, complete final checkout, and collect your handset.
                    </div>
                    <div style="margin-top: 10px; font-size: 12px; color: #92400e;">
                        📍 <strong>Showroom:</strong> {Config.SHOP_ADDRESS}<br/>
                        📞 <strong>Store Contact:</strong> {Config.SHOP_PHONE}
                    </div>
                </div>

                <!-- Digital Booking Pass CTA -->
                <div style="text-align: center; margin: 24px 0 20px;">
                    <a href="{pass_url}" style="display: inline-block; background: linear-gradient(135deg, #059669 0%, #10b981 100%); color: #ffffff; text-decoration: none; padding: 13px 28px; border-radius: 8px; font-weight: 700; font-size: 14px; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);">
                        🎫 Open Live Digital Pickup Pass
                    </a>
                    <div style="font-size: 11.5px; color: #64748b; margin-top: 8px;">Show this digital pass at the billing counter for instant pickup</div>
                </div>

                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />

                <!-- Footer -->
                <div style="font-size: 11.5px; color: #64748b; text-align: center; line-height: 1.6;">
                    <strong>{Config.SHOP_NAME}</strong><br/>
                    {Config.SHOP_ADDRESS}<br/>
                    📞 Phone: {Config.SHOP_PHONE} &nbsp;|&nbsp; ✉️ Email: {Config.SHOP_EMAIL}<br/>
                    <span style="color: #94a3b8;">This is an automated stock arrival alert from MOBIX ERP.</span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    plain_content = f"""
🎉 {Config.SHOP_NAME} — STOCK ARRIVED & READY FOR PICKUP!
==================================================
Booking Pass: #{booking.booking_no}
Queue Position: #{booking.queue_priority} (Allocated)

Dear {cust_name},
Great news! Your pre-ordered {booking.brand} {booking.model} has arrived in stock and is reserved exclusively for you!

ALLOCATED DEVICE DETAILS:
- Handset: {booking.brand} {booking.model} ({booking.variant})
- Reserved IMEI: {allocated_imei}
- Token Advance Credited: -₹{booking.token_advance:,.2f}
- Balance Payable at Pickup: ₹{booking.remaining_balance:,.2f}

SHOWROOM PICKUP INSTRUCTIONS:
- Store Address: {Config.SHOP_ADDRESS}
- Contact Phone: {Config.SHOP_PHONE}
- Please visit within 48 hours to complete POS checkout and collect your phone.

SHOW THIS PASS AT THE COUNTER:
{pass_url}

Store: {Config.SHOP_NAME}
    """

    return _send_smtp_multipart_mail(to_email, subject, plain_content, html_content)
 
 
def async_send_preorder_confirmation(app, booking_id, recipient_email=None, host_url=None):
    """
    Spawns a daemon thread with Flask application context to load PreBooking and dispatch
    pre-order confirmation email via Gmail SMTP without blocking the HTTP request or
    suffering detached SQLAlchemy session issues.
    """
    def _worker():
        with app.app_context():
            try:
                from models import db, PreBooking
                booking = db.session.get(PreBooking, booking_id)
                if not booking:
                    print(f"[PREORDER MAIL WORKER] Booking #{booking_id} not found.")
                    return
                send_email_preorder_confirmation(booking, recipient_email=recipient_email, host_url=host_url)
            except Exception as e:
                print(f"[PREORDER MAIL WORKER ERROR] {e}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return thread


def async_send_stock_arrival(app, booking_id, recipient_email=None, host_url=None):
    """
    Spawns a daemon thread with Flask application context to load PreBooking and dispatch
    stock arrival notification email via Gmail SMTP without blocking the HTTP request or
    suffering detached SQLAlchemy session issues.
    """
    def _worker():
        with app.app_context():
            try:
                from models import db, PreBooking
                booking = db.session.get(PreBooking, booking_id)
                if not booking:
                    print(f"[STOCK ARRIVAL WORKER] Booking #{booking_id} not found.")
                    return
                send_email_stock_arrival(booking, recipient_email=recipient_email, host_url=host_url)
            except Exception as e:
                print(f"[STOCK ARRIVAL WORKER ERROR] {e}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return thread
