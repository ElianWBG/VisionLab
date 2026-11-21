"""Detección de objetos por fotograma con OpenCV y Ultralytics YOLO."""
from collections import Counter
from threading import RLock

import cv2
import numpy as np
from django.conf import settings

_model = None
_model_lock = RLock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from ultralytics import YOLO

                _model = YOLO(settings.YOLO_MODEL_PATH)
    return _model


def detect_objects(frame_bytes: bytes) -> tuple[bytes, dict[str, int]]:
    """Recibe un JPEG, dibuja las detecciones y devuelve JPEG más conteo por clase."""
    if len(frame_bytes) > 1_500_000:
        raise ValueError("El fotograma es demasiado grande; reduce la resolución de cámara.")

    encoded = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if frame is None or frame.size == 0:
        raise ValueError("No se pudo leer el fotograma enviado por la cámara.")
    if frame.shape[0] * frame.shape[1] > 1_000_000:
        raise ValueError("La resolución supera un megapíxel. Usa la cámara en 640 × 480.")

    # Una instancia compartida evita volver a cargar el modelo en cada fotograma.
    with _model_lock:
        result = _get_model().predict(
            source=frame,
            imgsz=416,
            conf=0.35,
            classes=[67],  # COCO: cell phone
            device="cpu",
            verbose=False,
        )[0]

    annotated = result.plot()
    counts = Counter()
    if result.boxes is not None:
        for class_id in result.boxes.cls.tolist():
            name = "Celular" if int(class_id) == 67 else result.names.get(int(class_id), str(int(class_id)))
            counts[name] += 1

    success, output = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not success:
        raise ValueError("No se pudo codificar el fotograma procesado.")

    return output.tobytes(), dict(counts)
