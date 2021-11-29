# =======================================================================================
# 
# =======================================================================================
from autokeys.engine import Keyboard, HotKeys, SeqKeys


def config_commands():
    return {
        # exit
        HotKeys(Keyboard.CTRL, Keyboard.ALT, Keyboard.CMD): {
            SeqKeys(*[Keyboard.KEY(x) for x in 'exit']): (lambda _: exit(0))
        }
    }





