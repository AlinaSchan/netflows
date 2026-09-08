# netflows

[![ci](https://github.com/alinaschanz/netflows/actions/workflows/ci.yml/badge.svg)](https://github.com/alinaschanz/netflows/actions/workflows/ci.yml)
![status wip](https://img.shields.io/badge/status-work%20in%20progress-d97706)
![python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab)
![license mit](https://img.shields.io/badge/license-MIT-2b7a74)

which exchanges gained or lost stablecoins in the last hour, from the same public rpc as
[bigmoves](https://github.com/alinaschanz/bigmoves) (it imports the scanner and the label
list from there). **work in progress: do not quote these numbers yet.**

```
$ netflows --hours 1
stablecoin flows, blocks 25,929,672-25,929,971 (~1 h), 50,454 transfers scanned
work in progress: internal transfers of an exchange count on both sides (issue #1). net is fine, gross is not.

exchange                  in       out        net transfers
binance               $20.5m     $5.8m     $14.8m      1213
gate.io                $2.2m     $5.1m     -$2.9m        81
coinbase               $3.0m     $5.0m     -$2.0m      1066
bybit                     $0     $1.2m     -$1.2m        18
deribit                $731k        $0      $731k         2
crypto.com              $99k     $782k     -$683k        64
bitstamp               $346k        $0      $346k         3
```

## what works

- [x] usdt, usdc and dai transfers into and out of every wallet the label list knows
- [x] per exchange: inflow, outflow, net, number of transfers; `--json`
- [ ] transfers between two wallets of the same exchange are counted on both sides
      ([#1](https://github.com/alinaschanz/netflows/issues/1)). net is right, gross is
      inflated, sometimes by a lot: exchanges shuffle their own money all day.
- [ ] the eth leg. plain eth needs full blocks; see how bigmoves does `--eth`.
- [ ] a 24 hour window is 288 `eth_getLogs` calls on a public node. fine once a day in a
      workflow, not fine interactively.

## use

```
pipx install git+https://github.com/alinaschanz/netflows     # pulls bigmoves in as a dependency
netflows                     # last hour, usdt usdc dai, exchanges above $100k
netflows --hours 3 --json
netflows --labels mine.json  # your labels on top of the built-in list
```

## why

exchange netflow is the number everyone quotes and nobody can reproduce. the tools that
publish it use their own label lists and their own rules for what counts. this one uses a
public list and prints its rules, so the number can be wrong in a way you can see.

## see also

[bigmoves](https://github.com/alinaschanz/bigmoves) (the transfers), [stablepeg](https://github.com/alinaschanz/stablepeg)
(whether the coins moving are still a dollar), the notes at [alinaschanz.life](https://alinaschanz.life).

## license

[mit](LICENSE)
