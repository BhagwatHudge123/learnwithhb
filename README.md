<<<<<<< HEAD
# LearnWithHB — local starter and EC2 deployment guide

A responsive Flask + SQLite starter for the LearnWithHB learning-resource site. It includes a public home page, categories/search, document detail pages, account registration/login, admin uploads, free blog publishing, purchase-history screens, and Razorpay order/signature/payment checks. It is intentionally easy to run on Windows first and Ubuntu EC2 later.

## Important implementation status

- **Works locally:** website pages, account registration/login, admin bootstrap, uploading PDF/DOCX/ZIP files, setting a price, publishing/unpublishing material and blogs, SQLite data persistence, admin dashboard, library pages, access checks, and free article pages.
- **Razorpay:** integration code is included but requires your own Razorpay Test Mode keys, webhook configuration, and end-to-end testing. Do not switch to live payments until you test order creation, capture, signature verification, webhook delivery, refunds and reconciliation.
- **Storage:** uploads are stored in the local `uploads/` directory in this starter. S3 settings are examples only; S3 upload/presigned-download logic is **not yet wired in**. For production, use a private S3 bucket and short-lived presigned downloads after checking entitlement.
- **Not production-certified:** add CSRF protection to every state-changing form, rate limiting, email verification/password reset, secure account recovery, database migrations/backups, malware scanning, structured audit logs, and a security review before accepting public traffic or live payments. The basic starter does not claim to satisfy every item in the original master prompt.
- Article body is stored as plain text; Markdown rendering and syntax highlighting are not enabled yet.

## A. Run on Windows locally

### 1. Install prerequisites

1. Install **Python 3.11 or 3.12** from https://www.python.org/downloads/ (check “Add Python to PATH”). Python 3.13 may work, but if a dependency fails, use Python 3.12.
2. Install **Git** only if you plan to use source control; it is not required to run the zip.
3. Extract `LearnWithHB.zip` into a folder such as `C:\Projects\LearnWithHB`.

### 2. Open PowerShell in the project folder

In File Explorer, open the extracted `LearnWithHB` folder, click the address bar, type `powershell`, and press Enter. Then run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, run this only for the current PowerShell window, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Set your local admin login

Open `.env` in Notepad. Change these values:

```dotenv
SECRET_KEY=replace-with-a-long-random-secret
ADMIN_EMAIL=your-admin-email@example.com
ADMIN_PASSWORD=Use-A-Long-Unique-Password-Here
SITE_URL=http://127.0.0.1:5000
```

Use a long random `SECRET_KEY` and a unique admin password. Do not share `.env`, upload it to GitHub, or include it in a public zip. The first time the app starts, it creates the admin account if that email does not already exist. If the database already exists, changing `ADMIN_PASSWORD` in `.env` does not reset an existing account's password.

### 4. Start the site

```powershell
python app.py
```

Open http://127.0.0.1:5000 in your browser. Stop the development server with `Ctrl+C`.

### 5. Add your first document and blog

1. Select **Login / Sign up** and sign in with the admin email/password from `.env`.
2. Open **Admin** in the navigation.
3. Choose **Add study material**. Add a title, description, category, price (default ₹100), PDF/DOCX/ZIP file, and select **Publish publicly**.
4. Save. Use **Preview** to open the shareable public product page. The public link will look like `http://127.0.0.1:5000/materials/your-document-slug`.
5. Choose **Write a blog**, enter the title, category, excerpt and article, and check **Publish article** to make it public without payment.
6. Register a normal user account in a private/incognito window to test the customer experience.

**Local payment behaviour:** if Razorpay keys are empty, the Buy action shows a message and does not grant a download. This is deliberate; there is no fake payment success. A real paid download is available only after a payment is verified.

### 6. Back up local data

Stop the server first. Copy `learnwithhb.db` and the `uploads` folder to a safe location. These contain the website's database and uploaded documents. Never commit them to a public repository.

## B. Configure Razorpay Test Mode

1. Create/sign in to your Razorpay account at https://razorpay.com/ and enable **Test Mode**.
2. Find the Test Mode Key ID and Key Secret in the Razorpay dashboard.
3. Put them in `.env` (server side only):

```dotenv
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxx
RAZORPAY_KEY_SECRET=your_test_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
SITE_URL=http://127.0.0.1:5000
```

