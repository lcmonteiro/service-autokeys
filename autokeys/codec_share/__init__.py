# =======================================================================================
# codec-share python binding
#
#   vendored from https://github.com/lcmonteiro/codec-share (wasm/), together with
#   codec-share.wasm built by its wasm/build.sh: update both files together
#
#   runs codec-share.wasm (see codec_share.cpp) with wasmtime: pip install wasmtime
#
#   codec  = Codec()                          # loads codec-share.wasm next to this file
#   stamp  = codec.stamp(seed)                # or the 512 bytes of a stamp file
#   frames = codec.seal(stamp, data, 2, 3)    # 3 frames, any 2 of them open the data
#   data   = codec.open(stamp, frames[:2], 2)
# =======================================================================================
from pathlib import Path

from wasmtime import Engine, Linker, Module, Store, WasiConfig

WASM = Path(__file__).with_name('codec-share.wasm')


class CodecError(Exception):
    pass


class SharesError(CodecError):
    """not enough independent frames to open"""


class StampError(CodecError):
    """the frames do not open with the given stamp, or are corrupted"""


class Codec:
    # token types
    SPARSE, STREAM, MESSAGE, FULL = range(4)
    # limits
    MAX_SPLIT, MAX_FRAMES = 16, 255

    _ERRORS = {
        -1: (CodecError, 'invalid arguments'),
        -2: (SharesError, 'not enough independent frames'),
        -3: (StampError, 'frames do not open with this stamp'),
        -4: (CodecError, 'output buffer too small'),
    }

    def __init__(self, wasm=WASM):
        engine = Engine()
        self._store = Store(engine)
        wasi = WasiConfig()  # only random_get is used, for the coding seeds
        self._store.set_wasi(wasi)
        linker = Linker(engine)
        linker.define_wasi()
        instance = linker.instantiate(self._store, Module.from_file(engine, str(wasm)))
        exports = instance.exports(self._store)
        exports['_initialize'](self._store)
        self._memory = exports['memory']
        self._fn = {name: exports[name] for name in (
            'cs_alloc', 'cs_free', 'cs_stamp_size', 'cs_stamp_generate',
            'cs_frame_size', 'cs_seal', 'cs_open')}
        self.stamp_size = self._call('cs_stamp_size')

    # -----------------------------------------------------------------------------------
    # interface
    # -----------------------------------------------------------------------------------
    def stamp(self, seed, kind=MESSAGE):
        """stamp generated from a 64 bits seed"""
        with self._buffer(self.stamp_size) as out:
            self._check(self._call('cs_stamp_generate', kind, seed & (2**64 - 1), out.ptr))
            return out.read(self.stamp_size)

    def seal(self, stamp, data, split, count):
        """codes data in count frames, any split independent frames open it"""
        stamp = self._stamp(stamp)
        frame = self._check(self._call('cs_frame_size', len(data), split))
        size = frame * count
        with self._buffer(stamp) as s, self._buffer(data) as d, self._buffer(size) as out:
            frame = self._check(
                self._call('cs_seal', s.ptr, d.ptr, len(data), split, count, out.ptr, size))
            raw = out.read(size)
        return [raw[i:i + frame] for i in range(0, size, frame)]

    def open(self, stamp, frames, split):
        """opens the data from frames sealed with the same stamp"""
        stamp = self._stamp(stamp)
        frames = list(frames)
        if not frames or len({len(f) for f in frames}) != 1:
            raise CodecError('frames must have the same size')
        data = b''.join(frames)
        with self._buffer(stamp) as s, self._buffer(data) as d, self._buffer(len(data)) as out:
            size = self._check(self._call(
                'cs_open', s.ptr, d.ptr, len(frames[0]), len(frames), split, out.ptr, len(data)))
            return out.read(size)

    # -----------------------------------------------------------------------------------
    # helpers
    # -----------------------------------------------------------------------------------
    def _stamp(self, stamp):
        stamp = bytes(stamp)
        if len(stamp) != self.stamp_size:
            raise StampError(f'a stamp has {self.stamp_size} bytes, got {len(stamp)}')
        return stamp

    def _call(self, name, *args):
        return self._fn[name](self._store, *args)

    def _check(self, result):
        if result < 0:
            kind, message = self._ERRORS.get(result, (CodecError, f'error {result}'))
            raise kind(message)
        return result

    def _buffer(self, init):
        return _Buffer(self, init)


class _Buffer:
    """block of the wasm memory, initialized with bytes or sized with an int"""

    def __init__(self, codec, init):
        self._codec = codec
        self._size = init if isinstance(init, int) else len(init)
        self.ptr = codec._call('cs_alloc', self._size)
        if not self.ptr:
            raise MemoryError('wasm allocation failed')
        if not isinstance(init, int) and init:
            codec._memory.write(codec._store, bytes(init), self.ptr)

    def read(self, size):
        return bytes(self._codec._memory.read(self._codec._store, self.ptr, self.ptr + size))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._codec._call('cs_free', self.ptr)
