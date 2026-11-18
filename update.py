"""
boxofficenews 블로그의 이번 주 새 글(제목·발췌·링크)을 모아 index.html 로 만들어 줍니다.
API 키가 필요 없어요.

준비:   py -m pip install requests beautifulsoup4
실행:   py update.py   → 같은 폴더에 index.html 생성 (더블클릭으로 열기)
매주:   작업 스케줄러(윈도우)나 cron(맥/리눅스)으로 주 1회 실행
"""
import html
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import truststore
truststore.inject_into_ssl()

import requests
from bs4 import BeautifulSoup

BLOG_ID = "boxofficenews"
RSS_URL = f"https://rss.blog.naver.com/{BLOG_ID}.xml"
DAYS = 7           # 최근 며칠 치 글을 '이번 주'로 볼지
EXCERPT_LEN = 100  # 발췌 글자 수
HERE = Path(__file__).parent
HISTORY = HERE / "history.json"


def fetch_posts():
    """RSS에서 글 목록(제목, 링크, 날짜, 발췌)을 가져온다."""
    r = requests.get(RSS_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    posts = []
    for item in ET.fromstring(r.content).iter("item"):
        text = BeautifulSoup(item.findtext("description") or "", "html.parser").get_text(" ", strip=True)
        if len(text) > EXCERPT_LEN:
            text = text[:EXCERPT_LEN].rstrip() + "…"
        posts.append({
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
            "date": parsedate_to_datetime(item.findtext("pubDate")),
            "excerpt": text,
        })
    return posts


def render(history):
    def block(entry, latest=False):
        cards = "".join(
            f'<a class="post" href="{html.escape(p["link"])}">'
            f'<time>{p["date"][:10]}</time><strong>{html.escape(p["title"])}</strong>'
            f'<span>{html.escape(p["excerpt"])}</span></a>'
            for p in entry["posts"]
        )
        tag = "h2" if latest else "h3"
        return f'<section><{tag}>{entry["week"]}</{tag}>{cards}</section>'

    history = [e for e in history if "posts" in e]
    if not history:
        body = "<p>아직 글이 없어요. update.py 를 실행해 주세요.</p>"
    else:
        body = block(history[0], True)
        if len(history) > 1:
            body += "<h4>지난 주</h4>" + "".join(block(e) for e in history[1:])
    updated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>이번 주 박스오피스</title>
<style>
:root{{--bg:#eef0f3;--paper:#fff;--ink:#14213d;--sub:#5b6478;--accent:#b3202f;--line:#d5d9e0}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 "Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif}}
main{{max-width:680px;margin:0 auto;padding:40px 20px 64px}}
h1{{font:800 clamp(26px,6vw,38px)/1.2 "Batang","Noto Serif KR",serif;margin:0 0 6px}}
header p{{margin:0 0 28px;color:var(--sub);font-size:14px}}
h2,h3{{font-size:15px;color:var(--sub);margin:0 0 10px}}
h4{{font-size:14px;color:var(--sub);margin:36px 0 12px}}
section{{margin-bottom:12px}}
.post{{display:block;background:var(--paper);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:4px;padding:16px 20px;margin-bottom:12px;color:inherit;text-decoration:none}}
.post:hover,.post:focus-visible{{border-color:var(--accent)}}
.post time{{display:block;font-size:13px;color:var(--sub)}}
.post strong{{display:block;font-size:18px;margin:2px 0 6px}}
.post span{{display:block;font-size:15px;color:var(--sub)}}
</style></head><body><main>
<header><h1>이번 주 박스오피스</h1><p>blog.naver.com/{BLOG_ID} · 마지막 업데이트 {updated}</p></header>
{body}</main></body></html>"""


def main():
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS)
    posts = sorted((p for p in fetch_posts() if p["date"] >= cutoff), key=lambda p: p["date"], reverse=True)
    history = json.loads(HISTORY.read_text("utf-8")) if HISTORY.exists() else []

    if posts:
        week = f"{min(p['date'] for p in posts):%m/%d} ~ {max(p['date'] for p in posts):%m/%d}"
        entry = {"week": week, "posts": [
            {"title": p["title"], "link": p["link"], "date": p["date"].isoformat(), "excerpt": p["excerpt"]}
            for p in posts]}
        history = [e for e in history if e.get("week") != week]
        history.insert(0, entry)
        HISTORY.write_text(json.dumps(history[:12], ensure_ascii=False, indent=1), "utf-8")
    else:
        print(f"최근 {DAYS}일 안에 올라온 새 글이 없어요. 기존 내용으로 페이지만 다시 만듭니다.")

    (HERE / "index.html").write_text(render(history), "utf-8")
    print(f"완료: index.html (이번 주 글 {len(posts)}개)")


if __name__ == "__main__":
    main()
