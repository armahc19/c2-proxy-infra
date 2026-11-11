#!/usr/bin/env python3
# render/proxy_addon.py — same schema as the VPS logger
import os, sys, time, httpx, sqlite3
from mitmproxy import http

DB = sqlite3.connect("/tmp/proxy.db", check_same_thread=False)
DB.execute("""CREATE TABLE IF NOT EXISTS reqs (
    ts REAL, client TEXT, host TEXT, method TEXT,
    uri TEXT, status INT, auth TEXT)""")
DB.commit()
UPSTREAM = os.environ.get("COLLECTOR_URL", "")
AUTH_KEYS = {"authorization", "cookie", "x-auth-token", "x-api-key"}

# /ingest is Bearer-protected; shipping without the token fails silently
if UPSTREAM and not os.environ.get("COLLECT_TOKEN"):
    print("proxy_addon: COLLECTOR_URL is set but COLLECT_TOKEN is missing - "
          "the collector will reject every /ingest", file=sys.stderr)

def response(flow: http.HTTPFlow):
    auth = "; ".join(f"{k}={v[:120]}" for k, v in flow.request.headers.items()
                     if k.lower() in AUTH_KEYS)
    row = (time.time(), flow.client_conn.peername[0] if flow.client_conn.peername else "",
           flow.request.host, flow.request.method,
           flow.request.pretty_url, flow.response.status_code, auth)
    DB.execute("INSERT INTO reqs VALUES (?,?,?,?,?,?,?)", row)
    DB.commit()
    if UPSTREAM and os.environ.get("COLLECT_TOKEN"):
        try:
            httpx.post(f"{UPSTREAM}/ingest",
                       headers={"Authorization": f"Bearer {os.environ['COLLECT_TOKEN']}"},
                       json={"ts": row[0], "client": row[1], "host": row[2],
                             "method": row[3], "uri": row[4], "status": row[5],
                             "auth": row[6]},
                       timeout=2)
        except Exception:
            pass
