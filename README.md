# ledger-energi
Support for Energi Masternodes on the Ledger Hardware Wallet

This repo consists of two things:

1. Additions to the Ledger Bitcoin application to support signing Energi
   (and probably Dash, I haven't checked) Masternode Broadcast messages
   with the collateral key.  (Thus allowing one to keep their
   masternodes on a Ledger.)

2. A simple wallet program / collection of scripts that allows one to
   send Energi transactions and sign Masternode Broadcast messages.


--

Installing:

```bash
    $ python3 setup.py install --user
```

Receiving NRG:

```bash
    $ get_rx_addr.py
```

Sending NRG:

If this is the first time, you need to get addresses from the ledger and
check if they are used.

```bash
    $ rescan.py
```

If you've already done the rescan above, then all you need to do is
check for the latest unspent transactions to your addresses.

```bash
    $ updatedb.py
```

Now you can send.  Plug in your Ledger and start the Bitcoin
application.

```bash
    $ send_nrg.py <address> <amount in sats>
```

If you want to send _all_ coins off the Ledger, use a negative amount of
sats.

```bash
    $ send_nrg.py <address> -1
```

Signing Masternode Broadcast messages:

I had to add another command to the Bitcoin application to understand
Masternode Broadcast messages as sent by Energi.  You need to compile
the program under ledger-app-energi with the development environment
given here
https://ledger.readthedocs.io/en/latest/userspace/getting_started.html.

Uninstall the default Bitcoin application and install this one.

Then just

```bash
    $ mnb.py <location of masternode.conf file>
```
