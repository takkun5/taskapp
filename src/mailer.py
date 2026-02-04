"""
Email Sender Module

Sends daily news reports via email using SMTP.
Supports HTML and plain text formats.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.fetcher import Article


class EmailSender:
    """Sends news reports via email."""

    def __init__(self, config: dict):
        """
        Initialize the email sender.

        Args:
            config: Configuration dictionary containing email settings.
        """
        self.config = config
        self.email_config = config.get("email", {})
        self.enabled = self.email_config.get("enabled", False)

        # SMTP settings (can be overridden by environment variables)
        self.smtp_server = os.getenv("SMTP_SERVER", self.email_config.get("smtp_server", "smtp.gmail.com"))
        self.smtp_port = int(os.getenv("SMTP_PORT", self.email_config.get("smtp_port", 587)))
        self.smtp_user = os.getenv("SMTP_USER", self.email_config.get("smtp_user", ""))
        self.smtp_password = os.getenv("SMTP_PASSWORD", self.email_config.get("smtp_password", ""))
        self.use_tls = self.email_config.get("use_tls", True)

        # Email settings
        self.from_address = os.getenv("EMAIL_FROM", self.email_config.get("from_address", self.smtp_user))
        self.to_addresses = self.email_config.get("to_addresses", [])

        # Add recipients from environment variable (comma-separated)
        env_recipients = os.getenv("EMAIL_TO", "")
        if env_recipients:
            self.to_addresses.extend([addr.strip() for addr in env_recipients.split(",")])

    def is_configured(self) -> bool:
        """Check if email is properly configured."""
        return bool(
            self.smtp_server and
            self.smtp_user and
            self.smtp_password and
            self.to_addresses
        )

    def send_report(
        self,
        articles: list[Article],
        date: Optional[datetime] = None,
        ai_enabled: bool = False
    ) -> bool:
        """
        Send a news report via email.

        Args:
            articles: List of processed Article objects.
            date: Date for the report (defaults to today).
            ai_enabled: Whether AI processing was used.

        Returns:
            True if email was sent successfully, False otherwise.
        """
        if not self.is_configured():
            print("❌ Email not configured. Please set SMTP credentials.")
            return False

        if date is None:
            date = datetime.now(timezone.utc)

        # Generate email content
        subject = self._generate_subject(articles, date)
        html_content = self._generate_html(articles, date, ai_enabled)
        text_content = self._generate_text(articles, date, ai_enabled)

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_address
        msg["To"] = ", ".join(self.to_addresses)

        # Attach both plain text and HTML versions
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Send email
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_address, self.to_addresses, msg.as_string())

            print(f"✅ Email sent to: {', '.join(self.to_addresses)}")
            return True

        except smtplib.SMTPAuthenticationError:
            print("❌ Email authentication failed. Check SMTP credentials.")
            return False
        except smtplib.SMTPException as e:
            print(f"❌ Failed to send email: {e}")
            return False
        except Exception as e:
            print(f"❌ Email error: {e}")
            return False

    def _generate_subject(self, articles: list[Article], date: datetime) -> str:
        """Generate email subject line."""
        jst = timezone(timedelta(hours=9))
        date_str = date.astimezone(jst).strftime("%Y/%m/%d")
        high_importance = sum(1 for a in articles if a.importance_score >= 4)

        if high_importance > 0:
            return f"🚁 エアモビリティ ニュース ({date_str}) - 注目記事 {high_importance}件"
        else:
            return f"🚁 エアモビリティ ニュース ({date_str}) - {len(articles)}件"

    def _generate_html(self, articles: list[Article], date: datetime, ai_enabled: bool) -> str:
        """Generate HTML email content."""
        jst = timezone(timedelta(hours=9))
        date_str = date.astimezone(jst).strftime("%Y年%m月%d日")

        # Group by category
        categories = {}
        for article in articles:
            if article.category not in categories:
                categories[article.category] = []
            categories[article.category].append(article)

        # Top stories
        top_stories = sorted(
            [a for a in articles if a.importance_score >= 4],
            key=lambda x: x.importance_score,
            reverse=True
        )

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 24px;">✈️ エアモビリティ ニュース</h1>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">{date_str}</p>
    </div>

    <div style="background: #f8fafc; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <p style="margin: 0;"><strong>📊 本日のサマリー:</strong> {len(articles)}件の記事"""

        if top_stories:
            html += f" (注目: {len(top_stories)}件)"

        html += "</p></div>"

        # Top stories section
        if top_stories:
            html += """
    <div style="margin-bottom: 25px;">
        <h2 style="color: #dc2626; font-size: 18px; border-bottom: 2px solid #dc2626; padding-bottom: 5px;">🔥 注目ニュース</h2>
"""
            for article in top_stories[:5]:
                stars = "⭐" * article.importance_score
                title = article.title_ja or article.title
                html += f"""
        <div style="background: white; border-left: 4px solid #dc2626; padding: 12px; margin-bottom: 10px; border-radius: 0 8px 8px 0;">
            <div style="font-size: 12px; color: #666;">{stars} | {article.source}</div>
            <h3 style="margin: 5px 0; font-size: 15px;"><a href="{article.url}" style="color: #1e3a5f; text-decoration: none;">{title}</a></h3>
            <p style="margin: 5px 0 0 0; font-size: 13px; color: #666;">{article.summary_ja.replace(chr(10), ' ')[:100] if article.summary_ja else ''}</p>
        </div>
"""
            html += "</div>"

        # Category sections
        category_colors = {
            "技術": "#3b82f6",
            "規制": "#8b5cf6",
            "ビジネス": "#10b981",
            "その他": "#6b7280"
        }

        for cat in ["技術", "規制", "ビジネス", "その他"]:
            if cat in categories:
                color = category_colors.get(cat, "#6b7280")
                html += f"""
    <div style="margin-bottom: 25px;">
        <h2 style="color: {color}; font-size: 16px; border-bottom: 2px solid {color}; padding-bottom: 5px;">{"🔧" if cat=="技術" else "📋" if cat=="規制" else "💼" if cat=="ビジネス" else "📌"} {cat}</h2>
"""
                for article in categories[cat][:5]:
                    title = article.title_ja or article.title
                    html += f"""
        <div style="padding: 8px 0; border-bottom: 1px solid #eee;">
            <div style="font-size: 11px; color: #888;">{"⭐" * article.importance_score} {article.source}</div>
            <a href="{article.url}" style="color: #333; text-decoration: none; font-size: 14px;">{title}</a>
        </div>
"""
                html += "</div>"

        html += """
    <div style="text-align: center; padding: 20px; color: #999; font-size: 12px; border-top: 1px solid #eee; margin-top: 20px;">
        <p>Air Mobility News Aggregator により自動生成</p>
    </div>
</body>
</html>
"""
        return html

    def _generate_text(self, articles: list[Article], date: datetime, ai_enabled: bool) -> str:
        """Generate plain text email content."""
        jst = timezone(timedelta(hours=9))
        date_str = date.astimezone(jst).strftime("%Y年%m月%d日")

        lines = [
            "=" * 50,
            f"エアモビリティ ニュース - {date_str}",
            "=" * 50,
            "",
            f"本日の記事: {len(articles)}件",
            "",
        ]

        # Top stories
        top_stories = [a for a in articles if a.importance_score >= 4]
        if top_stories:
            lines.append("【注目ニュース】")
            lines.append("-" * 30)
            for article in sorted(top_stories, key=lambda x: -x.importance_score)[:5]:
                title = article.title_ja or article.title
                lines.append(f"★{'★' * (article.importance_score - 1)} {title}")
                lines.append(f"   {article.source}")
                lines.append(f"   {article.url}")
                lines.append("")
            lines.append("")

        # By category
        categories = {}
        for article in articles:
            if article.category not in categories:
                categories[article.category] = []
            categories[article.category].append(article)

        for cat in ["技術", "規制", "ビジネス", "その他"]:
            if cat in categories:
                lines.append(f"【{cat}】")
                lines.append("-" * 30)
                for article in categories[cat][:5]:
                    title = article.title_ja or article.title
                    lines.append(f"・{title}")
                    lines.append(f"  {article.source} | {article.url}")
                lines.append("")

        lines.append("-" * 50)
        lines.append("Air Mobility News Aggregator")

        return "\n".join(lines)


if __name__ == "__main__":
    # Test the email sender
    import yaml
    from dotenv import load_dotenv

    load_dotenv()

    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    sender = EmailSender(config)
    print(f"Email configured: {sender.is_configured()}")
    print(f"SMTP Server: {sender.smtp_server}")
    print(f"Recipients: {sender.to_addresses}")
