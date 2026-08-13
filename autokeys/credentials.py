# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
"""Usernames behind `Ctrl+Alt+U`, passwords behind `Ctrl+Alt+P`."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from autokeys.engine import (
    Branch, Chord, Clipboard, Keyboard, Pattern, Sequence, chars)


# =======================================================================================
# actions
# =======================================================================================
def write_user(user: str):
    """Replace the trigger the user just typed with their username."""
    def action(pattern: Pattern) -> None:
        Keyboard.type(user, backspaces=len(pattern))
    return action


def write_pass(password: str, stage: bool = False, timeout: Optional[float] = None):
    """Replace the trigger with the password, optionally staging a copy.

    Staging puts the password where every process on the machine can read it,
    so it is off unless the settings file asks for it.
    """
    def action(pattern: Pattern) -> None:
        Keyboard.type(password, backspaces=len(pattern))
        if stage:
            Clipboard.stage(password, timeout)
    return action


# =======================================================================================
# build credentials config
# =======================================================================================
def config_credentials(data: Optional[Mapping[str, Any]] = None,
                       options=None) -> Dict[Pattern, Branch]:
    """Bind a trigger per credential under each of the two chords.

        credentials:
          gh:
            user: octocat
            pass-env: GITHUB_PASSWORD
    """
    # Imported here to keep the import graph acyclic; config builds on us.
    from autokeys.config import ConfigError, Options, _mapping, secret

    options = options or Options()

    users: Dict[Pattern, Branch] = {}
    passwords: Dict[Pattern, Branch] = {}
    for alias, entry in _mapping(data, 'credentials').items():
        alias = str(alias)
        if not alias:
            raise ConfigError('credentials: trigger must not be empty')
        entry = _mapping(entry, "credentials: '{}'".format(alias))
        users[Sequence(*chars(alias))] = write_user(
            secret(entry, 'user', alias))
        passwords[Sequence(*chars(alias))] = write_pass(
            secret(entry, 'pass', alias),
            stage=options.clipboard,
            timeout=options.clipboard_timeout,
        )

    return {
        Chord(Keyboard.CTRL, Keyboard.ALT, Keyboard.key('u')): users,
        Chord(Keyboard.CTRL, Keyboard.ALT, Keyboard.key('p')): passwords,
    }
