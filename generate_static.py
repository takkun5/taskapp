#!/usr/bin/env python3
"""Generate standalone HTML files with embedded CSS."""

import os
import sys
sys.path.insert(0, '/home/user/taskapp')

from datetime import datetime, timezone, timedelta
from collections import defaultdict
from src.fetcher import Article

def generate_demo_articles():
    now = datetime.now(timezone.utc)
    demo_data = [
        {"title": "Joby Aviation Receives FAA Type Certification", "source": "Aviation Today", "importance_score": 5, "title_ja": "Joby AviationがFAA型式証明を取得", "summary_ja": "・FAA型式証明取得\n・歴史的マイルストーン\n・商業運航に前進", "category": "規制", "language": "en"},
        {"title": "Archer Aviation $500M Investment", "source": "Bloomberg", "importance_score": 4, "title_ja": "Archer Aviationが5億ドル投資獲得", "summary_ja": "・5億ドルの大型投資\n・エアタクシー事業拡大\n・航空会社参入加速", "category": "ビジネス", "language": "en"},
        {"title": "空飛ぶクルマ、大阪万博運航へ", "source": "日経新聞", "importance_score": 4, "title_ja": "空飛ぶクルマ、大阪万博運航へ", "summary_ja": "・万博での商用運航\n・安全基準確認\n・実用化の象徴", "category": "ビジネス", "language": "ja"},
        {"title": "Lilium Jet Transition Flight Success", "source": "TechCrunch", "importance_score": 3, "title_ja": "Lilium Jet遷移飛行成功", "summary_ja": "・遷移飛行成功\n・推進システム実証\n・技術進展", "category": "技術", "language": "en"},
        {"title": "国交省、運航ルール策定へ", "source": "NHK", "importance_score": 4, "title_ja": "国交省、運航ルール策定へ", "summary_ja": "・有識者会議設置\n・ルール策定\n・制度整備本格化", "category": "規制", "language": "ja"},
        {"title": "Wisk Aero New Design", "source": "Forbes", "importance_score": 3, "title_ja": "Wisk Aero新設計発表", "summary_ja": "・新設計発表\n・安全性向上\n・都市運航特化", "category": "技術", "language": "en"},
        {"title": "ヘリ大手、eVTOL参入", "source": "Aviation Wire", "importance_score": 3, "title_ja": "ヘリ大手、eVTOL参入", "summary_ja": "・eVTOL市場参入\n・技術活用\n・相乗効果", "category": "ビジネス", "language": "ja"},
        {"title": "EASA Updates UAM Framework", "source": "FlightGlobal", "importance_score": 3, "title_ja": "EASAがUAM規制更新", "summary_ja": "・新ガイドライン\n・認証道筋明確化\n・欧州制度進展", "category": "規制", "language": "en"},
        {"title": "新バッテリーで航続500km", "source": "IEEE Spectrum", "importance_score": 4, "title_ja": "新バッテリーで航続500km", "summary_ja": "・固体電池開発\n・500km達成\n・技術突破", "category": "技術", "language": "en"},
        {"title": "SkyDrive-Suzuki提携", "source": "Reuters", "importance_score": 4, "title_ja": "SkyDrive-Suzuki提携", "summary_ja": "・生産提携発表\n・量産体制構築\n・2025年運航目標", "category": "ビジネス", "language": "en"},
    ]
    articles = []
    for i, d in enumerate(demo_data):
        a = Article(title=d["title"], url=f"#article-{i}", source=d["source"], published_date=now-timedelta(hours=i*2), language=d["language"], keyword_matched="eVTOL")
        a.importance_score, a.title_ja, a.summary_ja, a.category = d["importance_score"], d["title_ja"], d["summary_ja"], d["category"]
        articles.append(a)
    return articles

CSS = open('/home/user/taskapp/static/css/style.css').read()
articles = generate_demo_articles()
grouped = defaultdict(list)
for a in articles:
    grouped[a.category].append(a)

top_stories = sorted([a for a in articles if a.importance_score >= 4], key=lambda x: -x.importance_score)

html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>エアモビリティ ニュース</title>
<style>{CSS}</style>
</head>
<body>
<header class="header"><div class="container">
<a href="#" class="logo"><span class="logo-icon">✈</span><span class="logo-text">Air Mobility News</span></a>
<nav class="nav">
<a href="#" class="nav-link active">ホーム</a>
<a href="#tech" class="nav-link">技術</a>
<a href="#reg" class="nav-link">規制</a>
<a href="#biz" class="nav-link">ビジネス</a>
</nav>
</div></header>
<main class="main"><div class="container">
<div class="page-header">
<h1>エアモビリティ ニュース</h1>
<p class="subtitle">eVTOL・空飛ぶクルマ・UAMの最新ニュース</p>
<div class="stats"><span class="stat-item"><span class="stat-number">{len(articles)}</span><span class="stat-label">件の記事</span></span></div>
</div>

<section class="section top-stories">
<h2 class="section-title"><span class="section-icon">🔥</span>注目ニュース</h2>
<div class="top-stories-grid">
'''

for a in top_stories[:5]:
    color = {"技術":"#3b82f6","規制":"#8b5cf6","ビジネス":"#10b981"}.get(a.category,"#6b7280")
    html += f'''<div class="top-story-card">
<div class="card-header"><span class="importance">{"★"*a.importance_score}</span>
<span class="category-badge" style="background:{color}20;color:{color}">{a.category}</span></div>
<h3 class="card-title">{a.title_ja}</h3>
<div class="card-meta"><span class="source">{a.source}</span></div>
<p class="card-summary">{a.summary_ja.replace(chr(10)," ")[:80]}</p>
</div>'''

html += '</div></section>'

for cat, color, anchor in [("技術","#3b82f6","tech"),("規制","#8b5cf6","reg"),("ビジネス","#10b981","biz")]:
    if cat in grouped:
        html += f'''<section class="section" id="{anchor}">
<h2 class="section-title" style="color:{color}">{"🔧" if cat=="技術" else "📋" if cat=="規制" else "💼"} {cat}</h2>
<div class="articles-list-full">'''
        for a in sorted(grouped[cat], key=lambda x:-x.importance_score):
            html += f'''<div class="article-card-full">
<div class="article-card-importance" style="background:{color}">{"★"*a.importance_score}</div>
<div class="article-card-content">
<h3 class="article-card-title">{a.title_ja}</h3>
<div class="article-card-meta"><span class="source">{a.source}</span></div>
<p class="article-card-summary">{a.summary_ja.replace(chr(10)," ")}</p>
</div></div>'''
        html += '</div></section>'

html += '''</div></main>
<footer class="footer"><div class="container"><p>© 2024 Air Mobility News Aggregator</p></div></footer>
</body></html>'''

with open('/home/user/taskapp/output/standalone.html', 'w') as f:
    f.write(html)
print("Generated: output/standalone.html")
