"""
AI Processor Module

Handles AI-powered summarization and translation of news articles.
Supports OpenAI and Anthropic APIs with fallback to simple processing.
"""

import os
import json
import re
from typing import Optional
from dataclasses import dataclass

# Import Article type
from src.fetcher import Article


@dataclass
class ProcessedArticle:
    """Represents AI-processed article data."""
    importance_score: int
    title_ja: str
    summary_ja: str
    category: str


class AIProcessor:
    """Processes articles using AI for summarization and translation."""

    SYSTEM_PROMPT = """あなたはエアモビリティ（空飛ぶクルマ、eVTOL、UAM）業界の専門家アナリストです。
ニュース記事を分析し、日本のビジネスパーソン向けに情報を整理してください。

与えられた記事情報を分析し、以下のJSON形式で出力してください：

{
    "importance_score": <1-5の整数。5が最も重要>,
    "title_ja": "<日本語でのタイトル>",
    "summary_ja": "<日本語での3行要約。各行は「・」で始める>",
    "category": "<技術 / 規制 / ビジネス / その他 のいずれか>"
}

重要度スコアの基準：
- 5: 業界全体に影響する重大ニュース（大型投資、規制変更、事故など）
- 4: 主要企業の重要な発表（新製品、パートナーシップ、認証取得など）
- 3: 業界の動向を示すニュース（イベント、テスト飛行、市場動向など）
- 2: 参考程度のニュース（地域限定、小規模な動きなど）
- 1: 関連性が低い、または情報が不十分

カテゴリの判断基準：
- 技術: 機体開発、バッテリー、自律飛行、インフラ技術など
- 規制: 認証、法規制、安全基準、空域管理など
- ビジネス: 資金調達、M&A、パートナーシップ、商業運航開始など
- その他: 上記に該当しないもの

出力はJSON形式のみで、他のテキストは含めないでください。"""

    def __init__(self, config: dict):
        """
        Initialize the AI processor.

        Args:
            config: Configuration dictionary containing AI settings.
        """
        self.config = config
        self.ai_config = config.get("ai", {})
        self.enabled = self.ai_config.get("enabled", True)
        self.provider = os.getenv("AI_PROVIDER", self.ai_config.get("provider", "openai"))
        self.max_articles = self.ai_config.get("max_articles_to_process", 50)

        # Initialize API clients
        self.openai_client = None
        self.anthropic_client = None
        self._init_clients()

    def _init_clients(self):
        """Initialize AI API clients based on available keys."""
        # Check for OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "your_openai_api_key_here":
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=openai_key)
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e}")

        # Check for Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key and anthropic_key != "your_anthropic_api_key_here":
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
            except Exception as e:
                print(f"Warning: Failed to initialize Anthropic client: {e}")

    def is_ai_available(self) -> bool:
        """Check if AI processing is available."""
        if not self.enabled:
            return False

        env_enabled = os.getenv("AI_ENABLED", "true").lower()
        if env_enabled == "false":
            return False

        return self.openai_client is not None or self.anthropic_client is not None

    def process_articles(self, articles: list[Article]) -> list[Article]:
        """
        Process articles with AI summarization/translation.

        Args:
            articles: List of Article objects to process.

        Returns:
            List of processed Article objects with AI-generated fields populated.
        """
        if not self.is_ai_available():
            print("AI processing is not available. Using fallback processing.")
            return self._fallback_process(articles)

        # Limit number of articles to process
        articles_to_process = articles[:self.max_articles]

        processed = []
        for i, article in enumerate(articles_to_process):
            print(f"Processing article {i+1}/{len(articles_to_process)}: {article.title[:50]}...")

            try:
                result = self._process_single_article(article)
                if result:
                    article.importance_score = result.importance_score
                    article.title_ja = result.title_ja
                    article.summary_ja = result.summary_ja
                    article.category = result.category
                else:
                    # Fallback for failed processing
                    self._apply_fallback(article)
            except Exception as e:
                print(f"Error processing article: {e}")
                self._apply_fallback(article)

            processed.append(article)

        # Add remaining articles without AI processing
        for article in articles[self.max_articles:]:
            self._apply_fallback(article)
            processed.append(article)

        return processed

    def _process_single_article(self, article: Article) -> Optional[ProcessedArticle]:
        """
        Process a single article with AI.

        Args:
            article: Article to process.

        Returns:
            ProcessedArticle with AI-generated data or None on failure.
        """
        # Prepare the prompt
        user_prompt = f"""以下のニュース記事を分析してください：

タイトル: {article.title}
ソース: {article.source}
言語: {"英語" if article.language == "en" else "日本語"}
キーワード: {article.keyword_matched}
概要: {article.snippet if article.snippet else "（概要なし）"}

JSON形式で出力してください。"""

        # Try preferred provider first
        response_text = None

        if self.provider == "anthropic" and self.anthropic_client:
            response_text = self._call_anthropic(user_prompt)
        elif self.provider == "openai" and self.openai_client:
            response_text = self._call_openai(user_prompt)

        # Fallback to other provider if preferred fails
        if not response_text:
            if self.openai_client and self.provider != "openai":
                response_text = self._call_openai(user_prompt)
            elif self.anthropic_client and self.provider != "anthropic":
                response_text = self._call_anthropic(user_prompt)

        if not response_text:
            return None

        # Parse the response
        return self._parse_response(response_text)

    def _call_openai(self, user_prompt: str) -> Optional[str]:
        """Call OpenAI API."""
        try:
            model = self.ai_config.get("openai_model", "gpt-4o-mini")
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None

    def _call_anthropic(self, user_prompt: str) -> Optional[str]:
        """Call Anthropic API."""
        try:
            model = self.ai_config.get("anthropic_model", "claude-3-haiku-20240307")
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=500,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Anthropic API error: {e}")
            return None

    def _parse_response(self, response_text: str) -> Optional[ProcessedArticle]:
        """
        Parse AI response into ProcessedArticle.

        Args:
            response_text: Raw response text from AI.

        Returns:
            ProcessedArticle or None on parse failure.
        """
        try:
            # Extract JSON from response (handle potential markdown code blocks)
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            return ProcessedArticle(
                importance_score=int(data.get("importance_score", 3)),
                title_ja=data.get("title_ja", ""),
                summary_ja=data.get("summary_ja", ""),
                category=data.get("category", "その他")
            )
        except Exception as e:
            print(f"Error parsing AI response: {e}")
            return None

    def _fallback_process(self, articles: list[Article]) -> list[Article]:
        """
        Process articles without AI (fallback mode).

        Args:
            articles: List of articles to process.

        Returns:
            Articles with basic processing applied.
        """
        for article in articles:
            self._apply_fallback(article)
        return articles

    def _apply_fallback(self, article: Article):
        """
        Apply fallback processing to a single article.

        Args:
            article: Article to process.
        """
        # Default importance score based on source/keyword
        article.importance_score = 3

        # Keep original title if already Japanese, or mark as needing translation
        if article.language == "ja":
            article.title_ja = article.title
            article.summary_ja = article.snippet if article.snippet else "（要約なし）"
        else:
            article.title_ja = f"[EN] {article.title}"
            article.summary_ja = f"（要約なし - 原文: {article.snippet[:200]}...）" if article.snippet else "（要約なし）"

        # Guess category based on keywords
        article.category = self._guess_category(article.title + " " + article.snippet)

    def _guess_category(self, text: str) -> str:
        """
        Guess category based on keywords in text.

        Args:
            text: Text to analyze.

        Returns:
            Category string.
        """
        text_lower = text.lower()

        # Technology keywords
        tech_keywords = [
            "battery", "バッテリー", "autonomous", "自律", "technology", "技術",
            "prototype", "プロトタイプ", "test flight", "試験飛行", "electric",
            "電動", "hydrogen", "水素", "software", "ソフトウェア"
        ]

        # Regulation keywords
        reg_keywords = [
            "faa", "easa", "国土交通省", "certification", "認証", "regulation",
            "規制", "approval", "承認", "safety", "安全", "airspace", "空域",
            "法案", "bill", "policy", "政策"
        ]

        # Business keywords
        biz_keywords = [
            "investment", "投資", "funding", "資金調達", "ipo", "merger", "M&A",
            "買収", "partnership", "提携", "commercial", "商業", "market",
            "市場", "revenue", "売上", "billion", "million", "launch", "開始"
        ]

        # Count matches
        tech_count = sum(1 for k in tech_keywords if k.lower() in text_lower)
        reg_count = sum(1 for k in reg_keywords if k.lower() in text_lower)
        biz_count = sum(1 for k in biz_keywords if k.lower() in text_lower)

        if reg_count > tech_count and reg_count > biz_count:
            return "規制"
        elif tech_count > biz_count:
            return "技術"
        elif biz_count > 0:
            return "ビジネス"
        else:
            return "その他"


if __name__ == "__main__":
    # Test the processor
    import yaml
    from dotenv import load_dotenv

    load_dotenv()

    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    processor = AIProcessor(config)
    print(f"AI Available: {processor.is_ai_available()}")
    print(f"Provider: {processor.provider}")
