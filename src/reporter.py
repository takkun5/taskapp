"""
Report Generator Module

Generates formatted Markdown reports from processed news articles.
"""

import os
from datetime import datetime
from typing import Optional
from collections import defaultdict

from src.fetcher import Article


class ReportGenerator:
    """Generates Markdown reports from processed articles."""

    def __init__(self, config: dict):
        """
        Initialize the report generator.

        Args:
            config: Configuration dictionary containing output settings.
        """
        self.config = config
        self.output_config = config.get("output", {})
        self.output_dir = self.output_config.get("directory", "output")
        self.filename_template = self.output_config.get(
            "filename_template",
            "daily_report_{date}.md"
        )
        self.categories = config.get("categories", ["技術", "規制", "ビジネス", "その他"])

    def generate(
        self,
        articles: list[Article],
        date: Optional[datetime] = None,
        ai_enabled: bool = True
    ) -> str:
        """
        Generate a Markdown report from articles.

        Args:
            articles: List of processed Article objects.
            date: Date for the report (defaults to today).
            ai_enabled: Whether AI processing was enabled.

        Returns:
            Path to the generated report file.
        """
        if date is None:
            date = datetime.now()

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Generate filename
        date_str = date.strftime("%Y-%m-%d")
        filename = self.filename_template.replace("{date}", date_str)
        filepath = os.path.join(self.output_dir, filename)

        # Generate report content
        content = self._generate_content(articles, date, ai_enabled)

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def _generate_content(
        self,
        articles: list[Article],
        date: datetime,
        ai_enabled: bool
    ) -> str:
        """
        Generate the Markdown content for the report.

        Args:
            articles: List of processed articles.
            date: Report date.
            ai_enabled: Whether AI processing was enabled.

        Returns:
            Markdown content string.
        """
        lines = []

        # Header
        date_str = date.strftime("%Y年%m月%d日")
        lines.append(f"# エアモビリティ ニュースレポート")
        lines.append(f"## {date_str}")
        lines.append("")

        # Summary section
        lines.append("---")
        lines.append("")
        lines.append("### 📊 本日のサマリー")
        lines.append("")
        lines.append(f"- **収集記事数**: {len(articles)}件")

        # Count by category
        category_counts = defaultdict(int)
        for article in articles:
            category_counts[article.category] += 1

        for cat in self.categories:
            count = category_counts.get(cat, 0)
            if count > 0:
                lines.append(f"- **{cat}**: {count}件")

        # Count by importance
        high_importance = sum(1 for a in articles if a.importance_score >= 4)
        if high_importance > 0:
            lines.append(f"- **重要度4以上**: {high_importance}件")

        lines.append("")

        if not ai_enabled:
            lines.append("> ⚠️ AI処理が無効のため、自動要約・翻訳は行われていません。")
            lines.append("")

        # Top stories (importance >= 4)
        top_articles = [a for a in articles if a.importance_score >= 4]
        if top_articles:
            lines.append("---")
            lines.append("")
            lines.append("### 🔥 注目ニュース")
            lines.append("")

            for article in sorted(top_articles, key=lambda x: x.importance_score, reverse=True):
                lines.extend(self._format_article(article, detailed=True))
                lines.append("")

        # Articles by category
        for category in self.categories:
            category_articles = [a for a in articles if a.category == category and a.importance_score < 4]

            if category_articles:
                lines.append("---")
                lines.append("")

                # Category emoji
                emoji = self._get_category_emoji(category)
                lines.append(f"### {emoji} {category}")
                lines.append("")

                for article in category_articles:
                    lines.extend(self._format_article(article, detailed=False))
                    lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("### 📝 レポート情報")
        lines.append("")
        lines.append(f"- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- AI処理: {'有効' if ai_enabled else '無効'}")
        lines.append(f"- データソース: Google News RSS")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*このレポートは Air Mobility News Aggregator によって自動生成されました。*")

        return "\n".join(lines)

    def _format_article(self, article: Article, detailed: bool = False) -> list[str]:
        """
        Format a single article for the report.

        Args:
            article: Article to format.
            detailed: Whether to include detailed information.

        Returns:
            List of Markdown lines.
        """
        lines = []

        # Title with importance indicator
        importance_indicator = "⭐" * min(article.importance_score, 5)

        if article.title_ja and not article.title_ja.startswith("[EN]"):
            title = article.title_ja
        else:
            title = article.title

        lines.append(f"#### {importance_indicator} {title}")
        lines.append("")

        # Metadata line
        pub_date = article.published_date.strftime("%Y-%m-%d %H:%M")
        lines.append(f"📰 **{article.source}** | 🕐 {pub_date} | 🏷️ {article.category}")
        lines.append("")

        # Summary (for detailed view or if we have a summary)
        if detailed and article.summary_ja:
            lines.append(f"> {article.summary_ja}")
            lines.append("")

        # Original title (if different from Japanese title)
        if article.language == "en" and article.title_ja and not article.title_ja.startswith("[EN]"):
            lines.append(f"*原題: {article.title}*")
            lines.append("")

        # Link
        lines.append(f"🔗 [記事を読む]({article.url})")

        return lines

    def _get_category_emoji(self, category: str) -> str:
        """Get emoji for a category."""
        emoji_map = {
            "技術": "🔧",
            "規制": "📋",
            "ビジネス": "💼",
            "その他": "📌"
        }
        return emoji_map.get(category, "📌")

    def generate_console_summary(self, articles: list[Article]) -> str:
        """
        Generate a brief console-friendly summary.

        Args:
            articles: List of processed articles.

        Returns:
            Summary string for console output.
        """
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("エアモビリティ ニュースサマリー")
        lines.append("=" * 60)
        lines.append(f"収集記事数: {len(articles)}件")

        # Show top 5 important articles
        top_articles = sorted(articles, key=lambda x: x.importance_score, reverse=True)[:5]

        if top_articles:
            lines.append("\n📰 トップニュース:")
            for i, article in enumerate(top_articles, 1):
                title = article.title_ja if article.title_ja else article.title
                if len(title) > 60:
                    title = title[:57] + "..."
                stars = "⭐" * article.importance_score
                lines.append(f"  {i}. {stars} {title}")
                lines.append(f"     └─ {article.source} | {article.category}")

        lines.append("=" * 60 + "\n")

        return "\n".join(lines)


if __name__ == "__main__":
    # Test the reporter with sample data
    from datetime import timezone

    sample_article = Article(
        title="Joby Aviation Completes Major Milestone",
        url="https://example.com/article1",
        source="TechCrunch",
        published_date=datetime.now(timezone.utc),
        snippet="Joby Aviation announced today...",
        language="en",
        keyword_matched="eVTOL"
    )
    sample_article.importance_score = 4
    sample_article.title_ja = "Joby Aviationが重要なマイルストーンを達成"
    sample_article.summary_ja = "・Joby Aviationが認証取得に向けた重要な進展\n・商業運航開始に一歩前進\n・エアタクシー市場の競争が激化"
    sample_article.category = "ビジネス"

    import yaml
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    reporter = ReportGenerator(config)
    print(reporter.generate_console_summary([sample_article]))
