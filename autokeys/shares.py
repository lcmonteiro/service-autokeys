# =======================================================================================
#                          \    |  | __ __| _ \  |  /  __| \ \  /  __|
#                         _ \   |  |    |  (   | . <   _|   \  / \__ \
# @autor: Luis Monteiro _/  _\ \__/    _| \___/ _|\_\ ___|   _|  ____/
# =======================================================================================
# settings shares
#
#   the settings file is coded with codec-share in n share files, any k of them together
#   with the stamp (a file, or derived from a pin) give the settings back.
#
#   share file: magic | k | n | index | 0 | set id (8 bytes) | coded frame
#
#   the coding hides the settings from a casual reader, it is NOT encryption: keep the
#   shares apart and private, a share alone does not open, all together with a weak pin
#   can be brute forced.
# =======================================================================================
import os
import struct
import sys
from argparse import ArgumentParser
from getpass import getpass
from hashlib import pbkdf2_hmac
from itertools import combinations
from math import comb

from yaml import safe_load

from autokeys.codec_share import Codec, CodecError, SharesError, StampError

# =======================================================================================
# definitions
# =======================================================================================
MAGIC = b'AKS1'
HEADER = struct.Struct('<4sBBBx8s')
PIN_SALT = b'autokeys/codec-share/stamp'
PIN_ROUNDS = 200_000
MAX_CHECKS = 500
MAX_RETRIES = 10

_codec = None


def codec():
    global _codec
    if _codec is None:
        _codec = Codec()
    return _codec


class ShareError(Exception):
    pass


__all__ = [
    'ShareError', 'CodecError', 'SharesError', 'StampError',
    'is_share', 'stamp_from_pin', 'stamp_from_file', 'new_stamp', 'split', 'join',
    'load_stamp', 'add_stamp_arguments', 'main',
]


# =======================================================================================
# stamps
# =======================================================================================
def stamp_from_pin(pin):
    seed = pbkdf2_hmac('sha256', pin.encode(), PIN_SALT, PIN_ROUNDS)[:8]
    return codec().stamp(int.from_bytes(seed, 'little'))


def stamp_from_file(path):
    with open(path, 'rb') as ss:
        stamp = ss.read()
    if len(stamp) != codec().stamp_size:
        raise ShareError(f'{path} is not a stamp file')
    return stamp


def new_stamp():
    return codec().stamp(int.from_bytes(os.urandom(8), 'little'))


# =======================================================================================
# shares
# =======================================================================================
def is_share(data):
    return data[:len(MAGIC)] == MAGIC


def split(data, stamp, count=3, needed=2):
    """codes data in count shares, any needed of them open it"""
    if not 1 <= needed <= count <= Codec.MAX_FRAMES or needed > Codec.MAX_SPLIT:
        raise ShareError(
            f'needs 1 <= needed <= {Codec.MAX_SPLIT} and needed <= shares <= {Codec.MAX_FRAMES}')
    for _ in range(MAX_RETRIES):
        frames = codec().seal(stamp, data, needed, count)
        if _verify(data, stamp, frames, needed):
            break
    else:
        raise ShareError('could not code independent shares, try another stamp')
    uid = os.urandom(8)
    return [HEADER.pack(MAGIC, needed, count, i, uid) + f for i, f in enumerate(frames, 1)]


def join(shares, stamp):
    """opens the data from shares"""
    frames, header = {}, None
    for share in shares:
        if not is_share(share) or len(share) <= HEADER.size:
            raise ShareError('not a share file')
        _, needed, count, index, uid = HEADER.unpack_from(share)
        if header and header != (needed, count, uid):
            raise ShareError('shares from different splits')
        header = (needed, count, uid)
        frames[index] = share[HEADER.size:]
    needed, count, _ = header
    if len(frames) < needed:
        raise SharesError(f'{needed} of {count} shares are needed, got {len(frames)}')
    try:
        return codec().open(stamp, frames.values(), needed)
    except SharesError:
        # split verifies the shares are independent, so this comes from a wrong stamp
        raise StampError('shares do not open, wrong pin or stamp') from None


def _verify(data, stamp, frames, needed):
    groups = (combinations(frames, needed)
              if comb(len(frames), needed) <= MAX_CHECKS else [frames])
    try:
        return all(codec().open(stamp, group, needed) == data for group in groups)
    except CodecError:
        return False


# =======================================================================================
# command line helpers
# =======================================================================================
def _read_files(paths):
    data = []
    for path in paths:
        with open(path, 'rb') as ss:
            data.append(ss.read())
    return data


def _write_private(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'wb') as ss:
        ss.write(data)


def load_stamp(arguments, confirm=False):
    if arguments.stamp:
        return stamp_from_file(arguments.stamp)
    pin = os.environ.get('AUTOKEYS_PIN')
    if pin is None:
        pin = getpass('pin: ')
        if confirm and getpass('pin (again): ') != pin:
            raise ShareError('pins do not match')
    if not pin:
        raise ShareError('empty pin')
    return stamp_from_pin(pin)


def add_stamp_arguments(parser):
    parser.add_argument(
        '--stamp', metavar='FILE',
        help='stamp file of the shares (see autokeys-share stamp), '
             'by default a pin is asked (or read from $AUTOKEYS_PIN).')


# =======================================================================================
# entry point
# =======================================================================================
def main(args=None):
    parser = ArgumentParser(
        prog='autokeys-share', description='split the settings file in coded shares.')
    commands = parser.add_subparsers(dest='command', required=True)

    stamp_cmd = commands.add_parser('stamp', help='create a random stamp file.')
    stamp_cmd.add_argument('output', help='stamp file path.')

    split_cmd = commands.add_parser('split', help='split a settings file in shares.')
    split_cmd.add_argument('settings', help='settings file path.')
    split_cmd.add_argument(
        '-n', '--shares', type=int, default=3, help='number of shares (default 3).')
    split_cmd.add_argument(
        '-k', '--needed', type=int, default=2,
        help='number of shares needed to open (default 2).')
    split_cmd.add_argument(
        '-o', '--output', help='shares path prefix (default the settings path).')
    add_stamp_arguments(split_cmd)

    join_cmd = commands.add_parser('join', help='print the settings opened from shares.')
    join_cmd.add_argument('shares', nargs='+', help='share file paths.')
    add_stamp_arguments(join_cmd)

    arguments = parser.parse_args(args=args)
    try:
        if arguments.command == 'stamp':
            _write_private(arguments.output, new_stamp())
            print(arguments.output)
        elif arguments.command == 'split':
            data = _read_files([arguments.settings])[0]
            safe_load(data)  # only valid settings are split
            parts = split(
                data, load_stamp(arguments, confirm=True), arguments.shares, arguments.needed)
            prefix = arguments.output or arguments.settings
            for i, part in enumerate(parts, 1):
                path = f'{prefix}.{i}.share'
                _write_private(path, part)
                print(path)
        elif arguments.command == 'join':
            data = join(_read_files(arguments.shares), load_stamp(arguments))
            sys.stdout.buffer.write(data)
    except Exception as error:
        parser.exit(1, f'autokeys-share: {error}\n')
