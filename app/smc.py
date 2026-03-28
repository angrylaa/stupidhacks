"""
Reads lid state from the AppleSMC IOKit driver via ctypes.

On M1 Pro, MSLD usually returns a binary flag (0=closed, 1=open).
On some firmware versions it returns a continuous value that we map to degrees.
The reader auto-classifies the data type from the SMC's own type field.
"""
import ctypes
import ctypes.util
import struct
from dataclasses import dataclass
from typing import Optional

# ── IOKit framework ────────────────────────────────────────────────────────────

_iokit = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
_libc  = ctypes.CDLL("/usr/lib/libSystem.B.dylib")

_iokit.IOServiceGetMatchingService.restype  = ctypes.c_uint32
_iokit.IOServiceGetMatchingService.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
_iokit.IOServiceMatching.restype            = ctypes.c_void_p
_iokit.IOServiceMatching.argtypes           = [ctypes.c_char_p]
_iokit.IOServiceOpen.restype                = ctypes.c_int
_iokit.IOServiceOpen.argtypes               = [ctypes.c_uint32, ctypes.c_uint32,
                                               ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
_iokit.IOServiceClose.restype               = ctypes.c_int
_iokit.IOServiceClose.argtypes              = [ctypes.c_uint32]
_iokit.IOObjectRelease.restype              = ctypes.c_int
_iokit.IOObjectRelease.argtypes             = [ctypes.c_uint32]
_iokit.IOConnectCallStructMethod.restype    = ctypes.c_int
_iokit.IOConnectCallStructMethod.argtypes   = [
    ctypes.c_uint32,                       # connection
    ctypes.c_uint32,                       # selector
    ctypes.c_void_p,                       # inputStruct
    ctypes.c_size_t,                       # inputStructCnt
    ctypes.c_void_p,                       # outputStruct
    ctypes.POINTER(ctypes.c_size_t),       # outputStructCnt
]

_libc.mach_task_self_.restype  = ctypes.c_uint32
_libc.mach_task_self_.argtypes = []

# ── SMC constants ──────────────────────────────────────────────────────────────

_IO_OBJECT_NULL      = 0
_kIOReturnSuccess    = 0
_kSMCHandleYPCEvent  = 2
_kSMCGetKeyInfo      = 9
_kSMCReadKey         = 5

# Four-char type codes as big-endian uint32
_TYPE_FLT  = struct.unpack(">I", b"flt ")[0]   # float
_TYPE_SP78 = struct.unpack(">I", b"sp78")[0]   # signed fixed-point 7.8
_TYPE_UI8  = struct.unpack(">I", b"ui8 ")[0]   # uint8
_TYPE_FLAG = struct.unpack(">I", b"flag")[0]   # boolean


# ── SMC struct (matches C natural-alignment layout exactly) ───────────────────

class _SMCVersion(ctypes.Structure):
    _fields_ = [("major", ctypes.c_uint8), ("minor", ctypes.c_uint8),
                ("build", ctypes.c_uint8), ("reserved", ctypes.c_uint8),
                ("release", ctypes.c_uint16)]

class _SMCPLimitData(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint16), ("length", ctypes.c_uint16),
                ("cpuPLimit", ctypes.c_uint32), ("gpuPLimit", ctypes.c_uint32),
                ("memPLimit", ctypes.c_uint32)]

class _SMCKeyInfoData(ctypes.Structure):
    _fields_ = [("dataSize", ctypes.c_uint32), ("dataType", ctypes.c_uint32),
                ("dataAttributes", ctypes.c_uint8)]

class _SMCKeyData(ctypes.Structure):
    _fields_ = [
        ("key",        ctypes.c_uint32),
        ("vers",       _SMCVersion),
        ("pLimitData", _SMCPLimitData),
        ("keyInfo",    _SMCKeyInfoData),
        ("result",     ctypes.c_uint8),
        ("status",     ctypes.c_uint8),
        ("data8",      ctypes.c_uint8),
        ("data32",     ctypes.c_uint32),
        ("bytes",      ctypes.c_uint8 * 32),
    ]

