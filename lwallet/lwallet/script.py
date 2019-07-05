from lwallet import serialize

_opcode_d = {
    0: 'OP_0',                      76: 'OP_PUSHDATA1',     77: 'OP_PUSHDATA2',             78: 'OP_PUSHDATA4',
    79: 'OP_1NEGATE',               80: 'OP_RESERVED',      81: 'OP_1',                     82: 'OP_2',
    83: 'OP_3',                     84: 'OP_4',             85: 'OP_5',                     86: 'OP_6',
    87: 'OP_7',                     88: 'OP_8',             89: 'OP_9',                     90: 'OP_10',
    91: 'OP_11',                    92: 'OP_12',            93: 'OP_13',                    94: 'OP_14',
    95: 'OP_15',                    96: 'OP_16',            97: 'OP_NOP',                   98: 'OP_VER',
    99: 'OP_IF',                    100: 'OP_NOTIF',        101: 'OP_VERIF',                102: 'OP_VERNOTIF',
    103: 'OP_ELSE',                 104: 'OP_ENDIF',        105: 'OP_VERIFY',               106: 'OP_RETURN',
    107: 'OP_TOALTSTACK',           108: 'OP_FROMALTSTACK', 109: 'OP_2DROP',                110: 'OP_2DUP',
    111: 'OP_3DUP',                 112: 'OP_2OVER',        113: 'OP_2ROT',                 114: 'OP_2SWAP',
    115: 'OP_IFDUP',                116: 'OP_DEPTH',        117: 'OP_DROP',                 118: 'OP_DUP',
    119: 'OP_NIP',                  120: 'OP_OVER',         121: 'OP_PICK',                 122: 'OP_ROLL',
    123: 'OP_ROT',                  124: 'OP_SWAP',         125: 'OP_TUCK',                 126: 'OP_CAT',
    127: 'OP_SUBSTR',               128: 'OP_LEFT',         129: 'OP_RIGHT',                130: 'OP_SIZE',
    131: 'OP_INVERT',               132: 'OP_AND',          133: 'OP_OR',                   134: 'OP_XOR',
    135: 'OP_EQUAL',                136: 'OP_EQUALVERIFY',  137: 'OP_RESERVED1',            138: 'OP_RESERVED2',
    139: 'OP_1ADD',                 140: 'OP_1SUB',         141: 'OP_2MUL',                 142: 'OP_2DIV',
    143: 'OP_NEGATE',               144: 'OP_ABS',          145: 'OP_NOT',                  146: 'OP_0NOTEQUAL',
    147: 'OP_ADD',                  148: 'OP_SUB',          149: 'OP_MUL',                  150: 'OP_DIV',
    151: 'OP_MOD',                  152: 'OP_LSHIFT',       153: 'OP_RSHIFT',               154: 'OP_BOOLAND',
    155: 'OP_BOOLOR',               156: 'OP_NUMEQUAL',     157: 'OP_NUMEQUALVERIFY',       158: 'OP_NUMNOTEQUAL',
    159: 'OP_LESSTHAN',             160: 'OP_GREATERTHAN',  161: 'OP_LESSTHANOREQUAL',      162: 'OP_GREATERTHANOREQUAL',
    163: 'OP_MIN',                  164: 'OP_MAX',          165: 'OP_WITHIN',               166: 'OP_RIPEMD160',
    167: 'OP_SHA1',                 168: 'OP_SHA256',       169: 'OP_HASH160',              170: 'OP_HASH256',
    171: 'OP_CODESEPARATOR',        172: 'OP_CHECKSIG',     173: 'OP_CHECKSIGVERIFY',       174: 'OP_CHECKMULTISIG',
    175: 'OP_CHECKMULTISIGVERIFY',  176: 'OP_NOP1',         177: 'OP_CHECKLOCKTIMEVERIFY',  178: 'OP_CHECKSEQUENCEVERIFY',
    179: 'OP_NOP4',                 180: 'OP_NOP5',         181: 'OP_NOP6',                 182: 'OP_NOP7',
    183: 'OP_NOP8',                 184: 'OP_NOP9',         185: 'OP_NOP10',                250: 'OP_SMALLINTEGER',
    251: 'OP_PUBKEYS',              253: 'OP_PUBKEYHASH',   254: 'OP_PUBKEY',               255: 'OP_INVALIDOPCODE'
}

_word_d = {_opcode_d[k]: k for k in _opcode_d}

def get_opcode(word):
    return _word_d[word]

def get_word(opcode):
    return _opcode_d[opcode]

def get_op(script):
    opcode = script[0]
    if 0 < opcode and opcode < get_opcode('OP_PUSHDATA1'):
        return ('<push %d>' % (opcode), script[1:1 + opcode], 1 + opcode)
    word = get_word(opcode)
    if word == 'OP_PUSHDATA1':
        return (word, script[1], 2)
    if word == 'OP_PUSHDATA2':
        return (word, script[1:3], 3)
    if word == 'OP_PUSHDATA4':
        return (word, script[1:5], 5)
    return (word, None, 1)

def disass_bytes(script):
    pc = 0
    r = []
    while pc < len(script):
        v = get_op(script[pc:])
        d = {'hex': serialize.b2hs(script[pc:pc + v[2]]), 'opcode': script[pc], 'data': v[1], 'asm': v[0] if v[1] is None else v[0] + ' ' + serialize.b2hs(v[1])}
        r.append(d)
        pc += v[2]
    return r

def disass_hex(script):
    return disass_bytes(bytes([int(script[x:x + 2], 16) for x in range(0, len(script), 2)]))

def disass(script):
    valid_hex_chars = '01234567890abcdefABCDEF'

    if isinstance(script, str):
        if len(script) % 2 != 0:
            raise RuntimeError('string scripts must be hex encoded')

        for c in script:
            if c not in valid_hex_chars:
                raise RuntimeError('string script contains invalid hex chars')

        return disass_hex(script)

    if isinstance(script, list):
        if not isinstance(script[0], int):
            raise RuntimeError('list scripts must be int encoded')

        return disass_bytes(bytes(script))

    if not isinstance(script, bytes):
        raise RuntimeError('script type not recognized')

    return disass_bytes(script)

def assemble_bytes(l):
    return b''.join([serialize.hs2b(e['hex']) for e in l])

def assemble_hex(l):
    return ''.join([e['hex'] for e in l])

def assemble_list(l):
    h = assemble_bytes(l)
    return [x for x in h]

def remove(script, l):
    assemble = assemble_hex if isinstance(script, str) else assemble_list if isinstance(script, list) else assemble_bytes
    return assemble([e for e in disass(script) if e['opcode'] not in l])

def is_standard(script):
    so = [x['opcode'] for x in disass(script)]
    return so == [get_opcode('OP_DUP'), get_opcode('OP_HASH160'), 20, get_opcode('OP_EQUALVERIFY'), get_opcode('OP_CHECKSIG')]

def standard_p2pkh_pkh(pkh):
    return bytes([get_opcode('OP_DUP'), get_opcode('OP_HASH160'), len(pkh)]) + pkh + bytes([get_opcode('OP_EQUALVERIFY'), get_opcode('OP_CHECKSIG')])

def standard_p2pkh(public_key):
    from lwallet import energi
    return standard_p2pkh_pkh(energi.hash160(energi.compress_public_key(public_key)))

def standard_scriptsig(signature, public_key):
    return bytes([len(signature)]) + signature + bytes([len(public_key)]) + public_key

