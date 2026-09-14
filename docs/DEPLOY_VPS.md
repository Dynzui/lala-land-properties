# VPS launch path

This is the provider-neutral alternative to `render.yaml`. Do not use both deployments for the
same live domain. The VPS hosts Caddy, Django/Wagtail, PostgreSQL, and uploaded media. Caddy
handles HTTPS; the application and database are reachable only inside the Compose network.

## Before provisioning

- Choose the provider and region from current checkout prices, not introductory marketing rates.
- For a single low-traffic site, start with at least **1 vCPU, 2 GB RAM, and 40 GB SSD**.
- Obtain the domain and a working SMTP service. The public site must not use a personal mailbox
  as its long-term inquiry alert recipient.
- Arrange an off-server backup destination and an external uptime monitor. A VPS snapshot alone
  is not a complete recovery plan for the database and uploaded photos.

## Server setup

1. Install a supported Linux LTS release, create a non-root operator with an SSH key, disable
   password SSH, enable the provider firewall for ports 22, 80, and 443, and enable automatic
   security updates. Restrict SSH to a known IP or use a VPN if feasible.
2. Install Docker Engine and Compose from the vendor's official packages. Add the operator to
   the Docker group only if appropriate; Docker access is effectively root access.
3. Clone the repository and copy `.env.vps.example` to `.env.vps`. Replace every placeholder with
   real values and restrict that file to the operator. Never commit it or paste secrets into chat.
4. Point the domain's DNS A record at the VPS IP. If an AAAA record exists, it must point to a
   reachable IPv6 address or be removed. Allow ports 80 and 443 so Caddy can obtain HTTPS.
5. From the repository root, start the database and apply migrations:

   ```sh
   docker compose --env-file .env.vps -f compose.vps.yaml up -d db
   docker compose --env-file .env.vps -f compose.vps.yaml run --rm web python manage.py migrate --noinput
   ```

6. Start the website, then check the production settings and public pages:

   ```sh
   docker compose --env-file .env.vps -f compose.vps.yaml up -d --build web proxy
   docker compose --env-file .env.vps -f compose.vps.yaml exec web python manage.py check --deploy
   ```

7. Create the production owner account, enable MFA, then test an inquiry and the private email
   alert. Set the Wagtail Site hostname to the real domain. Do not copy development test users or
   inquiries to production without reviewing them first.

## Backups and updates

- Before accepting real inquiries, schedule daily PostgreSQL logical backups **and** uploaded
  media backups to storage outside the VPS. Encrypt backups, set retention, monitor failures, and
  perform a test restore of both. Also enable provider snapshots if affordable.
- Keep only ports 22, 80, and 443 open; do not publish PostgreSQL or Django's port 8000.
- To update: back up the database and media, pull the reviewed commit, build the new image, run
  migrations, then replace `web` and `proxy`. Verify the public site and CMS afterward. Keep the
  previous image and a rollback procedure for incompatible changes.
- Once HTTPS and every intended subdomain work, increase `SECURE_HSTS_SECONDS` from `0` to the
  production value. Do not enable HSTS preload casually; it is difficult to undo.

The VPS is not launch-ready until the domain, SMTP, off-server backup, restore test, and uptime
alert are all working. Those require provider and account choices that are not part of this
repository.
