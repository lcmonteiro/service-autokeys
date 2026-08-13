# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
"""End-to-end checks against a backend with real, distinct modifier keys.

The dummy backend defines every `Key` member as `KeyCode.from_vk(0)`, which the
enum then folds into a single member - `Key.ctrl is Key.alt` there. That is
enough to exercise the pattern logic, but it cannot tell `Ctrl+Alt+U` apart from
`Ctrl` alone, so these tests skip unless a real backend is in play.

Run them with, for example::

    PYNPUT_BACKEND=xorg xvfb-run -a pytest tests/test_integration.py
"""
import pytest
from pynput import keyboard

from autokeys.config import build

DEGENERATE = keyboard.Key.ctrl == keyboard.Key.alt

pytestmark = pytest.mark.skipif(
    DEGENERATE,
    reason='backend folds the modifiers together; set PYNPUT_BACKEND=xorg')

SETTINGS = {
    'credentials': {
        'aa': {'user': 'octocat', 'pass': 'hunter2'},
        'bb': {'user': 'hubot', 'pass': 'correct-horse'},
    },
    'commands': {'addr': '221B Baker Street'},
}


# =======================================================================================
# helpers
# =======================================================================================
def fire(patterns, modifiers, trigger):
    for key in modifiers:
        patterns._on_press(key)
    for key in reversed(modifiers):
        patterns._on_release(key)
    for char in trigger:
        patterns._on_press(keyboard.KeyCode(char=char))
        patterns._on_release(keyboard.KeyCode(char=char))


@pytest.fixture
def patterns(typed):
    from autokeys.engine import KeyPatterns
    return KeyPatterns(build(SETTINGS))


CTRL_ALT = [keyboard.Key.ctrl_l, keyboard.Key.alt_l]


# =======================================================================================
# tests
# =======================================================================================
class TestRealBackend:
    def test_modifiers_are_distinct(self):
        assert len({keyboard.Key.ctrl, keyboard.Key.alt, keyboard.Key.cmd}) == 3

    def test_user_chord_types_the_username(self, patterns, typed):
        fire(patterns, CTRL_ALT + [keyboard.KeyCode(char='u')], 'aa')
        assert typed == [('octocat', 2, False)]

    def test_password_chord_types_the_password(self, patterns, typed):
        fire(patterns, CTRL_ALT + [keyboard.KeyCode(char='p')], 'aa')
        assert typed == [('hunter2', 2, False)]

    def test_trigger_selects_between_credentials(self, patterns, typed):
        fire(patterns, CTRL_ALT + [keyboard.KeyCode(char='u')], 'bb')
        assert typed == [('hubot', 2, False)]

    def test_command_chord_expands_the_snippet(self, patterns, typed):
        fire(patterns, CTRL_ALT + [keyboard.Key.cmd], 'addr')
        assert typed == [('221B Baker Street', 4, False)]

    def test_a_bare_modifier_fires_nothing(self, patterns, typed):
        """The command chord is Ctrl+Alt+Cmd; on a folded backend Ctrl alone
        would match it."""
        fire(patterns, [keyboard.Key.ctrl_l], '')
        assert typed == []

    def test_an_unknown_trigger_fires_nothing(self, patterns, typed):
        fire(patterns, CTRL_ALT + [keyboard.KeyCode(char='u')], 'zz')
        assert typed == []

    def test_the_service_recovers_after_a_bad_trigger(self, patterns, typed):
        fire(patterns, CTRL_ALT + [keyboard.KeyCode(char='u')], 'zz')
        fire(patterns, CTRL_ALT + [keyboard.KeyCode(char='u')], 'aa')
        assert typed == [('octocat', 2, False)]
