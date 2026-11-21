from django.contrib import admin

from .models import DetectionSession


@admin.register(DetectionSession)
class DetectionSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "started_at", "finished_at", "frames_processed", "detections_total", "duration_seconds")
    list_filter = ("started_at",)
    readonly_fields = ("id", "started_at", "finished_at", "frames_processed", "detections_total", "class_counts", "duration_seconds")
    search_fields = ("id",)
