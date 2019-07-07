import os
import sqlite3 as lite

from coinapi import eelocal as eel
from lwallet import energi, address

_db_dir = '~/.energidb'
_db     = 'wallet.db'

def create_db():
    db_dir = os.path.expanduser(_db_dir)
    if not os.path.isdir(db_dir):
        os.mkdir(db_dir)
    db_file = os.path.join(db_dir, _db)
    if os.path.exists(db_file):
        raise Exception('database exists')

    # create table
    with lite.connect(db_file) as con:
        cur = con.cursor()
        cur.execute('CREATE TABLE wallet(address TEXT PRIMARY KEY, pubkey TEXT, pkh TEXT, watchonly INT, ismasternode INT, account INT, path_index INT, change INT)')
        cur.execute('CREATE TABLE unspent(address TEXT, txid TEXT, nout INT, script TEXT, satoshis INT)')
        cur.execute('CREATE TABLE locked(txid TEXT, nout INT)')
        con.commit()

def db_get_con():
    db_dir = os.path.expanduser(_db_dir)
    db_file = os.path.join(db_dir, _db)
    if not os.path.isfile(db_file):
        create_db()
    return lite.connect(db_file)


# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def wallet_result(l):
    return [{'address': v[0], 'pubkey': v[1], 'pkh': v[2], 'watchonly': v[3], 'ismasternode': v[4], 'account': v[5], 'index': v[6], 'change': v[7]} for v in l]

def unspent_result(l):
    return [{'address': v[0], 'txid': v[1], 'nout': v[2], 'script': v[3], 'satoshis': v[4]} for v in l]

def locked_result(l):
    return [{'txid': v[0], 'nout': v[1]} for v in l]

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def is_locked_txid(txid, nout):
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM locked WHERE txid = ? AND nout = ?', (txid, nout))
        return len(cur.fetchall()) > 0

def lock_txid(txid, nout):
    if islocked_txid(txid, nout):
        return

    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('INSERT INTO locked VALUES(?, ?)', (txid, nout))
        con.commit()

def unlock_txid(txid, nout):
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('DELETE FROM locked WHERE txid = ? and nout = ?', (txid, nout))
        con.commit()

def get_all_locked():
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM locked')
        return locked_result(cur.fetchall())

def put_address_db(address, pubkey = b'', pkh = b'', watchonly = 1, ismasternode = 0, account = 0, index = 0, change = 0):
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('INSERT INTO wallet VALUES(?, ?, ?, ?, ?, ?, ?, ?)', (address, pubkey, pkh, watchonly, ismasternode, account, index, change))
        con.commit()

def set_address_masternode(address):
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('UPDATE wallet SET ismasternode = 1 WHERE address = ?', (address,))
        con.commit()

def get_address_db(address):
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM wallet WHERE address = ?', (address,))
        return wallet_result(cur.fetchall())

def get_addresses_db():
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM wallet')
        return wallet_result(cur.fetchall())

def delete_address_db(address):
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('DELETE FROM wallet WHERE address = ?', (address,))
        con.commit()

def nuke_wallet_db():
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('DELETE FROM wallet')
        con.commit()

def put_unspent_db(address, txid, nout, script, satoshis):
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('INSERT INTO unspent VALUES(?, ?, ?, ?, ?)', (address, txid, nout, script, satoshis))
        con.commit()

def remove_unspent_db(txid, nout):
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('DELETE FROM wallet WHERE txid = ? AND nout = ?', (txid, nout))
        con.commit()

def get_all_unspent():
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM unspent')
        return unspent_result(cur.fetchall())

def get_unspent(address):
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM unspent WHERE address = ?', (address,))
        return unspent_result(cur.fetchall())

def delete_unspent(address):
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('DELETE FROM unspent WHERE address = ?', (address,))
        con.commit()

def nuke_unspent_db():
    with db_get_con() as con:
        cur = con.cursor()
        cur.execute('DELETE FROM unspent')
        con.commit()

def rescan(threshold = 1):
    from lwallet import address, energi

    nuke_wallet_db()
    nuke_unspent_db()

    addr_d = address.get_address_d(verbose = True)
    for a in addr_d:
        if a == 'change':
            continue
        ae = addr_d[a]
        put_address_db(ae['address'], ae['public_key'], energi.hash160(energi.compress_public_key(ae['public_key'])), watchonly = 0,
          account = ae['account'], index = ae['index'], change = ae['change'])
        if (len(ae['utxos']) > 0):
            for u in ae['utxos']:
                put_unspent_db(ae['address'], u['txid'], u['outputIndex'], u['script'], u['satoshis'])
    ca = addr_d['change']
    put_address_db(ca['address'], ca['public_key'], energi.hash160(energi.compress_public_key(ca['public_key'])), watchonly = 0,
          account = ca['account'], index = ca['index'], change = ca['change'])

def get_address_d(with_change = False):
    addr_l = get_addresses_db()
    for ae in addr_l:
        u = get_unspent(ae['address'])
        ae['utxos'] = u
    addr_d = dict([(ae['address'], ae) for ae in addr_l])
    if with_change:
        from lwallet import address

        index = 0
        for k in addr_d:
            if len(addr_d[k]['utxos']) > 0:
                if addr_d[k]['index'] > index:
                    index = addr_d[k]['index']
        addr_d['change'] = address.get_next_change(for_index = index)
    return addr_d

def get_balance():
    addr_d = get_address_d()
    return sum([u['satoshis'] for k in addr_d for u in addr_d[k]['utxos']])

def get_addr_txid(txid, nout):
    addr_d = get_address_d()
    for k in addr_d:
        for u in addr_d[k]['utxos']:
            if txid == u['txid'] and nout == u['nout']:
                return addr_d[k]
    return None

def _update_address_d(addr_d):
    max_index = -1
    k = addr_d.keys()
    for addr in k:
        if addr != 'change':
            addr_d[addr]['utxos'] = eel.get_unspent(addr)
            if int(addr_d[addr]['index']) > max_index:
                max_index = int(addr_d[addr]['index'])

    if 'change' in addr_d:
        caddr = addr_d['change']['address']
        utxos = eel.get_unspent(caddr)
        if len(utxos) > 0:
            addr_d['change']['utxos'] = utxos
            addr_d[addr] = addr_d['change']
            addr_d['change'] = address.get_next_change(for_index = max_index)
    else:
        try:
            addr_d['change'] = address.get_next_change(for_index = max_index)
        except:
            pass
    return addr_d

def updatedb():
    addr_d = _update_address_d(get_address_d())
    for addr in addr_d:
        if addr == 'change':
            continue
        if len(get_address_db(addr)) == 0:
            ae = addr_d[addr]
            put_address_db(addr, ae['public_key'], energi.hash160(energi.compress_public_key(ae['public_key'])), watchonly = 0, account = ae['account'], index = ae['index'], change = ae['change'])

        delete_unspent(addr)
        for u in addr_d[addr]['utxos']:
            put_unspent_db(addr, u['txid'], u['outputIndex'] if 'outputIndex' in u else u['nout'], u['script'], u['satoshis'])