4. Install/use a secure tunnel if you need Razorpay to call a local webhook; configure the webhook URL as `https://YOUR-TUNNEL-HOST/razorpay/webhook` and subscribe to `payment.captured`. Set the same webhook secret in `.env`.
5. Restart Flask after changing `.env`.
6. Test with Razorpay's documented test credentials/payment methods, not a real card. Check pending, failed, successful, duplicate webhook and browser-closed cases.
7. For production, use HTTPS and the production keys only after all tests and security review. Never place the key secret in HTML/JavaScript or expose `.env`.

The webhook route checks the webhook signature and captured payment amount/currency/order. The browser return handler also checks the signature and fetches payment status server-side. Before launch, verify the exact payment capture behaviour for your Razorpay account and add reconciliation for pending/authorized payments.

## C. Deploy to AWS EC2 Ubuntu (recommended pattern)

This is a single-instance starter deployment. For a real storefront, use PostgreSQL (RDS), private S3, HTTPS, monitoring, backups and a tested deployment/rollback process. Do not expose Flask's development server to the internet.

### 1. Create the EC2 instance

1. Launch Ubuntu Server 24.04 LTS (or your organisation's supported Ubuntu LTS).
2. Use a key pair and restrict SSH (port 22) to your office/home public IP only.
3. For public web traffic, allow inbound 80/443. Do not expose port 5000 or a database port publicly.
4. Attach an IAM instance role if you later connect private S3/CloudWatch; prefer role credentials over static AWS keys.
5. Connect by SSH.

### 2. Install OS packages and copy the code

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx rsync
sudo adduser --system --group --home /opt/learnwithhb learnwithhb
sudo mkdir -p /opt/learnwithhb/app
sudo chown -R "$USER":"$USER" /opt/learnwithhb
```

Copy the extracted project folder from your computer to the instance. From **your Windows PowerShell**, run (replace the key and public IP):

```powershell
scp -i .\your-ec2-key.pem -r .\LearnWithHB\* ubuntu@YOUR_EC2_PUBLIC_IP:/tmp/learnwithhb-upload/
```

If the temporary folder doesn't exist, create it first over SSH with `mkdir -p /tmp/learnwithhb-upload`. Then on EC2:

```bash
sudo rsync -av --exclude='.venv' --exclude='.env' /tmp/learnwithhb-upload/ /opt/learnwithhb/app/
sudo chown -R learnwithhb:learnwithhb /opt/learnwithhb
```

For repeated releases, use a private Git repository or CI/CD rather than manually copying secrets. Never copy your local database to production unless that is intentional.

### 3. Create production environment and install Python packages

```bash
sudo -u learnwithhb python3 -m venv /opt/learnwithhb/venv
sudo -u learnwithhb /opt/learnwithhb/venv/bin/pip install --upgrade pip
sudo -u learnwithhb /opt/learnwithhb/venv/bin/pip install -r /opt/learnwithhb/app/requirements.txt gunicorn
sudo mkdir -p /var/lib/learnwithhb/uploads
sudo chown -R learnwithhb:learnwithhb /var/lib/learnwithhb
```

For a first basic SQLite deployment, edit `app.py` to point `UPLOAD_FOLDER` to `/var/lib/learnwithhb/uploads` (or change the configuration to make the upload folder configurable), then use that same durable directory for uploads. Do not leave uploads in a directory that a deployment cleanup may delete. Better: implement private S3 storage before taking real payments.

Create `/etc/learnwithhb.env`:

```bash
sudo nano /etc/learnwithhb.env
```

Example values (replace them; do not paste these placeholders as real secrets):

```dotenv
SECRET_KEY=GENERATE_A_LONG_RANDOM_SECRET
DATABASE_URL=sqlite:////var/lib/learnwithhb/learnwithhb.db
ADMIN_EMAIL=your-admin-email@example.com
ADMIN_PASSWORD=USE_A_LONG_UNIQUE_PASSWORD
SITE_URL=https://your-domain.example
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
MAX_UPLOAD_MB=25
```

Generate a secret with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`. Restrict file permissions:

```bash
sudo chown root:learnwithhb /etc/learnwithhb.env
sudo chmod 640 /etc/learnwithhb.env
```

**Note:** The current code uses the project directory's `uploads` folder. Before enabling uploads on EC2, update `app.py` so `UPLOAD_FOLDER` points at `/var/lib/learnwithhb/uploads`, then set ownership/permissions and test file replacement. Also confirm the SQLite database path and back it up. For multiple application instances, use PostgreSQL rather than SQLite.

### 4. Run Gunicorn using systemd

Create the service:

```bash
sudo nano /etc/systemd/system/learnwithhb.service
```

Paste:

```ini
[Unit]
Description=LearnWithHB Flask application
After=network.target

[Service]
User=learnwithhb
Group=learnwithhb
WorkingDirectory=/opt/learnwithhb/app
EnvironmentFile=/etc/learnwithhb.env
ExecStart=/opt/learnwithhb/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
Restart=on-failure
RestartSec=5
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

Start and verify:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now learnwithhb
sudo systemctl status learnwithhb --no-pager
curl -I http://127.0.0.1:8000
sudo journalctl -u learnwithhb -n 100 --no-pager
```

### 5. Configure Nginx reverse proxy

```bash
sudo nano /etc/nginx/sites-available/learnwithhb
```

Replace `your-domain.example` with your domain, or use your EC2 public DNS for an initial smoke test:

```nginx
server {
    listen 80;
    server_name your-domain.example www.your-domain.example;
    client_max_body_size 25m;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and validate:

```bash
sudo ln -s /etc/nginx/sites-available/learnwithhb /etc/nginx/sites-enabled/learnwithhb
sudo nginx -t
sudo systemctl reload nginx
```

Point your domain DNS A record to the EC2 public IP or Elastic IP. Add HTTPS using Certbot after DNS resolves and port 80/443 are open. Follow https://certbot.eff.org/ for the current Ubuntu + Nginx instructions. Set `SITE_URL=https://your-domain.example` afterward and restart the app.

### 6. How to update the website later

**Recommended release flow:** back up the database and uploads, copy the new code, install changed dependencies, run smoke tests, then restart the service. Keep `.env` and persistent data outside the source upload.

From Windows PowerShell:

```powershell
scp -i .\your-ec2-key.pem -r .\LearnWithHB\* ubuntu@YOUR_EC2_PUBLIC_IP:/tmp/learnwithhb-upload/
```

On EC2:

```bash
# Back up before deploying
sudo mkdir -p /var/backups/learnwithhb
sudo cp /var/lib/learnwithhb/learnwithhb.db /var/backups/learnwithhb/learnwithhb-$(date +%F-%H%M).db 2>/dev/null || true
sudo tar -czf /var/backups/learnwithhb/uploads-$(date +%F-%H%M).tar.gz /var/lib/learnwithhb/uploads 2>/dev/null || true

# Sync code only; preserve .env, virtualenv, DB and uploaded files
sudo rsync -av --delete --exclude='.env' --exclude='.venv' --exclude='venv' --exclude='uploads/' --exclude='*.db' /tmp/learnwithhb-upload/ /opt/learnwithhb/app/
sudo chown -R learnwithhb:learnwithhb /opt/learnwithhb/app
sudo -u learnwithhb /opt/learnwithhb/venv/bin/pip install -r /opt/learnwithhb/app/requirements.txt
sudo systemctl restart learnwithhb
sudo systemctl status learnwithhb --no-pager
curl -I http://127.0.0.1:8000
sudo journalctl -u learnwithhb -n 80 --no-pager
```

Do not use `--delete` unless you understand the exclusions and have a backup. Verify the uploaded directory layout before syncing. After each update, open the public site, sign in as admin, preview a material and blog, and test a permitted download. For rollback, restore the previous source release and restart the service; restore the database backup only if the release changed the schema/data and the rollback requires it.

### 7. Production checklist before real customers

- [ ] Use a domain and HTTPS; keep port 8000/5000 private.
- [ ] Replace SQLite with PostgreSQL/RDS for production and use migrations.
- [ ] Implement private S3 uploads and short-lived presigned downloads after entitlement checks.
- [ ] Add CSRF protection, rate limiting, password reset, email verification, secure cookie settings and login throttling.
- [ ] Verify Razorpay test orders, captured-payment webhooks, duplicate events, failed/pending payments, amount/currency/order matching, and refunds.
- [ ] Keep all secrets in a secrets manager or restricted environment file; never in source control.
- [ ] Add upload malware scanning, file-size/type validation, backups, monitoring and alerts.
- [ ] Replace placeholder Privacy, Terms, Refund and Contact information with accurate business details.
- [ ] Test access denial: a logged-out user and a non-purchaser must not download a paid file.
- [ ] Test admin role separation and restore from backup.

## Files

- `app.py` — Flask routes, models, login, admin, checkout verification and webhook
- `templates/` — responsive website pages and forms
- `static/style.css` — LearnWithHB theme and responsive styles
- `.env.example` — configuration template; no real credentials
- `requirements.txt` — Python dependencies
- `uploads/` — local development uploads (do not publish private files)
=======
# learnwithhb
>>>>>>> e195d4f8a6f9e19f6de5e515c7db1d72a35d692b
