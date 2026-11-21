import base64
import binascii
import json
from uuid import UUID

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import DetectionSession
from .services import detect_objects

MAX_FRAME_BYTES = 1_500_000


def home(request):
    return render(request, "processor/home.html")


@require_POST
def start_session(request):
    session = DetectionSession.objects.create()
    return JsonResponse({"session_id": str(session.id), "started_at": session.started_at.isoformat()})


@require_POST
def detect_frame(request):
    if len(request.body) > 2_100_000:
        return JsonResponse({"error": "El fotograma excede el tamaño permitido."}, status=413)

    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError("La solicitud debe ser un objeto JSON.")
        data_url = payload.get("frame", "")
        encoded_frame = data_url.split(",", 1)[-1]
        if not encoded_frame or len(encoded_frame) > MAX_FRAME_BYTES * 2:
            raise ValueError("El fotograma no es válido o es demasiado grande.")
        frame_bytes = base64.b64decode(encoded_frame, validate=True)
        if not frame_bytes or len(frame_bytes) > MAX_FRAME_BYTES:
            raise ValueError("El fotograma excede el tamaño permitido.")
        image_bytes, counts = detect_objects(frame_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError, binascii.Error, ValueError) as error:
        return JsonResponse({"error": str(error) or "Solicitud de fotograma inválida."}, status=400)

    image = base64.b64encode(image_bytes).decode("ascii")
    return JsonResponse({"image": f"data:image/jpeg;base64,{image}", "counts": counts})


@require_POST
def finish_session(request):
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError
        session_id = UUID(payload.get("session_id", ""))
        frames_processed = max(0, min(int(payload.get("frames_processed", 0)), 100_000))
        counts = payload.get("class_counts", {})
        if not isinstance(counts, dict):
            raise ValueError
        safe_counts = {
            str(label)[:80]: max(0, min(int(count), 1_000_000))
            for label, count in counts.items()
            if isinstance(label, str)
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"error": "Los datos de la sesión no son válidos."}, status=400)

    try:
        session = DetectionSession.objects.get(pk=session_id, finished_at__isnull=True)
    except DetectionSession.DoesNotExist:
        return JsonResponse({"error": "La sesión no existe o ya finalizó."}, status=404)

    session.finished_at = timezone.now()
    session.frames_processed = frames_processed
    session.class_counts = safe_counts
    session.detections_total = sum(safe_counts.values())
    session.duration_seconds = max(0, int((session.finished_at - session.started_at).total_seconds()))
    session.save(update_fields=["finished_at", "frames_processed", "class_counts", "detections_total", "duration_seconds"])
    return JsonResponse({"saved": True, "detections_total": session.detections_total})
