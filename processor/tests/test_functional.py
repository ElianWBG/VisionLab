import base64
import json
from types import SimpleNamespace
from unittest.mock import patch

import cv2
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from processor.models import DetectionSession

from .test_detection import jpeg_frame


class DetectionFlowTests(TestCase):
    @patch("processor.services._get_model")
    def test_camera_frame_returns_overlay_and_persists_summary(self, get_model):
        image, jpeg = jpeg_frame()
        annotated = cv2.rectangle(image.copy(), (80, 80), (180, 280), (0, 255, 0), 8)
        model = get_model.return_value
        model.names = {67: "cell phone"}
        model.predict.return_value = [
            SimpleNamespace(boxes=[object()], plot=lambda: annotated)
        ]

        browser = Client(enforce_csrf_checks=True)
        home = browser.get(reverse("home"))
        for control in ("startButton", "stopButton", "processedFrame", "currentTotal"):
            self.assertContains(home, f'id="{control}"')
        csrf_token = browser.cookies[settings.CSRF_COOKIE_NAME].value

        def post(route, data):
            response = browser.post(
                reverse(route), json.dumps(data), content_type="application/json",
                HTTP_X_CSRFTOKEN=csrf_token,
            )
            self.assertEqual(response.status_code, 200)
            return response.json()

        session_id = post("start_session", {})["session_id"]
        frame = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
        detection = post("detect_frame", {"frame": frame})
        self.assertEqual(detection["counts"], {"Celular": 1})
        self.assertTrue(detection["image"].startswith("data:image/jpeg;base64,"))
        self.assertNotEqual(detection["image"], frame)

        summary = {"session_id": session_id, "frames_processed": 1, "class_counts": detection["counts"]}
        self.assertEqual(post("finish_session", summary), {"saved": True, "detections_total": 1})
        self.assertEqual(post("finish_session", summary)["detections_total"], 1)
        session = DetectionSession.objects.get(pk=session_id)
        self.assertIsNotNone(session.finished_at)
        self.assertEqual(session.frames_processed, 1)
        self.assertEqual(session.class_counts, {"Celular": 1})
