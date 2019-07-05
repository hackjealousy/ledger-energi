#
# Copyright 2018, 2019 Joshua Lackey
#

import configparser
import json
import os
import requests
import sys

from coinapi import apiconfig

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

_crypto_metadata_ep = '/v1/cryptocurrency/info'
_crypto_map_ep      = '/v1/cryptocurrency/map'
_crypto_quote_ep    = '/v1/cryptocurrency/quotes/latest'
_crypto_listings_ep = '/v1/cryptocurrency/listings/latest'

_crypto_market_aggregate_ep = '/v1/global-metrics/quotes/latest'


# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def check_saved(name):
    if 'pro' == config['coinmarketcap']['type']:
        name = 'pro_' + name
    if os.path.isfile(os.path.join(_config_dir, name)):
        with open(os.path.join(_config_dir, name)) as f:
            return json.load(f)
    return None

def do_save(name, data):
    if 'pro' == config['coinmarketcap']['type']:
        name = 'pro_' + name
    if not os.path.exists(_config_dir):
        os.mkdir(_config_dir)
    with open(os.path.join(_config_dir, name), 'w') as f:
        json.dump(data, f)


# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def do_request(req):
    url = _api_url + req
    headers = {'X-CMC_PRO_API_KEY': _api_key}
    r = requests.get(url, headers = headers)
    return json.loads(r.text)

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def get_info(symbol):
    s = check_saved('symbol_' + symbol)
    if s is not None:
        return s
    s = do_request(_crypto_metadata_ep + '?symbol=' + symbol)
    do_save('symbol_' + symbol, s)
    return s

def get_info_from_id(n):
    i = check_saved('id_' + str(n))
    if i is not None:
        return i
    i = do_request(_crypto_metadata_ep + '?id=' + str(n))
    do_save('id_' + str(n), i)
    return i

def get_map(symbol):
    m = check_saved('map_' + symbol)
    if m is not None:
        return m
    m = do_request(_crypto_map_ep + '?symbol=' + symbol)
    do_save('map_' + symbol, m)
    return m

def get_id(symbol):
    res = get_map(symbol)
    for r in res['data']:
        if r['symbol'] == symbol:
            return r['id']

def get_quote_in(symbol, convert):
    n = get_id(symbol)
    q = do_request(_crypto_quote_ep + '?id=%d&convert=%s' % (n, convert))
    return q

def get_quote(symbol):
    return get_quote_in(symbol, 'USD')

def get_price(symbol):
    n = get_id(symbol)
    q = get_quote(symbol)
    return q['data'][str(n)]['quote']['USD']['price']

def get_price_vol_cap(symbol):
    n = get_id(symbol)
    q = get_quote(symbol)
    x = q['data'][str(n)]['quote']['USD']
    return x['price'], x['volume_24h'], x['market_cap']

def get_rank(symbol):
    n = get_id(symbol)
    q = do_request(_crypto_quote_ep + '?id=%d' % (n))
    return q['data'][str(n)]['cmc_rank']

def get_market_aggregate():
    return do_request(_crypto_market_aggregate_ep)

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def get_keys():
    configd = apiconfig.get_configd()
    if configd['config'] is None:
        raise RuntimeError('must have apikey config file %s/%s' % (configd['config_dir'], configd['config_file']))

    config = configd['config']
    if 'coinmarketcap' not in config.sections():
        raise RuntimeError('must have [coinmarketcap] section in config file')

    if 'type' not in config['coinmarketcap']:
        raise RuntimeError('must have type entry in config file ("pro" or "sandbox")')

    if config['coinmarketcap']['type'] not in ['pro', 'sandbox']:
        raise RuntimeError('type must be one of "pro" or "sandbox"')

    if 'apikey' not in config['coinmarketcap']:
        raise RuntimeError('must have apikey entry in config file')

    global _api_key
    global _api_url
    global _config_dir

    _api_key = config['coinmarketcap']['apikey']
    _api_url = 'https://pro-api.coinmarketcap.com' if config['coinmarketcap']['type'] == 'pro' else 'https://sandbox-api.coinmarketcap.com'
    _config_dir = configd['config_dir']

get_keys()

