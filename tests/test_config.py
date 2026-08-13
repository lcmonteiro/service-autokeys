# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
import os

import pytest

from autokeys.commands import config_commands
from autokeys.config import ConfigError, Options, build, load_settings, secret
from autokeys.credentials import config_credentials
from autokeys.engine import Chord


# =======================================================================================
# load_settings
# =======================================================================================
class TestLoadSettings:
    def test_no_path_yields_no_settings(self):
        assert load_settings(None) == {}
        assert load_settings('') == {}

    def test_reads_a_settings_file(self, settings):
        path = settings('credentials:\n  aa:\n    user: u\n    pass: p\n')
        assert load_settings(path)['credentials']['aa']['user'] == 'u'

    def test_empty_file_is_not_a_crash(self, settings):
        """Regression: safe_load returns None, and `None.get` used to end the
        process with an AttributeError."""
        assert load_settings(settings('')) == {}

    def test_comment_only_file_is_not_a_crash(self, settings):
        assert load_settings(settings('# nothing here\n')) == {}

    def test_missing_file_is_reported_clearly(self, tmp_path):
        with pytest.raises(ConfigError, match='no such file'):
            load_settings(str(tmp_path / 'absent.yml'))

    def test_malformed_yaml_is_reported_clearly(self, settings):
        with pytest.raises(ConfigError):
            load_settings(settings('credentials: [unclosed\n'))

    def test_unknown_section_is_rejected(self, settings):
        with pytest.raises(ConfigError, match='unknown section'):
            load_settings(settings('nonsense:\n  a: 1\n'))

    def test_non_mapping_document_is_rejected(self, settings):
        with pytest.raises(ConfigError, match='expected a mapping'):
            load_settings(settings('- just\n- a list\n'))

    @pytest.mark.skipif(os.name != 'posix', reason='POSIX permissions')
    def test_world_readable_settings_are_refused(self, settings):
        path = settings('credentials: {}\n', mode=0o644)
        with pytest.raises(ConfigError, match='readable by other users'):
            load_settings(path)

    @pytest.mark.skipif(os.name != 'posix', reason='POSIX permissions')
    def test_group_readable_settings_are_refused(self, settings):
        path = settings('credentials: {}\n', mode=0o640)
        with pytest.raises(ConfigError, match='readable by other users'):
            load_settings(path)


# =======================================================================================
# Options
# =======================================================================================
class TestOptions:
    def test_defaults_keep_the_password_off_the_clipboard(self):
        assert Options.parse(None).clipboard is False

    def test_reads_the_switches(self):
        options = Options.parse({'clipboard': True, 'clipboard-timeout': 5})
        assert options.clipboard is True
        assert options.clipboard_timeout == 5.0

    def test_unknown_option_is_rejected(self):
        with pytest.raises(ConfigError, match='unknown setting'):
            Options.parse({'clipbaord': True})

    def test_non_numeric_timeout_is_rejected(self):
        with pytest.raises(ConfigError, match='must be a number'):
            Options.parse({'clipboard-timeout': 'soon'})

    def test_negative_timeout_is_rejected(self):
        with pytest.raises(ConfigError, match='must be positive'):
            Options.parse({'clipboard-timeout': -1})


# =======================================================================================
# secret
# =======================================================================================
class TestSecret:
    def test_reads_a_literal(self):
        assert secret({'pass': 'hunter2'}, 'pass', 'aa') == 'hunter2'

    def test_reads_the_environment(self, monkeypatch):
        monkeypatch.setenv('AUTOKEYS_TEST_PASS', 'from-env')
        assert secret({'pass-env': 'AUTOKEYS_TEST_PASS'}, 'pass', 'aa') == 'from-env'

    def test_missing_environment_variable_is_reported(self, monkeypatch):
        monkeypatch.delenv('AUTOKEYS_ABSENT', raising=False)
        with pytest.raises(ConfigError, match='is not set'):
            secret({'pass-env': 'AUTOKEYS_ABSENT'}, 'pass', 'aa')

    def test_both_sources_at_once_is_rejected(self):
        with pytest.raises(ConfigError, match='not both'):
            secret({'pass': 'a', 'pass-env': 'B'}, 'pass', 'aa')

    def test_missing_field_names_the_credential(self):
        with pytest.raises(ConfigError, match="credential 'aa'"):
            secret({'user': 'u'}, 'pass', 'aa')


