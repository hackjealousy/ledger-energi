#!/usr/bin/env python3.7

import sys

from lwallet import walletdb

addr_d = walletdb.get_address_d()

tot = 0
for k in addr_d:
    ae = addr_d[k]
    path = 'm/44\'/9797\'/%(account)d\'/%(change)d/%(index)d' % ae

    for u in ae.get('utxos', []):
        tot += u['satoshis']

        print('%s: %s: %f %s' % (path, u['address'], float(u['satoshis']) / 10**8, '(LOCKED)' if walletdb.is_locked_txid(u['txid'], u['nout']) else ''))

print('Total: %f' % (float(tot) / 10**8))
