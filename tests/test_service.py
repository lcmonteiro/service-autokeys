# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
import logging

import pytest

import autokeys.service as service
from autokeys import __version__
from autokeys.service import EXIT_CONFIG, EXIT_OK, main, parser, verbosity


@pytest.fixture
def listener(monkeypatch):
    """Stand in for the real listener so main() returns immediately."""
    seen = {}

    class Fake:
        def __init__(self, config):
            seen['config'] = config

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def join(self):
            seen['joined'] = True

    monkeypatch.setattr(service, 'KeyPatterns', Fake)
    return seen


# =======================================================================================
# argument parsing
# =======================================================================================
class TestParser:
    def test_settings_is_optional(self):
        """Regression: the positional was required, so its `default` was dead
        and running `autokeys` bare exited with a usage error."""
        assert parser().parse_args([]).settings is None

    def test_settings_is_accepted(self):
        assert parser().parse_args(['cfg.yml']).settings == 'cfg.yml'

    def test_version_is_reported(self, capsys):
        with pytest.raises(SystemExit) as exit:
            parser().parse_args(['--version'])
        assert exit.value.code == 0
        assert __version__ in capsys.readouterr().out

    def test_verbosity_levels(self):
        assert verbosity(0) == logging.WARNING
        assert verbosity(1) == logging.INFO
        assert verbosity(2) == logging.DEBUG
        assert verbosity(9) == logging.DEBUG


# =======================================================================================
# main
# =======================================================================================
class TestMain:
    def test_runs_without_a_settings_file(self, listener):
        assert main([]) == EXIT_OK
        assert listener['joined'] is True
        # the built-in chords are still wired up
        assert len(listener['config']) == 3

    def test_runs_with_a_settings_file(self, listener, settings):
        path = settings('credentials:\n  aa:\n    user: u\n    pass: p\n')
        assert main([path]) == EXIT_OK
        assert len(listener['config']) == 3

    def test_missing_file_exits_with_a_message(self, listener, tmp_path, caplog):
        code = main([str(tmp_path / 'absent.yml')])
        assert code == EXIT_CONFIG
        assert 'no such file' in caplog.text
        assert 'joined' not in listener

    def test_unreadable_settings_exit_before_listening(self, listener, settings,
                                                       caplog):
        path = settings('credentials: {}\n', mode=0o644)
        assert main([path]) == EXIT_CONFIG
        assert 'readable by other users' in caplog.text
        assert 'joined' not in listener

    def test_bad_config_does_not_leak_a_traceback(self, listener, settings, caplog):
        path = settings('options:\n  clipboard-timeout: soon\n')
        assert main([path]) == EXIT_CONFIG
        assert 'Traceback' not in caplog.text

    def test_keyboard_interrupt_is_a_clean_exit(self, monkeypatch):
        class Interrupting:
            def __init__(self, config):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def join(self):
                raise KeyboardInterrupt

        monkeypatch.setattr(service, 'KeyPatterns', Interrupting)
        assert main([]) == EXIT_OK