# =======================================================================================
# credentials
# =======================================================================================
class TestCredentials:
    def test_builds_one_branch_per_chord(self):
        config = config_credentials({'aa': {'user': 'u', 'pass': 'p'},
                                     'bb': {'user': 'u2', 'pass': 'p2'}})
        assert len(config) == 2
        assert all(isinstance(key, Chord) for key in config)
        assert all(len(branch) == 2 for branch in config.values())

    def test_empty_section_still_builds_the_chords(self):
        assert len(config_credentials(None)) == 2

    def test_malformed_entry_is_reported(self):
        with pytest.raises(ConfigError, match='expected a mapping'):
            config_credentials({'aa': 'not-a-mapping'})

    def test_typing_a_username(self, typed):
        config = config_credentials({'aa': {'user': 'octocat', 'pass': 'p'}})
        _fire(config, 'u', 'aa')
        # two backspaces to swallow the trigger the user typed
        assert typed == [('octocat', 2, False)]

    def test_typing_a_password(self, clipboard, typed):
        config = config_credentials({'aa': {'user': 'u', 'pass': 'hunter2'}})
        _fire(config, 'p', 'aa')
        assert typed == [('hunter2', 2, False)]

    def test_clipboard_is_off_unless_asked_for(self, clipboard, typed):
        config = config_credentials(
            {'aa': {'user': 'u', 'pass': 'hunter2'}}, Options())
        _fire(config, 'p', 'aa')
        assert clipboard['value'] == ''

    def test_clipboard_stages_when_asked_for(self, clipboard, typed):
        config = config_credentials(
            {'aa': {'user': 'u', 'pass': 'hunter2'}},
            Options(clipboard=True, clipboard_timeout=60))
        _fire(config, 'p', 'aa')
        assert clipboard['value'] == 'hunter2'

    def test_the_trigger_selects_the_credential(self, typed):
        config = config_credentials({'aa': {'user': 'first', 'pass': 'p'},
                                     'bb': {'user': 'second', 'pass': 'p'}})
        _fire(config, 'u', 'bb')
        assert typed == [('second', 2, False)]


def _fire(config, chord_key, trigger):
    """Drive `Ctrl+Alt+<chord_key>` then `trigger` through a built config."""
    from autokeys.engine import KeyPatterns, Keyboard

    patterns = KeyPatterns(config)
    held = [Keyboard.CTRL, Keyboard.ALT, Keyboard.key(chord_key)]
    for key in held:
        patterns._on_press(key)
    for key in reversed(held):
        patterns._on_release(key)
    for char in trigger:
        patterns._on_press(Keyboard.key(char))
        patterns._on_release(Keyboard.key(char))


# =======================================================================================
# commands
# =======================================================================================
class TestCommands:
    def test_quit_is_always_present(self):
        config = config_commands(None)
        assert len(config) == 1
        assert len(next(iter(config.values()))) == 1

    def test_snippets_are_bound(self):
        config = config_commands({'addr': '221B Baker Street'})
        assert len(next(iter(config.values()))) == 2

    def test_reserved_trigger_is_rejected(self):
        with pytest.raises(ConfigError, match='reserved'):
            config_commands({'exit': 'nope'})

    def test_non_text_expansion_is_rejected(self):
        with pytest.raises(ConfigError, match='must expand to text'):
            config_commands({'addr': ['a', 'list']})

    def test_snippet_types_its_text(self, typed):
        from autokeys.commands import write_text
        from autokeys.engine import Sequence, chars

        write_text('221B Baker Street')(Sequence(*chars('addr')))
        assert typed == [('221B Baker Street', 4, False)]


# =======================================================================================
# build
# =======================================================================================
class TestBuild:
    def test_assembles_every_source(self):
        config = build({'credentials': {'aa': {'user': 'u', 'pass': 'p'}},
                        'commands': {'addr': 'somewhere'}})
        # user chord, password chord, command chord
        assert len(config) == 3

    def test_empty_settings_still_offer_the_built_ins(self):
        assert len(build({})) == 3

    def test_bad_options_surface_as_config_errors(self):
        with pytest.raises(ConfigError):
            build({'options': {'clipboard-timeout': 'soon'}})
