import uuid

import django.db.models.deletion
import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("home", "0002_create_homepage"),
        ("wagtailimages", "0027_image_description"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArticleCategory",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=80, unique=True)),
                ("slug", models.SlugField(max_length=90, unique=True)),
                ("description", models.CharField(blank=True, max_length=240)),
                ("active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name_plural": "article categories",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="ResourceIndexPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=models.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "intro",
                    wagtail.fields.RichTextField(
                        blank=True,
                        default=(
                            "Practical guidance for making informed property decisions."
                        ),
                        features=["bold", "italic", "link"],
                    ),
                ),
            ],
            options={"abstract": False},
            bases=("wagtailcore.page",),
        ),
        migrations.CreateModel(
            name="ArticlePage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=models.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                ("summary", models.CharField(max_length=300)),
                ("cover_alt_text", models.CharField(blank=True, max_length=250)),
                (
                    "body",
                    wagtail.fields.RichTextField(
                        features=[
                            "h2",
                            "h3",
                            "bold",
                            "italic",
                            "ol",
                            "ul",
                            "hr",
                            "link",
                            "document-link",
                            "image",
                            "blockquote",
                        ]
                    ),
                ),
                (
                    "author_name",
                    models.CharField(default="Lala Land Properties", max_length=120),
                ),
                ("featured", models.BooleanField(default=False)),
                (
                    "archived",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Hide this article from the public site while keeping its CMS record."
                        ),
                    ),
                ),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="articles",
                        to="sitecontent.articlecategory",
                    ),
                ),
                (
                    "cover_image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="article_covers",
                        to="wagtailimages.image",
                    ),
                ),
            ],
            options={
                "ordering": ["-first_published_at", "-latest_revision_created_at"],
                "abstract": False,
            },
            bases=("wagtailcore.page",),
        ),
    ]
