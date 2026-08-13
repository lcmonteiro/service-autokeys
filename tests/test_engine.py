# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
from time import sleep

import pytest

import autokeys.engine as engine
from autokeys.engine import (
    Clipboard, HotKeys, KeyPatterns, SeqKeys, is_equal, is_subseq, is_subset)

from conftest import KEY, chord, depth, press, release, tap


# =======================================================================================
# helpers
# =======================================================================================
class TestHelpers:
    def test_is_equal(self):
        assert is_equal('abc', ['a', 'b', 'c'])
        assert not is_equal('abc', 'ab')

    def test_is_subset_ignores_order(self):
        assert is_subset('ba', 'abc')
        assert not is_subset('az', 'abc')

    def test_is_subseq_is_a_prefix_check(self):
        assert is_subseq('ab', 'abc')
        assert not is_subseq('ax', 'abc')
        assert not is_subseq('abcd', 'abc')


# =======================================================================================
# HotKeys
# =======================================================================================
class TestHotKeys:
    def combo(self):
        return HotKeys(KEY('a'), KEY('b'))

    def test_completed_combo_fires_once_every_key_is_up(self):
        keys = self.combo()
        keys.press(KEY('a'), None)
        keys.press(KEY('b'), None)
        # still held: no verdict yet
        assert keys.release(KEY('a'), None) is None
        assert keys.release(KEY('b'), None) is True

    def test_partial_combo_stays_pending(self):
        keys = self.combo()
        keys.press(KEY('a'), None)
        assert keys.release(KEY('a'), None) is None

    def test_foreign_key_disables_the_combo(self):
        keys = self.combo()
        keys.press(KEY('a'), None)
        keys.press(KEY('z'), None)
        release_all = [keys.release(KEY('a'), None), keys.release(KEY('z'), None)]
        assert release_all[-1] is False

    def test_gives_up_once_lives_are_spent(self):
        """Regression: `not self._lives <= 0` inverted the guard, so MAX_LIVES
        never retired a combo - it made release() report *pending* forever."""
        keys = self.combo()
        for i in range(HotKeys.MAX_LIVES):
            keys.press(KEY(str(i)), None)
        assert keys._lives == 0
        # keys are still held, but the combo is spent and must say so
        assert keys.release(KEY('0'), None) is False

    def test_reset_restores_lives(self):
        keys = self.combo()
        for i in range(HotKeys.MAX_LIVES):
            keys.press(KEY(str(i)), None)
        keys.reset()
        assert keys._lives == HotKeys.MAX_LIVES
        keys.press(KEY('a'), None)
        keys.press(KEY('b'), None)
        keys.release(KEY('a'), None)
        assert keys.release(KEY('b'), None) is True

    def test_repeated_press_of_a_held_key_is_ignored(self):
        keys = self.combo()
        keys.press(KEY('a'), None)
        keys.press(KEY('a'), None)
        assert keys._press == [KEY('a')]


# =======================================================================================
# SeqKeys
# =======================================================================================
class TestSeqKeys:
    def sequence(self):
        return SeqKeys(KEY('x'), KEY('y'))

    def test_matching_sequence_activates(self):
        keys = self.sequence()
        keys.press(KEY('x'), KEY('x'))
        assert keys.release(KEY('x'), None) is None
        keys.press(KEY('y'), KEY('y'))
        assert keys.release(KEY('y'), None) is True

    def test_wrong_character_disables(self):
        keys = self.sequence()
        keys.press(KEY('x'), KEY('x'))
        keys.release(KEY('x'), None)
        keys.press(KEY('z'), KEY('z'))
        assert keys.release(KEY('z'), None) is False

    def test_order_matters(self):
        keys = self.sequence()
        keys.press(KEY('y'), KEY('y'))
        assert keys.release(KEY('y'), None) is False


