"""Unit tests for template_content_functions.py."""
import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from netbox_qrcode.template_content_functions import (
    config_for_modul,
    create_QRCode,
    create_text,
    create_url,
    get_text_fields,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parent_self(model, config, request=None):
    """Build a mock object resembling the PluginTemplateExtension self."""
    ps = MagicMock()
    ps.models = (model,)
    ps.context = {
        "config": config,
        "request": request or MagicMock(),
    }
    return ps


def _base_config(**overrides):
    """Return a minimal plugin config dict with sensible defaults."""
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
        "title": "",
    }
    cfg.update(overrides)
    return cfg


# ===========================================================================
# config_for_modul
# ===========================================================================


class TestConfigForModul:
    def test_returns_config_dict(self):
        config = _base_config(device={"text_fields": ["name", "serial"]})
        ps = _make_parent_self("dcim.device", config)
        result = config_for_modul(ps, 1)
        assert isinstance(result, dict)

    def test_merges_module_specific_fields(self):
        config = _base_config(device={"text_fields": ["serial"]})
        ps = _make_parent_self("dcim.device", config)
        result = config_for_modul(ps, 1)
        assert result["text_fields"] == ["serial"]

    def test_preserves_global_fields(self):
        config = _base_config(device={"text_fields": ["serial"]})
        ps = _make_parent_self("dcim.device", config)
        result = config_for_modul(ps, 1)
        assert result["with_text"] is True

    def test_label_design_no_1_no_suffix(self):
        config = _base_config(rack={"text_fields": ["name"]})
        ps = _make_parent_self("dcim.rack", config)
        result = config_for_modul(ps, 1)
        assert result["text_fields"] == ["name"]

    def test_label_design_no_2_uses_suffix(self):
        config = _base_config(device_2={"text_fields": ["asset_tag"]})
        ps = _make_parent_self("dcim.device", config)
        result = config_for_modul(ps, 2)
        assert result["text_fields"] == ["asset_tag"]

    def test_label_design_no_3_uses_suffix(self):
        config = _base_config(cable_3={"text_fields": ["label"]})
        ps = _make_parent_self("dcim.cable", config)
        result = config_for_modul(ps, 3)
        assert result["text_fields"] == ["label"]

    def test_returns_default_config_when_no_module_config(self):
        config = _base_config()
        ps = _make_parent_self("dcim.device", config)
        result = config_for_modul(ps, 1)
        assert result["text_fields"] == ["name"]

    def test_strips_dcim_prefix(self):
        config = _base_config(powerfeed={"text_fields": ["power"]})
        ps = _make_parent_self("dcim.powerfeed", config)
        result = config_for_modul(ps, 1)
        assert result["text_fields"] == ["power"]

    def test_strips_netbox_inventory_prefix(self):
        config = _base_config(asset={"text_fields": ["asset_tag"]})
        ps = _make_parent_self("netbox_inventory.asset", config)
        result = config_for_modul(ps, 1)
        assert result["text_fields"] == ["asset_tag"]

    def test_does_not_mutate_original_config(self):
        original_fields = ["name"]
        config = _base_config(
            text_fields=original_fields,
            device={"text_fields": ["serial"]},
        )
        ps = _make_parent_self("dcim.device", config)
        config_for_modul(ps, 1)
        assert config["text_fields"] == ["name"]


# ===========================================================================
# create_QRCode
# ===========================================================================


class TestCreateQRCode:
    def test_returns_base64_string(self):
        config = _base_config()
        result = create_QRCode("https://example.com", config)
        assert isinstance(result, str)

    def test_output_is_valid_base64_png(self):
        config = _base_config()
        result = create_QRCode("https://example.com", config)
        decoded = base64.b64decode(result)
        img = Image.open(BytesIO(decoded))
        assert img.format == "PNG"

    def test_passes_qr_prefixed_args(self):
        config = _base_config(qr_box_size=10, qr_border=2)
        result = create_QRCode("test", config)
        decoded = base64.b64decode(result)
        img = Image.open(BytesIO(decoded))
        assert img.size[0] > 0

    def test_ignores_non_qr_config_keys(self):
        config = _base_config(font_size="5mm", label_width="80mm")
        result = create_QRCode("test", config)
        assert isinstance(result, str)

    def test_different_text_different_output(self):
        config = _base_config()
        r1 = create_QRCode("aaa", config)
        r2 = create_QRCode("bbb", config)
        assert r1 != r2


# ===========================================================================
# create_url
# ===========================================================================


class TestCreateUrl:
    def test_default_uses_request_absolute_uri(self):
        request = MagicMock()
        obj = MagicMock()
        obj.get_absolute_url.return_value = "/dcim/devices/1/"
        request.build_absolute_uri.return_value = "https://netbox.local/dcim/devices/1/"

        config = _base_config()
        ps = _make_parent_self("dcim.device", config, request=request)
        result = create_url(ps, config, obj)

        assert result == "https://netbox.local/dcim/devices/1/"
        request.build_absolute_uri.assert_called_once_with("/dcim/devices/1/")

    def test_url_template_renders_object(self):
        """When url_template is set, Django template engine is used."""
        mock_engine = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "https://custom.local/device/42"
        mock_engine.from_string.return_value = mock_template

        from django.template import engines
        engines["django"] = mock_engine

        obj = MagicMock()
        config = _base_config(url_template="https://custom.local/device/{{ obj.pk }}")
        ps = _make_parent_self("dcim.device", config)
        result = create_url(ps, config, obj)

        assert result == "https://custom.local/device/42"
        mock_engine.from_string.assert_called_once_with(
            "https://custom.local/device/{{ obj.pk }}"
        )
        mock_template.render.assert_called_once_with({"obj": obj})

        del engines["django"]

    def test_url_template_none_falls_through(self):
        request = MagicMock()
        request.build_absolute_uri.return_value = "https://nb/rack/5/"
        obj = MagicMock()
        obj.get_absolute_url.return_value = "/rack/5/"
        config = _base_config(url_template=None)
        ps = _make_parent_self("dcim.rack", config, request=request)
        result = create_url(ps, config, obj)
        assert result == "https://nb/rack/5/"


