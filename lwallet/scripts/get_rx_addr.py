#!/usr/bin/env python3.7

import sys

from lwallet import address, energi, serialize, walletdb

def get_address_at(index):
    ae = energi.create_pathd(index = index)
    sys.stdout.write('Getting address from ledger...  '); sys.stdout.flush()
    ae = address.get_address(ae, display = True)
    print('\nAddress: %(address)s (path: %(path)s)' % ae)
    walletdb.put_address_db(ae['address'], pubkey = ae['public_key'], pkh = energi.hash160(energi.compress_public_key(ae['public_key'])),
      account = ae['account'], index = ae['index'], change = ae['change'])
    return ae

def get_next_unused():
    sys.stdout.write('Getting address from ledger...  '); sys.stdout.flush()
    addr_e = address.get_next_unused()[0]
    addr = addr_e['address']
    path = addr_e['path']
    print('\nAddress: %s (path: %s)' % (serialize.b2s(addr), path))
    return addr_e

if len(sys.argv) > 1:
    get_address_at(int(sys.argv[1]))
else:
    get_next_unused()
