# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __| 
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \ 
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/ 
# =======================================================================================
# settings shares
#
#   the settings file split in codec-share share files: the codec-share commands under
#   the autokeys names ($AUTOKEYS_PIN) with the settings validation.
#
#   autokeys-share split config.yml
#   autokeys-share edit config.yml.1.share config.yml.3.share
# =======================================================================================
from functools import partial

from yaml import safe_load

from codec_share.cli import ask_stamp as _ask_stamp
from codec_share.cli import commands

PIN_ENVVAR = 'AUTOKEYS_PIN'


def validate(data):
    """only yaml mappings are settings"""
    settings = safe_load(data)
    if settings is not None and not isinstance(settings, dict):
        raise ValueError('settings must be a yaml mapping')


ask_stamp = partial(_ask_stamp, pin_envvar=PIN_ENVVAR)

main = commands('autokeys-share', pin_envvar=PIN_ENVVAR, validate=validate,
                what='settings file')
