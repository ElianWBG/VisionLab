import uuid

from django.db import models


class DetectionSession(models.Model):
    """Resumen de una sesión de cámara y de sus detecciones."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    frames_processed = models.PositiveIntegerField(default=0)
    detections_total = models.PositiveIntegerField(default=0)
    class_counts = models.JSONField(default=dict, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Sesión {self.id} ({self.started_at:%Y-%m-%d %H:%M})"
