#!/usr/bin/env python3
# Runs mitmproxy in regular (explicit) proxy mode on Render.
# iOS HTTP proxy payload points here: http://proxy-xxxx.onrender.com:PORT
import os, subprocess

port = os.environ.get("PORT", "8080")

# mitmproxy regular mode — iOS profile sends traffic here as an explicit HTTP proxy
cmd = [
    "mitmdump", "--mode", "regular",
    "--listen-host", "0.0.0.0", "--listen-port", str(port),
    "--set", "block_global=false",
    # Render terminates TLS; behind it traffic is plaintext HTTP — fine for proxy fallback
    "-s", "/opt/proxy_addon.py" if os.path.exists("/opt/proxy_addon.py") else "-q",
]
# NOTE: COLLECTOR_URL (log shipping) is read by proxy_addon.py itself. Do not
# pass it as a mitmproxy option — there is no "upstream_log_url" option and
# mitmdump exits on unknown --set keys.
subprocess.run(cmd)
