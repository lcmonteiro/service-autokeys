# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
"""Pattern matching over global keyboard events.

Patterns are arranged in a tree. The root holds chords (`Ctrl+Alt+U`); matching
one descends into its branch, where a sequence (`g`, `h`) selects a leaf. Leaves
are callables, invoked with the pattern that selected them.
"""
from __future__ import annotations

import atexit
import logging
from collections import defaultdict
from enum import Enum, auto
from threading import Lock, Timer
from typing import Callable, Dict, Hashable, Iterable, Optional, Sequence as Seq, Tuple, Union

from pynput import keyboard
from pyperclip import copy, paste

log = logging.getLogger(__name__)

Key = Hashable
Action = Callable[['Pattern'], None]
Branch = Union[Action, Dict['Pattern', 'Branch']]


# =======================================================================================
# Exceptions
# =======================================================================================
class Shutdown(Exception):
    """Raised by an action to bring the listener down cleanly."""


# =======================================================================================
# Helpers
# =======================================================================================
def contains(whole: Iterable[Key], part: Iterable[Key]) -> bool:
    """Every key of `part` appears somewhere in `whole`, order irrelevant."""
    return all(key in whole for key in part)


def starts_with(whole: Seq[Key], head: Seq[Key]) -> bool:
    """`head` is a prefix of `whole`, order significant."""
    return len(head) <= len(whole) and all(a == b for a, b in zip(head, whole))


def chars(text: str) -> Tuple[Key, ...]:
    """The key objects spelling out `text`, normalised for comparison."""
    return tuple(Keyboard.key(char) for char in text.lower())


# =======================================================================================
# Match
# =======================================================================================
class Match(Enum):
    """How a pattern reads the keys it has seen so far."""

    #: Could still match; keep feeding it.
    PENDING = auto()
    #: Complete. The branch behind it should be taken.
    MATCHED = auto()
    #: Cannot match what was typed. Unwind.
    FAILED = auto()


# =======================================================================================
# Clipboard
# =======================================================================================
class Clipboard:
    """Stage a secret on the clipboard, then take it back off again.

    Reverting on the next key release, as this once did, loses the race against
    the modifier keys still held from the triggering chord - and against the
    Ctrl+V the user is trying to paste with. A deadline is coarser, but it is
    the same deadline every time.
    """

    #: Seconds a staged secret stays available before being withdrawn.
    TIMEOUT = 20.0

    _lock = Lock()
    _pending: Optional[Tuple[str, str]] = None  # (staged, previous)
    _timer: Optional[Timer] = None
    _epoch = 0

    @classmethod
    def stage(cls, secret: str, timeout: Optional[float] = None) -> None:
        with cls._lock:
            try:
                # On back-to-back stages paste() would hand back the *previous*
                # secret, so carry the original clipboard value forward instead.
                previous = cls._pending[1] if cls._pending else paste()
                copy(secret)
            except Exception:  # pragma: no cover - no clipboard backend
                log.warning('clipboard unavailable; secret was not staged')
                return

            cls._epoch += 1
            cls._pending = (secret, previous)
            cls._cancel()
            cls._timer = Timer(
                cls.TIMEOUT if timeout is None else timeout,
                cls.revert,
                args=(cls._epoch,),
            )
            cls._timer.daemon = True
            cls._timer.start()

    @classmethod
    def revert(cls, epoch: Optional[int] = None) -> None:
        """Restore the clipboard. Called on a deadline, and again at exit."""
        with cls._lock:
            if cls._pending is None:
                return
            if epoch is not None and epoch != cls._epoch:
                return  # a newer stage() owns the clipboard
            staged, previous = cls._pending
            try:
                if paste() == staged:  # do not clobber what the user copied
                    copy(previous)
            except Exception:  # pragma: no cover - no clipboard backend
                log.warning('clipboard unavailable; secret was not withdrawn')
            cls._pending = None
            cls._cancel()

    @classmethod
    def _cancel(cls) -> None:
        if cls._timer is not None:
            cls._timer.cancel()
            cls._timer = None


atexit.register(Clipboard.revert)


# =======================================================================================
# Keyboard
# =======================================================================================
class Keyboard:
    """Synthesises key events, and names the keys patterns are built from."""

    _controller = keyboard.Controller()

    SHIFT = keyboard.Key.shift
    CTRL = keyboard.Key.ctrl
    ALT = keyboard.Key.alt
    CMD = keyboard.Key.cmd

    @staticmethod
    def key(char: str) -> Key:
        return keyboard.KeyCode(char=char)

    @classmethod
    def type(cls, text: Optional[str] = None, backspaces: int = 0, enter: bool = False) -> None:
        for _ in range(backspaces):
            cls.tap(keyboard.Key.backspace)
        if text:
            cls._controller.type(text)
        if enter:
            cls.tap(keyboard.Key.enter)

    @classmethod
    def tap(cls, key) -> None:
        cls._controller.press(key)
        cls._controller.release(key)


