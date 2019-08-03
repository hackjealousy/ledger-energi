#!/usr/bin/env python3.7

import sys

from lwallet import Masternode

def b2hs(b):
    return ''.join(['%2.2x' % c for c in b])

if len(sys.argv) > 1:
    pk, v = Masternode.decode_privkey(sys.argv[1])
    print('privkey: (version %d) %s' % (v, b2hs(pk)))
    sys.exit(0)

print(Masternode.generate_privkey())
