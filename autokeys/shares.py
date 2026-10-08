# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __| 
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \ 
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/ 
# =======================================================================================
# settings shares
#
#   the settings file split in codec-share share files (split, join, edit), see
#   codec_share.shares: here only with the autokeys names and the settings validation.
#
#   autokeys-share split config.yml
#   autokeys-share edit config.yml.1.share config.yml.3.share
# =======================================================================================
from functools import partial

from yaml import safe_load

from codec_share import shares

PIN_ENV = 'AUTOKEYS_PIN'
PROG = 'autokeys-share'


def validate(data):
    """only yaml mappings are settings"""
    settings = safe_load(data)
    if settings is not None and not isinstance(settings, dict):
        raise ValueError('settings must be a yaml mapping')


load_stamp = partial(shares.load_stamp, pin_env=PIN_ENV)
add_stamp_arguments = partial(shares.add_stamp_arguments, pin_env=PIN_ENV, prog=PROG)


def main(args=None):
    shares.main(args, prog=PROG, pin_env=PIN_ENV, validate=validate, what='settings file')
