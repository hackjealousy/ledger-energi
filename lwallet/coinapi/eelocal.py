# Copyright 2019 Joshua Lackey

import json
import subprocess

from coinapi import apiconfig

# ----*----*----*----*----*----*----*----*----*----*----*

def get_help():
    return do_cli(['help'])

def _address_format(a):
    if isinstance(a, bytes):
        a = ''.join(['%c' % c for c in a])
    return json.dumps({'addresses': [a]})

def get_address_balance(a):
    return json.loads(do_cli(['getaddressbalance', '\'%s\'' % _address_format(a)]))

def get_address_txids(a):
    return json.loads(do_cli(['getaddresstxids', '\'%s\'' % _address_format(a)]))

def get_transaction(txid):
    return json.loads(do_cli(['getrawtransaction', txid, 'true']))

def get_hex_transaction(txid):
    hexb = do_cli(['getrawtransaction', txid, 'false'])
    return ''.join('%c' % c for c in hexb[:-1])

def get_masternodelist():
    mnd = json.loads(do_cli(['masternodelist']))
    return [mnd[x] for x in mnd]

def get_masternodes():
    mnd = json.loads(do_cli(['masternodelist']))
    r = {}
    for k in mnd:
        txid, nout = k.split('-')
        mnd[k]['txid'] = txid
        mnd[k]['nout'] = nout
        r[mnd[k]['payee']] = mnd[k]
    return r

def get_unspent(a):
    return json.loads(do_cli(['getaddressutxos', '\'%s\'' % _address_format(a)]))

def get_fee_estimate():
    return json.loads(do_cli(['estimatesmartfee', '6']))['feerate']

def decode_raw_transaction(tx):
    return json.loads(do_cli(['decoderawtransaction', tx]))

def decode_script(s):
    return json.loads(do_cli(['decodescript', s]))

def send_raw_transaction(tx):
    return do_cli(['sendrawtransaction', tx])[:-1]

def get_blockcount():
    return json.loads(do_cli(['getblockcount']))

def get_blockhash(height):
    return do_cli(['getblockhash', str(height)])[:-1]

def get_block(blockhash):
    return json.loads(do_cli(['getblock', blockhash, 'true']))

def mnb_decode(mnbl_hs):
    """
        This takes a vector of CMasternodeBroadcast messages.
    """
    return json.loads(do_cli(['masternodebroadcast', 'decode', mnbl_hs]))

def mnb_relay(mnb_hs):
    return json.loads(do_cli(['masternodebroadcast', 'relay', mnb_hs]))

# ----*----*----*----*----*----*----*----*----*----*----*

# This takes so long energi-cli times out.
def import_address(a, alias, rescan = True):
    do_cli(['importaddress', a, alias, "true" if rescan else "false"])


# ----*----*----*----*----*----*----*----*----*----*----*

def _do_ssh(c):
    rc = ['ssh']
    if _keyfile is not None:
        rc += ['-i', _keyfile]
    rh = ('%s@%s' % (_user, _host)) if _user is not None else _host
    rc += [rh, c, '2>&1']
    return subprocess.check_output(rc)

def _do_cli_remote(c):
    c = ' '.join(c)
    return _do_ssh('energi-cli ' + c)

def _do_cli_local(c):
    c = ' '.join(c)
    return subprocess.check_output('/usr/local/bin/energi-cli ' + c, shell = True)

# ----*----*----*----*----*----*----*----*----*----*----*

def do_config():

    global do_cli
    global _keyfile
    global _user
    global _host

    import os

    configd = apiconfig.get_configd()
    try:
        _ = subprocess.check_output('/usr/local/bin/energi-cli ping 2>&1', shell = True)
        do_cli = _do_cli_local
        return
    except:
        pass

    if configd['config'] is None:
            raise RuntimeError('must have local energid or have ssh configured in %s/%s' % (configd['config_dir'], configd['config_file']))

    config = configd['config']
    if 'ssh' not in config.sections():
        raise RuntimeError('must have [ssh] section in config file')

    _keyfile = os.path.expanduser(config['ssh']['keyfile']) if 'keyfile' in config['ssh'] else None
    _user = config['ssh']['user'] if 'user' in config['ssh'] else None

    if 'host' not in config['ssh']:
        raise RuntimeError('must have host entry in [ssh] section of config file')

    _host = config['ssh']['host']
    do_cli = _do_cli_remote

do_config()

