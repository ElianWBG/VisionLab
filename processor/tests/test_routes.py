import json
from uuid import uuid4

from django.test import Client, TestCase
from django.urls import reverse

from processor.models import DetectionSession


class RouteTests(TestCase):
    def post_json(self, route, payload):
        return self.client.post(reverse(route), json.dumps(payload), content_type="application/json")

    def test_home_exposes_detection_and_session_routes(self):
        response = self.client.get(reverse("home"))
        self.assertTemplateUsed(response, "processor/home.html")
        for action, route in (
            ("start", "start_session"),
            ("detect", "detect_frame"),
            ("finish", "finish_session"),
        ):
            self.assertContains(response, f'data-{action}-url="{reverse(route)}"')

    def test_session_routes_require_post(self):
        for route in ("start_session", "detect_frame", "finish_session"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 405)

    def test_start_requires_csrf_token(self):
        response = Client(enforce_csrf_checks=True).post(reverse("start_session"))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(DetectionSession.objects.exists())

    def test_invalid_inputs_return_json_errors(self):
        for route, data in (
            ("start_session", {"session_id": "invalido"}),
            ("detect_frame", {"frame": None}),
            ("finish_session", {"session_id": None}),
        ):
            with self.subTest(route=route):
                response = self.post_json(route, data)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json())

    def test_closing_before_start_keeps_the_session_closed(self):
        session_id = str(uuid4())
        payload = {"session_id": session_id}
        response = self.post_json("finish_session", {**payload, "start_pending": True})
        self.assertEqual(response.status_code, 200)
        original_finish = DetectionSession.objects.get(pk=session_id).finished_at
        self.assertIsNotNone(original_finish)

        self.assertEqual(self.post_json("start_session", payload).json()["session_id"], session_id)
        self.assertEqual(DetectionSession.objects.count(), 1)
        self.assertEqual(DetectionSession.objects.get(pk=session_id).finished_at, original_finish)
