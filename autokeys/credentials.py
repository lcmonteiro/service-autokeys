# =======================================================================================
# 
# =======================================================================================
from autokeys.engine import Keyboard, HotKeys, SeqKeys

data = {
    'qx': {'user':'qx-user', 'pass':'qx-pass', 'sites':[]},
    'ad': {'user':'ad-user', 'pass':'ad-pass', 'sites':[]},
    'cc': {'user':'cc-user', 'pass':'cc-pass', 'sites':[]},
}



def config_credentials():
    # actions
    def write_user(user):
        return lambda x: Keyboard.Type(user, len(x))
    def write_pass(user):
        return lambda x: Keyboard.Type(user, len(x))

    # load data
    hotkeys_user = HotKeys(Keyboard.CTRL, Keyboard.ALT, Keyboard.KEY('u'))
    hotkeys_pass = HotKeys(Keyboard.CTRL, Keyboard.ALT, Keyboard.KEY('p'))
    hotkeys_conf = {
        hotkeys_user:{},
        hotkeys_pass:{}}
    for key, entry in data.items():
        # user
        hotkeys_conf[hotkeys_user][SeqKeys(*[Keyboard.KEY(x) for x in key])] = write_user(entry['user']) 
        # pass
        hotkeys_conf[hotkeys_pass][SeqKeys(*[Keyboard.KEY(x) for x in key])] = write_pass(entry['pass'])
    return hotkeys_conf




