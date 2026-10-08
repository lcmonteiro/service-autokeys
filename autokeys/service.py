# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __| 
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \ 
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/ 
# =======================================================================================
from yaml import safe_load
from argparse import ArgumentParser
from autokeys.engine import KeyPatterns
from codec_share.shares import ShareError, is_share, join
from autokeys.shares import load_stamp, add_stamp_arguments

# configuration sources 
from autokeys.commands    import config_commands
from autokeys.credentials import config_credentials

# =======================================================================================
# helpers
# =======================================================================================
def load_settings(arguments):
    data = []
    for path in arguments.settings:
        with open(path, 'rb') as ss:
            data.append(ss.read())
    if not any(map(is_share, data)):
        if len(data) > 1:
            raise ShareError('only share files can be given together')
        return safe_load(data[0]) or {}
    return safe_load(join(data, load_stamp(arguments))) or {}

# =======================================================================================
# entry point
# =======================================================================================
def main(args=None):
    # parse commnand line arguments
    parser = ArgumentParser()
    parser.add_argument(
        'settings', nargs='+',
        help='settings file path, or the paths of its shares (see autokeys-share split).')
    add_stamp_arguments(parser)
    arguments = parser.parse_args(args=args)

    # load service settings 
    try:
        settings = load_settings(arguments)
    except Exception as error:
        parser.exit(1, f'autokeys: {error}\n')

    # load service keys configuration
    config = {}
    config.update(config_commands(settings.get('commands', {})))
    config.update(config_credentials(settings.get('credentials', {})))
    try:
        with KeyPatterns(config) as listener:
            listener.join()
    except KeyboardInterrupt:
        pass
