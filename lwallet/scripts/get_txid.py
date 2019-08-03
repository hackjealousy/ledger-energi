#!/usr/bin/env python3.7

import sys

from coinapi import eelocal as eel

tx = eel.get_transaction(sys.argv[1])
print(tx)
