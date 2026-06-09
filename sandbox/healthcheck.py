from __future__ import annotations

import json
from urllib.request import urlopen


with urlopen("http://127.0.0.1:8080/health", timeout=2) as response:
    payload = json.loads(response.read().decode("utf-8"))
    if response.status != 200 or payload.get("status") != "foundation_ready":
        raise SystemExit(1)
