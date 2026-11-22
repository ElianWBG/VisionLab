from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np
from django.test import SimpleTestCase, override_settings

from processor.services import PhoneClassUnavailable, detect_objects


def jpeg_frame(width=640, height=480):
    image = np.zeros((height, width, 3), dtype=np.uint8)
    success, jpeg = cv2.imencode(".jpg", image)
    if not success:
        raise RuntimeError("No se pudo crear el fotograma de prueba.")
    return image, jpeg.tobytes()


class DetectionTests(SimpleTestCase):
    @override_settings(YOLO_PHONE_CONFIDENCE=0.65)
    @patch("processor.services._get_model")
    def test_filters_phone_labels_and_encodes_annotated_image(self, get_model):
        image, jpeg = jpeg_frame()
        annotated = cv2.rectangle(image.copy(), (80, 80), (180, 280), (0, 255, 0), 8)
        model = Mock()
        model.names = {0: "bottle", 3: "Mobile_Phone", 8: "Celular"}
        model.predict.return_value = [
            SimpleNamespace(boxes=[object()], plot=lambda: annotated)
        ]
        get_model.return_value = model

        output, counts = detect_objects(jpeg)

        self.assertEqual(model.predict.call_args.kwargs["classes"], [3, 8])
        self.assertEqual(model.predict.call_args.kwargs["conf"], 0.65)
        decoded = cv2.imdecode(np.frombuffer(output, np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape, image.shape)
        self.assertGreater(int(decoded[80, 110, 1]), 150)
        self.assertEqual(counts, {"Celular": 1})

    @patch("processor.services._get_model")
    def test_empty_predictions_return_empty_counts(self, get_model):
        image, jpeg = jpeg_frame()
        model = get_model.return_value
        model.names = {67: "cell phone"}
        model.predict.return_value = [SimpleNamespace(boxes=[], plot=lambda: image)]

        _, counts = detect_objects(jpeg)

        self.assertEqual(counts, {})

    @patch("processor.services._get_model")
    def test_invalid_images_do_not_reach_yolo(self, get_model):
        _, oversized_jpeg = jpeg_frame(1024, 1024)
        for frame in (b"imagen invalida", oversized_jpeg):
            with self.subTest(length=len(frame)), self.assertRaises(ValueError):
                detect_objects(frame)
        get_model.assert_not_called()

    @patch("processor.services._get_model")
    def test_model_without_phone_class_is_rejected(self, get_model):
        _, jpeg = jpeg_frame()
        model = get_model.return_value
        model.names = {67: "bottle"}

        with self.assertRaises(PhoneClassUnavailable):
            detect_objects(jpeg)
        model.predict.assert_not_called()
