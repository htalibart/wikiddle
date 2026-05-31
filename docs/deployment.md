# Deployment

This document describes how to set up and deploy Wikiddle on a bare VPS.

## Infrastructure overview

- **VPS provider:** Hetzner
- **OS:** Debian 13 (trixie)
- **Web server:** Caddy (reverse proxy + static file server)
- **Backend:** FastAPI running via uvicorn, managed by systemd
- **Frontend:** Static HTML/CSS/JS bundled with Vite, served from `frontend/dist/`
- **TLS:** Cloudflare Origin Certificate (SSL/TLS mode: Full strict)

---

## Base server setup

### 1. Configure the firewall

The firewall is configured in the Hetzner dashboard under **Firewalls**. The following inbound rules are set:

| Port | Protocol | Source        | Purpose    |
|------|----------|---------------|------------|
| 22   | TCP      | My IPs only | SSH access |
| 80   | TCP      | Any           | HTTP       |
| 443  | TCP      | Any           | HTTPS      |

### 2. Disable root login

On the server, edit the SSH configuration:

```bash
sudo vim /etc/ssh/sshd_config
```

Set the following:

```
PermitRootLogin no
```

Then restart SSH:

```bash
sudo systemctl restart ssh
```

### 3. Create personal user

Instead of using root, all operations run as a personal user with full sudo:

```bash
sudo adduser myname
sudo usermod -aG sudo myname
sudo mkdir /home/myname/.ssh
sudo cp ~/.ssh/authorized_keys /home/myname/.ssh/
sudo chown -R myname:myname /home/myname/.ssh
```

Open a new terminal and verify you can SSH in as `myname` before continuing.

### 4. Create the deploy user and deployers group

The `deploy` user is a restricted account used exclusively for deployments

```bash
sudo adduser deploy
sudo groupadd deployers
sudo usermod -aG deployers deploy
sudo usermod -aG deployers myname
```

### 5. Enable automatic security updates

```bash
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure unattended-upgrades
```

This automatically installs security updates in the background.

---

## Initial server setup

