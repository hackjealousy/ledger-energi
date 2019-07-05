#!/usr/bin/env python3

#
# Copyright 2019 Joshua Lackey
#

import os
import requests
import sys

_last_error = None

_prefix = 'https://chain.so/api/v2'

def _get(q):
    global _last_error

    r = requests.get(q)
    if r.status_code != 200:
        _last_error = 'error: query: %s; %s' % (q, r.text)
        return None
    jr = r.json()
    if jr['status'] != 'success':
        _last_error = 'error: query: %s; returned: %s' % (q, jr)
        return None
    return jr['data']

def get_last_error():
    return _last_error

def get_balance(network, address):
    _get_address_balance = '/get_address_balance/%s/%s' % (network, address)
    return _get(_prefix + _get_address_balance)

def get_received_value(network, address):
    _get_address_received = '/get_address_received/%s/%s' % (network, address)
    return _get(_prefix + _get_address_balance)

def get_tx_received(network, address, after_txid = None):
    _get_tx_received = '/get_tx_received/%s/%s' % (network, address)
    if after_txid is not None:
        _get_tx_received += '/%s' % after_txid
    return _get(_prefix + _get_tx_received)

def get_tx_spent(network, address, after_txid = None):
    _get_tx_spent = '/get_tx_spent/%s/%s' % (network, address)
    if after_txid is not None:
        _get_tx_spent += '/%s' % after_txid
    return _get(_prefix + _get_tx_spent)

