#!/usr/bin/env python3.7

import io
import sys

from coinapi import eelocal as eel
from lwallet import address, energi, serialize, walletdb, Transaction

_NRGSAT = 10**8

def basename(p):
    return p[p.rfind('/') + 1:] if '/' in p else p

def txid_eq(a, b):
    return (a['txid'] == b['txid']) and (a['nout'] == b['nout'])

def extract_txid(a):
    return {'txid': a['txid'], 'nout': a['nout']}

def balance(addr_d):
    s = 0
    for a in addr_d.keys():
        if a == 'change':
            continue
        for u in addr_d[a].get('utxos', []):
            s += u.get('satoshis', 0)
    return s

def s2b(s):
    return bytes([ord(c) for c in s])

def main():
    if len(sys.argv) != 4:
        print('usage: %s <to> <send value sats; negative to send everything> <max num inputs>' % basename(sys.argv[0]))
        sys.exit(0)

    to = sys.argv[1]
    val = int(sys.argv[2])
    max_in = int(sys.argv[3])

    if not energi.check_address(to):
        raise RuntimeError('bad to address: %s' % to)

    if val < 0:
        val = None
        print('Sending ALL NRG to %s.' % (to))
    else:
        print('Sending %f NRG to %s.' % (val / _NRGSAT, to))

    addr_d = walletdb.get_address_d(with_change = True)

    bal = balance(addr_d)
    print('\nCurrent balance: %f NRG. (%d Sat)' % (bal / _NRGSAT, bal))

    print('Removing locked outputs.')
    count = 0
    for a in addr_d.keys():
        nul = []
        for u in addr_d[a].get('utxos', []):
            if not walletdb.is_locked_txid(u['txid'], u['nout']) and count < max_in:
                nul.append(u)
                count += 1
        addr_d[a]['utxos'] = nul
    bal = balance(addr_d)
    print('\nAvailable balance: %f NRG. (%d Sat)' % (bal / _NRGSAT, bal))

    print('Creating transaction.')
    used_inputs = []
    tx = Transaction.create_tx(to, val, addr_d, fee_minimum = 4096, used_inputs = used_inputs)
    print('\n\nTransaction: (%d) %s' % (len(tx), serialize.b2hs(tx)))

    sys.stdout.write('\nVerifying transaction with energid... '); sys.stdout.flush()
    print(eel.decode_raw_transaction(serialize.b2hs(tx)))

    input('\n\nVerified.  Press <enter> to transmit ^C to cancel.  ')

    txid = eel.send_raw_transaction(serialize.b2hs(tx))
    print('Transmitted.  Txid = %s' % (serialize.b2s(txid)))

    for u in used_inputs:
        walletdb.remove_unspent_db(u['txid'], u['nout'])

if __name__ == '__main__':
    main()
