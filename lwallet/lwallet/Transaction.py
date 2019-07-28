import copy
import hashlib
from io import BytesIO, StringIO
import random
import secp256k1
import struct

from coinapi import eelocal as eel
from lwallet import address, energi, ledger, script, serialize
from lwallet.serialize import ser_string, deser_string, ser_vector, deser_vector, b2hs, hs2b

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def sha256(s):
    return hashlib.new('sha256', s).digest()

def hash256(s):
    return sha256(sha256(s))

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

class COutPoint:
    def __init__(self, hashin = b'', n = 0):
        self.hash = hashin[::-1] # txid
        if len(self.hash) < 32:
            self.hash += b'\x00' * (32 - len(self.hash))
        self.n = n

    def serialize(self):
        return self.hash + struct.pack('<I', self.n)

    def deserialize(self, m):
        self.hash = m.read(32)
        self.n = struct.unpack('<I', m.read(4))[0]
        return self

    def __repr__(self):
        return 'COutPoint(hash = %s, n = %i)' % (b2hs(self.hash[::-1]), self.n)

class CTxIn:
    def __init__(self, outpoint = None, scriptSig = b'', nSequence = 0):
        self.prevout = COutPoint() if outpoint is None else outpoint
        self.scriptSig = scriptSig
        self.nSequence = nSequence

    def serialize(self):
        b = self.prevout.serialize()
        b += ser_string(self.scriptSig)
        b += struct.pack('<I', self.nSequence)
        return b

    def deserialize(self, m):
        self.prevout = COutPoint()
        self.prevout.deserialize(m)
        self.scriptSig = deser_string(m)
        self.nSequence = struct.unpack('<I', m.read(4))[0]
        return self

    def __repr__(self):
        return 'CTxIn(prevout = %s, scriptSig = %s, nSequence = %i)' % (repr(self.prevout), b2hs(self.scriptSig), self.nSequence)

