"""
RSS Feed Fetcher Module

Fetches news articles from Google News RSS feeds based on configured keywords.
Handles filtering by date and deduplication of articles.
Uses standard library for RSS parsing (no feedparser dependency).
"""

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass
from urllib.parse import quote
from email.utils import parsedate_to_datetime
import hashlib
import re
import time
import ssl


@dataclass
class Article:
    """Represents a news article."""
    title: str
    url: str
    source: str
    published_date: datetime
    snippet: str = ""
    language: str = "en"
    keyword_matched: str = ""

    # Fields populated by AI processing
    importance_score: int = 0
    title_ja: str = ""
    summary_ja: str = ""
    category: str = "その他"

    def __post_init__(self):
        # Generate a unique ID based on URL
        self.id = hashlib.md5(self.url.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        """Convert article to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_date": self.published_date.isoformat(),
            "snippet": self.snippet,
            "language": self.language,
            "keyword_matched": self.keyword_matched,
            "importance_score": self.importance_score,
            "title_ja": self.title_ja,
            "summary_ja": self.summary_ja,
            "category": self.category,
        }


class NewsFetcher:
    """Fetches and filters news articles from RSS feeds."""

    def __init__(self, config: dict):
        """
        Initialize the fetcher with configuration.

        Args:
            config: Configuration dictionary containing keywords and RSS sources.
        """
        self.config = config
        self.keywords = config.get("keywords", {})
        self.rss_sources = config.get("rss_sources", {})
        self.filtering = config.get("filtering", {})
        self.max_age_hours = self.filtering.get("max_age_hours", 24)
        self.similarity_threshold = self.filtering.get("title_similarity_threshold", 0.8)

        # SSL context for HTTPS requests
        self.ssl_context = ssl.create_default_context()

    def fetch_all(self) -> list[Article]:
        """
        Fetch articles for all configured keywords from all sources.

        Returns:
            List of deduplicated Article objects within the time window.
        """
        all_articles = []

        # Fetch English articles
        english_keywords = self.keywords.get("english", [])
        for keyword in english_keywords:
            print(f"   Fetching: {keyword}")
            articles = self._fetch_keyword(
                keyword,
                self.rss_sources.get("google_news_global", ""),
                language="en"
            )
            all_articles.extend(articles)
            time.sleep(0.5)  # Rate limiting

        # Fetch Japanese articles
        japanese_keywords = self.keywords.get("japanese", [])
        for keyword in japanese_keywords:
            print(f"   Fetching: {keyword}")
            articles = self._fetch_keyword(
                keyword,
                self.rss_sources.get("google_news_japan", ""),
                language="ja"
            )
            all_articles.extend(articles)
            time.sleep(0.5)  # Rate limiting

        # Filter and deduplicate
        filtered_articles = self._filter_by_date(all_articles)
        deduplicated_articles = self._deduplicate(filtered_articles)

        # Sort by published date (newest first)
        deduplicated_articles.sort(key=lambda x: x.published_date, reverse=True)

        return deduplicated_articles

    def _fetch_keyword(self, keyword: str, rss_template: str, language: str = "en") -> list[Article]:
        """
        Fetch articles for a specific keyword from an RSS feed.

        Args:
            keyword: The search keyword.
            rss_template: RSS URL template with {keyword} placeholder.
            language: Language code (en/ja).

        Returns:
            List of Article objects.
        """
        if not rss_template:
            return []

        # Build RSS URL
        encoded_keyword = quote(keyword)
        rss_url = rss_template.replace("{keyword}", encoded_keyword)

        articles = []

        try:
            # Create request with user agent
            req = urllib.request.Request(
                rss_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AirMobilityNewsBot/1.0)"}
            )

            # Fetch the RSS feed
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=30) as response:
                xml_content = response.read().decode("utf-8")

            # Parse XML
            root = ET.fromstring(xml_content)

            # Find all items (RSS format)
            for item in root.findall(".//item"):
                article = self._parse_item(item, keyword, language)
                if article:
                    articles.append(article)

        except urllib.error.URLError as e:
            print(f"     Network error for '{keyword}': {e}")
        except ET.ParseError as e:
            print(f"     XML parsing error for '{keyword}': {e}")
        except Exception as e:
            print(f"     Error fetching feed for '{keyword}': {e}")

        return articles

    def _parse_item(self, item: ET.Element, keyword: str, language: str) -> Optional[Article]:
        """
        Parse an RSS item into an Article object.

        Args:
            item: XML Element representing an RSS item.
            keyword: The keyword that matched this entry.
            language: Language code.

        Returns:
            Article object or None if parsing fails.
        """
        try:
            # Extract title
            title_elem = item.find("title")
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            if not title:
                return None

            # Extract URL
            link_elem = item.find("link")
            url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
            if not url:
                return None

            # Extract source (Google News format: "Title - Source")
            source = ""
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                if len(parts) == 2:
                    title = parts[0].strip()
                    source = parts[1].strip()

            # If source not in title, try to get from source element
            if not source:
                source_elem = item.find("source")
                source = source_elem.text.strip() if source_elem is not None and source_elem.text else "Unknown"

            # Parse published date
            published_date = self._parse_date(item)
            if not published_date:
                published_date = datetime.now(timezone.utc)

            # Extract snippet/description
            desc_elem = item.find("description")
            snippet = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
            # Clean HTML tags from snippet
            snippet = re.sub(r"<[^>]+>", "", snippet).strip()
            # Limit snippet length
            if len(snippet) > 500:
                snippet = snippet[:500] + "..."

            return Article(
                title=title,
                url=url,
                source=source,
                published_date=published_date,
                snippet=snippet,
                language=language,
                keyword_matched=keyword,
            )

        except Exception as e:
            print(f"     Error parsing item: {e}")
            return None

    def _parse_date(self, item: ET.Element) -> Optional[datetime]:
        """
        Parse the published date from an RSS item.

        Args:
            item: XML Element representing an RSS item.

        Returns:
            datetime object or None.
        """
        # Try pubDate first (standard RSS)
        pub_date_elem = item.find("pubDate")
        if pub_date_elem is not None and pub_date_elem.text:
            try:
                return parsedate_to_datetime(pub_date_elem.text)
            except Exception:
                pass

        # Try dc:date (Dublin Core)
        for ns in ["dc", "{http://purl.org/dc/elements/1.1/}"]:
            date_elem = item.find(f"{ns}date")
            if date_elem is not None and date_elem.text:
                try:
                    # ISO format
                    return datetime.fromisoformat(date_elem.text.replace("Z", "+00:00"))
                except Exception:
                    pass

        return None

    def _filter_by_date(self, articles: list[Article]) -> list[Article]:
        """
        Filter articles to only include those within the time window.

        Args:
            articles: List of Article objects.

        Returns:
            Filtered list of articles.
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.max_age_hours)

        filtered = []
        for article in articles:
            # Ensure published_date is timezone-aware
            pub_date = article.published_date
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)

            if pub_date >= cutoff_time:
                filtered.append(article)

        return filtered

    def _deduplicate(self, articles: list[Article]) -> list[Article]:
        """
        Remove duplicate articles based on URL and title similarity.

        Args:
            articles: List of Article objects.

        Returns:
            Deduplicated list of articles.
        """
        seen_urls = set()
        seen_titles = []
        unique_articles = []

        for article in articles:
            # Check URL duplication
            if article.url in seen_urls:
                continue

            # Check title similarity
            is_duplicate = False
            for seen_title in seen_titles:
                if self._calculate_similarity(article.title, seen_title) >= self.similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_urls.add(article.url)
                seen_titles.append(article.title)
                unique_articles.append(article)

        return unique_articles

    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles using Jaccard similarity.

        Args:
            title1: First title.
            title2: Second title.

        Returns:
            Similarity score between 0.0 and 1.0.
        """
        # Normalize titles
        def normalize(text: str) -> set:
            text = text.lower()
            text = re.sub(r"[^\w\s]", "", text)
            return set(text.split())

        words1 = normalize(title1)
        words2 = normalize(title2)

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)


if __name__ == "__main__":
    # Test the fetcher with sample config
    import yaml

    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    fetcher = NewsFetcher(config)
    articles = fetcher.fetch_all()

    print(f"Fetched {len(articles)} unique articles")
    for article in articles[:5]:
        print(f"- [{article.source}] {article.title}")
