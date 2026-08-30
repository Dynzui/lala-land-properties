from django.db import migrations


ADMIN_GROUP = "Lala Land Content Admins"
PAGE_PERMISSION_CODENAMES = [
    "add_page",
    "change_page",
    "publish_page",
    "lock_page",
    "unlock_page",
]


def create_about_page(apps, schema_editor):
    from apps.sitecontent.models import AboutPage
    from home.models import HomePage

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    GroupPagePermission = apps.get_model("wagtailcore", "GroupPagePermission")

    home = HomePage.objects.first()
    if home is None:
        return
    about = AboutPage.objects.first()
    if about is None:
        about = AboutPage(title="About Lala", slug="about")
        home.add_child(instance=about)
        about.save_revision().publish()

    admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    permissions = Permission.objects.filter(
        content_type__app_label="wagtailcore",
        codename__in=PAGE_PERMISSION_CODENAMES,
    )
    for permission in permissions:
        GroupPagePermission.objects.get_or_create(
            group=admin_group,
            page_id=about.pk,
            permission=permission,
        )


def remove_about_permissions(apps, schema_editor):
    GroupPagePermission = apps.get_model("wagtailcore", "GroupPagePermission")
    GroupPagePermission.objects.filter(
        group__name=ADMIN_GROUP,
        page__slug="about",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("sitecontent", "0003_add_about_page")]

    operations = [
        migrations.RunPython(create_about_page, remove_about_permissions),
    ]
