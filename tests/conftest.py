# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
import os

# pynput picks its backend on first import and the X11/Win32/Darwin ones need a
# real session. Force the headless backend so the suite runs anywhere, unless the
# developer has already asked for something else.
os.environ.setdefault('PYNPUT_BACKEND', 'dummy')

import pytest

import autokeys.engine as engine
from autokeys.engine import Clipboard, Keyboard


# =======================================================================================
# helpers
# =======================================================================================
def KEY(char):
    """A distinct, hashable key object.

    The dummy backend collapses every `Key` member onto the same value, so
    `Key.ctrl == Key.alt` there. `KeyCode`s stay distinct, and the pattern
    classes are generic over any hashable key, so tests use these throughout.
    """
    return Keyboard.KEY(char)


def press(patterns, *chars, injected=False):
    for char in chars:
        patterns._on_press(KEY(char), injected)


def release(patterns, *chars, injected=False):
    for char in chars:
        patterns._on_release(KEY(char), injected)


def chord(patterns, *chars, injected=False):
    """Press every key of a combo, then release them in reverse order."""
    press(patterns, *chars, injected=injected)
    release(patterns, *reversed(chars), injected=injected)


def tap(patterns, char, injected=False):
    press(patterns, char, injected=injected)
    release(patterns, char, injected=injected)


def depth(patterns):
    return len(patterns._stack._stack)


# =======================================================================================
# fixtures
# =======================================================================================
@pytest.fixture
def clipboard(monkeypatch):
    """A fake clipboard, plus a clean `Clipboard` class between tests.

    `Clipboard` keeps its staging state on the class, so a leaked timer from one
    test would fire into the next one - or, worse, into the real pyperclip once
    monkeypatch unwinds.
    """
    box = {'value': ''}
    monkeypatch.setattr(engine, 'copy', lambda text: box.__setitem__('value', text))
    monkeypatch.setattr(engine, 'paste', lambda: box['value'])

    def reset():
        if Clipboard._timer is not None:
            Clipboard._timer.cancel()
        Clipboard._timer   = None
        Clipboard._pending = None
        Clipboard._epoch   = 0

    reset()
    yield box
    reset()
