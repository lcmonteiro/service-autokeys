from autokeys.engine import KeyPatterns

# configuration sources 
from autokeys.credentials import config_credentials

# =======================================================================================
# entry point
# =======================================================================================
def main():
    config = {}
    config.update(config_credentials())
    try:
        with KeyPatterns(config) as listener:
            listener.join()
    except KeyboardInterrupt:
        pass
