#!/usr/bin/env python3
"""
Air Mobility News Aggregator

Main entry point for the news aggregation application.
Collects, processes, and generates reports on eVTOL and air mobility news.
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.fetcher import NewsFetcher
from src.processor import AIProcessor
from src.reporter import ReportGenerator


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

    # Fetch articles
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

    # Process articles with AI (if available)
    if ai_available:
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
