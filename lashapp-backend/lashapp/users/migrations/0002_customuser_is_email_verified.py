from django.db import migrations, models


def mark_existing_users_verified(apps, schema_editor):
    User = apps.get_model("users", "CustomUser")
    User.objects.all().update(is_email_verified=True)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="is_email_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_existing_users_verified, migrations.RunPython.noop),
    ]
