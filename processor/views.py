import base64
import binascii
import json
from uuid import UUID

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import DetectionSession
from .services import PhoneClassUnavailable, detect_objects

MAX_FRAME_BYTES = 1_500_000


def home(request):
    return render(request, "processor/home.html", {
        "phone_confidence_percent": round(settings.YOLO_PHONE_CONFIDENCE * 100),
    })


@require_POST
def start_session(request):
    try:
        payload = json.loads(request.body or b"{}")
        if not isinstance(payload, dict):
            raise ValueError
        session_id = UUID(payload["session_id"]) if "session_id" in payload else None
    except RequestDataTooBig:
        return JsonResponse({"error": "La solicitud excede el tamaño permitido."}, status=413)
    except (AttributeError, TypeError, ValueError):
        return JsonResponse({"error": "El identificador de sesión no es válido."}, status=400)

    if session_id is None:
        session = DetectionSession.objects.create()
    else:
        session, _ = DetectionSession.objects.get_or_create(pk=session_id)
    return JsonResponse({"session_id": str(session.id), "started_at": session.started_at.isoformat()})


@require_POST
def detect_frame(request):
    try:
        body = request.body
        if len(body) > 2_100_000:
            raise RequestDataTooBig
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("La solicitud debe ser un objeto JSON.")
        data_url = payload.get("frame", "")
        if not isinstance(data_url, str):
            raise ValueError("El fotograma debe enviarse como texto Base64.")
        encoded_frame = data_url.split(",", 1)[-1]
        if not encoded_frame or len(encoded_frame) > MAX_FRAME_BYTES * 2:
            raise ValueError("El fotograma no es válido o es demasiado grande.")
        frame_bytes = base64.b64decode(encoded_frame, validate=True)
        if not frame_bytes or len(frame_bytes) > MAX_FRAME_BYTES:
            raise ValueError("El fotograma excede el tamaño permitido.")
        image_bytes, counts = detect_objects(frame_bytes)
    except RequestDataTooBig:
        return JsonResponse({"error": "El fotograma excede el tamaño permitido."}, status=413)
    except PhoneClassUnavailable as error:
        return JsonResponse({"error": str(error)}, status=503)
    except (binascii.Error, ValueError) as error:
        return JsonResponse({"error": str(error) or "Solicitud de fotograma inválida."}, status=400)

    image = base64.b64encode(image_bytes).decode("ascii")
    return JsonResponse({"image": f"data:image/jpeg;base64,{image}", "counts": counts})


@require_POST
def finish_session(request):
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError
        raw_session_id = payload.get("session_id")
        if not isinstance(raw_session_id, str):
            raise ValueError
        session_id = UUID(raw_session_id)
        frames_processed = max(0, min(int(payload.get("frames_processed", 0)), 100_000))
        counts = payload.get("class_counts", {})
        if not isinstance(counts, dict):
            raise ValueError
        safe_counts = {
            str(label)[:80]: max(0, min(int(count), 1_000_000))
            for label, count in counts.items()
            if isinstance(label, str)
        }
        detections_total = sum(safe_counts.values())
        if detections_total > 2_147_483_647:
            raise ValueError
    except RequestDataTooBig:
        return JsonResponse({"error": "El resumen excede el tamaño permitido."}, status=413)
    except (OverflowError, TypeError, ValueError):
        return JsonResponse({"error": "Los datos de la sesión no son válidos."}, status=400)

    try:
        if payload.get("start_pending") is True:
            # El cierre puede llegar antes que el inicio al abandonar la página.
            session, _ = DetectionSession.objects.get_or_create(pk=session_id)
        else:
            session = DetectionSession.objects.get(pk=session_id)
    except DetectionSession.DoesNotExist:
        return JsonResponse({"error": "La sesión no existe."}, status=404)

    finished_at = timezone.now()
    updated = DetectionSession.objects.filter(pk=session_id, finished_at__isnull=True).update(
        finished_at=finished_at,
        frames_processed=frames_processed,
        class_counts=safe_counts,
        detections_total=detections_total,
        duration_seconds=max(0, int((finished_at - session.started_at).total_seconds())),
    )
    if not updated:
        session.refresh_from_db(fields=["detections_total"])
        detections_total = session.detections_total
    return JsonResponse({"saved": True, "detections_total": detections_total})
