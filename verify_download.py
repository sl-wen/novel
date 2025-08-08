#!/usr/bin/env python3
import time
import requests
import re

BASE = "http://0.0.0.0:8000"

start = requests.post(
    f"{BASE}/api/novels/download/start",
    params={
        "url": "https://www.0xs.net/txt/1.html",
        "sourceId": 11,
        "format": "txt",
    },
    timeout=30,
)
start.raise_for_status()
data = start.json()
assert data.get("code") == 202, data
TASK_ID = data["data"]["task_id"]
print("TASK_ID:", TASK_ID)

# Poll until completed or timeout
status = None
for i in range(180):  # up to ~6 minutes
    time.sleep(2)
    pr = requests.get(f"{BASE}/api/novels/download/progress", params={"task_id": TASK_ID}, timeout=30)
    try:
        pj = pr.json()
    except Exception:
        print("Non-JSON progress:", pr.text)
        continue
    status = pj.get("data", {}).get("status")
    pct = pj.get("data", {}).get("progress_percentage")
    print(f"progress: {status} {pct}%")
    if status == "completed":
        break
    if status == "failed":
        raise SystemExit("Download failed: " + pj.get("data", {}).get("error_message", ""))

if status != "completed":
    raise SystemExit("Timeout waiting for completion")

# Fetch result
rr = requests.get(f"{BASE}/api/novels/download/result", params={"task_id": TASK_ID}, stream=True, timeout=120)
rr.raise_for_status()

# Determine filename from headers
cd = rr.headers.get("content-disposition", "")
m = re.search(r"filename\*=UTF-8''([^;]+)", cd)
filename = m.group(1) if m else "downloaded.txt"
filename = requests.utils.unquote(filename)

size = 0
with open(filename, "wb") as f:
    for chunk in rr.iter_content(chunk_size=8192):
        if chunk:
            size += len(chunk)
            f.write(chunk)

print("FILE:", filename)
print("SIZE:", size)

preview = open(filename, "r", encoding="utf-8", errors="ignore").read(500)
print("PREVIEW:\n", preview)

# Basic checks
ok = size > 1024 and ("书名" in preview or "作者" in preview or len(preview.strip()) > 50)
print("VALID:", ok)