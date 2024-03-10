# Generated by Django 4.2.6 on 2023-11-06 14:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("social", "0007_joinrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="group",
            name="creator",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="created_groups",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
