#!/usr/bin/env python3.7

import io
import secp256k1
import time
import sys

from coinapi import eelocal as eel
from lwallet import address, energi, ledger, serialize, walletdb, Masternode, Transaction

def basename(p):
    return p[p.rfind('/') + 1:] if '/' in p else p

def parse_conf(fn):
    with open(fn) as f:
        confl = f.read()

    confl = [l for l in confl.splitlines() if not l.strip().startswith('#')]
    r = []
    for l in confl:
        mne = l.split()
        if len(mne) != 5:
            raise RuntimeError('bad conf line: %s' % l)
        r.append({'alias': mne[0], 'ip': mne[1], 'mn_privkey': mne[2], 'txid': mne[3], 'nout': int(mne[4])})
    return r

def parse_ipport(ipp):
    ip, port = ipp.split(':')
    ipb = bytes([int(x) for x in ip.split('.')])

    # check this is ipv4
    if len(ipb) != 4:
        raise RuntimeError('we only handle IPv4 at this point')

    # ipv4 in ipv6
    ipb = b'\x00' * 10 + b'\xff' * 2 + ipb

    return Masternode.CService(ipb, int(port))

def create_mnb(mne):
    collat_outpoint = Transaction.COutPoint(serialize.hs2b(mne['txid']), mne['nout'])

    mnp = Masternode.CMasternodePing(collat_outpoint)
    mn_privkey = energi.decode_address(mne['mn_privkey'])
    block_hash = Masternode.get_block_hash()
    mnp.sign(block_hash, mn_privkey)

    mnb = Masternode.CMasternodeBroadcast()
    mnb.outpoint = collat_outpoint
    mnb.addr = parse_ipport(mne['ip'])

    mn_private_key = secp256k1.PrivateKey(mn_privkey, raw = True)
    mn_public_key = mn_private_key.pubkey.serialize(compressed = False)

    co_ae = walletdb.get_addr_txid(mne['txid'], mne['nout'])
    if co_ae is None:
        raise RuntimeError('cannot find address for txid: %s' % mne['txid'])
    co_public_key = co_ae['pubkey']

    mnb.pubkey_collateral = energi.compress_public_key(co_public_key)
    mnb.pubkey_masternode = mn_public_key

    mnb.last_ping = mnp

    print('Signing on ledger:')
    mnb.hw_sign(energi.serialize_pathd(co_ae))

    print('MasternodeBroadcast:\n%s' % mnb)
    return mnb

def decode(smnb_hs):
    mnb_l = serialize.deser_vector(io.BytesIO(serialize.hs2b(smnb_hs)), Masternode.CMasternodeBroadcast)
    for mnb in mnb_l:
        print('verify: %s' % mnb.verify())

def main():
    if len(sys.argv) < 2:
        print('usage: %s <masternode.conf>' % basename(sys.argv[0]))
        sys.exit(0)

    mn_l = parse_conf(sys.argv[1])
    mnb_l = []
    for mne in mn_l:
        mnb_l.append(create_mnb(mne))
        walletdb.lock_txid(mne['txid'], mne['nout'])

    smnb = serialize.ser_vector(mnb_l)
    smnb_hs = serialize.b2hs(smnb)
    decode(smnb_hs)

    print('checking with energid:')
    print(eel.mnb_decode(smnb_hs))

    input('Press enter to relay announcement or ^C to abort.')
    print(eel.mnb_relay(smnb_hs))


if __name__ == '__main__':
    main()
