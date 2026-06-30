# IJFINK Backend — Server Deployment Guide

End-to-end guide for deploying the IJFINK Flask backend on an Ubuntu VPS (tested on Oracle Cloud Ubuntu 24.04 LTS). Covers OS packages, virtual environment, Gunicorn, firewall rules, and keeping the service running after SSH disconnect.

For application features, environment variables, and API reference, see [README.md](README.md).

---

## 1. Prerequisites

- Ubuntu 22.04 / 24.04 VPS with `sudo` access
- Public IPv4 address assigned to the instance
- A MySQL server reachable from the VPS (local or remote)
- Domain DNS pointing an `A` record to your VPS public IP (optional, only needed for `api.yourdomain.com`)

If you are on Oracle Cloud, additional networking steps are required (Section 7). Other providers (DigitalOcean, Hetzner, AWS Lightsail) usually only need the OS-level firewall step.

---

## 2. Initial Server Setup

SSH into the VPS:

```bash
ssh ubuntu@YOUR_VPS_IP
```

Update the package index and upgrade installed packages:

```bash
sudo apt update
sudo apt upgrade -y
```

Install Python, pip, venv, git, and the MySQL client libraries needed by `mysql-connector-python`:

```bash
sudo apt install -y python3 python3-venv python3-pip git build-essential pkg-config default-libmysqlclient-dev
```

Verify versions:

```bash
python3 --version    # 3.11+ expected
pip3 --version
git --version
```

---

## 3. Clone the Repository

```bash
cd ~
git clone https://github.com/sayanroy058/IJFINK-Backend.git
cd IJFINK-Backend
```

To deploy a specific branch (e.g. `Server-test-branch`):

```bash
git checkout Server-test-branch
```

---

## 4. Python Virtual Environment

Create and activate a virtual environment inside the project directory:

```bash
python3 -m venv venv
source venv/bin/activate
```

Your prompt will change to `(venv) ubuntu@...`. Install project dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

`gunicorn` is the production WSGI server. It is not in `requirements.txt` by default — install it explicitly.

---

## 5. Environment Configuration

Create a `.env` file in the project root:

```bash
nano .env
```

Paste and edit:

```env
SECRET_KEY=replace-with-a-long-random-string
DEBUG=False
MYSQL_HOST=your-mysql-host
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=your_database_name
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X` in nano).

Set `DEBUG=False` for production. Never commit `.env` to git.

---

## 6. Database Schema

Load the schema into your MySQL server:

```bash
mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p "$MYSQL_DATABASE" < SQL_Scripts_\&_ERD/journaldb.sql
```

Or run the SQL manually in your database client of choice.

---

## 7. Oracle Cloud Networking (skip on other providers)

Oracle Cloud blocks all inbound traffic by default. Configure both the VCN-level Network Security Group **and** the OS-level firewall.

### 7.1 Network Security Group (NSG)

In the Oracle Cloud Console:

1. Navigate to **Networking → Virtual Cloud Networks → your VCN → Network Security Groups**.
2. Open the NSG attached to your instance (often `ig-quick-action-NSG`).
3. Add the following **Ingress** rules. Source Type: `CIDR`, Source CIDR: `0.0.0.0/0`, IP Protocol: `TCP`.

| Direction | Port | Purpose |
|-----------|------|---------|
| Ingress   | 80   | HTTP (Nginx, Certbot validation) |
| Ingress   | 443  | HTTPS |
| Ingress   | 5000 | Gunicorn (temporary; remove after Nginx is in front) |

### 7.2 Route Table

Confirm the VCN's default route table contains:

| Destination | Target |
|-------------|--------|
| `0.0.0.0/0` | Internet Gateway |

If missing, add it.

### 7.3 Subnet

The instance's subnet must be marked **Public Subnet**. Check under **VCN → Subnets**.

---

## 8. Host-Level Firewall (iptables)

Oracle's Ubuntu image ships with an `iptables` rule that rejects all inbound traffic except SSH. UFW is not installed by default, so `ufw status` will not show this rule — you must use `iptables` directly.

Check the current rules:

```bash
sudo iptables -L INPUT -n -v --line-numbers
```

You will see a final rule like:

```
REJECT  all  --  0.0.0.0/0  0.0.0.0/0  reject-with icmp-host-prohibited
```

Insert ACCEPT rules **before** the REJECT (replace `5` with the line number of the REJECT rule):

```bash
sudo iptables -I INPUT 5 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 5 -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 5 -p tcp --dport 5000 -j ACCEPT
```