# =======================================================================================
# Patterns
# =======================================================================================
class Pattern:
    """A shape of keystrokes that reports a `Match` as events arrive.

    Patterns are identified by object identity so that two triggers spelled the
    same way remain distinct keys in the tree.
    """

    def __init__(self, *keys: Key) -> None:
        self._keys = tuple(keys)
        self.reset()

    def __len__(self) -> int:
        return len(self._keys)

    def __repr__(self) -> str:
        return '{}({})'.format(
            type(self).__name__, '+'.join(str(key) for key in self._keys))

    def press(self, key: Key) -> None:
        raise NotImplementedError

    def release(self, key: Key) -> Match:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError


class Chord(Pattern):
    """Keys held down together, such as `Ctrl+Alt+U`.

    A chord commits only once every one of its keys is back up, so a sequence
    nested behind it is typed without the modifiers still masking it.
    """

    #: Stray keys tolerated before the chord gives up until the tree unwinds.
    MAX_MISSES = 5

    def press(self, key: Key) -> None:
        if key in self._held:
            return
        self._held.append(key)
        if not contains(self._keys, self._held):
            self._state = Match.FAILED
            self._misses += 1
        elif contains(self._held, self._keys):
            self._state = Match.MATCHED
        else:
            self._state = Match.PENDING

    def release(self, key: Key) -> Match:
        self._held = [held for held in self._held if held != key]
        if self._held and self._misses < self.MAX_MISSES:
            return Match.PENDING
        return self._state

    def reset(self) -> None:
        self._held: list = []
        self._state = Match.PENDING
        self._misses = 0


class Sequence(Pattern):
    """Keys typed one after another, such as `g` then `h`."""

    def press(self, key: Key) -> None:
        if key in self._held:
            return
        self._held.append(key)
        self._typed.append(key)
        if not starts_with(self._keys, self._typed):
            self._state = Match.FAILED
        elif starts_with(self._typed, self._keys):
            self._state = Match.MATCHED
        else:
            self._state = Match.PENDING

    def release(self, key: Key) -> Match:
        self._held = [held for held in self._held if held != key]
        return self._state

    def reset(self) -> None:
        self._held: list = []
        self._typed: list = []
        self._state = Match.PENDING


# =======================================================================================
# KeyPatterns
# =======================================================================================
class KeyPatterns(keyboard.Listener):
    """Feeds global key events into a tree of patterns."""

    class Cursor:
        """How deep into the pattern tree the user currently is."""

        def __init__(self, root: Dict[Pattern, Branch]) -> None:
            self._path = [root]

        def __len__(self) -> int:
            return len(self._path)

        @property
        def level(self) -> Dict[Pattern, Branch]:
            return self._path[-1]

        def descend(self, level: Dict[Pattern, Branch]) -> None:
            self._path.append(level)

        def rewind(self) -> None:
            for level in reversed(self._path):
                for pattern in level:
                    pattern.reset()
            del self._path[1:]

    def __init__(self, config: Dict[Pattern, Branch]) -> None:
        super().__init__(on_press=self._on_press, on_release=self._on_release)
        self._cursor = self.Cursor(config)

    # ---------------------------------------------------------------
    # listener callbacks
    # ---------------------------------------------------------------
    def _on_press(self, key, injected: bool = False) -> None:
        # Keyboard.type() synthesises events through a Controller and the OS
        # reports them back to this listener. Replaying our own output would
        # corrupt the match state, so drop it. The default keeps the callback
        # working on pynput releases that pass the key alone.
        if injected:
            return
        key = self.canonical(key)
        for pattern in self._cursor.level:
            pattern.press(key)

    def _on_release(self, key, injected: bool = False) -> None:
        if injected:
            return
        key = self.canonical(key)

        outcome: Dict[Match, Dict[Pattern, Branch]] = defaultdict(dict)
        for pattern, branch in self._cursor.level.items():
            outcome[pattern.release(key)][pattern] = branch

        if outcome[Match.MATCHED]:
            self._advance(outcome[Match.MATCHED])
        elif outcome[Match.FAILED] and not outcome[Match.PENDING]:
            self._cursor.rewind()

    # ---------------------------------------------------------------
    # internals
    # ---------------------------------------------------------------
    def _advance(self, matched: Dict[Pattern, Branch]) -> None:
        deeper: Dict[Pattern, Branch] = {}
        for pattern, branch in matched.items():
            if callable(branch):
                self._fire(branch, pattern)
            else:
                deeper.update(branch)
        if deeper:
            self._cursor.descend(deeper)
        else:
            self._cursor.rewind()

    def _fire(self, action: Action, pattern: Pattern) -> None:
        try:
            action(pattern)
        except Shutdown:
            log.info('shutdown requested')
            self.stop()
        except Exception:
            # An escaping exception would otherwise take the listener - and the
            # whole service - down with it.
            log.exception('action for %r failed', pattern)
