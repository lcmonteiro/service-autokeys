# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __| 
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \ 
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/ 
# =======================================================================================
from pynput import keyboard
from multiprocessing import Process
from pyperclip import copy, paste
from time import time

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
    @classmethod
    def Stage(cls, text):
        Process(target=cls.Revert, args=(paste(),), daemon=True).start()
        copy(text)
        
    @classmethod
    def Revert(cls, text):
        def on_release(key):
            copy(text) 
            exit(0)
        # start listener
        with keyboard.Listener(on_release=on_release) as listener:
            listener.join()
    
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
        if not self._press or not self._lives <= 0:
            return self._active

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
    
    def _on_press(self, key):
        for comb in self._stack.get():
            comb.press(self.canonical(key), key)
    
    def _on_release(self, key):
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
