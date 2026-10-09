# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __| 
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \ 
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/ 
# =======================================================================================
from pathlib import Path

import click
from yaml import YAMLError, safe_load

from autokeys.engine import KeyPatterns
from autokeys.shares import ask_stamp
from codec_share import CodecError, InvalidShare, Share, join

# configuration sources 
from autokeys.commands    import config_commands
from autokeys.credentials import config_credentials

# =======================================================================================
# helpers
# =======================================================================================
def load_settings(paths, stamp_file=None):
    """settings of a settings file, or of its shares"""
    data = [Path(path).read_bytes() for path in paths]
    if not any(map(Share.is_share, data)):
        if len(data) > 1:
            raise InvalidShare('only share files can be given together')
        return safe_load(data[0]) or {}
    shares = [Share.parse(item) for item in data]
    return safe_load(join(shares, ask_stamp(stamp_file))) or {}

# =======================================================================================
# entry point
# =======================================================================================
@click.command(context_settings={'help_option_names': ['-h', '--help']})
@click.argument('settings', nargs=-1, required=True,
                type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option('--stamp', 'stamp_file', metavar='FILE',
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help='Stamp file of the shares, instead of a pin (asked, or $AUTOKEYS_PIN).')
def main(settings, stamp_file):
    """Type credentials and run commands from hotkeys.

    SETTINGS is the settings file, or the paths of its shares (see autokeys-share split).
    """
    # load service settings
    try:
        loaded = load_settings(settings, stamp_file)
    except (CodecError, OSError, YAMLError) as error:
        raise click.ClickException(str(error)) from None

    # load service keys configuration
    config = {}
    config.update(config_commands(loaded.get('commands', {})))
    config.update(config_credentials(loaded.get('credentials', {})))
    try:
        with KeyPatterns(config) as listener:
            listener.join()
    except KeyboardInterrupt:
        pass
