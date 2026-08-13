# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
from time import sleep

import pytest

import autokeys.engine as engine
from autokeys.engine import (
    Chord, Clipboard, KeyPatterns, Match, Sequence, Shutdown, chars, contains,
    starts_with)

from conftest import KEY, chord, depth, tap


# =======================================================================================
# helpers
# =======================================================================================
class TestHelpers:
    def test_contains_ignores_order(self):
        assert contains('abc', 'ba')
        assert not contains('abc', 'az')

    def test_starts_with_is_order_sensitive(self):
        assert starts_with('abc', 'ab')
        assert not starts_with('abc', 'ax')
        assert not starts_with('abc', 'abcd')

    def test_chars_normalises_case(self):
        assert chars('AB') == chars('ab')
        assert len(chars('ab')) == 2


# =======================================================================================
# Chord
# =======================================================================================
class TestChord:
    def combo(self):
        return Chord(KEY('a'), KEY('b'))

    def test_commits_once_every_key_is_up(self):
        keys = self.combo()
        keys.press(KEY('a'))
        keys.press(KEY('b'))
        # still held: no verdict yet
        assert keys.release(KEY('a')) is Match.PENDING
        assert keys.release(KEY('b')) is Match.MATCHED

    def test_partial_chord_stays_pending(self):
        keys = self.combo()
        keys.press(KEY('a'))
        assert keys.release(KEY('a')) is Match.PENDING

    def test_foreign_key_fails_the_chord(self):
        keys = self.combo()
        keys.press(KEY('a'))
        keys.press(KEY('z'))
        keys.release(KEY('a'))
        assert keys.release(KEY('z')) is Match.FAILED

    def test_gives_up_once_misses_are_spent(self):
        """Regression: `not self._lives <= 0` inverted the guard, so the miss
        budget never retired a chord - it reported *pending* forever instead."""
        keys = self.combo()
        for index in range(Chord.MAX_MISSES):
            keys.press(KEY(str(index)))
        # keys are still held, but the chord is spent and must say so
        assert keys.release(KEY('0')) is Match.FAILED

    def test_reset_restores_the_miss_budget(self):
        keys = self.combo()
        for index in range(Chord.MAX_MISSES):
            keys.press(KEY(str(index)))
        keys.reset()
        keys.press(KEY('a'))
        keys.press(KEY('b'))
        keys.release(KEY('a'))
        assert keys.release(KEY('b')) is Match.MATCHED

    def test_auto_repeat_of_a_held_key_is_ignored(self):
        keys = self.combo()
        keys.press(KEY('a'))
        keys.press(KEY('a'))
        assert keys._held == [KEY('a')]

    def test_len_reports_the_key_count(self):
        assert len(self.combo()) == 2


# =======================================================================================
# Sequence
# =======================================================================================
class TestSequence:
    def sequence(self):
        return Sequence(*chars('xy'))

    def test_matching_sequence_activates(self):
        keys = self.sequence()
        keys.press(KEY('x'))
        assert keys.release(KEY('x')) is Match.PENDING
        keys.press(KEY('y'))
        assert keys.release(KEY('y')) is Match.MATCHED

    def test_wrong_character_fails(self):
        keys = self.sequence()
        keys.press(KEY('x'))
        keys.release(KEY('x'))
        keys.press(KEY('z'))
        assert keys.release(KEY('z')) is Match.FAILED

    def test_order_matters(self):
        keys = self.sequence()
        keys.press(KEY('y'))
        assert keys.release(KEY('y')) is Match.FAILED


