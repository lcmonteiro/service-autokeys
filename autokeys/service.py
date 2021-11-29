# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __| 
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \ 
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/ 
# =======================================================================================
from yaml import safe_load
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
        return safe_load(ss)

# =======================================================================================
# entry point
# =======================================================================================
def main(args=None):
    # parse commnand line arguments
    parser = ArgumentParser()
    parser.add_argument(
        'settings', help='settings file path.', type=str, default='.')
    arguments = parser.parse_args(args=args)

    # load service settings 
    settings = load_settings(arguments.settings)

    # load service keys configuration
    config = {}
    config.update(config_commands(settings.get('commands', {})))
    config.update(config_credentials(settings.get('credentials', {})))
    try:
        with KeyPatterns(config) as listener:
            listener.join()
    except KeyboardInterrupt:
        pass
