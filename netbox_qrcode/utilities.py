import base64
import logging
from io import BytesIO
from django.template import engines

import qrcode

logger = logging.getLogger('netbox_qrcode')

# ******************************************************************************************
# Includes useful tools to create the content.
# ******************************************************************************************

##################################          
# Creates a QR code as an image.: https://pypi.org/project/qrcode/3.0/
# --------------------------------
# Parameter:
#   text: Text to be included in the QR code.
#   **kwargs: List of parameters which properties the QR code should have. (e.g. version, box_size, error_correction, border etc.)
def get_qr(text, **kwargs):
    try:
        qr = qrcode.QRCode(**kwargs)
    except TypeError as exc:
        raise ValueError(
            "Invalid QR code parameters: {}".format(kwargs)
        ) from exc
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image()
    img = img.get_image()
    return img

##################################          
# Converts an image to Base64
# --------------------------------
# Parameter:
#   img: Image file
def get_img_b64(img):
    stream = BytesIO()
    try:
        img.save(stream, format='png')
    except Exception:
        logger.exception("Failed to save image to PNG format")
        raise
    return str(base64.b64encode(stream.getvalue()), encoding='ascii')

##################################
# Extracts the short model name from a full model reference string.
# e.g. 'dcim.device' -> 'device', 'netbox_inventory.asset' -> 'asset'
# --------------------------------
# Parameter:
#   models: Tuple of model references, e.g. ('dcim.device',)
def get_model_short_name(models):
    name = models[0]
    name = name.replace('dcim.', '')
    name = name.replace('netbox_inventory.', '')
    return name

##################################
# Renders a Django template string with the given context.
# --------------------------------
# Parameter:
#   template_string: A Django/Jinja2 template string
#   context: Dictionary of template variables
def render_django_template(template_string, context):
    django_engine = engines["django"]
    template = django_engine.from_string(template_string)
    return template.render(context)
