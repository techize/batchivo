"""Email service using Brevo for transactional emails."""

import logging
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Brevo API endpoint for transactional emails
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailService:
    """Service for sending transactional emails via Brevo."""

    def __init__(self):
        """Initialize Brevo client."""
        settings = get_settings()
        self.api_key = settings.brevo_api_key
        self.from_address = settings.email_from_address
        self.from_name = settings.email_from_name
        self.frontend_base_url = settings.frontend_base_url.rstrip("/")

        # Shop branding configuration
        self.shop_name = settings.shop_name
        self.shop_tagline = settings.shop_tagline
        self.shop_website_url = settings.shop_website_url.rstrip("/")
        self.shop_orders_email = settings.shop_orders_email
        self.shop_support_email = settings.shop_support_email
        self.shop_social_handle = settings.shop_social_handle
        self.shop_brand_color = settings.shop_brand_color

    @property
    def is_configured(self) -> bool:
        """Check if email service is configured."""
        return bool(self.api_key)

    def _send_email_sync(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        reply_to: str | None = None,
    ) -> bool:
        """Synchronous email sending via Brevo (internal helper)."""
        try:
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "sender": {"name": self.from_name, "email": self.from_address},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content,
            }
            if reply_to:
                payload["replyTo"] = {"email": reply_to}

            with httpx.Client(timeout=30.0) as client:
                response = client.post(BREVO_API_URL, json=payload, headers=headers)
                response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def _send_email_async(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        reply_to: str | None = None,
    ) -> bool:
        """Async email sending via Brevo."""
        try:
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "sender": {"name": self.from_name, "email": self.from_address},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content,
            }
            if reply_to:
                payload["replyTo"] = {"email": reply_to}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(BREVO_API_URL, json=payload, headers=headers)
                response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_order_confirmation(
        self,
        to_email: str,
        customer_name: str,
        order_number: str,
        order_items: list[dict],
        subtotal: float,
        shipping_cost: float,
        total: float,
        shipping_address: dict,
        receipt_url: Optional[str] = None,
    ) -> bool:
        """
        Send order confirmation email to customer.

        Args:
            to_email: Customer email address
            customer_name: Customer name
            order_number: Order number (e.g., MF-20251218-001)
            order_items: List of items with name, quantity, price
            subtotal: Order subtotal
            shipping_cost: Shipping cost
            total: Order total
            shipping_address: Shipping address dict
            receipt_url: Optional Square receipt URL

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping order confirmation")
            return False

        # Build order items HTML
        items_html = ""
        for item in order_items:
            items_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{item["name"]}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{item["quantity"]}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">£{item["price"]:.2f}</td>
            </tr>
            """

        # Build shipping address
        address_lines = [
            shipping_address.get("address_line1", ""),
            shipping_address.get("address_line2", ""),
            shipping_address.get("city", ""),
            shipping_address.get("county", ""),
            shipping_address.get("postcode", ""),
            shipping_address.get("country", ""),
        ]
        address_html = "<br>".join(line for line in address_lines if line)

        # Receipt link section
        receipt_section = ""
        if receipt_url:
            receipt_section = f"""
            <p style="margin-top: 20px;">
                <a href="{receipt_url}" style="color: #8b5cf6;">View Payment Receipt</a>
            </p>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Order Confirmation - {order_number}</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: {self.shop_brand_color}; margin-bottom: 5px;">{self.shop_name}</h1>
                <p style="color: #666; margin: 0;">{self.shop_tagline}</p>
            </div>

            <div style="background: #f9fafb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #111; margin-top: 0;">Thank you for your order!</h2>
                <p>Hi {customer_name},</p>
                <p>We've received your order and are getting it ready. We'll send you another email when your order ships.</p>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #111;">Order #{order_number}</h3>

                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <thead>
                        <tr style="background: #f3f4f6;">
                            <th style="padding: 10px; text-align: left;">Item</th>
                            <th style="padding: 10px; text-align: center;">Qty</th>
                            <th style="padding: 10px; text-align: right;">Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>

                <div style="border-top: 2px solid #e5e7eb; padding-top: 15px; margin-top: 15px;">
                    <table style="width: 100%;">
                        <tr>
                            <td style="padding: 5px 0;">Subtotal:</td>
                            <td style="text-align: right;">£{subtotal:.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 5px 0;">Shipping:</td>
                            <td style="text-align: right;">£{shipping_cost:.2f}</td>
                        </tr>
                        <tr style="font-weight: bold; font-size: 1.1em;">
                            <td style="padding: 10px 0 5px;">Total:</td>
                            <td style="text-align: right; padding: 10px 0 5px;">£{total:.2f}</td>
                        </tr>
                    </table>
                </div>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #111;">Shipping Address</h3>
                <p style="margin: 0; line-height: 1.6;">
                    {address_html}
                </p>
            </div>

            {receipt_section}

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.9em;">
                <p>Questions about your order? Reply to this email or contact us at {self.shop_orders_email}</p>
                <p style="margin-top: 15px;">
                    <a href="{self.shop_website_url}" style="color: {self.shop_brand_color};">{self.shop_website_url.replace("https://", "").replace("http://", "")}</a>
                </p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(to_email, f"Order Confirmation - {order_number}", html_content):
            logger.info(f"Order confirmation email sent to {to_email} for order {order_number}")
            return True
        else:
            logger.error(f"Failed to send order confirmation email to {to_email}")
            return False

    def send_refund_confirmation(
        self,
        to_email: str,
        customer_name: str,
        order_number: str,
        refund_amount: float,
        currency: str = "GBP",
        reason: Optional[str] = None,
    ) -> bool:
        """
        Send refund confirmation email to customer.

        Args:
            to_email: Customer email address
            customer_name: Customer name
            order_number: Order number
            refund_amount: Amount refunded
            currency: Currency code
            reason: Optional refund reason

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping refund confirmation")
            return False

        # Currency symbol mapping
        currency_symbols = {"GBP": "£", "USD": "$", "EUR": "€"}
        symbol = currency_symbols.get(currency, currency)

        reason_section = ""
        if reason:
            reason_section = f"""
            <div style="background: #f3f4f6; border-radius: 4px; padding: 15px; margin: 20px 0;">
                <strong>Reason:</strong> {reason}
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Refund Confirmation - {order_number}</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: {self.shop_brand_color}; margin-bottom: 5px;">{self.shop_name}</h1>
                <p style="color: #666; margin: 0;">{self.shop_tagline}</p>
            </div>

            <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #92400e; margin-top: 0;">Refund Processed</h2>
                <p>Hi {customer_name},</p>
                <p>We've processed a refund for your order <strong>#{order_number}</strong>.</p>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #111;">Refund Details</h3>
                <table style="width: 100%;">
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid #eee;">Order Number:</td>
                        <td style="padding: 10px 0; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">{order_number}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0;">Refund Amount:</td>
                        <td style="padding: 10px 0; text-align: right; font-weight: bold; font-size: 1.2em; color: #059669;">{symbol}{refund_amount:.2f}</td>
                    </tr>
                </table>

                {reason_section}

                <p style="margin-top: 20px; color: #666; font-size: 0.9em;">
                    The refund will be credited to your original payment method within 5-10 business days,
                    depending on your bank or card issuer.
                </p>
            </div>

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.9em;">
                <p>Questions about your refund? Reply to this email or contact us at {self.shop_orders_email}</p>
                <p style="margin-top: 15px;">
                    <a href="{self.shop_website_url}" style="color: {self.shop_brand_color};">{self.shop_website_url.replace("https://", "").replace("http://", "")}</a>
                </p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(to_email, f"Refund Confirmation - {order_number}", html_content):
            logger.info(f"Refund confirmation email sent to {to_email} for order {order_number}")
            return True
        else:
            logger.error(f"Failed to send refund confirmation email to {to_email}")
            return False

    def send_contact_notification(
        self,
        name: str,
        email: str,
        subject: str,
        message: str,
        reference: str,
        order_number: Optional[str] = None,
    ) -> bool:
        """
        Send contact form notification to shop owner and confirmation to customer.

        Args:
            name: Customer name
            email: Customer email address
            subject: Subject category (e.g., 'order', 'custom', 'feedback')
            message: Customer message
            reference: Contact reference number
            order_number: Optional related order number

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping contact notification")
            return False

        # Map subject codes to readable labels
        subject_labels = {
            "order": "Order Inquiry",
            "custom": "Custom Request",
            "wholesale": "Wholesale/Events",
            "feedback": "Feedback",
            "other": "General Inquiry",
        }
        subject_label = subject_labels.get(subject, subject.title())

        order_section = ""
        if order_number:
            order_section = f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">Related Order:</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{order_number}</td>
            </tr>
            """

        # Email to shop owner
        owner_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>New Contact Form Submission - {reference}</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: {self.shop_brand_color}; margin-bottom: 5px;">{self.shop_name}</h1>
                <p style="color: #666; margin: 0;">New Contact Form Submission</p>
            </div>

            <div style="background: #172c3c; border-radius: 8px; padding: 20px; margin-bottom: 20px; color: #BDBCB9;">
                <h2 style="color: #fff; margin-top: 0;">Reference: {reference}</h2>
                <p>You've received a new message from the website contact form.</p>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #111;">Contact Details</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold; width: 120px;">Name:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">Email:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">
                            <a href="mailto:{email}" style="color: {self.shop_brand_color};">{email}</a>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold;">Subject:</td>
                        <td style="padding: 10px; border-bottom: 1px solid #eee;">{subject_label}</td>
                    </tr>
                    {order_section}
                </table>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #111;">Message</h3>
                <div style="background: #f9fafb; border-radius: 4px; padding: 15px; white-space: pre-wrap;">{message}</div>
            </div>

            <div style="text-align: center; margin-top: 20px;">
                <a href="mailto:{email}?subject=Re: {subject_label} - {reference}"
                   style="display: inline-block; background: {self.shop_brand_color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Reply to {name}
                </a>
            </div>
        </body>
        </html>
        """

        # Confirmation email to customer
        customer_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>We've received your message - {reference}</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: {self.shop_brand_color}; margin-bottom: 5px;">{self.shop_name}</h1>
                <p style="color: #666; margin: 0;">{self.shop_tagline}</p>
            </div>

            <div style="background: #172c3c; border-radius: 8px; padding: 20px; margin-bottom: 20px; color: #BDBCB9;">
                <h2 style="color: #fff; margin-top: 0;">Thanks for getting in touch!</h2>
                <p>Hi {name},</p>
                <p>We've received your message and will get back to you within 24-48 hours during weekdays.</p>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; color: #111;">Your Reference: {reference}</h3>
                <p style="color: #666; font-size: 0.9em;">Please keep this reference number in case you need to follow up.</p>

                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee;">
                    <strong>Subject:</strong> {subject_label}<br>
                    <strong>Your message:</strong>
                    <div style="background: #f9fafb; border-radius: 4px; padding: 15px; margin-top: 10px; white-space: pre-wrap; font-size: 0.9em;">{message}</div>
                </div>
            </div>

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.9em;">
                <p>In the meantime, feel free to browse our shop!</p>
                <p style="margin-top: 15px;">
                    <a href="{self.shop_website_url}" style="color: {self.shop_brand_color};">{self.shop_website_url.replace("https://", "").replace("http://", "")}</a>
                </p>
            </div>
        </body>
        </html>
        """

        try:
            # Send to shop owner
            if not self._send_email_sync(
                self.shop_support_email,
                f"[Contact Form] {subject_label} from {name} - {reference}",
                owner_html,
                reply_to=email,
            ):
                logger.error(f"Failed to send contact notification to shop owner for {reference}")
                return False
            logger.info(f"Contact notification sent to shop owner for {reference}")

            # Send confirmation to customer
            if not self._send_email_sync(
                email,
                f"We've received your message - {reference}",
                customer_html,
            ):
                logger.error(f"Failed to send contact confirmation to {email}")
                return False
            logger.info(f"Contact confirmation sent to {email} for {reference}")

            return True
        except Exception as e:
            logger.error(f"Failed to send contact notification: {e}")
            return False

    def send_order_shipped(
        self,
        to_email: str,
        customer_name: str,
        order_number: str,
        tracking_number: Optional[str] = None,
        tracking_url: Optional[str] = None,
        shipping_method: str = "Royal Mail",
    ) -> bool:
        """
        Send order shipped notification email to customer.

        Args:
            to_email: Customer email address
            customer_name: Customer name
            order_number: Order number
            tracking_number: Optional tracking number
            tracking_url: Optional tracking URL
            shipping_method: Shipping carrier/method

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping shipped notification")
            return False

        # Build tracking section
        tracking_section = ""
        if tracking_number:
            if tracking_url:
                tracking_section = f"""
                <div style="background: #f0fdf4; border: 1px solid #22c55e; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0 0 10px; color: #166534;"><strong>Tracking Number:</strong></p>
                    <p style="margin: 0 0 15px; font-size: 1.3em; font-family: monospace; color: #111;">{tracking_number}</p>
                    <a href="{tracking_url}" style="display: inline-block; background: #22c55e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Track Your Package
                    </a>
                </div>
                """
            else:
                tracking_section = f"""
                <div style="background: #f0fdf4; border: 1px solid #22c55e; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0 0 10px; color: #166534;"><strong>Tracking Number:</strong></p>
                    <p style="margin: 0; font-size: 1.3em; font-family: monospace; color: #111;">{tracking_number}</p>
                    <p style="margin: 10px 0 0; color: #666; font-size: 0.9em;">
                        Track your parcel at <a href="https://www.royalmail.com/track-your-item" style="color: #8b5cf6;">royalmail.com</a>
                    </p>
                </div>
                """
        else:
            tracking_section = """
            <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 15px; margin: 20px 0;">
                <p style="margin: 0; color: #92400e;">
                    Tracking information will be sent separately once your package is scanned by the carrier.
                </p>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Your Order Has Shipped! - {order_number}</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: {self.shop_brand_color}; margin-bottom: 5px;">{self.shop_name}</h1>
                <p style="color: #666; margin: 0;">{self.shop_tagline}</p>
            </div>

            <div style="background: #f0fdf4; border-radius: 8px; padding: 20px; margin-bottom: 20px; text-align: center;">
                <div style="font-size: 3em; margin-bottom: 10px;">📦</div>
                <h2 style="color: #166534; margin: 0 0 10px;">Your order is on its way!</h2>
                <p style="margin: 0; color: #333;">Order <strong>#{order_number}</strong></p>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <p>Hi {customer_name},</p>
                <p>Great news! Your order has been dispatched and is making its way to you via <strong>{shipping_method}</strong>.</p>

                {tracking_section}

                <div style="background: #f9fafb; border-radius: 4px; padding: 15px; margin-top: 20px;">
                    <p style="margin: 0 0 10px; font-weight: bold;">What happens next?</p>
                    <ul style="margin: 0; padding-left: 20px; color: #666;">
                        <li style="margin-bottom: 5px;">Your parcel is on its way to you</li>
                        <li style="margin-bottom: 5px;">Standard delivery typically takes 2-5 working days</li>
                        <li>We'll send another email when your order is delivered</li>
                    </ul>
                </div>
            </div>

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.9em;">
                <p>Questions about your delivery? Reply to this email or contact us at {self.shop_orders_email}</p>
                <p style="margin-top: 15px;">
                    <a href="{self.shop_website_url}" style="color: {self.shop_brand_color};">{self.shop_website_url.replace("https://", "").replace("http://", "")}</a>
                </p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(
            to_email, f"Your Order Has Shipped! - {order_number}", html_content
        ):
            logger.info(f"Shipped notification email sent to {to_email} for order {order_number}")
            return True
        else:
            logger.error(f"Failed to send shipped notification email to {to_email}")
            return False

    def send_order_delivered(
        self,
        to_email: str,
        customer_name: str,
        order_number: str,
    ) -> bool:
        """
        Send order delivered notification email to customer.

        Args:
            to_email: Customer email address
            customer_name: Customer name
            order_number: Order number

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping delivered notification")
            return False

        # Build social section only if handle is configured
        social_section = ""
        if self.shop_social_handle:
            social_section = f"""
                <div style="background: #faf5ff; border: 1px solid {self.shop_brand_color}; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0 0 15px; color: #5b21b6; font-weight: bold;">We'd love to hear from you!</p>
                    <p style="margin: 0; color: #666; font-size: 0.95em;">
                        If you're happy with your purchase, please consider sharing a photo on social media
                        and tagging us <strong>{self.shop_social_handle}</strong>
                    </p>
                </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Your Order Has Been Delivered! - {order_number}</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: {self.shop_brand_color}; margin-bottom: 5px;">{self.shop_name}</h1>
                <p style="color: #666; margin: 0;">{self.shop_tagline}</p>
            </div>

            <div style="background: #f0fdf4; border-radius: 8px; padding: 20px; margin-bottom: 20px; text-align: center;">
                <div style="font-size: 3em; margin-bottom: 10px;">✅</div>
                <h2 style="color: #166534; margin: 0 0 10px;">Your order has arrived!</h2>
                <p style="margin: 0; color: #333;">Order <strong>#{order_number}</strong></p>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <p>Hi {customer_name},</p>
                <p>Your order has been delivered! We hope you love your new items. 🎉</p>

                {social_section}

                <div style="background: #f9fafb; border-radius: 4px; padding: 15px; margin-top: 20px;">
                    <p style="margin: 0 0 10px; font-weight: bold;">Something not right?</p>
                    <p style="margin: 0; color: #666; font-size: 0.95em;">
                        If there are any issues with your order, please don't hesitate to contact us.
                        We're here to help and want to make sure you're completely satisfied.
                    </p>
                </div>
            </div>

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.9em;">
                <p>Thank you for shopping with {self.shop_name}!</p>
                <p>Questions or feedback? Reply to this email or contact us at {self.shop_orders_email}</p>
                <p style="margin-top: 15px;">
                    <a href="{self.shop_website_url}" style="color: {self.shop_brand_color};">{self.shop_website_url.replace("https://", "").replace("http://", "")}</a>
                </p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(
            to_email, f"Your Order Has Been Delivered! - {order_number}", html_content
        ):
            logger.info(f"Delivered notification email sent to {to_email} for order {order_number}")
            return True
        else:
            logger.error(f"Failed to send delivered notification email to {to_email}")
            return False

    def send_order_cancelled(
        self,
        to_email: str,
        customer_name: str,
        order_number: str,
        reason: Optional[str] = None,
        refund_info: Optional[str] = None,
    ) -> bool:
        """
        Send order cancellation notification email to customer.

        Args:
            to_email: Customer email address
            customer_name: Customer name
            order_number: Order number
            reason: Optional cancellation reason
            refund_info: Optional refund information

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping cancellation notification")
            return False

        # Build reason section
        reason_section = ""
        if reason:
            reason_section = f"""
            <div style="background: #f3f4f6; border-radius: 4px; padding: 15px; margin: 20px 0;">
                <strong>Reason:</strong> {reason}
            </div>
            """

        # Build refund section
        refund_section = ""
        if refund_info:
            refund_section = f"""
            <div style="background: #f0fdf4; border: 1px solid #22c55e; border-radius: 8px; padding: 15px; margin: 20px 0;">
                <p style="margin: 0; color: #166534;">
                    <strong>Refund Information:</strong> {refund_info}
                </p>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Order Cancelled - {order_number}</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: {self.shop_brand_color}; margin-bottom: 5px;">{self.shop_name}</h1>
                <p style="color: #666; margin: 0;">{self.shop_tagline}</p>
            </div>

            <div style="background: #fef2f2; border-radius: 8px; padding: 20px; margin-bottom: 20px; text-align: center;">
                <div style="font-size: 3em; margin-bottom: 10px;">❌</div>
                <h2 style="color: #991b1b; margin: 0 0 10px;">Order Cancelled</h2>
                <p style="margin: 0; color: #333;">Order <strong>#{order_number}</strong></p>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <p>Hi {customer_name},</p>
                <p>Your order <strong>#{order_number}</strong> has been cancelled.</p>

                {reason_section}
                {refund_section}

                <div style="background: #f9fafb; border-radius: 4px; padding: 15px; margin-top: 20px;">
                    <p style="margin: 0 0 10px; font-weight: bold;">What happens next?</p>
                    <p style="margin: 0; color: #666; font-size: 0.95em;">
                        If a payment was made, a refund will be processed to your original payment method
                        within 5-10 business days, depending on your bank or card issuer.
                    </p>
                </div>
            </div>

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.9em;">
                <p>Questions about your cancellation? Reply to this email or contact us at {self.shop_orders_email}</p>
                <p style="margin-top: 15px;">
                    <a href="{self.shop_website_url}" style="color: {self.shop_brand_color};">{self.shop_website_url.replace("https://", "").replace("http://", "")}</a>
                </p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(to_email, f"Order Cancelled - {order_number}", html_content):
            logger.info(
                f"Cancellation notification email sent to {to_email} for order {order_number}"
            )
            return True
        else:
            logger.error(f"Failed to send cancellation notification email to {to_email}")
            return False

    def send_customer_welcome(
        self,
        to_email: str,
        customer_name: str,
        verification_token: str,
        shop_name: str | None = None,
    ) -> bool:
        """
        Send welcome email to new customer with verification link.

        Args:
            to_email: Customer email address
            customer_name: Customer name
            verification_token: Email verification token
            shop_name: Shop name for branding (uses config default if not provided)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping welcome email")
            return False

        # Use configured shop name if not provided
        display_shop_name = shop_name or self.shop_name

        verification_url = f"{self.frontend_base_url}/verify-email?token={verification_token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to {display_shop_name}!</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: {self.shop_brand_color}; margin-bottom: 5px;">{display_shop_name}</h1>
                <p style="color: #666; margin: 0;">{self.shop_tagline}</p>
            </div>

            <div style="background: #faf5ff; border-radius: 8px; padding: 20px; margin-bottom: 20px; text-align: center;">
                <div style="font-size: 3em; margin-bottom: 10px;">🎉</div>
                <h2 style="color: #5b21b6; margin: 0 0 10px;">Welcome aboard!</h2>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <p>Hi {customer_name},</p>
                <p>Thank you for creating an account with {display_shop_name}! We're excited to have you.</p>
                <p>With your account, you can:</p>
                <ul style="color: #666;">
                    <li>Track your orders easily</li>
                    <li>Save your addresses for faster checkout</li>
                    <li>View your order history anytime</li>
                </ul>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" style="display: inline-block; background: {self.shop_brand_color}; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Verify Your Email
                    </a>
                </div>

                <p style="color: #666; font-size: 0.9em; text-align: center;">
                    Or copy and paste this link: <br>
                    <a href="{verification_url}" style="color: {self.shop_brand_color}; word-break: break-all;">{verification_url}</a>
                </p>
            </div>

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.9em;">
                <p>Happy shopping!</p>
                <p style="margin-top: 15px;">
                    <a href="{self.shop_website_url}" style="color: {self.shop_brand_color};">{self.shop_website_url.replace("https://", "").replace("http://", "")}</a>
                </p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(to_email, f"Welcome to {display_shop_name}!", html_content):
            logger.info(f"Welcome email sent to {to_email}")
            return True
        else:
            logger.error(f"Failed to send welcome email to {to_email}")
            return False

    def send_customer_verification(
        self,
        to_email: str,
        customer_name: str,
        verification_token: str,
        shop_name: str | None = None,
    ) -> bool:
        """
        Send email verification (resend).

        Args:
            to_email: Customer email address
            customer_name: Customer name
            verification_token: Email verification token
            shop_name: Shop name for branding (uses config default if not provided)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping verification email")
            return False

        # Use configured shop name if not provided
        display_shop_name = shop_name or self.shop_name

        verification_url = f"{self.frontend_base_url}/verify-email?token={verification_token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Verify Your Email</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: {self.shop_brand_color}; margin-bottom: 5px;">{display_shop_name}</h1>
                <p style="color: #666; margin: 0;">{self.shop_tagline}</p>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <p>Hi {customer_name},</p>
                <p>Please verify your email address by clicking the button below:</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" style="display: inline-block; background: {self.shop_brand_color}; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Verify Your Email
                    </a>
                </div>

                <p style="color: #666; font-size: 0.9em;">
                    This link will expire in 24 hours. If you didn't create an account, you can safely ignore this email.
                </p>
            </div>

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.9em;">
                <p style="margin-top: 15px;">
                    <a href="{self.shop_website_url}" style="color: {self.shop_brand_color};">{self.shop_website_url.replace("https://", "").replace("http://", "")}</a>
                </p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(to_email, "Verify Your Email", html_content):
            logger.info(f"Verification email sent to {to_email}")
            return True
        else:
            logger.error(f"Failed to send verification email to {to_email}")
            return False

    def send_customer_password_reset(
        self,
        to_email: str,
        customer_name: str,
        reset_token: str,
        shop_name: str | None = None,
    ) -> bool:
        """
        Send password reset email.

        Args:
            to_email: Customer email address
            customer_name: Customer name
            reset_token: Password reset token
            shop_name: Shop name for branding (uses config default if not provided)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping password reset email")
            return False

        # Use configured shop name if not provided
        display_shop_name = shop_name or self.shop_name

        reset_url = f"{self.frontend_base_url}/reset-password?token={reset_token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reset Your Password</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: {self.shop_brand_color}; margin-bottom: 5px;">{display_shop_name}</h1>
                <p style="color: #666; margin: 0;">{self.shop_tagline}</p>
            </div>

            <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #92400e; margin-top: 0;">Password Reset Request</h2>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <p>Hi {customer_name},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="display: inline-block; background: {self.shop_brand_color}; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Reset Password
                    </a>
                </div>

                <p style="color: #666; font-size: 0.9em;">
                    This link will expire in 1 hour. If you didn't request a password reset, you can safely ignore this email.
                </p>
            </div>

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.9em;">
                <p>If you're having trouble with the button, copy and paste this URL into your browser:</p>
                <p style="word-break: break-all;">
                    <a href="{reset_url}" style="color: {self.shop_brand_color};">{reset_url}</a>
                </p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(to_email, "Reset Your Password", html_content):
            logger.info(f"Password reset email sent to {to_email}")
            return True
        else:
            logger.error(f"Failed to send password reset email to {to_email}")
            return False

    def send_admin_password_reset(
        self,
        to_email: str,
        user_name: str,
        reset_token: str,
    ) -> bool:
        """
        Send password reset email to admin/tenant users.

        Args:
            to_email: User email address
            user_name: User name for personalization
            reset_token: Password reset token

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping admin password reset email")
            return False

        reset_url = f"https://batchivo.com/reset-password?token={reset_token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reset Your Password</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #6366f1; margin-bottom: 5px;">Batchivo</h1>
                <p style="color: #666; margin: 0;">Production Tracking for Makers</p>
            </div>

            <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #92400e; margin-top: 0;">Password Reset Request</h2>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <p>Hi {user_name},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="display: inline-block; background: #6366f1; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Reset Password
                    </a>
                </div>

                <p style="color: #666; font-size: 0.9em;">
                    This link will expire in 1 hour. If you didn't request a password reset, you can safely ignore this email.
                </p>
            </div>

            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #666; font-size: 0.9em;">
                <p>If you're having trouble with the button, copy and paste this URL into your browser:</p>
                <p style="word-break: break-all;">
                    <a href="{reset_url}" style="color: #6366f1;">{reset_url}</a>
                </p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(to_email, "Reset Your Batchivo Password", html_content):
            logger.info(f"Admin password reset email sent to {to_email}")
            return True
        else:
            logger.error(f"Failed to send admin password reset email to {to_email}")
            return False

    def send_return_approved(
        self,
        to_email: str,
        customer_name: str,
        rma_number: str,
        order_number: str,
        return_instructions: str | None = None,
        return_label_url: str | None = None,
    ) -> bool:
        """
        Send return approval email to customer with return instructions.

        Args:
            to_email: Customer email
            customer_name: Customer name
            rma_number: RMA number for the return
            order_number: Original order number
            return_instructions: Optional custom return instructions
            return_label_url: Optional URL to return shipping label

        Returns:
            True if sent successfully
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping return approved email")
            return False

        instructions_html = ""
        if return_instructions:
            instructions_html = f"""
            <div style="background: #f0fdf4; border: 1px solid #22c55e; border-radius: 8px; padding: 15px; margin: 20px 0;">
                <h3 style="color: #166534; margin-top: 0;">Return Instructions</h3>
                <p style="margin-bottom: 0;">{return_instructions}</p>
            </div>
            """

        label_html = ""
        if return_label_url:
            label_html = f"""
            <div style="text-align: center; margin: 20px 0;">
                <a href="{return_label_url}" style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Download Return Label
                </a>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><title>Return Approved</title></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #6366f1; margin-bottom: 5px;">{self.from_name}</h1>
            </div>

            <div style="background: #f0fdf4; border: 1px solid #22c55e; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #166534; margin-top: 0;">✓ Return Request Approved</h2>
                <p style="margin-bottom: 0;">RMA #: <strong>{rma_number}</strong></p>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px;">
                <p>Hi {customer_name},</p>
                <p>Your return request for order <strong>{order_number}</strong> has been approved.</p>
                {instructions_html}
                {label_html}
                <p>Please ensure items are securely packaged before shipping.</p>
            </div>

            <div style="text-align: center; margin-top: 30px; color: #666; font-size: 0.9em;">
                <p>Questions? Reply to this email for assistance.</p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(to_email, f"Return Approved - RMA #{rma_number}", html_content):
            logger.info(f"Return approved email sent to {to_email} for RMA {rma_number}")
            return True
        else:
            logger.error(f"Failed to send return approved email to {to_email}")
            return False

    def send_return_completed(
        self,
        to_email: str,
        customer_name: str,
        rma_number: str,
        order_number: str,
        refund_amount: float | None = None,
        replacement_order_number: str | None = None,
    ) -> bool:
        """
        Send return completion email to customer.

        Args:
            to_email: Customer email
            customer_name: Customer name
            rma_number: RMA number
            order_number: Original order number
            refund_amount: Amount refunded (if applicable)
            replacement_order_number: Replacement order number (if applicable)

        Returns:
            True if sent successfully
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping return completed email")
            return False

        resolution_html = ""
        if refund_amount:
            resolution_html = f"""
            <div style="background: #f0fdf4; border: 1px solid #22c55e; border-radius: 8px; padding: 15px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Refund Amount:</strong> £{refund_amount:.2f}</p>
                <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">Please allow 5-10 business days for the refund to appear on your statement.</p>
            </div>
            """
        elif replacement_order_number:
            resolution_html = f"""
            <div style="background: #eff6ff; border: 1px solid #3b82f6; border-radius: 8px; padding: 15px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Replacement Order:</strong> #{replacement_order_number}</p>
                <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">Your replacement order has been created and will ship soon.</p>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><title>Return Completed</title></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #6366f1; margin-bottom: 5px;">{self.from_name}</h1>
            </div>

            <div style="background: #f0fdf4; border: 1px solid #22c55e; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #166534; margin-top: 0;">✓ Return Completed</h2>
                <p style="margin-bottom: 0;">RMA #: <strong>{rma_number}</strong></p>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px;">
                <p>Hi {customer_name},</p>
                <p>Your return for order <strong>{order_number}</strong> has been processed.</p>
                {resolution_html}
                <p>Thank you for your patience throughout this process.</p>
            </div>

            <div style="text-align: center; margin-top: 30px; color: #666; font-size: 0.9em;">
                <p>Questions? Reply to this email for assistance.</p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(to_email, f"Return Completed - RMA #{rma_number}", html_content):
            logger.info(f"Return completed email sent to {to_email} for RMA {rma_number}")
            return True
        else:
            logger.error(f"Failed to send return completed email to {to_email}")
            return False

    def send_return_rejected(
        self,
        to_email: str,
        customer_name: str,
        rma_number: str,
        order_number: str,
        rejection_reason: str,
    ) -> bool:
        """
        Send return rejection email to customer.

        Args:
            to_email: Customer email
            customer_name: Customer name
            rma_number: RMA number
            order_number: Original order number
            rejection_reason: Reason for rejection

        Returns:
            True if sent successfully
        """
        if not self.is_configured:
            logger.warning("Email service not configured - skipping return rejected email")
            return False

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><title>Return Request Update</title></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #6366f1; margin-bottom: 5px;">{self.from_name}</h1>
            </div>

            <div style="background: #fef2f2; border: 1px solid #ef4444; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #991b1b; margin-top: 0;">Return Request Update</h2>
                <p style="margin-bottom: 0;">RMA #: <strong>{rma_number}</strong></p>
            </div>

            <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px;">
                <p>Hi {customer_name},</p>
                <p>We've reviewed your return request for order <strong>{order_number}</strong> and unfortunately we're unable to approve it at this time.</p>

                <div style="background: #f9fafb; border-radius: 6px; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; color: #666;"><strong>Reason:</strong></p>
                    <p style="margin: 5px 0 0 0;">{rejection_reason}</p>
                </div>

                <p>If you have questions about this decision or would like to discuss further, please reply to this email.</p>
            </div>

            <div style="text-align: center; margin-top: 30px; color: #666; font-size: 0.9em;">
                <p>We're here to help if you need anything.</p>
            </div>
        </body>
        </html>
        """

        if self._send_email_sync(
            to_email, f"Return Request Update - RMA #{rma_number}", html_content
        ):
            logger.info(f"Return rejected email sent to {to_email} for RMA {rma_number}")
            return True
        else:
            logger.error(f"Failed to send return rejected email to {to_email}")
            return False


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
