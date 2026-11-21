import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DetectionSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("frames_processed", models.PositiveIntegerField(default=0)),
                ("detections_total", models.PositiveIntegerField(default=0)),
                ("class_counts", models.JSONField(blank=True, default=dict)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["-started_at"]},
        ),
    ]