# =======================================================================================
# KeyPatterns
# =======================================================================================
class TestKeyPatterns:
    @pytest.fixture
    def patterns(self):
        self.fired = []
        return KeyPatterns({
            Chord(KEY('a'), KEY('b')): {
                Sequence(*chars('xy')): (lambda pattern: self.fired.append(pattern))
            }
        })

    def test_chord_descends_into_its_branch(self, patterns):
        assert depth(patterns) == 1
        chord(patterns, 'a', 'b')
        assert depth(patterns) == 2

    def test_full_pattern_invokes_the_action(self, patterns):
        chord(patterns, 'a', 'b')
        tap(patterns, 'x')
        assert self.fired == []
        tap(patterns, 'y')
        assert len(self.fired) == 1
        # the leaf receives the pattern that selected it, which the actions use
        # for the backspace count
        assert len(self.fired[0]) == 2

    def test_cursor_unwinds_after_the_action(self, patterns):
        chord(patterns, 'a', 'b')
        tap(patterns, 'x')
        tap(patterns, 'y')
        assert depth(patterns) == 1

    def test_wrong_sequence_unwinds_the_cursor(self, patterns):
        chord(patterns, 'a', 'b')
        tap(patterns, 'z')
        assert depth(patterns) == 1
        assert self.fired == []

    def test_uppercase_matches_its_trigger(self, patterns):
        """`canonical` folds case, so a trigger matches however it is typed."""
        chord(patterns, 'a', 'b')
        tap(patterns, 'X')
        tap(patterns, 'Y')
        assert len(self.fired) == 1

    def test_injected_events_are_ignored(self, patterns):
        """Regression: Keyboard.type() drives a Controller and the OS reports
        those events straight back to this listener."""
        chord(patterns, 'a', 'b', injected=True)
        assert depth(patterns) == 1
        assert self.fired == []

    def test_injected_events_do_not_corrupt_a_live_match(self, patterns):
        """The real scenario: an action types a password, and every one of those
        characters is echoed back while the cursor sits on the sequence."""
        chord(patterns, 'a', 'b')
        for char in 'secret':
            tap(patterns, char, injected=True)
        assert depth(patterns) == 2
        tap(patterns, 'x')
        tap(patterns, 'y')
        assert len(self.fired) == 1

    def test_unrelated_key_is_harmless_at_the_root(self, patterns):
        tap(patterns, 'q')
        assert depth(patterns) == 1
        assert self.fired == []

    def test_a_failing_action_does_not_kill_the_listener(self, caplog):
        def explode(pattern):
            raise ValueError('boom')

        patterns = KeyPatterns({
            Chord(KEY('a')): {Sequence(*chars('x')): explode}})
        chord(patterns, 'a')
        tap(patterns, 'x')
        assert 'boom' in caplog.text
        # and the tree is usable again
        assert depth(patterns) == 1

    def test_shutdown_stops_the_listener(self, monkeypatch):
        stopped = []

        def quit_now(pattern):
            raise Shutdown()

        patterns = KeyPatterns({
            Chord(KEY('a')): {Sequence(*chars('x')): quit_now}})
        monkeypatch.setattr(
            KeyPatterns, 'stop', lambda self: stopped.append(True))
        chord(patterns, 'a')
        tap(patterns, 'x')
        assert stopped == [True]


# =======================================================================================
# Clipboard
# =======================================================================================
class TestClipboard:
    def test_stage_puts_the_secret_up_and_revert_takes_it_down(self, clipboard):
        clipboard['value'] = 'original'
        Clipboard.stage('secret', timeout=60)
        assert clipboard['value'] == 'secret'
        Clipboard.revert()
        assert clipboard['value'] == 'original'

    def test_revert_leaves_a_newer_user_copy_alone(self, clipboard):
        clipboard['value'] = 'original'
        Clipboard.stage('secret', timeout=60)
        clipboard['value'] = 'something the user copied'
        Clipboard.revert()
        assert clipboard['value'] == 'something the user copied'

    def test_back_to_back_stages_restore_the_original(self, clipboard):
        """The second stage() must not treat the first secret as the value worth
        restoring."""
        clipboard['value'] = 'original'
        Clipboard.stage('first', timeout=60)
        Clipboard.stage('second', timeout=60)
        assert clipboard['value'] == 'second'
        Clipboard.revert()
        assert clipboard['value'] == 'original'

    def test_a_stale_timer_cannot_clobber_a_newer_stage(self, clipboard):
        clipboard['value'] = 'original'
        Clipboard.stage('first', timeout=60)
        stale = Clipboard._epoch
        Clipboard.stage('second', timeout=60)
        Clipboard.revert(stale)
        assert clipboard['value'] == 'second'
        Clipboard.revert(Clipboard._epoch)
        assert clipboard['value'] == 'original'

    def test_the_deadline_actually_fires(self, clipboard):
        clipboard['value'] = 'original'
        Clipboard.stage('secret', timeout=0.05)
        assert clipboard['value'] == 'secret'
        for _ in range(50):
            if clipboard['value'] == 'original':
                break
            sleep(0.02)
        assert clipboard['value'] == 'original'

    def test_revert_is_idempotent(self, clipboard):
        clipboard['value'] = 'original'
        Clipboard.stage('secret', timeout=60)
        Clipboard.revert()
        clipboard['value'] = 'later'
        Clipboard.revert()
        assert clipboard['value'] == 'later'

    def test_staging_forks_no_processes(self, clipboard):
        """Regression: the old implementation forked a process that already held
        an X11 connection, and passed the secret as a process argument."""
        assert not hasattr(engine, 'Process')
        Clipboard.stage('secret', timeout=60)
        from multiprocessing import active_children
        assert active_children() == []

    def test_a_broken_clipboard_is_survivable(self, clipboard, monkeypatch, caplog):
        """pyperclip raises when it cannot find a backend; typing the password
        already worked, so that must not take the action down."""
        monkeypatch.setattr(
            engine, 'paste', lambda: (_ for _ in ()).throw(RuntimeError('no backend')))
        Clipboard.stage('secret', timeout=60)
        assert 'clipboard unavailable' in caplog.text
        assert Clipboard._pending is None