_STRUCT_SIZE = ctypes.sizeof(_SMCKeyData)


# ── Public API ─────────────────────────────────────────────────────────────────

@dataclass
class LidReading:
    kind:  str           # "angle" | "binary" | "unavailable"
    value: object = None # float (degrees) or bool


class SMCLidReader:
    def __init__(self):
        self._conn: ctypes.c_uint32 = ctypes.c_uint32(0)
        self._connected = False

    def connect(self) -> bool:
        matching = _iokit.IOServiceMatching(b"AppleSMC")
        service  = _iokit.IOServiceGetMatchingService(0, matching)  # 0 = kIOMainPortDefault
        if service == _IO_OBJECT_NULL:
            return False
        conn = ctypes.c_uint32(0)
        kr   = _iokit.IOServiceOpen(service, _libc.mach_task_self_(), 0, ctypes.byref(conn))
        _iokit.IOObjectRelease(service)
        if kr == _kIOReturnSuccess:
            self._conn      = conn
            self._connected = True
        return self._connected

    def disconnect(self):
        if self._connected:
            _iokit.IOServiceClose(self._conn)
            self._connected = False

    def read_lid_state(self) -> LidReading:
        if not self._connected:
            return LidReading("unavailable")
        raw = self._read_key("MSLD")
        if raw is None:
            return LidReading("unavailable")
        data, data_type, data_size = raw
        return self._parse(data, data_type, data_size)

    # ── Private ────────────────────────────────────────────────────────────────

    def _parse(self, data: bytes, data_type: int, data_size: int) -> LidReading:
        if data_type == _TYPE_FLT and data_size >= 4:
            # Big-endian IEEE 754 float from SMC
            f = struct.unpack(">f", data[:4])[0]
            angle = f if f > 1.5 else f * 180.0   # normalise 0-1 range to degrees
            return LidReading("angle", max(0.0, min(180.0, angle)))

        if data_type == _TYPE_SP78 and data_size >= 2:
            # Signed fixed-point 7.8 — divide by 256, scale to 180°
            raw = struct.unpack(">h", data[:2])[0]
            angle = (raw / 256.0) * 180.0
            return LidReading("angle", max(0.0, min(180.0, angle)))

        if data_type in (_TYPE_UI8, _TYPE_FLAG):
            return LidReading("binary", data[0] != 0)

        # Unknown type — guess from raw byte
        b = data[0]
        if b in (0, 1):
            return LidReading("binary", bool(b))
        return LidReading("angle", (b / 255.0) * 180.0)

    def _read_key(self, key: str):
        code = struct.unpack(">I", key.encode("ascii"))[0]

        # Step 1: get key info
        inp = _SMCKeyData()
        inp.key   = code
        inp.data8 = _kSMCGetKeyInfo
        out = self._call_smc(inp)
        if out is None or out.result != 0 or out.keyInfo.dataSize == 0:
            return None

        data_size = out.keyInfo.dataSize
        data_type = out.keyInfo.dataType

        # Step 2: read value
        inp2 = _SMCKeyData()
        inp2.key                = code
        inp2.keyInfo.dataSize   = data_size
        inp2.data8              = _kSMCReadKey
        out2 = self._call_smc(inp2)
        if out2 is None or out2.result != 0:
            return None

        raw_bytes = bytes(out2.bytes[:data_size])
        return raw_bytes, data_type, data_size

    def _call_smc(self, inp: _SMCKeyData) -> Optional[_SMCKeyData]:
        out      = _SMCKeyData()
        out_size = ctypes.c_size_t(_STRUCT_SIZE)
        kr = _iokit.IOConnectCallStructMethod(
            self._conn,
            _kSMCHandleYPCEvent,
            ctypes.byref(inp), _STRUCT_SIZE,
            ctypes.byref(out), ctypes.byref(out_size),
        )
        return out if kr == _kIOReturnSuccess else None
