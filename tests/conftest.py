# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
import os

# pynput picks its backend on first import and the X11/Win32/Darwin ones need a
# real session. Force the headless backend so the suite runs anywhere, unless
# the developer has already asked for something else.
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
    `Key.ctrl == Key.alt` there. `KeyCode`s stay distinct, and the patterns are
    generic over any hashable key, so tests use these throughout.
    """
    return Keyboard.key(char)


def press(patterns, *text, injected=False):
    for char in text:
        patterns._on_press(KEY(char), injected)


def release(patterns, *text, injected=False):
    for char in text:
        patterns._on_release(KEY(char), injected)


def chord(patterns, *text, injected=False):
    """Press every key of a chord, then release them in reverse order."""
    press(patterns, *text, injected=injected)
    release(patterns, *reversed(text), injected=injected)


def tap(patterns, char, injected=False):
    press(patterns, char, injected=injected)
    release(patterns, char, injected=injected)


def depth(patterns):
    return len(patterns._cursor)


# =======================================================================================
# fixtures
# =======================================================================================
@pytest.fixture
def clipboard(monkeypatch):
    """A fake clipboard, plus a clean `Clipboard` between tests.

    `Clipboard` keeps its staging state on the class, so a leaked timer from one
    test would fire into the next - or, worse, into the real pyperclip once
    monkeypatch unwinds.
    """
    box = {'value': ''}
    monkeypatch.setattr(engine, 'copy', lambda text: box.__setitem__('value', text))
    monkeypatch.setattr(engine, 'paste', lambda: box['value'])

    def reset():
        Clipboard._cancel()
        Clipboard._pending = None
        Clipboard._epoch = 0

    reset()
    yield box
    reset()


@pytest.fixture
def settings(tmp_path):
    """Write a settings file with credential-safe permissions."""
    def write(text, name='settings.yml', mode=0o600):
        file = tmp_path / name
        file.write_text(text, encoding='utf-8')
        file.chmod(mode)
        return str(file)
    return write


@pytest.fixture
def typed(monkeypatch):
    """Capture what the actions would have typed, instead of typing it."""
    keystrokes = []
    monkeypatch.setattr(
        Keyboard, 'type',
        classmethod(lambda cls, text=None, backspaces=0, enter=False:
                    keystrokes.append((text, backspaces, enter))))
    return keystrokes
