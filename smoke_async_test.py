#!/usr/bin/env python3
import time
import requests

BASE = "http://0.0.0.0:8000"

print("Starting async download...")
r = requests.post(
    f"{BASE}/api/novels/download/start",
    params={
        "url": "https://www.0xs.net/txt/1.html",
        "sourceId": 11,
        "format": "txt",
    },
    timeout=30,
)
print("START:", r.status_code, r.text)

data = r.json()
assert data.get("code") == 202, data
TASK_ID = data["data"]["task_id"]
print("TASK_ID:", TASK_ID)

for i in range(5):
    time.sleep(2)
    pr = requests.get(f"{BASE}/api/novels/download/progress", params={"task_id": TASK_ID}, timeout=30)
    print(f"PROGRESS {i+1}:", pr.status_code, pr.text)

rr = requests.get(f"{BASE}/api/novels/download/result", params={"task_id": TASK_ID}, timeout=30)
print("RESULT:", rr.status_code)
print(rr.text[:200])