class CTxOut:
    def __init__(self, nValue = 0, scriptPubKey = b''):
        self.nValue = nValue
        self.scriptPubKey = scriptPubKey

    def serialize(self):
        return struct.pack('<q', self.nValue) + ser_string(self.scriptPubKey)

    def deserialize(self, m):
        self.nValue = struct.unpack('<q', m.read(8))[0]
        self.scriptPubKey = deser_string(m)
        return self

    def __repr__(self):
        _NRGSAT = 10**8
        return 'CTxOut(nValue = %i.%08i, scriptPubKey = %s)' % (self.nValue // _NRGSAT, self.nValue % _NRGSAT, b2hs(self.scriptPubKey))

class CTransaction:
    def __init__(self, tx = None):
        if tx is None:
            self.nVersion = 1
            self.vin = []
            self.vout = []
            self.nLockTime = 0
            self.sha256 = None
            self.hash = None
        else:
            self.nVersion = tx.nVersion
            self.vin = copy.deepcopy(tx.vin)
            self.vout = copy.deepcopy(tx.vout)
            self.nLockTime = tx.nLockTime
            self.sha256 = tx.sha256
            self.hash = tx.hash

    def serialize(self):
        b = struct.pack('<i', self.nVersion)
        b += ser_vector(self.vin)
        b += ser_vector(self.vout)
        b += struct.pack('<I', self.nLockTime)
        return b

    def deserialize(self, m):
        self.nVersion = struct.unpack('<i', m.read(4))[0]
        self.vin = deser_vector(m, CTxIn)
        self.vout = deser_vector(m, CTxOut)
        self.nLockTime = struct.unpack('<I', m.read(4))[0]
        self.hash256 = None
        self.hash = None
        return self

    def rehash(self):
        self.calc_sha256()

    def calc_sha256(self):
        self.hash256 = hash256(self.serialize())
        self.hash = b2hs(self.hash256) # for display purposes

    def __repr__(self):
        return 'CTransaction(nVersion = %i, vin = %s, vout = %s, nLockTime = %i)' % (self.nVersion, repr(self.vin), repr(self.vout), self.nLockTime)

#----#----#----#----#----#----#----#----#----#----#----#----#----#----#----#

_hashtype_d = {
    'SIGHASH_ALL': 1,
    'SIGHASH_NONE': 2,
    'SIGHASH_SINGLE': 3,
    'SIGHASH_ANYONECANPAY': 0x80,
    'all and anyone': 0x81,
    'none and anyone': 0x82,
    'single and anyone': 0x83
}
_hashtype_rev_d = { _hashtype_d[k]: k for k in _hashtype_d.keys() }

def signature_hash(script_code, txto, inIdx, hashtype):
    if inIdx >= len(txto.vin):
        raise RuntimeError('input index out of range (%d >= %d)' % (i, len(txto.vin)))

    txtmp = CTransaction(txto)

    for i in range(len(txtmp.vin)):
        if i != inIdx:
            txtmp.vin[i].scriptSig = b''
    txtmp.vin[inIdx].scriptSig = script.remove(script_code, [script.get_opcode('OP_CODESEPARATOR')])

    if (hashtype & 0x1f) == _hashtype_d['SIGHASH_NONE']:
        txtmp.vout = []
        for i in range(len(txtmp.vin)):
            if i != inIdx:
                txtmp.vin[i].nSequence = 0

    elif (hashtype & 0x1f) == _hashtype_d['SIGHASH_SINGLE']:
        outIdx = inIdx
        if outIdx >= len(txtmp.vout):
            raise RuntimeError('output index out of range (%d >= %d)' % (outIdx, len(txtmp.vout)))

        tmp = txtmp.vout[outIdx]
        txtmp.vout = []
        for i in range(outIdx):
            txtmp.vout.append(CTxOut(-1))
        txtmp.vout.append(tmp)

        for i in range(len(txtmp.vin)):
            if i != inIdx:
                txtmp.vin[i].nSequence = 0

    if hashtype & _hashtype_d['SIGHASH_ANYONECANPAY']:
        txtmp.vin = [txtmp.vin[inIdx]]

    s = txtmp.serialize()
    s += struct.pack(b'<I', hashtype)

    return hash256(s)

def verify_tx(tx_in, prevout_d = {}):
    tx = CTransaction(tx_in)

    if len(tx.vin) == 0:
        return False

    # check each input signature
    for i in range(len(tx.vin)):

        # get the signature, hash type, and public key (from the standard P2PKH)
        sd = script.disass(tx.vin[i].scriptSig)
        if len(sd) != 2 or (sd[0]['opcode'] != 72 and sd[0]['opcode'] != 71) or (sd[1]['opcode'] != 33 and sd[1]['opcode'] != 65):
            raise RuntimeError('vin[%d] not standard P2PKH; %s' % (i, sd))

        signature = sd[0]['data']
        hashtype = signature[-1]
        signature = signature[:-1]
        public_key = sd[1]['data']

        if hashtype not in _hashtype_rev_d.keys():
            raise RuntimeError('hashtype in signature not recognized')

        # get the txid for the output this input refers to
        txid = serialize.b2hs(tx.vin[i].prevout.hash[::-1])

        # get the transaction from prevout dictionary or energid if not provided
        tx_i_hex = prevout_d[txid]['hex'] if txid in prevout_d else eel.get_hex_transaction(txid)
        tx_i = CTransaction().deserialize(BytesIO(serialize.hs2b(tx_i_hex)))

        n = tx.vin[i].prevout.n
        vout = tx_i.vout[n]

        vout_spkd = script.disass(vout.scriptPubKey)
        vout_hpk = vout_spkd[2]['data']

        hpk = energi.hash160(public_key)
        if hpk != vout_hpk:
            raise RuntimeError('OP_EQUALVERIFY failed: %s != %s' % (serialize.b2hs(hpk), serialize.b2hs(vout_hpk)))

        sighash = signature_hash(vout.scriptPubKey, tx_in, i, hashtype)
        pubkey = secp256k1.PublicKey(public_key, raw = True)
        sig = pubkey.ecdsa_deserialize(signature)

        if not pubkey.ecdsa_verify(sighash, sig, raw = True):
            return False

    # check output address for each
    #for i in range(len(tx.vout)):
    #    if not script.is_standard(tx.vout[i].scriptPubKey):
    #        print('vout[%d] is not standard' % i)
    #        continue
    #
    #    sd = script.disass(tx.vout[i].scriptPubKey)
    #    pkh = sd[2]['data']
    #    addr = energi.address_repr(pkh)

    return True

def sign_tx(tx_in, address_d, change_path = None, txid_d = None):
    tx = CTransaction(tx_in)

    # First, we need a trusted input blob for each vin[i].
    til = []
    for i in range(len(tx.vin)):
        d = {}

        # get the txid for the output this input refers to
        txid = tx.vin[i].prevout.hash
        txid_hs = serialize.b2hs(txid[::-1])

        # and the index into vout
        n = tx.vin[i].prevout.n

        # get the transaction from energid
        tx_i_hex = eel.get_hex_transaction(txid_hs) if txid_d is None else txid_d[txid_hs]['hex']
        tx_i = CTransaction().deserialize(BytesIO(serialize.hs2b(tx_i_hex)))

        # save scriptPubKey for later
        d['scriptPubKey'] = tx_i.vout[n].scriptPubKey

        # we'll send this in chunks; the first includes up to vin len
        buf = struct.pack('<i', tx_i.nVersion) + serialize.ser_compact_size(len(tx_i.vin))
        r = ledger.call_get_trusted_input_first(n, buf)
        if r != b'':
            raise RuntimeError('get_trusted_input_first: %s' % r)

        # now send vin
        for j in range(len(tx_i.vin)):
            buf = tx_i.vin[j].serialize()
            r = ledger.call_get_trusted_input_next(buf)
            if r != b'':
                raise RuntimeError('get_trusted_input_next: %s' % r)

        # send len of vout and vout[0]
        buf = serialize.ser_compact_size(len(tx_i.vout)) + tx_i.vout[0].serialize()
        r = ledger.call_get_trusted_input_next(buf)
        if r != b'':
            raise RuntimeError('get_trusted_input_next (0): %s' % (r))

        # send the rest of vout
        for j in range(1, len(tx_i.vout)):
            buf = tx_i.vout[j].serialize()
            r = ledger.call_get_trusted_input_next(buf)
            if r != b'':
                raise RuntimeError('get_trusted_input_next (%d): %s' % (j, r))

        # send locktime
        buf = struct.pack('<I', tx_i.nLockTime)
        r = ledger.call_get_trusted_input_next(buf)
        if r == b'':
            raise RuntimeError('bad trusted input response')

        d['tib'] = r
        til.append(d)

    # Second, we need a signature to put in each vin[i].scriptSig.
    sigs = []
    for i in range(len(tx.vin)):
        tx_i = CTransaction(tx)
        for v in tx_i.vin:
            v.scriptSig = b''
        tx_i.vin[i].scriptSig = til[i]['scriptPubKey']

        # get (hash160) public key we need to sign with
        if not script.is_standard(til[i]['scriptPubKey']):
            raise RuntimeError('we can only include P2PKH transactions')

        sd = script.disass(til[i]['scriptPubKey'])

        # save for later
        hpubkey = sd[2]['data']

        # again, we'll send the transaction in chunks
        buf = struct.pack('<i', tx_i.nVersion) + serialize.ser_compact_size(len(tx_i.vin)) + bytes([1, len(til[0]['tib'])]) + til[0]['tib'] + serialize.ser_string(tx_i.vin[0].scriptSig) + struct.pack('<I', tx_i.vin[0].nSequence)
        r = ledger.call_hash_input_start_first(buf)
        if b'' != r:
            raise RuntimeError('hash_input_start_first: %s' % r)

        for j in range(1, len(tx_i.vin)):
            buf = bytes([1, len(til[j]['tib'])]) + til[j]['tib'] + serialize.ser_string(tx_i.vin[j].scriptSig) + struct.pack('<I', tx_i.vin[j].nSequence)
            r = ledger.call_hash_input_start_next(buf)
            if b'' != r:
                raise RuntimeError('hash_input_start_next: %s' % r)

        # okay, all the inputs have been given; now the outputs
        buf = serialize.ser_vector(tx_i.vout)
        bufl = [buf[x:x + 200] for x in range(0, len(buf), 200)] # can be broken up arbitrarily

        # everything but the very last one
        for b in bufl[:-1]:
            r = ledger.call_hash_input_finalize_full(b)
            if b'' != r:
                raise RuntimeError('hash_input_finalize_full: %s' % r)

        # register the change path if we have it
        if change_path is not None:
            r = ledger.call_hash_input_finalize_full_change(change_path)
            if b'' != r:
                raise RuntimeError('hash_input_finalize_full_change: %s' % r)

        # now the last part of the outputs
        r = ledger.call_hash_input_finalize_full_last(bufl[-1])
        if r != bytearray(b'\x00\x00'):
            raise RuntimeError('hash_input_finalize_full: %s' % r)

        # get the address path for the given hashed pubkey
        addr = energi.address_repr(hpubkey)
        keypath = energi.serialize_pathd(address_d[addr])

        # now sign
        buf = serialize.hs2b(keypath) + b'\x00' + struct.pack('>I', tx_i.nLockTime) + bytes([_hashtype_d['SIGHASH_ALL']])
        r = ledger.call_hash_sign(buf) # last byte is hashtype

        # save for scriptSig
        pubkey = address_d[addr]['pubkey'] if 'pubkey' in address_d[addr] else address_d[addr]['public_key']
        if energi.hash160(pubkey) != hpubkey:
            pubkey = energi.compress_public_key(pubkey)
            if energi.hash160(pubkey) != hpubkey:
                raise RuntimeError('address confusion')
        sigs.append({'signature': r, 'pubkey': pubkey})

    # Finally, everything should be signed.  Construct scriptSig for each vin
    for i in range(len(tx.vin)):
        tx.vin[i].scriptSig = script.standard_scriptsig(sigs[i]['signature'], sigs[i]['pubkey'])

    return tx

def create_tx(address_to, value_sats, addr_d, fee_minimum = 0):
    # fee_minimum is in Sats
    _NRGSAT = 10**8

    # extract utxos from addr_d (not from the change address though)
    utxol = []
    for a in addr_d:
        if 'change' != a and 'utxos' in addr_d[a]:
            for u in addr_d[a]['utxos']:
                utxol.append(u)

    # calculate transfer amounts
    fee_est = eel.get_fee_estimate() * _NRGSAT
    if fee_est < fee_minimum:
        fee_est = fee_minimum
    fee_amt = int(fee_est)
    balance = sum([u['satoshis'] for u in utxol])
    send_amt = value_sats if value_sats is not None else balance - fee_amt

    # Use as many unspent txs as we need
    amt = 0
    ul = []
    for u in utxol:
        ul.append(u)
        amt += u['satoshis']
        if amt >= send_amt + fee_amt: # assuming 1kB tx
            break

    if amt < send_amt + fee_amt:
        raise RuntimeError('error: wallet balance insufficient: %d' % amt)

    # build transaction
    tx = CTransaction()
    tx.vin = []
    for u in ul:
        h = serialize.hs2b(u['txid'])
        op = COutPoint(h, u['nout'])
        tx.vin.append(CTxIn(outpoint = op, nSequence = 2**32 - 1))

    # randomize input order (somewhat)
    random.shuffle(tx.vin)

    txout = CTxOut(send_amt, script.standard_p2pkh_pkh(energi.decode_address(address_to)))
    tx.vout = [txout]

    change_path = None
    if send_amt + fee_amt < amt:
        change_pubkey = energi.compress_public_key(addr_d['change']['public_key'])
        change_out = CTxOut(amt - (send_amt + fee_amt), script.standard_p2pkh(change_pubkey))
        tx.vout.append(change_out)
        change_path = energi.serialize_pathd(addr_d['change'])

    # randomize output order (somewhat)
    random.shuffle(tx.vout)

    txs = sign_tx(tx, address_d = addr_d, change_path = change_path)

    if not verify_tx(txs):
        raise RuntimeError('transaction did not verify')

    return txs.serialize()