# ===========================================================================
# get_text_fields
# ===========================================================================


class TestGetTextFields:
    def test_simple_field(self):
        obj = SimpleNamespace(name="Switch-01")
        config = _base_config(text_fields=["name"])
        result = get_text_fields(config, obj)
        assert result == "Switch-01"

    def test_multiple_fields_joined_with_br(self):
        obj = SimpleNamespace(name="Switch-01", serial="ABC123")
        config = _base_config(text_fields=["name", "serial"])
        result = get_text_fields(config, obj)
        assert result == "Switch-01<br>ABC123"

    def test_missing_field_skipped(self):
        obj = SimpleNamespace(name="Switch-01")
        config = _base_config(text_fields=["name", "serial"])
        result = get_text_fields(config, obj)
        assert result == "Switch-01"

    def test_none_field_skipped(self):
        obj = SimpleNamespace(name="Switch-01", serial=None)
        config = _base_config(text_fields=["name", "serial"])
        result = get_text_fields(config, obj)
        assert result == "Switch-01"

    def test_empty_text_fields(self):
        obj = SimpleNamespace(name="Switch-01")
        config = _base_config(text_fields=[])
        result = get_text_fields(config, obj)
        assert result == ""

    def test_custom_text_appended(self):
        obj = SimpleNamespace(name="Switch-01")
        config = _base_config(text_fields=["name"], custom_text="Property of Acme")
        result = get_text_fields(config, obj)
        assert result == "Switch-01<br>Property of Acme"

    def test_custom_text_only(self):
        obj = SimpleNamespace()
        config = _base_config(text_fields=[], custom_text="Custom Only")
        result = get_text_fields(config, obj)
        assert result == "Custom Only"

    def test_dot_notation_dict_attribute(self):
        obj = SimpleNamespace(a_terminations={"device": "Router-A"})
        config = _base_config(text_fields=["a_terminations.device"])
        result = get_text_fields(config, obj)
        assert result == "Router-A"

    def test_dot_notation_list_attribute(self):
        term = SimpleNamespace(device="Router-B")
        obj = SimpleNamespace(a_terminations=[term])
        config = _base_config(text_fields=["a_terminations.device"])
        result = get_text_fields(config, obj)
        assert result == "Router-B"

    def test_dot_notation_empty_list(self):
        obj = SimpleNamespace(a_terminations=[])
        config = _base_config(text_fields=["a_terminations.device"])
        result = get_text_fields(config, obj)
        assert result == ""

    def test_dot_notation_missing_child_field(self):
        term = SimpleNamespace(name="something")
        obj = SimpleNamespace(a_terminations=[term])
        config = _base_config(text_fields=["a_terminations.device"])
        result = get_text_fields(config, obj)
        assert result == ""

    def test_dot_notation_dict_missing_key(self):
        obj = SimpleNamespace(a_terminations={"name": "Router-A"})
        config = _base_config(text_fields=["a_terminations.device"])
        result = get_text_fields(config, obj)
        assert result == ""

    def test_no_custom_text_no_fields(self):
        obj = SimpleNamespace()
        config = _base_config(text_fields=[], custom_text=None)
        result = get_text_fields(config, obj)
        assert result == ""

    def test_dot_notation_multiple_dots_falls_back(self):
        """When a field has more than one dot, split raises ValueError and cfn stays None."""
        obj = SimpleNamespace()
        # After ValueError, text_field remains "a.b.c" and cfn stays None
        setattr(obj, "a.b.c", "fallback-value")
        config = _base_config(text_fields=["a.b.c"])
        result = get_text_fields(config, obj)
        assert result == "fallback-value"


# ===========================================================================
# create_text
# ===========================================================================


class TestCreateText:
    def test_with_text_false_returns_none(self):
        config = _base_config(with_text=False)
        obj = SimpleNamespace(name="Switch")
        result = create_text(config, obj, "dummy_qr")
        assert result is None

    def test_with_text_fields(self):
        config = _base_config(with_text=True, text_fields=["name"])
        obj = SimpleNamespace(name="Switch-01")
        result = create_text(config, obj, "dummy_qr")
        assert result == "Switch-01"

    def test_with_text_template(self):
        mock_engine = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<b>Switch-01</b>"
        mock_engine.from_string.return_value = mock_template

        from django.template import engines
        engines["django"] = mock_engine

        config = _base_config(
            with_text=True,
            text_template="<b>{{ obj.name }}</b>",
            logo="logo.png",
        )
        obj = SimpleNamespace(name="Switch-01")
        qr_code = "base64qr"
        result = create_text(config, obj, qr_code)

        assert result == "<b>Switch-01</b>"
        mock_engine.from_string.assert_called_once_with("<b>{{ obj.name }}</b>")
        mock_template.render.assert_called_once_with({
            "obj": obj,
            "logo": "logo.png",
            "qrCode": "base64qr",
        })

        del engines["django"]

    def test_text_template_takes_precedence_over_fields(self):
        mock_engine = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "TEMPLATE"
        mock_engine.from_string.return_value = mock_template

        from django.template import engines
        engines["django"] = mock_engine

        config = _base_config(
            with_text=True,
            text_fields=["name"],
            text_template="{{ obj.name }}",
        )
        obj = SimpleNamespace(name="Switch")
        result = create_text(config, obj, "qr")

        assert result == "TEMPLATE"

        del engines["django"]
