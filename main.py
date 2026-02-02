#!/usr/bin/env python3
"""
Air Mobility News Aggregator

Main entry point for the news aggregation application.
Collects, processes, and generates reports on eVTOL and air mobility news.
"""

import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.fetcher import NewsFetcher, Article
from src.processor import AIProcessor
from src.reporter import ReportGenerator


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
    ]

    articles = []
    for i, data in enumerate(demo_data):
        # Vary the published dates
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


def load_config(config_path: str = "config.yaml") -> dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Configuration dictionary.
    """
    config_file = Path(config_path)

    if not config_file.exists():
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)

    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    """Main entry point for the application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Air Mobility News Aggregator - Collect and summarize eVTOL/UAM news"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable AI processing even if API keys are available"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory from config"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch articles but don't generate report"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with sample data (no network required)"
    )

    args = parser.parse_args()

    # Load environment variables from .env file
    load_dotenv()

    # Load configuration
    print("📂 Loading configuration...")
    config = load_config(args.config)

    # Override output directory if specified
    if args.output_dir:
        config["output"]["directory"] = args.output_dir

    # Initialize components
    print("🔧 Initializing components...")
    fetcher = NewsFetcher(config)
    processor = AIProcessor(config)
    reporter = ReportGenerator(config)

    # Check AI availability
    ai_available = processor.is_ai_available() and not args.no_ai
    if ai_available:
        print(f"🤖 AI processing enabled (provider: {processor.provider})")
    else:
        if args.no_ai:
            print("🤖 AI processing disabled by user")
        else:
            print("⚠️  AI processing unavailable (no API keys configured)")

    # Fetch articles (or use demo data)
    if args.demo:
        print("\n🎮 Running in DEMO mode with sample data...")
        articles = generate_demo_articles()
        print(f"✅ Generated {len(articles)} demo articles")
    else:
        print("\n📡 Fetching news articles...")
        print("   This may take a moment as we query multiple sources...")

        try:
            articles = fetcher.fetch_all()
        except Exception as e:
            print(f"❌ Error fetching articles: {e}")
            sys.exit(1)

        if not articles:
            print("⚠️  No articles found matching the criteria.")
            print("   This might happen if:")
            print("   - No news was published in the last 24 hours")
            print("   - Network issues prevented fetching")
            print("   - Keywords need adjustment")
            print("\n💡 Tip: Try running with --demo flag to see sample output")
            sys.exit(0)

    print(f"✅ Found {len(articles)} unique articles")

    if args.verbose:
        print("\n📋 Articles by source:")
        sources = {}
        for article in articles:
            sources[article.source] = sources.get(article.source, 0) + 1
        for source, count in sorted(sources.items(), key=lambda x: -x[1])[:10]:
            print(f"   - {source}: {count}")

    # Dry run - stop before processing
    if args.dry_run:
        print("\n🔍 Dry run mode - skipping AI processing and report generation")
        print("\nSample articles:")
        for article in articles[:5]:
            print(f"   [{article.language.upper()}] {article.title[:60]}...")
        return

    # Process articles with AI (if available, and not in demo mode)
    if args.demo:
        print("\n📝 Demo mode: Using pre-processed sample data...")
    elif ai_available:
        print(f"\n🤖 Processing articles with AI...")
        print(f"   (Processing up to {processor.max_articles} articles)")
        try:
            articles = processor.process_articles(articles)
            print("✅ AI processing complete")
        except Exception as e:
            print(f"⚠️  AI processing error: {e}")
            print("   Falling back to basic processing...")
            articles = processor._fallback_process(articles)
    else:
        print("\n📝 Applying basic processing (no AI)...")
        articles = processor._fallback_process(articles)

    # Generate report
    print("\n📄 Generating report...")
    try:
        report_path = reporter.generate(articles, ai_enabled=ai_available)
        print(f"✅ Report saved to: {report_path}")
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        sys.exit(1)

    # Print console summary
    print(reporter.generate_console_summary(articles))

    print("🎉 Done!")


if __name__ == "__main__":
    main()
