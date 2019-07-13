import base58
import io
import secp256k1
import socket
import time

from coinapi import eelocal as eel
from lwallet import energi, ledger, serialize, Transaction
from lwallet.serialize import b2hs, hs2b

_PROTOCOL_VERSION = 70212

#----#----#----#----#----#----#----#----#----#----#----#----#----#----#----#

def get_block_hash(n = 12):
    return serialize.hs2b(eel.get_blockhash(eel.get_blockcount() - n))

#----#----#----#----#----#----#----#----#----#----#----#----#----#----#----#

def verify_sig(msg_b, sig_s, raw = True):
    hash_b = msg_b if raw else Transaction.hash256(msg_b)

    recid = (sig_s[0] - 27) & 0x3
    sig_b = sig_s[1:]
    empty = secp256k1.PublicKey(raw = True, flags = secp256k1.ALL_FLAGS)
    sig = empty.ecdsa_recoverable_deserialize(sig_b, recid)
    pubkey_r = empty.ecdsa_recover(hash_b, sig, raw = True)
    pubkey = secp256k1.PublicKey(pubkey_r, flags = secp256k1.ALL_FLAGS)
    new_sig = pubkey.ecdsa_recoverable_convert(sig)

    return pubkey.ecdsa_verify(hash_b, new_sig, raw = True)

def sign(privkey_b, msg_b, raw = True):
    hash_b = msg_b if raw else Transaction.hash256(msg_b)

    private_key = secp256k1.PrivateKey(privkey = privkey_b, raw = True)
    signature = private_key.ecdsa_sign_recoverable(hash_b, raw = True)
    sig, recid = private_key.ecdsa_recoverable_serialize(signature)

    is_compressed = False
    r = bytes([27 + recid + (4 if is_compressed else 0)]) + sig

    if not verify_sig(hash_b, r):
        raise RuntimeError('could not verify signature')

    return r

def hw_sign(keypath, msg_b):
    ledger_sig, recid = ledger.call_sign_mnb(keypath, msg_b, recoverable = True)
    pubkey = secp256k1.PublicKey(raw = True, flags = secp256k1.ALL_FLAGS)
    compact_sig = pubkey.ecdsa_serialize_compact(pubkey.ecdsa_deserialize(ledger_sig))

    is_compressed = True
    recoverable_sig = bytes([27 + recid + (4 if is_compressed else 0)]) + compact_sig

    if not verify_sig(msg_b, recoverable_sig, raw = False):
        raise RuntimeError('could not verify signature')

    return recoverable_sig

#----#----#----#----#----#----#----#----#----#----#----#----#----#----#----#

class CMasternodePing:
    def __init__(self, mn_outpoint = None):
        self.mn_outpoint = mn_outpoint if mn_outpoint is not None else Transaction.COutPoint()
        self.block_hash = b'\x00' * 32
        self.sig_time = -1
        self.vchSig = b''
        self.fSentinelIsCurrent = True
        self.nSentinelVersion = 0x010001
        self.nDaemonVersion = 120200

    def serialize(self, SER_GETHASH = False):
        r = self.mn_outpoint.serialize()
        r += serialize.ser_uint256(self.block_hash)
        r += serialize.ser_int64(self.sig_time)
        if not SER_GETHASH:
            r += serialize.ser_string(self.vchSig)
        r += serialize.ser_bool(self.fSentinelIsCurrent)
        r += serialize.ser_uint32(self.nSentinelVersion)
        r += serialize.ser_uint32(self.nDaemonVersion)
        return r

    def deserialize(self, m):
        self.masternode_output = Transaction.COutPoint().deserialize(m)
        self.block_hash = serialize.deser_uint256(m)
        self.sig_time = serialize.deser_int64(m)
        self.vchSig = serialize.deser_string(m)
        self.fSentinelIsCurrent = serialize.deser_bool(m)
        self.nSentinelVersion = serialize.deser_uint32(m)
        self.nDaemonVersion = serialize.deser_uint32(m)
        return self

    def get_hash(self):
        self.hash = Transaction.hash256(self.serialize(True))
        return self.hash

    def sign(self, block_hash, mn_privkey_b):
        self.block_hash = block_hash
        self.sig_time = int(time.time())
        self.vchSig = sign(mn_privkey_b, self.get_hash())
        return self.vchSig

    def __repr__(self):
        return 'CMasternodePing(mn_outpoint = %s, block_hash = %s, sig_time = %d, vchSig = %s, fSentinelIsCurrent = %s, nSentinelVersion = %x, nDaemonVersion = %d)' % \
          (self.mn_outpoint, b2hs(self.block_hash), self.sig_time, b2hs(self.vchSig), \
          self.fSentinelIsCurrent, self.nSentinelVersion, self.nDaemonVersion)


