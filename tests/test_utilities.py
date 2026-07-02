import base64
from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image

from netbox_qrcode.utilities import get_img_b64, get_qr


class TestGetQr:
    """Tests for get_qr() which generates a QR code PIL image."""

    def test_returns_pil_image(self):
        img = get_qr("https://example.com")
        assert isinstance(img, Image.Image)

    def test_image_is_not_empty(self):
        img = get_qr("https://example.com")
        assert img.size[0] > 0
        assert img.size[1] > 0

    def test_different_text_produces_different_images(self):
        img_a = get_qr("text-a")
        img_b = get_qr("text-b")
        assert list(img_a.tobytes()) != list(img_b.tobytes())

    def test_respects_box_size_kwarg(self):
        img_small = get_qr("hello", box_size=2, border=0)
        img_large = get_qr("hello", box_size=10, border=0)
        assert img_large.size[0] > img_small.size[0]

    def test_respects_border_kwarg(self):
        img_no_border = get_qr("hello", box_size=4, border=0)
        img_with_border = get_qr("hello", box_size=4, border=4)
        assert img_with_border.size[0] > img_no_border.size[0]

    def test_respects_version_kwarg(self):
        img_v1 = get_qr("hi", version=1, box_size=4, border=0)
        img_v10 = get_qr("hi", version=10, box_size=4, border=0)
        assert img_v10.size[0] > img_v1.size[0]

    def test_handles_empty_string(self):
        img = get_qr("")
        assert isinstance(img, Image.Image)

    def test_handles_long_text(self):
        long_text = "A" * 500
        img = get_qr(long_text)
        assert isinstance(img, Image.Image)

    def test_handles_unicode_text(self):
        img = get_qr("日本語テスト")
        assert isinstance(img, Image.Image)

    def test_handles_special_characters(self):
        img = get_qr("https://example.com/path?q=1&b=2#anchor")
        assert isinstance(img, Image.Image)


class TestGetImgB64:
    """Tests for get_img_b64() which converts a PIL image to base64."""

    def test_returns_string(self):
        img = Image.new("RGB", (10, 10), color="white")
        result = get_img_b64(img)
        assert isinstance(result, str)

    def test_output_is_valid_base64(self):
        img = Image.new("RGB", (10, 10), color="white")
        result = get_img_b64(img)
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_output_decodes_to_png(self):
        img = Image.new("RGB", (10, 10), color="white")
        result = get_img_b64(img)
        decoded = base64.b64decode(result)
        restored = Image.open(BytesIO(decoded))
        assert restored.format == "PNG"

    def test_preserves_image_dimensions(self):
        img = Image.new("RGB", (42, 17), color="red")
        result = get_img_b64(img)
        decoded = base64.b64decode(result)
        restored = Image.open(BytesIO(decoded))
        assert restored.size == (42, 17)

    def test_different_images_produce_different_b64(self):
        img_a = Image.new("RGB", (10, 10), color="red")
        img_b = Image.new("RGB", (10, 10), color="blue")
        assert get_img_b64(img_a) != get_img_b64(img_b)

    def test_roundtrip_with_get_qr(self):
        """End-to-end: get_qr -> get_img_b64 -> decode -> valid PNG."""
        qr_img = get_qr("roundtrip test")
        b64 = get_img_b64(qr_img)
        decoded = base64.b64decode(b64)
        restored = Image.open(BytesIO(decoded))
        assert restored.format == "PNG"
        assert restored.size == qr_img.size
