#!/usr/bin/env python3
"""
Air Mobility News Aggregator - Web Application

Flask-based web interface for browsing collected news by category.
"""

import os
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from flask import Flask, render_template, request, jsonify
import yaml
from dotenv import load_dotenv

from src.fetcher import NewsFetcher, Article
from src.processor import AIProcessor

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Global storage for articles
_cached_articles: list[Article] = []
_last_fetch: datetime | None = None


def load_config() -> dict:
    """Load configuration from YAML file."""
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_demo_articles() -> list[Article]:
    """Generate sample articles for demo mode."""
    now = datetime.now(timezone.utc)

    demo_data = [
        {
            "title": "Joby Aviation Receives FAA Type Certification for S4 eVTOL Aircraft",
            "url": "https://news.example.com/joby-faa-certification",
            "source": "Aviation Today",
            "snippet": "Joby Aviation announced today that it has received type certification from the FAA for its S4 electric vertical takeoff and landing aircraft, marking a historic milestone for the urban air mobility industry.",
            "language": "en",
            "keyword_matched": "eVTOL",
            "importance_score": 5,
            "title_ja": "Joby AviationがS4 eVTOL機体のFAA型式証明を取得",
            "summary_ja": "・Joby AviationがFAAから型式証明を取得\n・都市型エアモビリティ業界における歴史的なマイルストーン\n・2024年の商業運航開始に向けた重要な一歩",
            "category": "規制",
        },
        {
            "title": "Archer Aviation Announces $500M Investment from United Airlines",
            "url": "https://news.example.com/archer-united-investment",
            "source": "Bloomberg",
            "snippet": "Archer Aviation secured a major investment of $500 million from United Airlines, strengthening their partnership to launch air taxi services across major US cities.",
            "language": "en",
            "keyword_matched": "Air Taxi",
            "importance_score": 4,
            "title_ja": "Archer Aviationがユナイテッド航空から5億ドルの投資を獲得",
            "summary_ja": "・ユナイテッド航空から5億ドルの大型投資\n・米国主要都市でのエアタクシーサービス開始に向けた提携強化\n・エアモビリティ市場への大手航空会社の参入が加速",
            "category": "ビジネス",
        },
        {
            "title": "空飛ぶクルマ、大阪万博での商用運航に向け最終調整",
            "url": "https://news.example.com/osaka-expo-evtol",
            "source": "日経新聞",
            "snippet": "2025年大阪・関西万博での空飛ぶクルマ商用運航に向け、運航事業者と関係機関が最終調整を進めている。安全基準の最終確認と運航ルートの調整が焦点となっている。",
            "language": "ja",
            "keyword_matched": "空飛ぶクルマ",
            "importance_score": 4,
            "title_ja": "空飛ぶクルマ、大阪万博での商用運航に向け最終調整",
            "summary_ja": "・2025年大阪万博での商用運航に向けた最終調整\n・安全基準と運航ルートの確認が焦点\n・日本のエアモビリティ実用化の象徴的イベントに",
            "category": "ビジネス",
        },
        {
            "title": "Lilium Jet Completes Full Transition Flight with Production Aircraft",
            "url": "https://news.example.com/lilium-transition-flight",
            "source": "TechCrunch",
            "snippet": "Lilium announced successful completion of a full transition flight using its production-conforming aircraft, demonstrating the viability of its unique electric jet propulsion system.",
            "language": "en",
            "keyword_matched": "eVTOL",
            "importance_score": 3,
            "title_ja": "Lilium Jetが量産機で完全遷移飛行に成功",
            "summary_ja": "・量産仕様機による完全遷移飛行に成功\n・独自の電動ジェット推進システムの実用性を実証\n・認証取得に向けた技術的進展",
            "category": "技術",
        },
        {
            "title": "国土交通省、空飛ぶクルマの運航ルール策定へ有識者会議を設置",
            "url": "https://news.example.com/mlit-evtol-rules",
            "source": "NHK",
            "snippet": "国土交通省は空飛ぶクルマの本格的な社会実装に向け、運航ルールや安全基準を検討する有識者会議を設置すると発表した。",
            "language": "ja",
            "keyword_matched": "空飛ぶクルマ",
            "importance_score": 4,
            "title_ja": "国土交通省、空飛ぶクルマの運航ルール策定へ有識者会議を設置",
            "summary_ja": "・国土交通省が有識者会議を設置\n・運航ルールと安全基準の策定を検討\n・社会実装に向けた制度整備が本格化",
            "category": "規制",
        },
        {
            "title": "Wisk Aero Unveils New Autonomous Air Taxi Design",
            "url": "https://news.example.com/wisk-autonomous",
            "source": "Forbes",
            "snippet": "Boeing-backed Wisk Aero revealed its latest autonomous air taxi design, featuring enhanced safety systems and longer range capabilities for urban operations.",
            "language": "en",
            "keyword_matched": "Air Taxi",
            "importance_score": 3,
            "title_ja": "Wisk Aeroが新型自律飛行エアタクシーを発表",
            "summary_ja": "・ボーイング支援のWisk Aeroが新設計を発表\n・安全システムの強化と航続距離の延長\n・都市部運航に特化した設計",
            "category": "技術",
        },
        {
            "title": "ヘリコプター大手、eVTOL事業参入を発表",
            "url": "https://news.example.com/heli-evtol-entry",
            "source": "Aviation Wire",
            "snippet": "大手ヘリコプターメーカーがeVTOL市場への参入を正式発表。既存の航空技術とインフラを活用した事業展開を計画している。",
            "language": "ja",
            "keyword_matched": "ヘリコプター事業",
            "importance_score": 3,
            "title_ja": "ヘリコプター大手、eVTOL事業参入を発表",
            "summary_ja": "・大手ヘリコプターメーカーがeVTOL市場参入\n・既存の航空技術とインフラを活用\n・従来事業との相乗効果を狙う",
            "category": "ビジネス",
        },
        {
            "title": "European Aviation Safety Agency Updates UAM Regulatory Framework",
            "url": "https://news.example.com/easa-uam-framework",
            "source": "FlightGlobal",
            "snippet": "EASA has published updated guidelines for Urban Air Mobility operations in Europe, providing clearer pathways for eVTOL certification and operations.",
            "language": "en",
            "keyword_matched": "Urban Air Mobility",
            "importance_score": 3,
            "title_ja": "欧州航空安全機関がUAM規制フレームワークを更新",
            "summary_ja": "・EASAがUAM運航に関する新ガイドラインを発表\n・eVTOL認証と運航の明確な道筋を提示\n・欧州での実用化に向けた制度整備が進展",
            "category": "規制",
        },
        {
            "title": "SkyDrive Announces Partnership with Suzuki for Flying Car Production",
            "url": "https://news.example.com/skydrive-suzuki",
            "source": "Reuters",
            "snippet": "Japanese startup SkyDrive has partnered with Suzuki Motor Corporation to accelerate the production of its SD-05 flying car, targeting commercial operations by 2025.",
            "language": "en",
            "keyword_matched": "Flying Car",
            "importance_score": 4,
            "title_ja": "SkyDriveがスズキと空飛ぶクルマ生産で提携",
            "summary_ja": "・SkyDriveとスズキが生産提携を発表\n・SD-05の量産体制構築を加速\n・2025年の商業運航開始を目指す",
            "category": "ビジネス",
        },
        {
            "title": "New Battery Technology Promises 500km Range for eVTOL Aircraft",
            "url": "https://news.example.com/evtol-battery-breakthrough",
            "source": "IEEE Spectrum",
            "snippet": "Researchers have developed a new solid-state battery technology that could enable eVTOL aircraft to achieve ranges of up to 500 kilometers on a single charge.",
            "language": "en",
            "keyword_matched": "eVTOL",
            "importance_score": 4,
            "title_ja": "新型バッテリー技術でeVTOL航続距離500kmを実現へ",
            "summary_ja": "・新型固体電池技術を開発\n・eVTOL機の航続距離500kmを達成可能に\n・実用化に向けた技術的ブレイクスルー",
            "category": "技術",
        },
    ]

    articles = []
    for i, data in enumerate(demo_data):
        pub_date = now - timedelta(hours=i * 2)
        article = Article(
            title=data["title"],
            url=data["url"],
            source=data["source"],
            published_date=pub_date,
            snippet=data["snippet"],
            language=data["language"],
            keyword_matched=data["keyword_matched"],
        )
        article.importance_score = data["importance_score"]
        article.title_ja = data["title_ja"]
        article.summary_ja = data["summary_ja"]
        article.category = data["category"]
        articles.append(article)

    return articles