class CService:
    def __init__(self, ip = b'\x00' * 16, port = 0):
        self.ip = ip                                                # unsigned char ip[16];
        self.port = port; # host order                              # unsigned short port;

    def serialize(self):
        r = serialize.ser_uint128(self.ip)
        r += serialize.ser_uint16(socket.htons(self.port))
        return r

    def deserialize(self, m):
        self.ip = serialize.deser_uint128(m)
        self.port = socket.ntohs(serialize.deser_uint16(m))
        return self

    def __repr__(self):
        return 'CService(ip = %s, port = %d)' % ('.'.join(['%d' % c for c in self.ip[:4]]), self.port)


class SMasternodeInfo:
    def __init__(self):
        self.n_active_state = 0                                     # int nActiveState;
        self.n_protocol_version = _PROTOCOL_VERSION                 # int nProtocolVersion;
        self.sig_time = 0                                           # int64_t sigTime; // mnb message time
        self.outpoint = Transaction.COutPoint()                     # COutPoint outpoint;
        self.addr = CService()                                      # CService addr;
        self.pubkey_collateral = b''                                # CPubKey pubKeyCollateralAddress; (basically just a serialized pubkey)
        self.pubkey_masternode = b''                                # CPubKey pubKeyMasternode;
        self.n_last_dsq = 0 # dsq count from last dsq broadcast     # int64_t nLastDsq;
        self.n_time_last_checked = 0                                # int64_t nTimeLastChecked;
        self.n_time_last_paid = 0                                   # int64_t nTimeLastPaid;
        self.f_info_valid = False                                   # bool fInfoValid;


