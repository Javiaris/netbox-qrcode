import logging

from .utilities import get_img_b64, get_qr, get_model_short_name, render_django_template

logger = logging.getLogger('netbox_qrcode')

# ******************************************************************************************
# For better clarity, the sub-functions of template_content.py have been outsourced.
# ******************************************************************************************

##################################
# The configuration is taken and all fields that are module-specific (e.g. Device, Rack, etc.) are replaced.
# --------------------------------
# Parameter:
#   labelDesignNo: Which label design should be loaded.
#   parentSelf: Self from Parrent Function
def config_for_modul(parentSelf, labelDesignNo):

    # Copy so that the Runtime data is not changed.
    config = parentSelf.context['config'].copy() # From Netbox Config File

    # Create suffix to read the correct module configuration.
    confModulsufix = str() # None if the first standard label

    if(labelDesignNo >= 2):
            confModulsufix = '_' + str(labelDesignNo)

    # Collect the QR code plugin configuration for the specific object such as device, rack etc.
    # and overwrite the default configuration fields.
    model_name = get_model_short_name(parentSelf.models)
    obj_cfg = config.get(model_name + confModulsufix) 
    if obj_cfg is not None: 
        config.update(obj_cfg) # Ovverride default confiv Values
        return config
    else:
        return config # No module customisation

##################################
# Create QR-Code
# --------------------------------
# Parameter:
#   text: Text for QR-Code
#   config: From the Netbox configuration file
def create_QRCode(text, config):

    # Collect the configuration entries that begin with "qr_.
    # These are required to generate the QR code.
    qr_args = {}
    for k, v in config.items():
        if k.startswith('qr_'):
            qr_args[k.replace('qr_', '')] = v

    # Create a QR code
    try:
        qrCode = get_qr(text, **qr_args)
    except Exception:
        logger.exception("Failed to generate QR code (qr_args=%s)", qr_args)
        raise

    try:
        return get_img_b64(qrCode)
    except Exception:
        logger.exception("Failed to convert QR code image to base64")
        raise


##################################
# Create URL for QR code
# --------------------------------
# Parameter:
#   config: From the Netbox configuration file
#   obj: Data from the model (e.g. device, rack, etc.)
#   request: HTML Request Information
def create_url(parentSelf, config, obj):

    request = parentSelf.context['request'] # HTML Request Informations

    url_template = config.get('url_template')
    if url_template:
        # A user-defined design specification of the URL is provided in ninja2 format.
        try:
            return render_django_template(url_template, {'obj': obj})
        except Exception:
            logger.exception(
                "Failed to render url_template '%s' for %s",
                url_template, type(obj).__name__,
            )
            raise
    else:
        return request.build_absolute_uri(obj.get_absolute_url()) # URL to the requested page

##################################
# Create text for label
# --------------------------------
# Parameter:
#   config: From the Netbox configuration file
#   obj: Data from the model (e.g. device, rack, etc.)
#   qrCode: QR-Code Image 
def create_text(config, obj, qrCode):

    if config.get('with_text'):
        if config.get('text_template'):
            return get_text_template(config, obj, qrCode) # Create text content based on the Ninja2 template from the user
        else:
            return get_text_fields(config, obj) # Use the list of variables from the Config.

    return ''

##################################
# A user-defined design specification of the text is provided in ninja2 format.
# --------------------------------
# Parameter:
#   config: From the Netbox configuration file
#   obj: Data from the model (e.g. device, rack, etc.)
#   qrCode: QR-Code Image (To create a freely defined label with QR code.)
def get_text_template(config, obj, qrCode):

    text_template = config.get('text_template')
    try:
        return render_django_template(
            text_template,
            {'obj': obj, 'logo': config.get('logo'), 'qrCode': qrCode}
        )
    except Exception:
        logger.exception(
            "Failed to render text_template '%s' for %s",
            text_template, type(obj).__name__,
        )
        raise

##################################
# Retrieves all values from the object (e.g. device, rack, etc.)
# depending on the configuration parameter that are to be displayed in list form and prepares them.
# --------------------------------
# Parameter:
#   config: From the Netbox configuration file
#   obj: Data from the model (e.g. device, rack, etc.)
def get_text_fields(config, obj):

    text = []

    for text_field in config.get('text_fields', []):
        cfn = None
        if '.' in text_field:
            parts = text_field.split('.')
            if len(parts) != 2:
                logger.warning(
                    "Skipping malformed text_field '%s': expected 'field.subfield' format",
                    text_field,
                )
                continue
            text_field, cfn = parts
        if getattr(obj, text_field, None):
            if cfn:
                try:
                    if getattr(obj, text_field).get(cfn):
                        text.append('{}'.format(getattr(obj, text_field).get(cfn)))
                except AttributeError:
                    # Fallback for list-type attributes (e.g. cable terminations in nb3.3+)
                    attr_value = getattr(obj, text_field)
                    if type(attr_value) is list:
                        first_element = next(iter(attr_value), None)
                        if first_element and getattr(first_element, cfn, None):
                            text.append('{}'.format(getattr(first_element, cfn)))
                    else:
                        logger.debug(
                            "Attribute '%s' on %s is not a dict or list; cannot resolve sub-field '%s'",
                            text_field, type(obj).__name__, cfn,
                        )
            else:
                text.append('{}'.format(getattr(obj, text_field)))

    # Append user-defined text to the end.
    custom_text = config.get('custom_text')

    if custom_text:
        text.append(custom_text)

    # Convert text list to string with line breaks.
    return '<br>'.join(text)