### 1. Install system dependencies

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y
```

To build the frontend, we need to install Node >= 24:

```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v
```

### 2. Install Caddy

Caddy is not in the default Debian repositories, so add the official Caddy repository first:

```bash
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
sudo chmod o+r /etc/apt/sources.list.d/caddy-stable.list
sudo apt install caddy
```

Caddy is automatically enabled on boot when installed this way.

Caddy runs as the `caddy` system user and needs to read files in `/var/www/wikiddle`, which belongs to the `deployers` group:

```bash
sudo usermod -aG deployers caddy
```

### 3. Set up the deploy key

The repo is private, so the server needs a deploy key to pull from GitHub.

Add the server's public key (`~/.ssh/github_deploy.pub`) to the GitHub repo under **Settings → Deploy keys**. Enable read-only access.

### 4. Clone the repository

```bash
sudo mkdir -p /var/www/wikiddle
sudo chown -R deploy:deployers /var/www/wikiddle
sudo chmod -R g+rw /var/www/wikiddle
git clone git@github.com:htalibart/wikiddle.git /var/www/wikiddle
```

### 5. Set up the Python virtual environment

```bash
cd /var/www/wikiddle
python3 -m venv venv
venv/bin/pip install -r backend/requirements.txt
```

### 6. Generate the database

The database is not in the repo (too large). It is generated from Wikipedia dumps using scripts in `scripts/`:

```bash
bash scripts/download_wikipedia.sh ${LANGUAGE}
```

This downloads Wikipedia dump files. Replace `${LANGUAGE}` with `en` for English, `fr` for French, etc.

```bash
python3 scripts/xml_to_sql.py ${LANGUAGE}
```

This reads the XML dump files and generates a SQL database.

```bash
python3 scripts/add_is_target_candidate.py ${LANGUAGE}
```

This adds the `is_target_candidate` column to the database based on filters (to remove articles no one cares about such as sport-related pages from candidate daily targets).



### 7. Build the frontend

`package.json` and `package-lock.json` are versioned in the repo, but `node_modules/` (the actual installed packages) is not. Install them first:

```bash
cd /var/www/wikiddle/frontend
npm ci
npm run build
```

`npm ci` installs the exact versions specified in `package-lock.json`. `npm run build` runs Vite, which bundles the JS files into `frontend/dist/`, which is what Caddy serves.

### 8. Set up Caddy and HTTPS

#### Step 1 — Point the domain to the server

In the Cloudflare dashboard:
1. Click on `wikiddle.com`
2. Click **DNS** in the left sidebar
3. Add an A record (a DNS entry that maps a domain name to an IP address) pointing `wikiddle.com` to the Hetzner server's public IP

The A record is set to **proxied** (orange cloud), meaning all traffic goes through Cloudflare rather than directly to the server. This enables Cloudflare's DDoS protection and caching.

#### Step 2 — Set up HTTPS

Because Cloudflare proxies traffic, Let's Encrypt cannot reach the server directly to issue a certificate. Instead, use a Cloudflare Origin Certificate — a certificate generated by Cloudflare specifically for the connection between Cloudflare and the server.

**Set SSL/TLS mode to Full (strict)**

In the Cloudflare dashboard:
1. Click **SSL/TLS** in the left sidebar
2. Click **Overview**
3. Set the encryption mode to **Full (strict)**

This means Cloudflare encrypts traffic both between users and Cloudflare, and between Cloudflare and the server, and verifies that the server's certificate is legitimate.

**Generate a Cloudflare Origin Certificate**

In the Cloudflare dashboard:
1. Click **SSL/TLS** in the left sidebar
2. Click **Origin Server**
3. Click **Create Certificate**
4. Leave the defaults (RSA, 15 years)
5. Copy the **Origin Certificate** and **Private Key**

Save them on the server:

```bash
sudo vim /etc/caddy/wikiddle.pem   # paste the Origin Certificate
sudo vim /etc/caddy/wikiddle.key   # paste the Private Key
```

Set correct permissions. Caddy runs as the `caddy` system user, so it needs ownership of these files to read them:

```bash
sudo chmod 600 /etc/caddy/wikiddle.key
sudo chown caddy:caddy /etc/caddy/wikiddle.pem /etc/caddy/wikiddle.key
```

#### Step 3 — Configure Caddy

Tell the Caddy systemd service to use the config file from the repo:

```bash
sudo systemctl edit caddy
```

Add the following:

```ini
[Service]
ExecStart=
ExecStart=/usr/bin/caddy run --environ --config /var/www/wikiddle/config/Caddyfile.prod
ExecReload=
ExecReload=/usr/bin/caddy reload --config /var/www/wikiddle/config/Caddyfile.prod
```

The empty `ExecStart=` and `ExecReload=` lines clear the defaults defined by Caddy's systemd service before setting the new ones.

Then reload and restart Caddy:

```bash
sudo systemctl daemon-reload
sudo systemctl restart caddy
```

### 9. Configure the systemd service

The service file is versioned in the repo at `config/wikiddle.service`. Create a symlink so systemd picks it up:

```bash
sudo ln -s /var/www/wikiddle/config/wikiddle.service /etc/systemd/system/wikiddle.service
```

Enable and start the service:

```bash
sudo systemctl daemon-reload  # reload systemd so it picks up the new service file
sudo systemctl enable wikiddle  # start wikiddle automatically on boot
sudo systemctl start wikiddle  # start wikiddle now
```

Grant the `deploy` user the right to restart wikiddle and caddy without a password:

```bash
echo "deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart wikiddle, /bin/systemctl restart caddy" | sudo tee /etc/sudoers.d/deploy-wikiddle
```

### 10. Auto refresh
The database of previous games is updated every day with a crontab job that calls an API endpoint. To set it up I generated a token with:
```bash
openssl rand -hex 32
```

and copied it into `/etc/wikiddle/secrets`
```
ADMIN_TOKEN=<my_secret_token>
```

The file is referenced in the wikiddle systemd file (`EnvironmentFile=/etc/wikiddle/secrets`).

Then configured a crontab job that calls the endpoint every day at 1AM:
```bash
crontab -e
```

```
0 1 * * * . /etc/wikiddle/secrets && curl -s -X POST -H "Authorization: Bearer $ADMIN_TOKEN" "http://127.0.0.1:8000/api/admin/refresh"
```


---

## Deploying a new version

```bash
cd /var/www/wikiddle
git pull origin main
venv/bin/pip install -r backend/requirements.txt  # only if dependencies changed; no need to activate the venv
cd frontend && npm ci && npm run build && cd ..  # only if frontend changed
sudo systemctl restart wikiddle
sudo systemctl restart caddy  # only if Caddyfile.prod changed
```

If changes are not reflected immediately, purge the Cloudflare cache: in the Cloudflare dashboard, click on `wikiddle.com`, then **Caching -> Configuration -> Purge Everything**.

---

## Useful commands

```bash
# View backend logs (live)
sudo journalctl -u wikiddle -f

# View Caddy logs (live)
sudo journalctl -u caddy -f

# Check backend service status
sudo systemctl status wikiddle

# Check Caddy service status
sudo systemctl status caddy
```
