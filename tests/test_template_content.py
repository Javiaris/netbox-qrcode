"""Unit tests for template_content.py — the PluginTemplateExtension classes."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from netbox_qrcode.template_content import (
    AssetQRCode,
    CableQRCode,
    DeviceQRCode,
    LocationQRCode,
    ModuleQRCode,
    PowerFeedQRCode,
    PowerPanelQRCode,
    QRCode,
    RackQRCode,
    template_extensions,
)


# ---------------------------------------------------------------------------
# Model registration
# ---------------------------------------------------------------------------


class TestModelRegistration:
    def test_device_model(self):
        assert DeviceQRCode.models == ("dcim.device",)

    def test_rack_model(self):
        assert RackQRCode.models == ("dcim.rack",)

    def test_cable_model(self):
        assert CableQRCode.models == ("dcim.cable",)

    def test_location_model(self):
        assert LocationQRCode.models == ("dcim.location",)

    def test_powerfeed_model(self):
        assert PowerFeedQRCode.models == ("dcim.powerfeed",)

    def test_powerpanel_model(self):
        assert PowerPanelQRCode.models == ("dcim.powerpanel",)

    def test_module_model(self):
        assert ModuleQRCode.models == ("dcim.module",)

    def test_asset_model(self):
        assert AssetQRCode.models == ("netbox_inventory.asset",)


class TestTemplateExtensionsList:
    def test_contains_core_classes(self):
        expected = {
            DeviceQRCode,
            ModuleQRCode,
            RackQRCode,
            CableQRCode,
            LocationQRCode,
            PowerFeedQRCode,
            PowerPanelQRCode,
        }
        assert expected.issubset(set(template_extensions))

    def test_all_inherit_from_qrcode(self):
        for cls in template_extensions:
            assert issubclass(cls, QRCode)


# ---------------------------------------------------------------------------
# Create_SubPluginContent
# ---------------------------------------------------------------------------


def _make_qrcode_instance(model, config, obj, request=None):
    """Create a QRCode instance with mocked context."""
    inst = QRCode.__new__(QRCode)
    inst.models = (model,)
    req = request or MagicMock()
    req.build_absolute_uri.return_value = "https://netbox.local/dcim/devices/1/"
    inst.context = {
        "config": config,
        "object": obj,
        "request": req,
    }
    return inst


def _minimal_config(**overrides):
    cfg = {
        "with_text": True,
        "text_fields": ["name"],
        "text_template": None,
        "custom_text": None,
        "url_template": None,
        "qr_version": 1,
        "qr_error_correction": 0,
        "qr_box_size": 4,
        "qr_border": 0,
        "with_qr": True,
        "title": "Test",
        "text_location": "right",
        "text_align_horizontal": "left",
        "text_align_vertical": "middle",
        "font": "TahomaBold",
        "font_size": "3mm",
        "font_weight": "normal",
        "font_color": "black",
        "label_qr_width": "12mm",
        "label_qr_height": "12mm",
        "label_qr_text_distance": "1mm",
        "label_width": "56mm",
        "label_height": "32mm",
        "label_edge_top": "0mm",
        "label_edge_left": "1.5mm",
        "label_edge_right": "1.5mm",
        "label_edge_bottom": "0mm",
        "device": {"text_fields": ["name"]},
    }
    cfg.update(overrides)
    return cfg


class TestCreateSubPluginContent:
    @patch("netbox_qrcode.template_content.version")
    def test_returns_string(self, mock_version):
        mock_version.parse.return_value.major = 3
        obj = SimpleNamespace(name="Switch-01")
        obj.get_absolute_url = MagicMock(return_value="/dcim/devices/1/")
        config = _minimal_config()
        inst = _make_qrcode_instance("dcim.device", config, obj)
        inst.render = MagicMock(return_value="<html>rendered</html>")

        result = inst.Create_SubPluginContent(1)
        assert result == "<html>rendered</html>"

    @patch("netbox_qrcode.template_content.version")
    def test_render_called_with_expected_context_keys(self, mock_version):
        mock_version.parse.return_value.major = 3
        obj = SimpleNamespace(name="Switch-01")
        obj.get_absolute_url = MagicMock(return_value="/dcim/devices/1/")
        config = _minimal_config()
        inst = _make_qrcode_instance("dcim.device", config, obj)
        inst.render = MagicMock(return_value="")

        inst.Create_SubPluginContent(1)

        call_args = inst.render.call_args
        assert call_args is not None
        extra = call_args.kwargs.get("extra_context") or call_args[1].get("extra_context")
        expected_keys = {
            "title", "labelDesignNo", "qrCode", "with_text", "text",
            "text_location", "text_align_horizontal", "text_align_vertical",
            "font", "font_size", "font_weight", "font_color", "with_qr",
            "label_qr_width", "label_qr_height", "label_qr_text_distance",
            "label_width", "label_height", "label_edge_top", "label_edge_left",
            "label_edge_right", "label_edge_bottom",
        }
        assert expected_keys == set(extra.keys())

    @patch("netbox_qrcode.template_content.version")
    def test_version_less_than_3_uses_old_template(self, mock_version):
        mock_version.parse.return_value.major = 2
        obj = SimpleNamespace(name="Switch-01")
        obj.get_absolute_url = MagicMock(return_value="/dcim/devices/1/")
        config = _minimal_config()
        inst = _make_qrcode_instance("dcim.device", config, obj)
        inst.render = MagicMock(return_value="<old>")

        result = inst.Create_SubPluginContent(1)

        call_args = inst.render.call_args
        template_name = call_args[0][0]
        assert template_name == "netbox_qrcode/qrcode.html"

    @patch("netbox_qrcode.template_content.version")
    def test_object_does_not_exist_returns_empty(self, mock_version):
        from django.core.exceptions import ObjectDoesNotExist

        mock_version.parse.return_value.major = 3
        obj = SimpleNamespace(name="Switch-01")
        obj.get_absolute_url = MagicMock(return_value="/dcim/devices/1/")
        config = _minimal_config()
        inst = _make_qrcode_instance("dcim.device", config, obj)
        inst.render = MagicMock(side_effect=ObjectDoesNotExist("gone"))

        result = inst.Create_SubPluginContent(1)
        assert result == ""


# ---------------------------------------------------------------------------
# Create_PluginContent
# ---------------------------------------------------------------------------


class TestCreatePluginContent:
    @patch("netbox_qrcode.template_content.version")
    def test_single_label(self, mock_version):
        mock_version.parse.return_value.major = 3
        obj = SimpleNamespace(name="Switch-01")
        obj.get_absolute_url = MagicMock(return_value="/dcim/devices/1/")
        config = _minimal_config()
        inst = _make_qrcode_instance("dcim.device", config, obj)
        inst.render = MagicMock(return_value="<label1>")

        result = inst.Create_PluginContent()
        assert "<label1>" in result

    @patch("netbox_qrcode.template_content.version")
    def test_multiple_labels(self, mock_version):
        mock_version.parse.return_value.major = 3
        obj = SimpleNamespace(name="Switch-01")
        obj.get_absolute_url = MagicMock(return_value="/dcim/devices/1/")
        config = _minimal_config(
            device_2={"text_fields": ["serial"]},
        )
        inst = _make_qrcode_instance("dcim.device", config, obj)
        inst.render = MagicMock(return_value="<label>")

        result = inst.Create_PluginContent()
        # Should be called at least twice (label 1 + label 2)
        assert inst.render.call_count >= 2

    @patch("netbox_qrcode.template_content.version")
    def test_stops_at_missing_config(self, mock_version):
        mock_version.parse.return_value.major = 3
        obj = SimpleNamespace(name="Switch-01")
        obj.get_absolute_url = MagicMock(return_value="/dcim/devices/1/")
        # Only device, no device_2
        config = _minimal_config()
        inst = _make_qrcode_instance("dcim.device", config, obj)
        inst.render = MagicMock(return_value="<label>")

        inst.Create_PluginContent()
        # Only the first label should render
        assert inst.render.call_count == 1


# ---------------------------------------------------------------------------
# Subclass right_page / left_page delegation
# ---------------------------------------------------------------------------


class TestSubclassPageMethods:
    @patch.object(QRCode, "Create_PluginContent", return_value="<content>")
    def test_device_right_page(self, mock_create):
        inst = DeviceQRCode.__new__(DeviceQRCode)
        assert inst.right_page() == "<content>"

    @patch.object(QRCode, "Create_PluginContent", return_value="<content>")
    def test_rack_right_page(self, mock_create):
        inst = RackQRCode.__new__(RackQRCode)
        assert inst.right_page() == "<content>"

    @patch.object(QRCode, "Create_PluginContent", return_value="<content>")
    def test_cable_left_page(self, mock_create):
        inst = CableQRCode.__new__(CableQRCode)
        assert inst.left_page() == "<content>"

    @patch.object(QRCode, "Create_PluginContent", return_value="<content>")
    def test_location_left_page(self, mock_create):
        inst = LocationQRCode.__new__(LocationQRCode)
        assert inst.left_page() == "<content>"

    @patch.object(QRCode, "Create_PluginContent", return_value="<content>")
    def test_powerfeed_right_page(self, mock_create):
        inst = PowerFeedQRCode.__new__(PowerFeedQRCode)
        assert inst.right_page() == "<content>"

    @patch.object(QRCode, "Create_PluginContent", return_value="<content>")
    def test_powerpanel_right_page(self, mock_create):
        inst = PowerPanelQRCode.__new__(PowerPanelQRCode)
        assert inst.right_page() == "<content>"

    @patch.object(QRCode, "Create_PluginContent", return_value="<content>")
    def test_module_right_page(self, mock_create):
        inst = ModuleQRCode.__new__(ModuleQRCode)
        assert inst.right_page() == "<content>"

    @patch.object(QRCode, "Create_PluginContent", return_value="<content>")
    def test_asset_right_page(self, mock_create):
        inst = AssetQRCode.__new__(AssetQRCode)
        assert inst.right_page() == "<content>"
