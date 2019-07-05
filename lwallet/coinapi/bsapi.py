#!/usr/bin/env python3

#
# Copyright 2019 Joshua Lackey
#

# Blockscout API

import os
import requests
import sys

_last_error = None

_prefix = 'https://blockscout.com/eth/mainnet/api'

def _query(module, name, address = None, txid = None, ca = None):
    q = '%s?module=%s&action=%s' % (_prefix, module, name)
    if address is not None:
        q += '&address=%s' % address
    if txid is not None:
        q += '&txhash=%s' % txid
    if ca is not None:
        q += '&contractaddress=%s' % ca
    return q

def _get(q):
    global _last_error

    r = requests.get(q)
    if r.status_code != 200:
        _last_error = 'error: query: %s; %s' % (q, r.text)
        return None
    jr = r.json()
    if jr['status'] != '1':
        _last_error = 'error: query: %s; returned: %s' % (q, jr)
        return None
    return jr['result']

def get_last_error():
    global _last_error

    r = _last_error
    _last_error = None
    return r

def get_balance(address):
    return _get(_query('account', 'balance', address))

def get_txlist(address):
    return _get(_query('account', 'txlist', address))

def get_txinfo(txid):
    return _get(_query('transaction', 'gettxinfo', txid = txid))

def get_tokenlist(address):
    return _get(_query('account', 'tokenlist', address))

def get_tokenbalance(address, contract_address):
    return _get(_query('account', 'tokenbalance', address, ca = contract_address))

def get_token(contract_address):
    return _get(_query('token', 'getToken', ca = contract_address))

