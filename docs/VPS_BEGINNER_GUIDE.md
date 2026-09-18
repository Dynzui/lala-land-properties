# Beginner's guide to hosting Lala Land Properties

This guide explains what we tested, what each part does, and how the website will move from this
computer to a live VPS.

## The website is like a small office

It helps to picture the whole system as a small real-estate office:

- **The domain** is the street address people type into their browser.
- **The VPS** is the rented building where the website runs all day.
- **Docker** packs each part of the office into a labelled room so it can be moved and rebuilt
  consistently.
- **Django and Wagtail** are the staff and office tools. They display the website and provide the
  CMS.
- **PostgreSQL** is the filing cabinet containing listings, pages, accounts, and inquiries.
- **The media volume** is the photo-storage room containing property images and floor plans.
- **Caddy** is the receptionist and security desk. It receives visitors, sends them to the website,
  and manages HTTPS.
- **A backup** is a copy of the filing cabinet and photo room kept in a different building.

Keeping a backup on the same VPS would be like keeping the only spare key inside the building. If
the entire VPS is lost, that backup could disappear with it. That is why the live backups must also
go to a separate storage provider.

## What the local rehearsal did

The rehearsal ran the same basic arrangement planned for the VPS, but inside Docker Desktop on
this computer. It used isolated rehearsal data and did not alter the normal development database.

From the project folder, we ran:

```powershell
.\scripts\run-vps-rehearsal.ps1
```

The script performed these steps:

1. **Validate the Compose configuration.** This checks the building plan before construction
   begins.
2. **Build the production image.** Docker packed the application, Python, and required libraries
   into a repeatable package.
3. **Start PostgreSQL.** This created the isolated filing cabinet used by the rehearsal.
4. **Run migrations separately.** Migrations prepare or update the drawers in that filing cabinet.
   Keeping this separate from normal startup prevents an application restart from silently
   changing the live database.
5. **Start Django and Caddy.** Django served the application while Caddy provided the local HTTPS
   entrance.
6. **Run Django's deployment check.** Django inspected important production security settings.
7. **Back up and restore PostgreSQL.** The script copied the database into a second disposable
   database and checked that Django's migration records matched.
8. **Back up and restore media.** It archived a test media file, extracted it, and verified that
   the restored file was identical.
9. **Check the public site and CMS over HTTPS.** This proved that a request could travel through
   Caddy to Django successfully.

The rehearsal passed. This proves that the application can be built and that its main services can
work together. It does not test Hostinger's network, the real domain, or real email delivery; those
can only be tested after provisioning the VPS.

## What happens next

### 1. Create the Hostinger account

Now that the local rehearsal passes, create the account and immediately enable two-factor
authentication. The account should belong to the business owner and use an email address that will
remain accessible long-term.

Creating the account is free. Before purchasing, confirm the exact checkout total, prepaid term,
renewal price, refund eligibility, and available Malaysia or Indonesia location. Do not share the
account password, recovery codes, or payment information in chat or commit them to Git.

### 2. Prepare the other services

Before launch, choose:

- A **domain registrar**, which controls the public address.
- An **SMTP provider**, which sends inquiry-alert emails reliably.
- An **off-server backup destination**, which stores encrypted database and media backups away
  from Hostinger.
- An **uptime monitor**, which alerts us if the public website stops responding.

These do not all have to come from the same company. Keeping the domain under the owner's account
also makes it easier to change hosting providers later.

### 3. Purchase and secure the VPS

After checking the final terms, purchase the selected VPS and install a supported Linux LTS image.
We will then:

1. Create a non-root operator account.
2. Use an SSH key instead of a reusable login password.
3. Enable automatic security updates.
4. Configure the firewall so only SSH, HTTP, and HTTPS are reachable.
5. Install Docker Engine and Docker Compose from their official packages.

This is like changing the building locks before moving the filing cabinet inside.

### 4. Connect the domain

The domain's DNS `A` record will point to the VPS's public IP address. DNS is like updating a map so
visitors know which building belongs to the street address. Once DNS is correct and ports 80 and
443 are open, Caddy can obtain and renew the public HTTPS certificate.

### 5. Add production configuration

We will create `.env.vps` directly on the server using the template in `.env.vps.example`. It will
hold the real domain, strong random secrets, database password, and SMTP credentials.

That file is the locked key cabinet. It must never be committed to Git, pasted into chat, or served
by the website.

### 6. Deploy the application

The live deployment will follow this order:

1. Start PostgreSQL.
2. Build the reviewed application version.
3. Run database migrations.
4. Start Django and Caddy.
5. Create the production owner account and enable MFA.
6. Check the public pages, CMS, images, and inquiry form.

### 7. Configure independent backups

Every day, an automated job will:

1. Export PostgreSQL using `pg_dump`.
2. Archive uploaded photos and floor plans.
3. Encrypt both backups.
4. Upload them to storage outside the VPS.
5. Report whether the job succeeded or failed.
6. Remove old backups according to the chosen retention policy.

Hostinger's weekly VPS backup remains useful, but it is an extra safety layer rather than the only
copy.

### 8. Prove that recovery works

Before accepting real customer inquiries, we will restore the database and media into a separate
test environment. We will confirm that listings, images, CMS pages, and inquiries appear correctly.

A backup that has never been restored is like an untested emergency key: it may look correct but we
do not know whether it opens the door.

### 9. Launch and monitor

The final launch checks include:

- The domain opens over HTTPS without a warning.
- Public pages, property listings, resources, and images load correctly.
- The CMS requires the intended login and MFA.
- A real test inquiry appears in the CMS and sends one alert email.
- Database and media backups complete successfully.
- The uptime monitor can detect and report an outage.

Only after these checks pass should the site be considered live.

## Routine maintenance after launch

The VPS should not require daily manual work. Normal maintenance is:

- Review alerts when the site or a backup fails.
- Check disk space and security updates regularly.
- Back up before deploying a website update.
- Deploy only reviewed commits, then check the public site and CMS.
- Test a full restore periodically.
- Renew the VPS, domain, backup storage, and email service before they expire.
- Replace the temporary personal inquiry email with the intended business address before launch.

The detailed command-oriented checklist remains in `docs/DEPLOY_VPS.md`. This guide explains the
same process from a beginner's point of view.
