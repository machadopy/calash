from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("scheduling", "0002_alter_appointment_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="workinghours",
            name="slot_interval_minutes",
            field=models.PositiveIntegerField(default=60),
        ),
    ]