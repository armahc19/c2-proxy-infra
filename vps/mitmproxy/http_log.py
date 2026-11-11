#!/usr/bin/env python3
import sqlite3, time, json, os
from mitmproxy import http

DB_PATH = os.environ.get("DB_PATH", "/logs/http.db")
DB = sqlite3.connect(DB_PATH, check_same_thread=False)
DB.execute("""CREATE TABLE IF NOT EXISTS reqs (
    ts REAL, client TEXT, sni TEXT, host TEXT, method TEXT,
    uri TEXT, status INT, req_len INT, resp_len INT,
    auth TEXT, user_agent TEXT, content_type TEXT)""")
DB.commit()

AUTH_KEYS = {"authorization", "cookie", "x-auth-token", "x-api-key", "x-csrf-token"}

def response(flow: http.HTTPFlow):
    c = flow.client_conn
    sni_raw = getattr(c, "sni", b"") or b""
    sni = sni_raw.decode() if isinstance(sni_raw, bytes) else sni_raw
    auth = "; ".join(f"{k}={v[:120]}" for k, v in flow.request.headers.items()
                     if k.lower() in AUTH_KEYS)
    DB.execute("INSERT INTO reqs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
        time.time(),
        c.peername[0] if c.peername else "",
        sni,
        flow.request.host,
        flow.request.method,
        flow.request.pretty_url,
        flow.response.status_code,
        len(flow.request.raw_content or b""),
        len(flow.response.raw_content or b""),
        auth,
        flow.request.headers.get("user-agent", ""),
        flow.request.headers.get("content-type", ""),
    ))
    DB.commit()