class CMasternode(SMasternodeInfo):
    def __init__(self, mn = None):
        if mn is not None and not isinstance(mn, CMasternode):
            raise RuntimeError('cannot initialize CMasternode with non-CMasternode object: %s' % (type(mn)))

        super().__init__()

        self.last_ping = CMasternodePing()                          # CMasternodePing lastPing;
        self.vchSig = b''                                           # vector<unsigned char> vchSig;
        self.n_collateral_hash = b'\x00' * 32                       # uint256 nCollateralMinConfBlockHash;
        self.n_block_last_paid = 0                                  # int nBlockLastPaid;
        self.n_po_se_ban_score = 0                                  # int nPoSeBanScore;
        self.n_po_se_ban_height = 0                                 # int nPoSeBanHeight;
        self.f_allow_mixing_tx = False                              # bool fAllowMixingTx;
        self.f_unit_test = False                                    # bool fUnitTest;
        self.gov_votes = {}                                         # map<uint256, int> mapGovernanceObjectsVotedOn;

        if mn is not None:
            return self.deserialize(io.BytesIO(mn.serialize()))

    def serialize(self, SER_GETHASH = False):
        r  = self.outpoint.serialize()
        r += self.addr.serialize()
        r += serialize.ser_string(self.pubkey_collateral)
        r += serialize.ser_string(self.pubkey_masternode)
        r += self.last_ping.serialize(SER_GETHASH)
        r += serialize.ser_string(self.vchSig)
        r += serialize.ser_int64(self.sig_time)
        r += serialize.ser_int64(self.n_last_dsq)
        r += serialize.ser_int64(self.n_time_last_checked)
        r += serialize.ser_int64(self.n_last_dsq)
        r += serialize.ser_int32(self.n_active_state)
        r += serialize.ser_uint256(self.n_collateral_hash)
        r += serialize.ser_int32(self.n_block_last_paid)
        r += serialize.ser_int32(self.n_protocol_version)
        r += serialize.ser_int32(self.n_po_se_ban_score)
        r += serialize.ser_int32(self.n_po_se_ban_height)
        r += serialize.ser_bool(self.f_allow_mixing_tx)
        r += serialize.ser_bool(self.f_unit_test)
        r += serialize.ser_map_uint256_int(self.gov_votes)
        return r

    def deserialize(self, m):
        self.outpoint = Transaction.COutPoint().deserialize(m)
        self.addr = CService().deserialize(m)
        self.pubkey_collateral = serialize.deser_string(m)
        self.pubkey_masternode = serialize.deser_string(m)
        self.last_ping = CMasternodePing().deserialize(m)
        self.vchSig = serialize.deser_string(m)
        self.sig_time = serialize.deser_int64(m)
        self.n_last_dsq = serialize.deser_int64(m)
        self.n_time_last_checked = serialize.deser_int64(m)
        self.n_last_dsq = serialize.deser_int64(m)
        self.n_active_state = serialize.deser_int32(m)
        self.n_collateral_hash = serialize.deser_uint256(m)
        self.n_block_last_paid = serialize.deser_int32(m)
        self.n_protocol_version = serialize.deser_int32(m)
        self.n_po_se_ban_score = serialize.deser_int32(m)
        self.n_po_se_ban_height = serialize.deser_int32(m)
        self.f_allow_mixing_tx = serialize.deser_bool(m)
        self.f_unit_test = serialize.deser_bool(m)
        self.gov_votes = serialize.deser_map_uint256_int(m)
        return self


class CMasternodeBroadcast(CMasternode):
    def __init__(self, mn = None):
        super().__init__(mn)

    def serialize(self, SER_GETHASH = False):
        r  = self.outpoint.serialize()
        r += self.addr.serialize()
        r += serialize.ser_string(self.pubkey_collateral)
        r += serialize.ser_string(self.pubkey_masternode)
        if not SER_GETHASH:
            r += serialize.ser_string(self.vchSig)
        r += serialize.ser_int64(self.sig_time)
        r += serialize.ser_int32(self.n_protocol_version)
        if not SER_GETHASH:
            r += self.last_ping.serialize(False)
        return r

    def deserialize(self, m):
        self.outpoint = Transaction.COutPoint().deserialize(m)
        self.addr = CService().deserialize(m)
        self.pubkey_collateral = serialize.deser_string(m)
        self.pubkey_masternode = serialize.deser_string(m)
        self.vchSig = serialize.deser_string(m)
        self.sig_time = serialize.deser_int64(m)
        self.n_protocol_version = serialize.deser_int32(m)
        self.last_ping = CMasternodePing().deserialize(m)
        return self

    def sign(self, privkey_collateral_b):
        self.sig_time = int(time.time())
        self.vchSig = sign(privkey_collateral_b, self.serialize(SER_GETHASH = True), raw = False)
        return self.vchSig

    def hw_sign(self, keypath_hs):
        self.sig_time = int(time.time())
        self.vchSig = hw_sign(keypath_hs, self.serialize(SER_GETHASH = True))
        return self.vchSig

    def verify(self):
        return verify_sig(self.serialize(SER_GETHASH = True), self.vchSig, raw = False)

    def __repr__(self):
        return 'CMasternodeBroadcast(outpoint = %s, addr = %s, pubkey_collateral = %s, pubkey_masternode = %s, ' \
          'vchSig = %s, sig_time = %d, n_protocol_version = %d, last_ping = %s)' % \
          (self.outpoint, self.addr, b2hs(self.pubkey_collateral), b2hs(self.pubkey_masternode), \
          b2hs(self.vchSig), self.sig_time, self.n_protocol_version, self.last_ping)

