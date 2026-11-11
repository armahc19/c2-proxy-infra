#!/usr/bin/env python3
# render/collector_api.py — receives logs from VPS + Render proxy, serves them back
import os, sqlite3, time, json
from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse

# Fail closed: this store holds intercepted auth headers, so it must never
# come up with an empty or well-known token.
TOKEN = os.environ.get("COLLECT_TOKEN", "")
if not TOKEN or TOKEN == "changeme":
    raise SystemExit(
        "COLLECT_TOKEN is not set (or still the default 'changeme') - "
        "set a strong random token before starting the collector."
    )
DB = sqlite3.connect("/tmp/collector.db", check_same_thread=False)
DB.execute("""CREATE TABLE IF NOT EXISTS events (
    ts REAL, source TEXT, client TEXT, host TEXT,
    method TEXT, uri TEXT, status INT, auth TEXT, extra TEXT)""")
DB.commit()

app = FastAPI()

def auth_tok(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer ") or authorization[7:] != TOKEN:
        raise HTTPException(403)

@app.post("/ingest", dependencies=[Depends(auth_tok)])
async def ingest(req: Request):
    d = await req.json()
    DB.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)", (
        d.get("ts", time.time()), d.get("source", "render"),
        d.get("client", ""), d.get("host", ""), d.get("method", ""),
        d.get("uri", ""), d.get("status", 0), d.get("auth", ""),
        json.dumps(d.get("extra", {}))))
    DB.commit()
    return {"ok": True}

@app.get("/events", dependencies=[Depends(auth_tok)])
async def events(limit: int = 100, host: str = None):
    q = "SELECT * FROM events"
    args = []
    if host:
        q += " WHERE host LIKE ?"
        args.append(f"%{host}%")
    q += " ORDER BY ts DESC LIMIT ?"
    args.append(limit)
    rows = DB.execute(q, args).fetchall()
    cols = ["ts", "source", "client", "host", "method", "uri", "status", "auth", "extra"]
    return JSONResponse([dict(zip(cols, r)) for r in rows])