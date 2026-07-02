import logging

from packaging import version
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from netbox.plugins import PluginTemplateExtension
from .template_content_functions import create_text, create_url, config_for_modul, create_QRCode
from .utilities import get_model_short_name

logger = logging.getLogger('netbox_qrcode')

# ******************************************************************************************
# Contains the main functionalities of the plugin and thus creates the content for the 
# individual modules, e.g: Device, Rack etc.
# ******************************************************************************************

# Check if netbox-inventory is available
try:
    import netbox_inventory
    INVENTORY_AVAILABLE = True
except ImportError:
    INVENTORY_AVAILABLE = False




##################################
# Class for creating the plugin content
class QRCode(PluginTemplateExtension):

    # Config keys passed to the qrcode3.html template as extra_context.
    TEMPLATE_CONFIG_KEYS = [
        'title', 'with_text', 'text_location',
        'text_align_horizontal', 'text_align_vertical',
        'font', 'font_size', 'font_weight', 'font_color',
        'with_qr',
        'label_qr_width', 'label_qr_height', 'label_qr_text_distance',
        'label_width', 'label_height',
        'label_edge_top', 'label_edge_left', 'label_edge_right', 'label_edge_bottom',
    ]

    ##################################          
    # Creates a plug-in view for a label.
    # --------------------------------
    # Parameter:
    #   labelDesignNo: Which label design should be loaded.
    def Create_SubPluginContent(self, labelDesignNo):
        
        thisSelf = self

        obj = self.context['object'] # An object of the type Device, Rack etc.

        # Config suitable for the module
        config = config_for_modul(thisSelf, labelDesignNo)

        # Abort if no config data. 
        if config is None: 
            return '' 

        # Get URL for QR code
        url = create_url(thisSelf, config, obj)

        # Create a QR code
        qrCode = create_QRCode(url, config)

        # Create the text for the label if required.
        text = create_text(config, obj, qrCode)

        # Create plugin using template
        try:
            if version.parse(settings.RELEASE.version).major >= 3:

                # Build extra_context from config keys
                extra_context = {key: config.get(key) for key in self.TEMPLATE_CONFIG_KEYS}
                extra_context['labelDesignNo'] = labelDesignNo
                extra_context['qrCode'] = qrCode
                extra_context['text'] = text

                render = self.render(
                    'netbox_qrcode/qrcode3.html', extra_context=extra_context
                )
            
                return render
            else:
                # Versions 1 and 2 are no longer supported.
                return self.render(
                    'netbox_qrcode/qrcode.html', extra_context={'image': qrCode}
                )
        except ObjectDoesNotExist:
            logger.warning(
                "Object not found while rendering QR code for %s (label design #%s)",
                type(obj).__name__, labelDesignNo,
            )
            return ''

    ##################################
    # Create plugin content
    # - First, a plugin view is created for the first label.
    # - If there are further configuration entries for the object/model (e.g. device, rack etc.),
    #   further label views are also created as additional plugin views.
    def Create_PluginContent(self):

        # First Plugin Content
        pluginContent = QRCode.Create_SubPluginContent(self, 1) 

        # Check whether there is another configuration for the object, e.g. device, rack, etc.
        # Support up to 10 additional label configurations (objectName_2 to ..._10) per object (e.g. device, rack, etc.).

        config = self.context['config'] # Django configuration
        model_name = get_model_short_name(self.models)

        for i in range(2, 11):

            configName = model_name + '_' + str(i)
            obj_cfg = config.get(configName) # Load configuration for additional label if possible.

            if(obj_cfg):
                pluginContent += QRCode.Create_SubPluginContent(self, i) # Add another plugin view
            else:
                break
        
        return pluginContent

##################################
# The following section serves to integrate the plugin into Netbox Core.
# Model QR code classes are generated from a registry to avoid boilerplate.

def _make_qrcode_class(class_name, model_ref, page_side):
    """Create a QRCode subclass for the given model.

    Parameters:
        class_name: Name for the generated class.
        model_ref:  Full model reference, e.g. 'dcim.device'.
        page_side:  'right' or 'left' – determines which page hook is used.
    """
    attrs = {'models': (model_ref,)}

    def _page_method(self):
        return self.Create_PluginContent()

    if page_side == 'right':
        attrs['right_page'] = _page_method
    else:
        attrs['left_page'] = _page_method

    return type(class_name, (QRCode,), attrs)

# Registry of (class_name, model_ref, page_side)
_MODEL_REGISTRY = [
    ('DeviceQRCode',    'dcim.device',              'right'),
    ('RackQRCode',      'dcim.rack',                'right'),
    ('CableQRCode',     'dcim.cable',               'left'),
    ('LocationQRCode',  'dcim.location',            'left'),
    ('PowerFeedQRCode', 'dcim.powerfeed',           'right'),
    ('PowerPanelQRCode','dcim.powerpanel',          'right'),
    ('ModuleQRCode',    'dcim.module',              'right'),
]

# Generate classes and inject into module namespace
for _name, _model, _side in _MODEL_REGISTRY:
    globals()[_name] = _make_qrcode_class(_name, _model, _side)

# Inventory plugin class (conditionally registered)
AssetQRCode = _make_qrcode_class('AssetQRCode', 'netbox_inventory.asset', 'right')

# Connects Netbox Core with the plug-in classes
template_extensions = [globals()[name] for name, _, _ in _MODEL_REGISTRY]
if INVENTORY_AVAILABLE:
    template_extensions.append(AssetQRCode)
