# HZM Rendezvous — Oracle Always-Free Setup

One tiny UDP service that lets friends join your coop server with a memorable code
instead of port forwarding. Runs comfortably on the smallest Always-Free shape.

## 1. Create the VM (one time, ~10 minutes)

1. Sign up / log in at cloud.oracle.com (Always Free tier — no charges, card required for identity).
2. Compute → Instances → **Create instance**:
   - Image: **Ubuntu 24.04** (or any recent Ubuntu/Debian)
   - Shape: **VM.Standard.E2.1.Micro** (Always-Free) — or the Ampere A1 flex shape, also free
   - Networking: keep the defaults (public IPv4 assigned)
   - Add your SSH public key (or let Oracle generate a key pair and download it)
3. Note the instance's **public IP** after it starts.

## 2. Open the UDP port

Two firewalls need the hole — Oracle's cloud one AND the OS one:

1. **Oracle side**: Instance page → its Virtual Cloud Network → Security Lists →
   Default Security List → **Add Ingress Rule**:
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: **UDP**
   - Destination Port Range: **12301**
2. **OS side** (after SSH-ing in):
   ```
   sudo iptables -I INPUT -p udp --dport 12301 -j ACCEPT
   sudo netfilter-persistent save   # (sudo apt install iptables-persistent if missing)
   ```

## 3. Build + install the daemon

```
ssh ubuntu@<VM_IP>
sudo apt update && sudo apt install -y gcc
# copy hzm_rendezvous.c over (scp from your PC, or paste into nano):
#   scp tools/rendezvous/hzm_rendezvous.c ubuntu@<VM_IP>:~
cc -O2 -o hzm_rendezvous hzm_rendezvous.c
sudo mv hzm_rendezvous /usr/local/bin/
```

Run it under systemd so it survives reboots:

```
sudo tee /etc/systemd/system/hzm-rendezvous.service > /dev/null <<'UNIT'
[Unit]
Description=HZM MOH Coop rendezvous
After=network.target

[Service]
ExecStart=/usr/local/bin/hzm_rendezvous 12301
Restart=always
User=nobody
DynamicUser=yes

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now hzm-rendezvous
systemctl status hzm-rendezvous    # should say "listening on udp/12301"
```

## 4. Point the game at it

Once the engine side ships, the host sets (console, saved automatically):

```
net_rdv_host <VM_IP>:12301
net_rdv_code <your-word>       // e.g. pizza — stable across sessions
net_rdv 1
```

Console prints `rendezvous: ONLINE - join code '<word>'` once registered.
Friends join with:

```
coop_join <your-word>
```

Fallback stays unchanged: port forwarding 12203/UDP + `connect <ip>` always works.

## Notes

- The daemon holds no state worth backing up; restart/redeploy freely.
- Codes expire 60 s after the host stops its keepalive (game closed).
- Rate-limited per IP; the join code is a weak shared secret — fine for friends.
- To watch it live: `journalctl -u hzm-rendezvous -f`