# =======================================================================================
# KeyPatterns
# =======================================================================================
class TestKeyPatterns:
    @pytest.fixture
    def patterns(self):
        self.fired = []
        config = {
            HotKeys(KEY('a'), KEY('b')): {
                SeqKeys(KEY('x'), KEY('y')): (lambda parent: self.fired.append(parent))
            }
        }
        return KeyPatterns(config)

    def test_hotkey_descends_into_its_sequence(self, patterns):
        assert depth(patterns) == 1
        chord(patterns, 'a', 'b')
        assert depth(patterns) == 2

    def test_full_pattern_invokes_the_action(self, patterns):
        chord(patterns, 'a', 'b')
        tap(patterns, 'x')
        assert self.fired == []
        tap(patterns, 'y')
        assert len(self.fired) == 1
        # the leaf receives the SeqKeys that matched, which the actions use for
        # the backspace count
        assert len(self.fired[0]) == 2

    def test_stack_unwinds_after_the_action(self, patterns):
        chord(patterns, 'a', 'b')
        tap(patterns, 'x')
        tap(patterns, 'y')
        assert depth(patterns) == 1

    def test_wrong_sequence_unwinds_the_stack(self, patterns):
        chord(patterns, 'a', 'b')
        tap(patterns, 'z')
        assert depth(patterns) == 1
        assert self.fired == []

    def test_injected_events_are_ignored(self, patterns):
        """Regression: Keyboard.Type() drives a Controller and the OS reports
        those events straight back to this listener."""
        chord(patterns, 'a', 'b', injected=True)
        assert depth(patterns) == 1
        assert self.fired == []

    def test_injected_events_do_not_corrupt_a_live_match(self, patterns):
        """The real scenario: an action types a password, and every one of those
        characters is echoed back while the stack sits on the sequence level."""
        chord(patterns, 'a', 'b')
        for char in 'secret':
            tap(patterns, char, injected=True)
        assert depth(patterns) == 2
        # the genuine sequence still matches
        tap(patterns, 'x')
        tap(patterns, 'y')
        assert len(self.fired) == 1

    def test_unrelated_key_is_harmless_at_the_root(self, patterns):
        tap(patterns, 'q')
        assert depth(patterns) == 1
        assert self.fired == []


# =======================================================================================
# Clipboard
# =======================================================================================
class TestClipboard:
    def test_stage_puts_the_secret_up_and_revert_takes_it_down(self, clipboard):
        clipboard['value'] = 'original'
        Clipboard.Stage('secret', timeout=60)
        assert clipboard['value'] == 'secret'
        Clipboard.Revert()
        assert clipboard['value'] == 'original'

    def test_revert_leaves_a_newer_user_copy_alone(self, clipboard):
        clipboard['value'] = 'original'
        Clipboard.Stage('secret', timeout=60)
        clipboard['value'] = 'something the user copied'
        Clipboard.Revert()
        assert clipboard['value'] == 'something the user copied'

    def test_back_to_back_stages_restore_the_original(self, clipboard):
        """The second Stage() must not treat the first secret as the value worth
        restoring."""
        clipboard['value'] = 'original'
        Clipboard.Stage('first', timeout=60)
        Clipboard.Stage('second', timeout=60)
        assert clipboard['value'] == 'second'
        Clipboard.Revert()
        assert clipboard['value'] == 'original'

    def test_a_stale_timer_cannot_clobber_a_newer_stage(self, clipboard):
        clipboard['value'] = 'original'
        Clipboard.Stage('first', timeout=60)
        stale = Clipboard._epoch
        Clipboard.Stage('second', timeout=60)
        Clipboard.Revert(stale)
        assert clipboard['value'] == 'second'
        Clipboard.Revert(Clipboard._epoch)
        assert clipboard['value'] == 'original'

    def test_the_deadline_actually_fires(self, clipboard):
        clipboard['value'] = 'original'
        Clipboard.Stage('secret', timeout=0.05)
        assert clipboard['value'] == 'secret'
        for _ in range(50):
            if clipboard['value'] == 'original':
                break
            sleep(0.02)
        assert clipboard['value'] == 'original'

    def test_revert_is_idempotent(self, clipboard):
        clipboard['value'] = 'original'
        Clipboard.Stage('secret', timeout=60)
        Clipboard.Revert()
        clipboard['value'] = 'later'
        Clipboard.Revert()
        assert clipboard['value'] == 'later'

    def test_staging_forks_no_processes(self, clipboard):
        """Regression: the old implementation forked a process that already held
        an X11 connection, and passed the secret as a process argument."""
        assert not hasattr(engine, 'Process')
        Clipboard.Stage('secret', timeout=60)
        from multiprocessing import active_children
        assert active_children() == []
