# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
"""Command line entry point."""
from __future__ import annotations

import logging
import sys
from argparse import ArgumentParser
from typing import List, Optional

from autokeys import __version__
from autokeys.config import ConfigError, build, load_settings
from autokeys.engine import KeyPatterns

log = logging.getLogger('autokeys')

EXIT_OK = 0
EXIT_CONFIG = 2


# =======================================================================================
# helpers
# =======================================================================================
def parser() -> ArgumentParser:
    parsing = ArgumentParser(
        prog='autokeys',
        description='Type credentials and text snippets from a global hotkey.')
    parsing.add_argument(
        'settings', nargs='?', default=None,
        help='settings file path; without one, only the built-in commands run')
    parsing.add_argument(
        '-v', '--verbose', action='count', default=0,
        help='log more; repeat for debug output')
    parsing.add_argument(
        '--version', action='version', version='%(prog)s {}'.format(__version__))
    return parsing


def verbosity(count: int) -> int:
    return {0: logging.WARNING, 1: logging.INFO}.get(count, logging.DEBUG)


# =======================================================================================
# entry point
# =======================================================================================
def main(args: Optional[List[str]] = None) -> int:
    arguments = parser().parse_args(args=args)
    logging.basicConfig(
        level=verbosity(arguments.verbose),
        format='%(asctime)s %(levelname)-7s %(name)s: %(message)s')

    try:
        config = build(load_settings(arguments.settings))
    except ConfigError as error:
        # The message names the file and the offending key; a traceback here
        # would only bury it.
        log.error('%s', error)
        return EXIT_CONFIG

    log.info('listening on %d chord(s)', len(config))
    try:
        with KeyPatterns(config) as listener:
            listener.join()
    except KeyboardInterrupt:
        log.info('interrupted')
    return EXIT_OK


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
