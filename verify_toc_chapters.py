#!/usr/bin/env python3
import requests
import re

BASE = "http://0.0.0.0:8000"
KEYWORD = "斗破苍穹"

print("Searching...", KEYWORD)
rs = requests.get(f"{BASE}/api/novels/search", params={"keyword": KEYWORD, "maxResults": 30}, timeout=60)
rs.raise_for_status()
res = rs.json()
results = res.get("data", []) or []

# group by sourceId
by_source = {}
for item in results:
    sid = item.get("source_id") or item.get("sourceId") or item.get("source")
    if sid is None:
        continue
    sid = int(sid)
    if sid not in by_source:
        by_source[sid] = item

print("Sources found:", list(by_source.keys()))

report = []

def is_clean(text: str) -> bool:
    if not text or len(text) < 100:
        return False
    bad = [
        "最新章节目录",
        "如遇到内容无法显示",
        "请更换谷歌浏览器",
        "首页 书库 排行",
        "手机版阅读",
    ]
    return not any(b in text for b in bad)

# test only a subset to keep fast
test_ids = list(by_source.keys())[:5]

for sid in test_ids:
    url = by_source[sid].get("url")
    if not url:
        report.append((sid, "no_url", None))
        continue
    print(f"Testing source {sid} TOC -> {url}")
    toc = requests.get(f"{BASE}/api/novels/toc", params={"url": url, "sourceId": sid}, timeout=90)
    if toc.status_code != 200:
        report.append((sid, f"toc {toc.status_code}", None))
        continue
    data = toc.json().get("data", []) or []
    if not data:
        report.append((sid, "toc_empty", None))
        continue
    # pick first
    first = data[0]
    ch_url = first.get("url")
    print(f"  chapter -> {first.get('title')}: {ch_url}")
    ch = requests.get(f"{BASE}/api/novels/chapter", params={"url": ch_url, "sourceId": sid}, timeout=90)
    if ch.status_code != 200:
        report.append((sid, f"chapter {ch.status_code}", None))
        continue
    chd = ch.json().get("data", {}) or {}
    content = chd.get("content", "")
    ok = is_clean(content)
    report.append((sid, "OK" if ok else "NOISY", len(content)))

print("REPORT:")
for sid, status, info in report:
    print(f"source {sid}: {status} - {info}")