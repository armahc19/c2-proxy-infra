FROM python:3.11-slim
RUN pip install mitmproxy fastapi uvicorn httpx
WORKDIR /app
COPY proxy_fallback.py /app/proxy_fallback.py
COPY collector_api.py /app/collector_api.py
COPY proxy_addon.py /opt/proxy_addon.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Render exposes exactly one port per web service ($PORT). ROLE picks what
# binds it so the two services sharing this image never fight over the port:
#   proxy-fallback -> ROLE=proxy      (mitmproxy explicit proxy on $PORT)
#   log-collector  -> ROLE=collector  (FastAPI collector on $PORT)
#   ROLE=both (default, local/dev)  -> collector on 127.0.0.1:$COLLECTOR_PORT,
#                                      proxy on $PORT (collector stays internal)
ENV PORT=8080 COLLECTOR_PORT=8000 ROLE=both
ENTRYPOINT ["/app/entrypoint.sh"]
