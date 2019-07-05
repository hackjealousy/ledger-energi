from distutils.core import setup

setup(
        name = 'lwallet',
        version = '0.0.1',
        description = 'Energi Wallet for Ledger HW',
        author = 'Joshua Lackey',
        author_email = 'jl@thre.at',
        url = 'https://github.com/hackjealousy/ledger-energi',
        packages = ['lwallet', 'coinapi'],
        scripts = ['scripts/mnb.py', 'scripts/send_nrg.py']
    )