Verify the new rules sit above the REJECT:

```bash
sudo iptables -L INPUT -n -v --line-numbers
```

Persist across reboots:

```bash
sudo apt install -y iptables-persistent
sudo netfilter-persistent save
```

---

## 9. Run Gunicorn

The project includes [wsgi.py](wsgi.py) as the WSGI entry point because `app.py` and the `app/` package share a name. Always reference `wsgi:app`, not `app:app`.

You can either run everything in one step using the [Auto Run script](#10-auto-run-runserversh), or run each command manually. The manual flow is documented first so the moving parts are clear; the auto-run script wraps the same steps.

### 9.1 Manual Run — Foreground (testing only)

```bash
cd ~/IJFINK-Backend
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

In another terminal, verify locally:

```bash
curl http://localhost:5000/health
```

Expected response:

```json
{"message": "IJFINK backend is running.", "success": true}
```

Then verify externally from your laptop:

```bash
curl http://YOUR_VPS_IP:5000/health
```

`Ctrl+C` to stop. Closing the SSH session also stops it — use one of the options below to keep it running.

### 9.2 Manual Run — Keep Running with nohup (quick option)

```bash
cd ~/IJFINK-Backend
source venv/bin/activate
nohup gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app > gunicorn.log 2>&1 &
disown
```

Flags explained:
- `nohup` — ignore the SIGHUP signal sent when the SSH session closes
- `> gunicorn.log 2>&1` — redirect stdout and stderr to a log file
- `&` — run in background
- `disown` — detach from the shell's job table so the process is fully independent

Useful commands:

```bash
ps aux | grep gunicorn          # check it's running
ss -tuln | grep 5000            # confirm port 5000 is bound
tail -f gunicorn.log            # tail logs
pkill -f "gunicorn -w 4 -b 0.0.0.0:5000"   # stop it
```

`nohup` does **not** auto-restart on crash and does **not** auto-start on reboot. For anything beyond short-term testing, use systemd (Section 9.3).

### 9.3 Keep Running with systemd (recommended for production)

Create a service unit:

```bash
sudo nano /etc/systemd/system/ijfink.service
```

Paste:

```ini
[Unit]
Description=IJFINK Flask backend (Gunicorn)
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/IJFINK-Backend
Environment="PATH=/home/ubuntu/IJFINK-Backend/venv/bin"
ExecStart=/home/ubuntu/IJFINK-Backend/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Reload, enable on boot, and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ijfink
sudo systemctl start ijfink
sudo systemctl status ijfink
```

Common operations:

```bash
sudo systemctl restart ijfink   # after pulling new code
sudo systemctl stop ijfink
sudo journalctl -u ijfink -f    # tail live logs
```

systemd handles SSH disconnect, crashes, and reboots automatically.

---

## 10. Auto Run (`run_server.sh`)

The repo ships with [run_server.sh](run_server.sh) — a single script that performs the full deploy cycle in one step:

1. `git pull --ff-only` to fetch the latest code (skippable)
2. Creates the venv if missing, otherwise reuses the existing one
3. Compares installed packages against `requirements.txt` and installs anything missing
4. Stops the current Gunicorn process (if any)
5. Restarts Gunicorn under `nohup` bound to `0.0.0.0:5000`, with logs in `gunicorn.log`

Use this when you want a quick "pull and restart" without remembering each manual step.

### 10.1 First-time setup

```bash
cd ~/IJFINK-Backend
chmod +x run_server.sh
./run_server.sh
```

That single command will install everything from scratch (venv, dependencies, Gunicorn) and start the backend. Run it again any time you push new code.

### 10.2 Available flags

| Flag | Effect |
|------|--------|
| _(none)_ | Pull latest code, sync venv/dependencies, restart Gunicorn |
| `--no-pull` | Skip `git pull` — useful when testing local edits |
| `--stop` | Stop the running Gunicorn process |
| `--status` | Print whether Gunicorn is running and what is bound to port 5000 |

### 10.3 What the script does internally

- Resolves its own directory, so it can be invoked from anywhere
- Activates the venv at `./venv` (creates it via `python3 -m venv` if absent)
- Upgrades `pip`, then iterates `requirements.txt` and runs `pip show <pkg>` to detect missing packages; only re-runs `pip install -r` when something is missing (a quick verification pass runs otherwise)
- Kills the existing Gunicorn process by pattern match (`gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app`) and falls back to `SIGKILL` if the process won't exit cleanly
- Launches Gunicorn with `nohup ... &` and `disown` so it survives SSH disconnect
- Verifies the process started; on failure, prints the last 20 lines of `gunicorn.log`

### 10.4 Logs and health check

```bash
tail -f ~/IJFINK-Backend/gunicorn.log
curl http://localhost:5000/health
```

### 10.5 Auto-start on reboot (optional)

`nohup` does not survive reboots. If you need that without switching to full systemd (Section 9.3), add a `@reboot` cron job:

```bash
crontab -e
```

Append:

```cron
@reboot /home/ubuntu/IJFINK-Backend/run_server.sh --no-pull >> /home/ubuntu/IJFINK-Backend/run_server.cron.log 2>&1
```

For long-term production use, systemd (Section 9.3) is still the better choice — it handles crash recovery, log rotation via journald, and graceful shutdown. `run_server.sh` is designed for fast iteration during development and testing.

---

## 11. Updating the Application

With the auto-run script:

```bash
cd ~/IJFINK-Backend
./run_server.sh
```

Manually:

```bash
cd ~/IJFINK-Backend
git pull
source venv/bin/activate
pip install -r requirements.txt    # only if dependencies changed
sudo systemctl restart ijfink      # or: pkill gunicorn && nohup ... if using nohup
```

---

## 12. Nginx Reverse Proxy + HTTPS (next step)

Once the backend is reachable on `http://YOUR_VPS_IP:5000`, put Nginx in front so the app is served on standard ports with TLS.

### 12.1 Install Nginx

```bash
sudo apt install -y nginx
```

### 12.2 Configure the site

```bash
sudo nano /etc/nginx/sites-available/ijfink
```

Paste (replace `api.yourdomain.com`):

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/ijfink /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 12.3 Install TLS certificate with Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

Certbot will edit the Nginx config to add HTTPS and set up auto-renewal.

### 12.4 Lock down port 5000

Once Nginx is proxying correctly, port 5000 no longer needs to be exposed publicly.

Remove the Oracle NSG rule for TCP 5000, and remove the iptables rule:

```bash
sudo iptables -L INPUT -n -v --line-numbers
sudo iptables -D INPUT <line-number-of-5000-rule>
sudo netfilter-persistent save
```

Gunicorn can also be bound to `127.0.0.1:5000` instead of `0.0.0.0:5000` for extra safety — update the `ExecStart` line in `ijfink.service` and `systemctl restart ijfink`.

---

## 13. Troubleshooting

### `Failed to find attribute 'app' in 'app'`

You ran `gunicorn app:app`. Because the project has both `app.py` and an `app/` package, Python imports the package, which only exposes `create_app`. Use `wsgi:app` instead — see [wsgi.py](wsgi.py).

### `curl http://VPS_IP:5000` times out from outside, works locally

The OS-level iptables REJECT rule (Section 8) is dropping packets. Insert ACCEPT rules **above** it.

### `curl http://VPS_IP:5000` times out from outside, port not listening locally either

Gunicorn is not running. Check `ss -tuln | grep 5000` and `sudo systemctl status ijfink`.

### Gunicorn stops after closing SSH

You started it in the foreground or without `nohup`/`disown`. Use systemd (Section 9.3) or nohup (Section 9.2).

### Connection works on `:5000` but not on `:80`

Nginx isn't installed yet or isn't proxying — see Section 12.

### Browser blocks API calls with "mixed content"

Your Vercel frontend is HTTPS but the backend is HTTP. Finish Section 12.3 to enable HTTPS on the backend.

---

## 14. Quick Reference

| Action | Command |
|--------|---------|
| Auto deploy | `./run_server.sh` |
| Auto deploy without git pull | `./run_server.sh --no-pull` |
| Stop (auto) | `./run_server.sh --stop` |
| Status (auto) | `./run_server.sh --status` |
| Activate venv | `source ~/IJFINK-Backend/venv/bin/activate` |
| Start (nohup) | `nohup gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app > gunicorn.log 2>&1 & disown` |
| Stop (nohup) | `pkill -f "gunicorn -w 4 -b 0.0.0.0:5000"` |
| Start (systemd) | `sudo systemctl start ijfink` |
| Restart (systemd) | `sudo systemctl restart ijfink` |
| Tail logs (systemd) | `sudo journalctl -u ijfink -f` |
| Tail logs (nohup/auto) | `tail -f ~/IJFINK-Backend/gunicorn.log` |
| Check port | `ss -tuln \| grep 5000` |
| Health check | `curl http://localhost:5000/health` |
