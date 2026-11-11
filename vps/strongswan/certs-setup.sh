#!/bin/sh
set -e
cd /etc/ipsec.d

if [ ! -f server.crt ]; then
    ipsec pki --gen --type rsa --size 4096 --outform pem > server-key.pem
    SERVER_IP=$(curl -s ifconfig.me)
    ipsec pki --pub --in server-key.pem --type rsa \
        | ipsec pki --issue --lifetime 3650 \
          --cacert ca-cert.pem --cakey ca-key.pem \
          --dn "CN=${SERVER_IP}" \
          --san "${SERVER_IP}" \
          --flag serverAuth \
          --outform pem > server.crt
    cp ca-cert.pem /etc/ipsec.d/ca.crt
fi
# NAT: full tunnel → egress; block QUIC (HTTP/3) so traffic hits mitmproxy over TCP
iptables -t nat -A POSTROUTING -s 10.10.0.0/24 -o eth0 -j MASQUERADE || true
iptables -A FORWARD -i tun0 -p udp --dport 443 -j DROP || true
iptables -t nat -A PREROUTING -i tun0 -p tcp --dport 80  -j REDIRECT --to-port 8080 || true
iptables -t nat -A PREROUTING -i tun0 -p tcp --dport 443 -j REDIRECT --to-port 8080 || true
# EAP secrets: the operator appends per-device lines to /etc/ipsec.secrets
# (see landing README), then runs 'ipsec rereadsecrets' inside the running
# container. There is no 'ipsec secrets' subcommand - and any failing command
# here would abort this script before 'ipsec start' runs (set -e).