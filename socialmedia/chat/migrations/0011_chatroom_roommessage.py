# Generated by Django 4.2.6 on 2023-11-21 15:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0010_delete_message"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatRoom",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=1000)),
                ("date", models.DateTimeField(auto_now_add=True)),
                (
                    "creator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "members",
                    models.ManyToManyField(
                        related_name="group_chat_members", to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Room",
                "ordering": ["-date"],
            },
        ),
        migrations.CreateModel(
            name="RoomMessage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("message", models.CharField(max_length=10000000000)),
                ("date", models.DateTimeField(auto_now_add=True)),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="room_messages",
                        to="chat.chatroom",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="room_sender",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Room Message",
                "ordering": ["-date"],
            },
        ),
    ]
