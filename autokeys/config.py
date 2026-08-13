# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
"""Reading, validating and assembling the settings file."""
from __future__ import annotations

import os
import stat
from collections import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from yaml import YAMLError, safe_load

from autokeys.engine import Branch, Clipboard, Pattern

#: Sections understood at the top level of a settings file.
SECTIONS = ('options', 'commands', 'credentials')


# =======================================================================================
# Exceptions
# =======================================================================================
class ConfigError(Exception):
    """The settings file is missing, unreadable or does not make sense."""


# =======================================================================================
# Options
# =======================================================================================
@dataclass(frozen=True)
class Options:
    """Behaviour switches from the `options` section."""

    #: Also place a password on the clipboard after typing it. Off by default:
    #: the clipboard is readable by every process on the machine, and the
    #: password has already been typed where it was wanted.
    clipboard: bool = False

    #: Seconds a staged password stays on the clipboard.
    clipboard_timeout: float = Clipboard.TIMEOUT

    @classmethod
    def parse(cls, data: Optional[Mapping[str, Any]]) -> 'Options':
        data = _mapping(data, 'options')
        unknown = set(data) - {'clipboard', 'clipboard-timeout'}
        if unknown:
            raise ConfigError(
                'options: unknown setting(s) {}'.format(_listed(unknown)))
        timeout = data.get('clipboard-timeout', cls.clipboard_timeout)
        try:
            timeout = float(timeout)
        except (TypeError, ValueError):
            raise ConfigError(
                'options: clipboard-timeout must be a number, '
                'got {!r}'.format(timeout)) from None
        if timeout <= 0:
            raise ConfigError('options: clipboard-timeout must be positive')
        return cls(clipboard=bool(data.get('clipboard', cls.clipboard)),
                   clipboard_timeout=timeout)


# =======================================================================================
# loading
# =======================================================================================
def load_settings(path: Optional[str] = None) -> Dict[str, Any]:
    """Read a settings file, refusing one other users can read."""
    if not path:
        return {}
    file = Path(path).expanduser()
    if not file.is_file():
        raise ConfigError('{}: no such file'.format(file))
    _check_permissions(file)
    try:
        with file.open(encoding='utf-8') as stream:
            settings = safe_load(stream)
    except YAMLError as error:
        raise ConfigError('{}: {}'.format(file, error)) from None
    except OSError as error:
        raise ConfigError('{}: {}'.format(file, error.strerror)) from None

    # An empty or comment-only file parses as None.
    settings = _mapping(settings or {}, str(file))
    unknown = set(settings) - set(SECTIONS)
    if unknown:
        raise ConfigError('{}: unknown section(s) {}; expected {}'.format(
            file, _listed(unknown), _listed(SECTIONS)))
    return settings


def build(settings: Mapping[str, Any]) -> Dict[Pattern, Branch]:
    """Turn parsed settings into the pattern tree the engine walks."""
    # Imported here so that `engine` stays free of any dependency on its
    # configuration sources.
    from autokeys.commands import config_commands
    from autokeys.credentials import config_credentials

    options = Options.parse(settings.get('options'))
    config: Dict[Pattern, Branch] = {}
    config.update(config_commands(settings.get('commands'), options))
    config.update(config_credentials(settings.get('credentials'), options))
    return config


def secret(entry: Mapping[str, Any], field: str, alias: str) -> str:
    """Read `field` from an entry, or `<field>-env` from the environment.

    The indirection keeps a password out of the settings file entirely, which
    is the only way to keep it out of backups and version control.
    """
    literal = entry.get(field)
    variable = entry.get('{}-env'.format(field))
    if literal is not None and variable is not None:
        raise ConfigError(
            "credential '{}': set either '{}' or '{}-env', not both".format(
                alias, field, field))
    if variable is not None:
        try:
            return str(os.environ[str(variable)])
        except KeyError:
            raise ConfigError(
                "credential '{}': environment variable {!r} is not set".format(
                    alias, variable)) from None
    if literal is None:
        raise ConfigError(
            "credential '{}': missing '{}' (or '{}-env')".format(
                alias, field, field))
    return str(literal)


# =======================================================================================
# helpers
# =======================================================================================
def _check_permissions(file: Path) -> None:
    """Refuse a settings file that group or others can reach."""
    if os.name != 'posix':
        return
    mode = file.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ConfigError(
            '{0}: readable by other users ({1}); '
            'this file holds credentials - run: chmod 600 {0}'.format(
                file, stat.filemode(mode)))


def _mapping(data: Any, where: str) -> Dict[str, Any]:
    if data is None:
        return {}
    if not isinstance(data, abc.Mapping):
        raise ConfigError('{}: expected a mapping, got {}'.format(
            where, type(data).__name__))
    return dict(data)


def _listed(names) -> str:
    return ', '.join(repr(str(name)) for name in sorted(names))
