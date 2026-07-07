#!/bin/bash
# HZM Rendezvous one-paste installer (Ubuntu/Debian).
# Usage (on the fresh Oracle VM):
#   curl -sL https://raw.githubusercontent.com/MOHCoopTrilogy/releases/main/tools/rendezvous/setup.sh | sudo bash
set -e

echo "== HZM Rendezvous setup =="

apt-get update -qq
apt-get install -y -qq gcc curl > /dev/null

echo "-- fetching + building daemon"
curl -sL https://raw.githubusercontent.com/MOHCoopTrilogy/releases/main/tools/rendezvous/hzm_rendezvous.c -o /tmp/hzm_rendezvous.c
cc -O2 -o /usr/local/bin/hzm_rendezvous /tmp/hzm_rendezvous.c

echo "-- opening udp/12301 in the OS firewall"
iptables -I INPUT -p udp --dport 12301 -j ACCEPT
# persist the rule (best effort - package name differs across images)
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq iptables-persistent > /dev/null 2>&1 && netfilter-persistent save > /dev/null 2>&1 || true

echo "-- installing service"
cat > /etc/systemd/system/hzm-rendezvous.service <<'UNIT'
[Unit]
Description=HZM MOH Coop rendezvous
After=network.target

[Service]
ExecStart=/usr/local/bin/hzm_rendezvous 12301
Restart=always
DynamicUser=yes

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now hzm-rendezvous
sleep 1
systemctl --no-pager status hzm-rendezvous | head -5

PUBIP=$(curl -sL ifconfig.me || echo "<your VM public IP>")
echo ""
echo "== DONE. Rendezvous running on udp/12301 =="
echo "   In the game (host): net_rdv_host ${PUBIP}:12301 ; net_rdv_code <word> ; net_rdv 1"
echo "   REMINDER: also open UDP 12301 in the Oracle web console (VCN Security List ingress rule)."