def get_articles(force_refresh: bool = False) -> list[Article]:
    """Get cached articles or fetch new ones."""
    global _cached_articles, _last_fetch

    # Use cached articles if available and fresh (less than 1 hour old)
    if not force_refresh and _cached_articles and _last_fetch:
        age = datetime.now(timezone.utc) - _last_fetch
        if age < timedelta(hours=1):
            return _cached_articles

    # Try to fetch real articles, fall back to demo
    config = load_config()
    fetcher = NewsFetcher(config)

    try:
        articles = fetcher.fetch_all()
        if articles:
            processor = AIProcessor(config)
            if processor.is_ai_available():
                articles = processor.process_articles(articles)
            else:
                articles = processor._fallback_process(articles)
            _cached_articles = articles
            _last_fetch = datetime.now(timezone.utc)
            return articles
    except Exception as e:
        print(f"Error fetching articles: {e}")

    # Fall back to demo articles
    _cached_articles = generate_demo_articles()
    _last_fetch = datetime.now(timezone.utc)
    return _cached_articles


def group_by_category(articles: list[Article]) -> dict[str, list[Article]]:
    """Group articles by category."""
    grouped = defaultdict(list)
    for article in articles:
        grouped[article.category].append(article)

    # Sort articles within each category by importance
    for category in grouped:
        grouped[category].sort(key=lambda x: x.importance_score, reverse=True)

    return dict(grouped)


