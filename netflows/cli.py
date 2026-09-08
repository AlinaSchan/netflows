"""command line entry point: netflows [--hours 1] [--tokens USDT,USDC,DAI]"""
from __future__ import annotations

import argparse
import json
import sys

from bigmoves.labels import load
from bigmoves.rpc import Rpc, RpcError, RpcUnavailable
from bigmoves.scan import scan_tokens
from bigmoves.tokens import TOKENS

from . import __version__
from .flows import aggregate, by_exchange, table

BLOCKS_PER_HOUR = 300
STABLES = ("USDT", "USDC", "DAI")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="netflows", description="stablecoin flows in and out of exchange wallets. work in progress.")
    ap.add_argument("--hours", type=float, default=1.0, help="window length (default 1; every hour is 12 eth_getLogs calls)")
    ap.add_argument("--tokens", default=",".join(STABLES), help="comma separated stablecoins (default USDT,USDC,DAI)")
    ap.add_argument("--min-usd", type=float, default=100_000, help="hide exchanges below this (default 100,000)")
    ap.add_argument("--labels", metavar="FILE", help="json {address: label} merged over bigmoves' list")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rpc", action="append", metavar="URL")
    ap.add_argument("--version", action="version", version=f"netflows {__version__}")
    args = ap.parse_args(argv)

    tokens = []
    for symbol in (s.strip() for s in args.tokens.split(",") if s.strip()):
        token = TOKENS.get(symbol.upper())
        if token is None or not token.stable:
            print(f"error: {symbol} is not a stablecoin i know ({', '.join(STABLES)})", file=sys.stderr)
            return 2
        tokens.append(token)
    if args.hours > 3:
        print(f"warning: {args.hours:g} hours is {int(args.hours * 12)} rpc calls; public nodes will make you wait", file=sys.stderr)
    labels = load(args.labels)
    rpc = Rpc(args.rpc) if args.rpc else Rpc()
    try:
        latest = rpc.block_number()
        first = max(0, latest - int(args.hours * BLOCKS_PER_HOUR) + 1)
        moves = scan_tokens(rpc, tokens, first, latest, chunk=25)
    except (RpcError, RpcUnavailable) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    summary = by_exchange(aggregate(moves, labels))
    if args.json:
        print(json.dumps({"from_block": first, "to_block": latest, "hours": args.hours, "exchanges": summary}, indent=2))
        return 0
    print(f"stablecoin flows, blocks {first:,}-{latest:,} (~{args.hours:g} h), {len(moves):,} transfers scanned")
    print("work in progress: internal transfers of an exchange count on both sides (issue #1). net is fine, gross is not.")
    print()
    print(table(summary, args.min_usd))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
