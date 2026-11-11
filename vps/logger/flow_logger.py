#!/usr/bin/env python3
# vps/logger/flow_logger.py
import sqlite3, time, threading, os
from scapy.all import sniff, IP, TCP, UDP, DNS

DB_PATH = os.environ.get("DB_PATH", "/logs/flows.db")
DB = sqlite3.connect(DB_PATH, check_same_thread=False)
DB.execute("""CREATE TABLE IF NOT EXISTS flows (
    ts REAL, src TEXT, dst TEXT, proto TEXT,
    sport INT, dport INT, bytes INT, info TEXT)""")
DB.commit()
LOCK = threading.Lock()

def log(row):
    with LOCK:
        DB.execute("INSERT INTO flows VALUES (?,?,?,?,?,?,?,?)", row)
        DB.commit()

def handle(pkt):
    if not pkt.haslayer(IP):
        return
    ip = pkt[IP]
    proto = "TCP" if pkt.haslayer(TCP) else "UDP" if pkt.haslayer(UDP) else str(ip.proto)
    sport = dport = 0
    if pkt.haslayer(TCP):
        sport, dport = pkt[TCP].sport, pkt[TCP].dport
    elif pkt.haslayer(UDP):
        sport, dport = pkt[UDP].sport, pkt[UDP].dport
    info = ""
    if pkt.haslayer(DNS) and pkt[DNS].qd:
        info = f"DNS q={pkt[DNS].qd.qname.decode(errors='replace')}"
    log((time.time(), ip.src, ip.dst, proto, sport, dport, len(pkt), info))

sniff(ifaces=["tun0", "eth0"], filter="ip", prn=handle, store=False)