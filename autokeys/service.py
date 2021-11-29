from autokeys.engine import KeyPatterns

# configuration sources 
from autokeys.commands    import config_commands
from autokeys.credentials import config_credentials

# =======================================================================================
# entry point
# =======================================================================================
def main():
    from pprint import pprint
    config = {}
    config.update(config_commands())
    config.update(config_credentials())
    try:
        with KeyPatterns(config) as listener:
            listener.join()
    except KeyboardInterrupt:
        pass
