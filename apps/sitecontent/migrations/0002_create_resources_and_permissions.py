from django.db import migrations


OWNER_GROUP = "Lala Land Owners"
ADMIN_GROUP = "Lala Land Content Admins"
PAGE_PERMISSION_CODENAMES = [
    "add_page",
    "change_page",
    "publish_page",
    "lock_page",
    "unlock_page",
]


def create_resources_and_permissions(apps, schema_editor):
    from apps.sitecontent.models import ResourceIndexPage
    from home.models import HomePage

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    GroupPagePermission = apps.get_model("wagtailcore", "GroupPagePermission")
    User = apps.get_model("accounts", "User")

    home = HomePage.objects.first()
    if home is None:
        return
    resources = ResourceIndexPage.objects.first()
    if resources is None:
        resources = ResourceIndexPage(
            title="Resources",
            slug="resources",
            intro="Practical guidance for making informed property decisions.",
        )
        home.add_child(instance=resources)
        resources.save_revision().publish()

    owner_group, _ = Group.objects.get_or_create(name=OWNER_GROUP)
    admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    permissions = Permission.objects.filter(
        content_type__app_label="wagtailcore",
        codename__in=PAGE_PERMISSION_CODENAMES,
    )
    for permission in permissions:
        GroupPagePermission.objects.get_or_create(
            group=owner_group,
            page_id=home.pk,
            permission=permission,
        )
        GroupPagePermission.objects.get_or_create(
            group=admin_group,
            page_id=resources.pk,
            permission=permission,
        )
    for user in User.objects.filter(role="OWNER"):
        user.groups.add(owner_group)
    for user in User.objects.filter(role="ADMIN"):
        user.groups.add(admin_group)


def remove_managed_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=[OWNER_GROUP, ADMIN_GROUP]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_user_options_alter_user_managers_and_more"),
        ("sitecontent", "0001_initial"),
        ("wagtailcore", "0097_baselogentry_uuid_action_timestamp_indexes"),
        ("wagtailsearch", "0010_add_text_fields"),
    ]

    operations = [
        migrations.RunPython(create_resources_and_permissions, remove_managed_groups),
    ]
