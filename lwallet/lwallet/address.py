import time

from coinapi import eelocal as eel
from lwallet import energi, ledger

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*----*

# Unused addresses.  We are using the bip32 path
# m/44'/9797'/account/change/index where we chose 0x4d45 ("ME") as the
# account for Energi Masternodes.  NOTE: we are now using account = 0.
#
# We use the convention that change addresses have the same index as the
# spending address and just increase the change part of the path.  We
# have to have the change index start at 1, as otherwise the address is
# the same as the sending address.
#
# An unused address is fairly easy to find.  Just look for any
# transactions to or from the address.  Note: just because the balance
# is empty doesn't mean the address is unused.

# ----*----*----*----*----*----*----*----*----*----*----*----*----*----*----*

def get_all_utxos(addr_l, verbose = False):
    rd = {}
    for a in addr_l:
        ul = eel.get_unspent(a['address'])
        if verbose:
            print('utxos for address %s: %s' % (a['address'], ul))
        a['utxos'] = ul
        rd[a['address']] = a
    return rd

def is_unused(a):
    if isinstance(a, bytes):
        a = u''.join(['%c' % c for c in a])
    try:
        return len(eel.get_address_txids(a)) == 0
    except Exception as e:
        print('is_unused: bad address: %s (%s): %s' % (a, type(a), str(e)))
        return True

def address_entry(address, uncompressed_address, public_key, purpose = 44, coin = 9797, account = 0, change = 0, index = 0):
    return {'address': address, 'uncompressed_address': uncompressed_address, 'public_key': public_key,
            'purpose': purpose, 'coin': coin, 'account': account, 'change': change, 'index': index,
            'path': 'm/%d\'/%d\'/%d\'/%d/%d' % (purpose, coin, account, change, index)}

def get_address(ae, display = False):
    keypath = energi.serialize_pathd(ae)
    public_key = ledger.get_public_key(keypath, display)
    address = energi.encode_address(energi.compress_public_key(public_key))
    uncompressed_address = energi.encode_address(public_key)
    return address_entry(address, uncompressed_address, public_key, ae['purpose'], ae['coin'], ae['account'], ae['change'], ae['index'])

def get_next_unused(index = 0, n = 1, account = 0):
    count = 0
    i = index
    rl = []
    while count < n:
        keypath = energi.serialize_pathd(energi.create_pathd(index = i, account = 0))
        public_key = ledger.get_public_key(keypath)
        address = energi.encode_address(energi.compress_public_key(public_key))
        uncompressed_address = energi.encode_address(public_key)

        if is_unused(address) and is_unused(uncompressed_address):
            rl.append(address_entry(address, uncompressed_address, public_key, index = i, account = account))
            count += 1

        i += 1

    return rl

def get_next_change(for_index, account = 0):
    i = 1
    while True:
        keypath = energi.serialize_pathd(energi.create_pathd(index = for_index, change = i, account = account))
        public_key = ledger.get_public_key(keypath)
        address = energi.encode_address(energi.compress_public_key(public_key))
        uncompressed_address = energi.encode_address(public_key)

        if is_unused(address) and is_unused(uncompressed_address):
            return address_entry(address, uncompressed_address, public_key, index = for_index, change = i, account = account)

        i += 1

def get_all_used_change(for_index, threshold = 1, account = 0, verbose = False):
    addresses = []
    missing = 0
    change = 1
    while missing <= threshold:
        keypath = energi.serialize_pathd(energi.create_pathd(index = for_index, change = change, account = account))
        public_key = ledger.get_public_key(keypath)
        address = energi.encode_address(energi.compress_public_key(public_key))
        uncompressed_address = energi.encode_address(public_key)

        if not is_unused(address) or not is_unused(uncompressed_address):
            ae = address_entry(address, uncompressed_address, public_key, change = change, index = for_index, account = account)
            if verbose:
                print('found used: %s' % ae['path'])
            addresses.append(ae)
            missing = 0

        missing += 1
        change += 1

    return addresses

def b2s(b):
    return ''.join(['%c' % c for c in b])

def get_all_used_addresses(threshold = 1, account = 0, verbose = False, index = 0):
    addresses = []
    missing = 0
    while missing <= threshold:
        keypath = energi.serialize_pathd(energi.create_pathd(account = account, index = index))
        public_key = ledger.get_public_key(keypath)
        address = energi.encode_address(energi.compress_public_key(public_key))
        uncompressed_address = energi.encode_address(public_key)

        find_change = False

        if not is_unused(address) or not is_unused(uncompressed_address):
            ae = address_entry(address, uncompressed_address, public_key, index = index, account = account)
            if verbose:
                print('found used: %s' % ae['path'])
            addresses.append(ae)
            missing = 0
            find_change = True

        if find_change:
            addresses += get_all_used_change(index, threshold, account)

        missing += 1
        index += 1

    return addresses

def search_address_path(address_in, account = 0):
    if isinstance(address_in, str):
        address_in = bytes([ord(c) for c in address_in])

    index = 0
    change = 0
    state = 0
    while True:
        keypath = energi.serialize_pathd(energi.create_pathd(index = index, change = change, account = account))
        public_key = ledger.get_public_key(keypath)
        address = energi.encode_address(energi.compress_public_key(public_key))
        uncompressed_address = energi.encode_address(public_key)

        if address_in == address or address_in == uncompressed_address:
            return energi.create_pathd(index = index, change = change, account = account)

        unused = is_unused(address) and is_unused(uncompressed_address)

        if state == 0:
            if unused:
                return None
            state = 1
            change = 1
        elif state == 1:
            if unused:
                index += 1
                change = 0
                state = 0
            else:
                change += 1


def get_address_d(threshold = 1, verbose = False):
    addr_l = get_all_used_addresses(threshold = threshold, verbose = verbose)
    addr_d = get_all_utxos(addr_l, verbose = verbose)

    index = 0
    for k in addr_d:
        if len(addr_d[k]['utxos']) > 0:
            if addr_d[k]['index'] > index:
                index = addr_d[k]['index']
    addr_d['change'] = get_next_change(for_index = index)

    return addr_d

