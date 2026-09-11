# Deploying Lala Land Properties on Render

The initial production architecture uses one Docker web service, one managed PostgreSQL 17
database, and a 1 GB persistent disk for uploaded property media. All resources use Render's
Singapore region. The repository's `render.yaml` defines this setup.

## Before creating resources

Prepare these SMTP values. Render will ask for values marked `sync: false` while applying the
Blueprint:

- `DEFAULT_FROM_EMAIL`
- `EMAIL_HOST`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`

The Blueprint supplies the database URL, generates the Django secret key, detects the public
Render hostname, and runs migrations before each deploy. Do not put secret values in Git.

## Create the production environment

1. In Render, choose **New → Blueprint** and connect the GitHub repository.
2. Select `render.yaml` and review the web service, PostgreSQL database, persistent disk, region,
   and monthly cost before applying it.
3. Enter the SMTP values when prompted.
4. Wait for the pre-deploy migration and Docker deployment to finish.
5. Open the generated `onrender.com` address and verify the home page, `/admin/`, static styling,
   and an uploaded image.
6. Create the production owner account with Render's service shell, then enable MFA immediately:

   ```sh
   python manage.py createsuperuser
   ```

7. Add the custom domain in Render. Render provisions and renews HTTPS automatically. After DNS
   resolves, set `DJANGO_ALLOWED_HOSTS` to the custom hostname and set
   `WAGTAILADMIN_BASE_URL=https://your-domain.example`.

## Release and backup checks

- Migrations run through `preDeployCommand`; they do not run every time the container starts.
- Only `/var/data` survives redeploys, so production uploads must remain under
  `/var/data/media`.
- A persistent disk limits the web service to one instance and prevents zero-downtime deploys.
  Move media to object storage before horizontal scaling becomes necessary.
- Enable Render PostgreSQL backups before adding irreplaceable production data. Database backups
  do not include the media disk; arrange a separate media backup/export.
- Test a database restore and a media restore before launch, not only the backup creation step.

## Expected starting cost

At the plans currently encoded in `render.yaml`, the baseline is approximately US$13.25/month:
US$7 for the web service, US$6 for PostgreSQL, and US$0.25 for 1 GB of persistent disk, before
bandwidth or other usage charges. Confirm current pricing in Render before applying the Blueprint.
