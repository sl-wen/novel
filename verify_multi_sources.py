#!/usr/bin/env python3
import time
import requests
import re
from collections import defaultdict

BASE = "http://0.0.0.0:8000"
KEYWORD = "斗破苍穹"
TEST_SOURCES = [1,2,3,4,5,6,7,8,9,10]  # 可调整
TIMEOUT = 120

print("Searching...", KEYWORD)
rs = requests.get(f"{BASE}/api/novels/search", params={"keyword": KEYWORD, "maxResults": 30}, timeout=TIMEOUT)
rs.raise_for_status()
res = rs.json()
results = res.get("data", []) or []

by_source = defaultdict(list)
for item in results:
    sid = item.get("source_id") or item.get("sourceId") or item.get("source")
    if sid is not None:
        by_source[int(sid)].append(item)

print("Found results per source:", {k: len(v) for k, v in by_source.items()})

summary = []

for sid in TEST_SOURCES:
    if not by_source.get(sid):
        summary.append((sid, False, "no search result", None))
        print(f"Source {sid}: no search result")
        continue
    url = by_source[sid][0].get("url")
    if not url:
        summary.append((sid, False, "missing url", None))
        print(f"Source {sid}: missing url in result")
        continue

    print(f"Starting download for source {sid} -> {url}")
    start = requests.post(f"{BASE}/api/novels/download/start", params={"url": url, "sourceId": sid, "format": "txt"}, timeout=TIMEOUT)
    if start.status_code != 202 and start.status_code != 200:
        summary.append((sid, False, f"start failed {start.status_code}", None))
        print(f"Source {sid}: start failed {start.status_code}")
        continue
    task_id = start.json().get("data", {}).get("task_id")
    if not task_id:
        summary.append((sid, False, "no task_id", None))
        print(f"Source {sid}: no task_id")
        continue

    # wait
    status = None
    for _ in range(240):  # up to 8 min
        time.sleep(2)
        pr = requests.get(f"{BASE}/api/novels/download/progress", params={"task_id": task_id}, timeout=TIMEOUT)
        try:
            pj = pr.json()
        except Exception:
            continue
        status = pj.get("data", {}).get("status")
        pct = pj.get("data", {}).get("progress_percentage")
        print(f"source {sid} progress: {status} {pct}%")
        if status == "completed":
            break
        if status == "failed":
            summary.append((sid, False, pj.get("data", {}).get("error_message", "failed"), None))
            print(f"Source {sid}: failed")
            break
    if status != "completed":
        if status == "failed":
            continue
        summary.append((sid, False, "timeout", None))
        print(f"Source {sid}: timeout")
        continue

    rr = requests.get(f"{BASE}/api/novels/download/result", params={"task_id": task_id}, stream=True, timeout=TIMEOUT)
    if rr.status_code != 200:
        summary.append((sid, False, f"result {rr.status_code}", None))
        print(f"Source {sid}: result error {rr.status_code}")
        continue

    cd = rr.headers.get("content-disposition", "")
    m = re.search(r"filename\*=UTF-8''([^;]+)", cd)
    filename = m.group(1) if m else f"download_{sid}.txt"
    filename = requests.utils.unquote(filename)

    size = 0
    with open(filename, "wb") as f:
        for chunk in rr.iter_content(chunk_size=8192):
            if chunk:
                size += len(chunk)
                f.write(chunk)

    text = open(filename, "r", encoding="utf-8", errors="ignore").read(1000)
    # Heuristic validation: size threshold and lack of obvious nav/seo lines
    bad_markers = ["最新章节目录", "如遇到内容无法显示", "首页 书库 排行"]
    ok = size > 1024 and not any(b in text for b in bad_markers)
    summary.append((sid, ok, f"size={size}", filename))
    print(f"Source {sid}: ok={ok}, file={filename}, size={size}")

print("SUMMARY:")
for sid, ok, msg, fn in summary:
    print(f"source {sid}: {'OK' if ok else 'BAD'} - {msg} - {fn or ''}")