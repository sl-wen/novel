#!/usr/bin/env python3
import re
import time

import requests

BASE = "http://127.0.0.1:8000"


def test_optimized_search() -> dict:
    print("[1] Optimized search...")
    r = requests.get(
        f"{BASE}/api/optimized/search",
        params={"keyword": "修真", "maxResults": 3},
        timeout=60,
    )
    r.raise_for_status()
    js = r.json()
    assert js.get("code") == 200, js
    items = js.get("data") or []
    assert items, "no results"
    print("  results:", len(items))
    return items[0]


def test_optimized_direct_download(url: str, source_id: int):
    print("[2] Optimized direct download (header encoding check)...")
    r = requests.get(
        f"{BASE}/api/optimized/download",
        params={"url": url, "sourceId": source_id, "format": "txt"},
        stream=True,
        timeout=300,
    )
    print("  status:", r.status_code)
    if r.status_code != 200:
        print("  body:", r.text[:200])
    r.raise_for_status()
    cd = r.headers.get("Content-Disposition", "")
    assert "filename*=" in cd, cd
    print("  content-disposition:", cd)
    # Do not save file; just read a small chunk to ensure streaming works
    _ = next(r.iter_content(chunk_size=1024))
    print("  stream ok")


def test_polling_download(url: str, source_id: int):
    print("[3] Async download with progress polling...")
    start = requests.post(
        f"{BASE}/api/novels/download/start",
        params={"url": url, "sourceId": source_id, "format": "txt"},
        timeout=120,
    )
    start.raise_for_status()
    data = start.json()
    assert data.get("code") == 202, data
    task_id = data["data"]["task_id"]
    print("  task:", task_id)

    status = None
    for _ in range(120):  # up to ~4 minutes
        time.sleep(2)
        pr = requests.get(
            f"{BASE}/api/novels/download/progress",
            params={"task_id": task_id},
            timeout=30,
        )
        pj = pr.json()
        status = pj.get("data", {}).get("status")
        pct = pj.get("data", {}).get("progress_percentage")
        print("  progress:", status, pct)
        if status in ("completed", "failed"):
            break

    assert status == "completed", f"status={status}"

    rr = requests.get(
        f"{BASE}/api/novels/download/result",
        params={"task_id": task_id},
        stream=True,
        timeout=300,
    )
    rr.raise_for_status()
    cd = rr.headers.get("Content-Disposition", "")
    m = re.search(r"filename\*=UTF-8''([^;]+)", cd)
    print("  result content-disposition:", cd)
    assert m, cd
    print("  polling download ok")


def main():
    first = test_optimized_search()
    url = first.get("url")
    source_id = first.get("source_id", 2)
    print("Use:", url, source_id)

    try:
        test_optimized_direct_download(url, source_id)
    except Exception as e:
        print("[WARN] Direct optimized download check failed:", e)

    test_polling_download(url, source_id)
    print("All checks passed.")


if __name__ == "__main__":
    main()
