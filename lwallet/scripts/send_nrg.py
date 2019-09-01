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

def main():
    if len(sys.argv) != 3:
        print('usage: %s <to> <send value sats; negative to send everything>' % basename(sys.argv[0]))
        sys.exit(0)

    to = sys.argv[1]
    val = int(sys.argv[2])

    if not energi.check_address(to):
        raise RuntimeError('bad to address: %s' % to)

    if val < 0:
        val = None
        print('Sending ALL NRG to %s.' % (to))
    else:
        print('Sending %f NRG to %s.' % (val / _NRGSAT, to))

    addr_d = walletdb.get_address_d(with_change = True)
    bal = walletdb.get_balance()
    print('\nCurrent balance: %f NRG.' % (bal / _NRGSAT))

    print('Removing locked outputs.')
    for a in addr_d:
        nul = []
        for u in addr_d[a].get('utxos', []):
            if not walletdb.is_locked_txid(u['txid'], u['nout']):
                nul.append(u)
            else:
                print('removing locked: %s' % u)
        addr_d[a]['utxos'] = nul

    sys.stdout.write('Creating transaction; confirm on ledger: '); sys.stdout.flush()
    tx = Transaction.create_tx(to, val, addr_d)
    print('\n\nTransaction: %s' % serialize.b2hs(tx))

    sys.stdout.write('\nVerifying transaction with energid... '); sys.stdout.flush()
    print(eel.decode_raw_transaction(serialize.b2hs(tx)))

    input('\n\nVerified.  Press <enter> to transmit ^C to cancel.  ')

    txid = eel.send_raw_transaction(serialize.b2hs(tx))
    print('Transmitted.  Txid = %s' % (serialize.b2s(txid)))

if __name__ == '__main__':
    main()
