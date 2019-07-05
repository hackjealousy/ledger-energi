#!/usr/bin/env python3

#
# Copyright 2018, 2019 Joshua Lackey
#

import requests

_last_error = None

# URL
_prefix = 'https://explore.energi.network'

# URN
_get_tx         = '/api/getrawtransaction?txid=%s&decrypt=1'
_get_address    = '/ext/getaddress/' # address
_get_balance    = '/ext/getbalance/' # address


def _get(q):
    global _last_error

    try:
        r = requests.get(q).json()
    except Exception as e:
        _last_error = 'error: requested: %s; %s' % (q, str(e))
        return None
    return r

def get_last_error():
    return _last_error

def get_tx(txid):
    return _get(_prefix + _get_tx % txid)

def get_address(a):
    return _get(_prefix + _get_address + a)

def get_balance(a):
    return _get(_prefix + _get_balance + a)

