"""
RSS Feed Fetcher Module

Fetches news articles from Google News RSS feeds based on configured keywords.
Handles filtering by date and deduplication of articles.
"""

import feedparser
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import quote
import hashlib
import re
import time


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

        # User agent for requests
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AirMobilityNewsBot/1.0)"
        }

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
            # Fetch and parse the RSS feed
            feed = feedparser.parse(rss_url)

            if feed.bozo and feed.bozo_exception:
                print(f"Warning: Feed parsing issue for '{keyword}': {feed.bozo_exception}")

            for entry in feed.entries:
                article = self._parse_entry(entry, keyword, language)
                if article:
                    articles.append(article)

        except Exception as e:
            print(f"Error fetching feed for '{keyword}': {e}")

        return articles

    def _parse_entry(self, entry: dict, keyword: str, language: str) -> Optional[Article]:
        """
        Parse a feed entry into an Article object.

        Args:
            entry: Feed entry dictionary from feedparser.
            keyword: The keyword that matched this entry.
            language: Language code.

        Returns:
            Article object or None if parsing fails.
        """
        try:
            # Extract title
            title = entry.get("title", "").strip()
            if not title:
                return None

            # Extract URL (Google News uses a redirect URL)
            url = entry.get("link", "")
            if not url:
                return None

            # Extract source (Google News format: "Title - Source")
            source = ""
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                if len(parts) == 2:
                    title = parts[0].strip()
                    source = parts[1].strip()

            # If source not in title, try to get from feed entry
            if not source:
                source_info = entry.get("source", {})
                source = source_info.get("title", "Unknown")

            # Parse published date
            published_date = self._parse_date(entry)
            if not published_date:
                published_date = datetime.now(timezone.utc)

            # Extract snippet/summary
            snippet = entry.get("summary", "")
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
            print(f"Error parsing entry: {e}")
            return None

    def _parse_date(self, entry: dict) -> Optional[datetime]:
        """
        Parse the published date from a feed entry.

        Args:
            entry: Feed entry dictionary.

        Returns:
            datetime object or None.
        """
        # Try published_parsed first
        if entry.get("published_parsed"):
            try:
                return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass

        # Try updated_parsed
        if entry.get("updated_parsed"):
            try:
                return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass

        # Try parsing from string
        date_str = entry.get("published") or entry.get("updated")
        if date_str:
            try:
                from dateutil import parser
                return parser.parse(date_str)
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
