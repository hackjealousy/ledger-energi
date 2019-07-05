import base58
import hashlib
import sys
import struct

from ledgerblue.comm import getDongle
from ledgerblue.commException import CommException

# -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- #

DEBUG = False

# -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- #

class ledger_device:
    def __enter__(self):
        self.d = getDongle(debug = DEBUG)
        return self.d

    def __exit__(self, type, value, traceback):
        self.d.close()

# -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- #

def hs2b(hs):
    return bytes([int(hs[x:x + 2], 16) for x in range(0, len(hs), 2)])

def b2hs(b):
    return ''.join(['%2.2x' % c for c in b])

def get_apdu(a, debug = False):
    _asm_d = {
        'CLA'                           : 'e0',
        'INS_GET_COIN_VERSION'          : '16',
        'INS_SETUP'                     : '20',
        'INS_GET_OPERATION_MODE'        : '24',
        'INS_GET_WALLET_PUBLIC_KEY'     : '40',
        'INS_GET_RANDOM'                : 'c0',
        'INS_GET_TRUSTED_INPUT'         : '42',
        'INS_HASH_INPUT_START'          : '44',
        'INS_HASH_SIGN'                 : '48',
        'INS_HASH_INPUT_FINALIZE_FULL'  : '4a',
        'INS_SIGN_MNB'                  : '50',

        '|'                             : ''
    }
    for k in _asm_d.keys():
        while k in a:
            a = a.replace(k, _asm_d[k])
    if debug:
        print('debug apdu: %s' % a)
    return hs2b(a)

def call(a, debug = False):
    with ledger_device() as d:
        return d.exchange(get_apdu(a, debug))

# -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- # -- #

def call_get_operation_mode():
    return call('CLA|INS_GET_OPERATION_MODE|00')

def call_get_coin_version():
    return call('CLA|INS_GET_COIN_VERSION')

def call_get_random(len = 0):
    return call('CLA|INS_GET_RANDOM|0000|%2.2x' % (len))

def parse_get_wallet_public_key_response(bpk):
    pubkey_len = bpk[0]
    pubkey = bytes(bpk[1:1 + pubkey_len])

    return pubkey

def call_get_wallet_public_key(keypath, display):
    apdu = 'CLA|INS_GET_WALLET_PUBLIC_KEY|%2.2x|00|%2.2x|%s' % (display, int(len(keypath) / 2), keypath)
    return call(apdu)

def get_public_key(keypath, display = False):
    r = call_get_wallet_public_key(keypath, display)
    return parse_get_wallet_public_key_response(r)

def call_get_trusted_input_first(ninput, bs):
    P1_FIRST = '00'

    data = struct.pack('>I', ninput) + bs
    apdu = 'CLA|INS_GET_TRUSTED_INPUT|%s|00|%2.2x|%s' % (P1_FIRST, len(data), b2hs(data))
    return call(apdu)

def call_get_trusted_input_next(bs):
    P1_NEXT = '80'

    apdu = 'CLA|INS_GET_TRUSTED_INPUT|%s|00|%2.2x|%s' % (P1_NEXT, len(bs), b2hs(bs))
    return call(apdu)

def call_hash_input_start_first(bs):
    P1_FIRST = '00'
    P2_NEW = '00'
    apdu = 'CLA|INS_HASH_INPUT_START|%s|%s|%2.2x|%s' % (P1_FIRST, P2_NEW, len(bs), b2hs(bs))
    return call(apdu)

def call_hash_input_start_next(bs):
    P1_NEXT = '80'
    P2_CONTINUE = '80'
    apdu = 'CLA|INS_HASH_INPUT_START|%s|%s|%2.2x|%s' % (P1_NEXT, P2_CONTINUE, len(bs), b2hs(bs))
    return call(apdu)

def call_hash_input_finalize_full(bs):
    P1_MORE = '00'
    P1_LAST = '80'
    P1_CHANGEINFO = 'ff'
    P2_DEFAULT = '00'

    apdu = 'CLA|INS_HASH_INPUT_FINALIZE_FULL|%s|00|%2.2x|%s' % (P1_MORE, len(bs), b2hs(bs))
    return call(apdu)

def call_hash_input_finalize_full_last(bs):
    P1_MORE = '00'
    P1_LAST = '80'
    P1_CHANGEINFO = 'ff'
    P2_DEFAULT = '00'

    apdu = 'CLA|INS_HASH_INPUT_FINALIZE_FULL|%s|00|%2.2x|%s' % (P1_LAST, len(bs), b2hs(bs))
    return call(apdu)

def call_hash_input_finalize_full_change(path_hs):
    P1_CHANGEINFO = 'ff'
    P2_DEFAULT = '00'

    apdu = 'CLA|INS_HASH_INPUT_FINALIZE_FULL|%s|00|%2.2x|%s' % (P1_CHANGEINFO, int(len(path_hs) / 2), path_hs)
    return call(apdu)

def _parse_signature(sig, recoverable):
    recid = sig[0] & 3
    sig = bytes([sig[0] & 0xfc]) + sig[1:]
    return (sig, recid) if recoverable else sig

def call_hash_sign(bs, recoverable = False):
    apdu = 'CLA|INS_HASH_SIGN|00|00|%2.2x|%s' % (len(bs), b2hs(bs))
    return _parse_signature(call(apdu), recoverable)

def call_sign_mnb(keypath, mnb, recoverable = False):
    apdu = 'CLA|INS_SIGN_MNB|a5|5a|%2.2x|%s%s' % (int(len(keypath)/2) + len(mnb), keypath, b2hs(mnb))
    return _parse_signature(call(apdu), recoverable)

