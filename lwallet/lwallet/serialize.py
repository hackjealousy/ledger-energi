import copy
import hashlib
import io
import struct

# NOTE: ser and deser are le unless they are appended with be

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def b2hs(b):
    return u''.join([u'%2.2x' % c for c in b])

def b2s(b):
    return u''.join([u'%c' % c for c in b])

def hs2b(hs):
    return bytes([int(hs[x:x + 2], 16) for x in range(0, len(hs), 2)])

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def ser_compact_size(l):
    if l < 253:
        return struct.pack('B', l)
    if l < 0x10000:
        return struct.pack('<BH', 253, l)
    if l < 0x100000000:
        return struct.pack('<BI', 254, l)
    return struct.pack('<BQ', 255, l)

def deser_compact_size(m):
    t = struct.unpack('<B', m.read(1))[0]
    if t == 253:
        return struct.unpack('<H', m.read(2))[0]
    if t == 254:
        return struct.unpack('<I', m.read(4))[0]
    if t == 255:
        return struct.unpack('<Q', m.read(8))[0]
    return t

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

'''
    uint256 - opaque blob of 256 bits with no arithmetic ops

    template <unsigned int BITS> class base_blob
    class uin256 : public base_blob<256>

    base_blob serialize and unserialize copy data directly from the
    uint8_t buffer but GetHex returns the data reversed.
'''

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def ser_uint256(b):
    if len(b) < 32:
        b = (b + b'\x00' * (32 - len(b)))[:32]
    return b

def deser_uint256(m):
    return m.read(32)

def ser_uint128(b):
    if len(b) != 16:
        b = (b + b'\x00' * (16 - len(b)))[:16]
    return b

def deser_uint128(m):
    return m.read(16)

def ser_int64(i):
    return struct.pack('<q', i)

def deser_int64(m):
    return struct.unpack('<q', m.read(8))[0]

def ser_uint32(u):
    return struct.pack('<I', u)

def deser_uint32(m):
    return struct.unpack('<I', m.read(4))[0]

def ser_int32(n):
    return struct.pack('<i', n)

def deser_int32(m):
    return struct.unpack('<i', m.read(4))[0]

def ser_uint16(u):
    return struct.pack('<H', u)

def deser_uint16(m):
    return struct.unpack('<H', m.read(2))[0]

def ser_bool(b):
    return b'\x01' if b else b'\x00'

def deser_bool(m):
    return True if m.read(1) == b'\x01' else False

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def ser_string(s):
    return ser_compact_size(len(s)) + s

def deser_string(m):
    return m.read(deser_compact_size(m))

def ser_vector(v):
    return ser_compact_size(len(v)) + b''.join([e.serialize() for e in v])

def deser_vector(m, c):
    return [c().deserialize(m) for i in range(deser_compact_size(m))]

def ser_map_uint256_int(d):
    return ser_compact_size(len(d)) + b''.join([ser_uint256(k) + ser_int32(d[k]) for k in d])

def deser_map_uint256_int(m):
    return dict([(deser_uint256(m), deser_int32(m)) for i in range(deser_compact_size(m))])


# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def from_hex(obj, hs):
    obj.deserialize(io.BytesIO(hs2b(hs)))
    return obj

def to_hex(obj):
    return b2hs(obj.serialize())

