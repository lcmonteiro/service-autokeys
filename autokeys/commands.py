# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
"""Text snippets and service control, behind `Ctrl+Alt+Cmd`."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from autokeys.engine import (
    Branch, Chord, Keyboard, Pattern, Sequence, Shutdown, chars)

#: Typing this after the chord stops the service.
QUIT = 'exit'


# =======================================================================================
# actions
# =======================================================================================
def write_text(text: str):
    """Replace the trigger the user just typed with `text`."""
    def action(pattern: Pattern) -> None:
        Keyboard.type(text, backspaces=len(pattern))
    return action


def quit_service(_: Pattern) -> None:
    raise Shutdown()


# =======================================================================================
# build commands config
# =======================================================================================
def config_commands(data: Optional[Mapping[str, Any]] = None,
                    options=None) -> Dict[Pattern, Branch]:
    """Bind typed triggers to literal text, plus the built-in quit command.

    A `commands` section maps a trigger to the text it expands to::

        commands:
          addr: 221B Baker Street
    """
    # Imported here to keep this module importable without a settings file.
    from autokeys.config import ConfigError, _mapping

    snippets: Dict[Pattern, Branch] = {
        Sequence(*chars(QUIT)): quit_service,
    }
    for trigger, text in _mapping(data, 'commands').items():
        trigger = str(trigger)
        if not trigger:
            raise ConfigError('commands: trigger must not be empty')
        if trigger.lower() == QUIT:
            raise ConfigError(
                "commands: {!r} is reserved for the built-in quit "
                'command'.format(QUIT))
        if not isinstance(text, str):
            raise ConfigError(
                'commands: {!r} must expand to text, got {}'.format(
                    trigger, type(text).__name__))
        snippets[Sequence(*chars(trigger))] = write_text(text)

    return {Chord(Keyboard.CTRL, Keyboard.ALT, Keyboard.CMD): snippets}
