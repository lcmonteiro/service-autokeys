# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __| 
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \ 
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/ 
# =======================================================================================
import atexit
from pynput import keyboard
from threading import Lock, Timer
from pyperclip import copy, paste

# =======================================================================================
# Helpers
# =======================================================================================
def is_equal(seq1, seq2):
    return list(seq1) == list(seq2)

def is_subset(sub, seq):
    return all(map(lambda p: p in seq, sub))

def is_subseq(sub, seq):
    return len(sub) <= len(seq) and all(map(lambda x, y: x==y, sub, seq))

# =======================================================================================
# Clipboard
# =======================================================================================
class MyException(Exception): pass
class Clipboard:
    """Stage a secret on the clipboard, then take it back off again.

    Reverting on the next key release, as this used to, loses the race against
    the modifier keys still held from the triggering hotkey - and against the
    Ctrl+V the user is trying to paste with. A deadline is coarser, but it is
    the same deadline every time.
    """
    TIMEOUT = 20.0

    _lock    = Lock()
    _pending = None    # (staged, previous) awaiting revert
    _timer   = None
    _epoch   = 0

    @classmethod
    def Stage(cls, text, timeout=None):
        with cls._lock:
            cls._epoch += 1
            epoch = cls._epoch
            if cls._timer is not None:
                cls._timer.cancel()
            # On back-to-back stages paste() would hand back the *previous*
            # secret, so carry the original clipboard value forward instead.
            previous = cls._pending[1] if cls._pending else paste()
            cls._pending = (text, previous)
            copy(text)
            cls._timer = Timer(
                cls.TIMEOUT if timeout is None else timeout,
                cls.Revert, args=(epoch,))
            cls._timer.daemon = True
            cls._timer.start()

    @classmethod
    def Revert(cls, epoch=None):
        with cls._lock:
            if cls._pending is None:
                return
            if epoch is not None and epoch != cls._epoch:
                return                  # a newer Stage() owns the clipboard
            staged, previous = cls._pending
            if paste() == staged:       # do not clobber what the user copied
                copy(previous)
            cls._pending = None
            cls._timer = None


atexit.register(Clipboard.Revert)


# =======================================================================================
# Keyboard
# =======================================================================================
class Keyboard:
    _controler = keyboard.Controller()
    @classmethod
    def Type(cls, text=None, backoff=0, enter=False):
        for _ in range(backoff): 
            cls.click(keyboard.Key.backspace)
        if text: 
            cls._controler.type(text)
        if enter: 
            cls.click(keyboard.Key.enter)

    @classmethod
    def click(cls, key):
        cls._controler.press(key)
        cls._controler.release(key)

    # Public Keys
    SHIFT = keyboard.Key.shift 
    CTRL  = keyboard.Key.ctrl
    ALT   = keyboard.Key.alt
    CMD   = keyboard.Key.cmd
    KEY   = lambda x : keyboard.KeyCode(char=x)

           

# =======================================================================================
# Keys
# =======================================================================================
class Keys:
    def __init__(self, *args):
        self._keys = tuple(args)

    def __len__(self):
        return len(self._keys)

    def press(self, key, char):   pass
    def release(self, key, char): pass
    def reset(self):              pass


# =======================================================================================
# HotKeys
# =======================================================================================
class HotKeys(Keys):
    MAX_LIVES = 5
    def __init__(self, *args):
        super().__init__(*args)
        self.reset()

    def press(self, key, _):
        if key not in self._press: 
            self._press.append(key)
            if not is_subset(self._press, self._keys):
                self._active = False
                self._lives -= 1
                return
            if not is_subset(self._keys, self._press):
                self._active = None
                return
            self._active = True

    def release(self, key, _):
        self._press = list(filter(lambda k: k!=key, self._press))
        # Commit to a verdict only once the whole combo is up, or once it has
        # burned through its lives; stay pending (None) while keys are held.
        if not self._press or self._lives <= 0:
            return self._active
        return None

    def reset(self):
        self._press = []
        self._active = None
        self._lives = self.MAX_LIVES

# =======================================================================================
# SeqKeys
# =======================================================================================
class SeqKeys(Keys):
    def __init__(self, *args):
        super().__init__(*args)
        self.reset()

    def press(self, key, char):
        if key not in self._press: 
            self._press.append(key)
            self._chars.append(char)
            if not is_subseq(self._chars, self._keys):
                self._active = False
                return
            if not is_subseq(self._keys, self._chars):
                self._active = None
                return
            self._active = True

    def release(self, key, _):
        self._press = list(filter(lambda k: k!=key, self._press))
        return self._active

    def reset(self):
        self._press = []
        self._chars = []
        self._active = None

# =======================================================================================
# KeyPatterns
# =======================================================================================
class KeyPatterns(keyboard.Listener):
    # ---------------------------------------------------------------
    # helper
    # ---------------------------------------------------------------
    class Stack:
        def __init__(self, init):
            self._stack = [init]

        def add(self, obj):
            self._stack.append(obj)

        def get(self): 
            return self._stack[-1]

        def clr(self):
            for step in reversed(self._stack):
                for obj in step:
                    obj.reset()
            self._stack = self._stack[:1]

    # ---------------------------------------------------------------
    # interfaces
    # ---------------------------------------------------------------
    def __init__(self, config):
        super().__init__(
            on_press = self._on_press,
            on_release = self._on_release)
        
        self._space = config
        self._stack = self.Stack(config)
        self._board = keyboard.Controller()
    
    def _on_press(self, key, injected=False):
        # Keyboard.Type() synthesises events through a Controller and the OS
        # reports them back to this listener. Replaying our own output would
        # corrupt the match state, so drop it. The default keeps the callback
        # working on pynput releases that pass the key alone.
        if injected:
            return
        for comb in self._stack.get():
            comb.press(self.canonical(key), key)

    def _on_release(self, key, injected=False):
        if injected:
            return
        active  = {}
        enable  = {}
        disable = {}
        for comb, children in self._stack.get().items():
            {
                True  : enable,
                False : disable,
                None  : active
            }[comb.release(self.canonical(key), key)][comb] = children
        
        # move point
        if enable:
            next = {}
            for parent, obj in enable.items(): 
                if callable(obj): 
                    obj(parent) 
                    continue
                next.update(obj)
            if next: 
                self._stack.add(next)
            else:
                self._stack.clr()
            return

        # do nothing when some are active
        if active: return

        # reset stack when all are disable
        if disable: self._stack.clr()
            
    def _reset(self):
        for step in reversed(self._stack):
            for obj in step:
                obj.reset()
        self._stack = [self._space]
