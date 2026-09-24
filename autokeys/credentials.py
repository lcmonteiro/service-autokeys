# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __| 
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \ 
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/ 
# =======================================================================================
from autokeys.engine import Keyboard, HotKeys, SeqKeys, Clipboard


# =======================================================================================
# build credentials config 
# =======================================================================================
def config_credentials(data):
    # actions
    def write_user(user):
        def process(x):
            Keyboard.Type(user, len(x))
        return process
    def write_pass(password):
        def process(x):
            Keyboard.Type(password, len(x))
            Clipboard.Stage(password)
        return process


    # build config
    hotkeys_user = HotKeys(Keyboard.CTRL, Keyboard.ALT, Keyboard.KEY('u'))
    hotkeys_pass = HotKeys(Keyboard.CTRL, Keyboard.ALT, Keyboard.KEY('p'))
    hotkeys_conf = {
        hotkeys_user:{},
        hotkeys_pass:{}}
    data = data or {}
    if not isinstance(data, dict):
        raise ValueError(f'credentials: expected a mapping, got {type(data).__name__}')
    for key, entry in data.items():
        # every entry is reachable by typing its name, so it must be text
        name = str(key)
        if not name:
            raise ValueError('credentials: an entry has no name')
        if not isinstance(entry, dict):
            raise ValueError(f'credentials {name}: expected user and pass')
        for field in ('user', 'pass'):
            if entry.get(field) is None:
                raise ValueError(f'credentials {name}: missing {field}')
        # user
        hotkeys_conf[hotkeys_user][SeqKeys(*[Keyboard.KEY(x) for x in name])] = write_user(str(entry['user']))
        # pass
        hotkeys_conf[hotkeys_pass][SeqKeys(*[Keyboard.KEY(x) for x in name])] = write_pass(str(entry['pass']))
    return hotkeys_conf
