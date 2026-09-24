# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __| 
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \ 
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/ 
# =======================================================================================
import sys
from yaml import YAMLError, safe_load
from argparse import ArgumentParser
from autokeys.engine import KeyPatterns

# configuration sources 
from autokeys.commands    import config_commands
from autokeys.credentials import config_credentials

# =======================================================================================
# helpers
# =======================================================================================
def load_settings(path):
    if not path:
        return {}
    with open(path, 'r') as ss:
        settings = safe_load(ss) or {}
    if not isinstance(settings, dict):
        raise ValueError(f'expected a mapping, got {type(settings).__name__}')
    return settings

# =======================================================================================
# entry point
# =======================================================================================
def main(args=None):
    # parse commnand line arguments
    parser = ArgumentParser()
    parser.add_argument(
        'settings', help='settings file path.', type=str, default='.')
    arguments = parser.parse_args(args=args)

    # load service settings and keys configuration
    try:
        settings = load_settings(arguments.settings)
        config = {}
        config.update(config_commands(settings.get('commands') or {}))
        config.update(config_credentials(settings.get('credentials') or {}))
    except (OSError, ValueError, YAMLError) as error:
        print(f'{arguments.settings}: {error}', file=sys.stderr)
        return 2
    try:
        with KeyPatterns(config) as listener:
            listener.join()
    except KeyboardInterrupt:
        pass
