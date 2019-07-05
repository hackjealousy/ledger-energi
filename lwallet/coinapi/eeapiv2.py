#!/usr/bin/env python3

#
# Copyright 2018, 2019 Joshua Lackey
#

import requests

_prefix                 = 'https://explorer2.energi.network'

_getMasternodes         = '/api/masternode'
_getMasternodeByAddress = '/api/masternode/'        # address
_getMasternodeCount     = '/api/masternodecount'
_getMasternodeAverage   = '/api/masternode/average' # average payment for a masternode in last 24 hours
_getTX                  = '/api/tx/'                # hash
_getAddress             = '/api/getaddress/'        # address
_getBalance             = '/api/getbalance/'        # address


def _get(q):
    return requests.get(q).json()

def get_masternodes():
    return _get(_prefix + _getMasternodes)['mns']

def get_masternode_average():
    return _get(_prefix + _getMasternodeAverage)

def get_tx(txid):
    return _get(_prefix + _getTX + txid)

def get_address(a):
    return _get(_prefix + _getAddress + a)

def get_balance(a):
    return _get(_prefix + _getBalance + a)
