import base58
import hashlib

NRG_COIN_ID = b'\x21' # first character in encoded address

# -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- #

def compress_public_key(pk):
    if len(pk) not in (33, 65):
        raise RuntimeError('public key length bad: %s (%d)' % (pk, len(pk)))
    if len(pk) == 33:
        return pk[0:33]
    if pk[64] & 1:
        return b'\x03' + pk[1:33]
    return b'\x02' + pk[1:33]

def hash160(public_key):
    h_sha = hashlib.new('sha256')
    h_sha.update(public_key)

    h_rip = hashlib.new('ripemd160')
    h_rip.update(h_sha.digest())

    return h_rip.digest()

def address_repr(h, coin_id = NRG_COIN_ID):
    vhpk = coin_id + h
    crc = hashlib.sha256(hashlib.sha256(vhpk).digest()).digest()[:4]
    return base58.b58encode(vhpk + crc)

def encode_address(public_key, coin_id = NRG_COIN_ID):
    return address_repr(hash160(public_key), coin_id)

def check_address(address):
    d = base58.b58decode(address)
    vhpk = d[:-4]
    crc = d[-4:]
    t_crc = hashlib.sha256(hashlib.sha256(vhpk).digest()).digest()[:4]

    return crc == t_crc

def decode_address(address, ret_version = False):
    d = base58.b58decode(address)
    vhpk = d[:-4]
    crc = d[-4:]
    t_crc = hashlib.sha256(hashlib.sha256(vhpk).digest()).digest()[:4]

    if crc != t_crc:
        raise RuntimeError('bad address: %s' % address)

    return vhpk[1:] if not ret_version else (vhpk[1:], vhpk[0])


# -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- #

# m / 44' / 9797' / account' / change / index
# XXX old account was 19781
def create_pathd(purpose = 44, coin = 9797, account = 0, change = 0, index = 0):
    return {'purpose': purpose, 'coin': coin, 'account': account, 'change': change, 'index': index}

def serialize_pathd(path):
    path_len = 5
    hs = '%2.2x' % path_len
    hs += '%8.8x' % ((path['purpose'] if 'purpose' in path else 44) | 0x80000000)
    hs += '%8.8x' % ((path['coin'] if 'coin' in path else 9797) | 0x80000000)
    hs += '%8.8x' % (path['account'] | 0x80000000)
    hs += '%8.8x' % path['change']
    hs += '%8.8x' % path['index']
    return hs

