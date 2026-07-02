"""Conftest to mock netbox and django dependencies for unit testing."""
import sys
from types import ModuleType
from unittest.mock import MagicMock


def _install_mock_modules():
    """Install mock modules for netbox and django so imports succeed."""
    mocks = {}

    # netbox.plugins
    netbox_mod = ModuleType("netbox")
    netbox_plugins = ModuleType("netbox.plugins")
    netbox_plugins.PluginConfig = type("PluginConfig", (), {})
    netbox_plugins.PluginTemplateExtension = type(
        "PluginTemplateExtension", (), {}
    )
    netbox_mod.plugins = netbox_plugins
    mocks["netbox"] = netbox_mod
    mocks["netbox.plugins"] = netbox_plugins

    # django pieces used by template_content / template_content_functions
    django_mod = ModuleType("django")
    django_conf = ModuleType("django.conf")
    django_conf.settings = MagicMock()
    django_mod.conf = django_conf
    mocks["django"] = django_mod
    mocks["django.conf"] = django_conf

    django_core = ModuleType("django.core")
    django_core_exc = ModuleType("django.core.exceptions")
    django_core_exc.ObjectDoesNotExist = type("ObjectDoesNotExist", (Exception,), {})
    django_core.exceptions = django_core_exc
    mocks["django.core"] = django_core
    mocks["django.core.exceptions"] = django_core_exc

    django_template = ModuleType("django.template")
    django_template.engines = {}
    mocks["django.template"] = django_template

    packaging_mod = ModuleType("packaging")
    packaging_version = ModuleType("packaging.version")
    packaging_version.parse = MagicMock()
    packaging_mod.version = packaging_version
    mocks["packaging"] = packaging_mod
    mocks["packaging.version"] = packaging_version

    # netbox_inventory (optional)
    mocks["netbox_inventory"] = ModuleType("netbox_inventory")

    for name, mod in mocks.items():
        sys.modules.setdefault(name, mod)


_install_mock_modules()
