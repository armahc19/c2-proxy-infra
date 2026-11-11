#!/usr/bin/env python3
"""Generate the QR code PNG for the lab landing URL (WhatsApp image flow).

    python3 render/whatsapp_qr.py http://172.24.241.91:5000 /tmp/lab-qr.png
    python3 render/whatsapp_qr.py https://c2-landing.onrender.com /tmp/render-qr.png

Send the PNG as the WhatsApp image; the recipient scans it or taps the
caption link. Both must point at the SAME landing page URL.
"""
import sys

import qrcode


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(f"usage: {sys.argv[0]} <landing-url> <out.png>")
    url, out = sys.argv[1], sys.argv[2]

    img = qrcode.make(url, box_size=10, border=2)
    img.save(out)

    print(f"QR written: {out}")
    print(f"  URL      : {url}")
    print(f"  WhatsApp : attach {out} + set the message link to the SAME url")
    print("  scan on the test iPhone via Camera, or tap the message link.")


if __name__ == "__main__":
    main()
