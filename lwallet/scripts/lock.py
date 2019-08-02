#!/usr/bin/env python3.7

import sys

from lwallet import walletdb

def get_locked():
    print('current locked:')
    for u in walletdb.get_all_locked():
        print('\t%(txid)s:%(nout)d' % u)

    print('should lock:')
    for u in walletdb.get_all_unspent():
        if u['satoshis'] == 1000000000000:
            print('\t%(txid)s:%(nout)d : %(satoshis)d' % u)


def basename(p):
    return p[p.rfind('/') + 1:] if '/' in p else p


def main():
    if len(sys.argv) <= 1:
        return get_locked()

    if len(sys.argv) <= 2:
        txid, nout = sys.argv[1].split(':')
        nout = int(nout)
    else:
        txid = sys.argv[1]
        nout = int(sys.argv[2])

    walletdb.lock_txid(txid, nout)

    get_locked()


if __name__ == '__main__':
    main()