def get_category_info(category: str) -> dict:
    """Get display information for a category."""
    info = {
        "技術": {"icon": "cpu", "color": "#3b82f6", "name_en": "Technology"},
        "規制": {"icon": "file-text", "color": "#8b5cf6", "name_en": "Regulation"},
        "ビジネス": {"icon": "briefcase", "color": "#10b981", "name_en": "Business"},
        "その他": {"icon": "folder", "color": "#6b7280", "name_en": "Other"},
    }
    return info.get(category, info["その他"])


@app.route("/")
def index():
    """Main page showing all categories."""
    articles = get_articles()
    grouped = group_by_category(articles)

    # Get top stories (importance >= 4)
    top_stories = [a for a in articles if a.importance_score >= 4]
    top_stories.sort(key=lambda x: x.importance_score, reverse=True)

    categories_with_info = []
    for cat in ["技術", "規制", "ビジネス", "その他"]:
        if cat in grouped:
            categories_with_info.append({
                "name": cat,
                "info": get_category_info(cat),
                "count": len(grouped[cat]),
                "articles": grouped[cat]
            })

    return render_template(
        "index.html",
        categories=categories_with_info,
        top_stories=top_stories[:5],
        total_count=len(articles),
        last_update=_last_fetch.strftime("%Y-%m-%d %H:%M") if _last_fetch else "N/A"
    )


@app.route("/category/<category_name>")
def category(category_name: str):
    """Page for a specific category."""
    articles = get_articles()
    grouped = group_by_category(articles)

    category_articles = grouped.get(category_name, [])
    category_info = get_category_info(category_name)

    return render_template(
        "category.html",
        category_name=category_name,
        category_info=category_info,
        articles=category_articles,
        total_count=len(category_articles)
    )


@app.route("/article/<article_id>")
def article_detail(article_id: str):
    """Detail page for a single article."""
    articles = get_articles()

    article = None
    for a in articles:
        if a.id == article_id:
            article = a
            break

    if not article:
        return render_template("404.html"), 404

    return render_template(
        "article.html",
        article=article,
        category_info=get_category_info(article.category)
    )


@app.route("/api/refresh", methods=["POST"])
def refresh():
    """API endpoint to refresh articles."""
    articles = get_articles(force_refresh=True)
    return jsonify({
        "success": True,
        "count": len(articles),
        "last_update": _last_fetch.strftime("%Y-%m-%d %H:%M") if _last_fetch else "N/A"
    })


@app.template_filter("importance_stars")
def importance_stars(score: int) -> str:
    """Convert importance score to star display."""
    return "★" * min(score, 5)


@app.template_filter("format_date")
def format_date(dt: datetime) -> str:
    """Format datetime for display."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Convert to JST
    jst = timezone(timedelta(hours=9))
    dt_jst = dt.astimezone(jst)
    return dt_jst.strftime("%Y/%m/%d %H:%M")


if __name__ == "__main__":
    # Load demo articles on startup
    _cached_articles = generate_demo_articles()
    _last_fetch = datetime.now(timezone.utc)

    print("Starting Air Mobility News Web App...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, host="0.0.0.0", port=5000)
