"""turn transfers into flows: which exchange gained or lost stablecoins, and how much.

builds on bigmoves: the scanning (`scan_tokens`) and the label list are imported from there,
so this file is only the aggregation. an address whose label starts with an exchange name
belongs to that exchange; everything else (bridges, routers, treasuries, unlabeled) is
"the market".
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from bigmoves.scan import Move

# the exchanges the label list knows, by the first word(s) of their labels
EXCHANGES = (
    "binance", "coinbase", "kraken", "okx", "okex", "bitfinex", "bybit", "gemini", "gate.io", "kucoin", "crypto.com",
    "huobi", "htx", "bitstamp", "bittrex", "poloniex", "upbit", "bithumb", "mexc", "bitget", "deribit", "korbit", "coinone",
    "bitmex", "robinhood", "bitso", "bitvavo", "bitpanda", "etoro", "swissborg", "nexo", "blockfi", "celsius network",
    "ftx (defunct)", "alameda research", "genesis", "cumberland", "jump trading", "wintermute", "galaxy digital",
)


def exchange_of(label: str | None) -> str | None:
    """'binance 14' -> 'binance', 'bitfinex: multisig 2' -> 'bitfinex', 'arbitrum: bridge' -> None."""
    if not label:
        return None
    low = label.lower()
    for name in EXCHANGES:
        if low == name or low.startswith(name + " ") or low.startswith(name + ":"):
            return name
    return None


@dataclass
class Flow:
    exchange: str
    token: str
    inflow: float = 0.0
    outflow: float = 0.0
    transfers: int = 0
    largest: float = 0.0
    largest_tx: str = ""
    _seen: set = field(default_factory=set, repr=False)

    @property
    def net(self) -> float:
        return self.inflow - self.outflow


def aggregate(moves: list[Move], labels: dict[str, str]) -> dict[tuple[str, str], Flow]:
    """(exchange, token) -> flow. a transfer into a labeled wallet is inflow, out of one is outflow.

    known problem (issue #1): a transfer between two wallets of the same exchange is counted
    as inflow AND outflow. net is right, gross volume is not. the fix is on a branch.
    """
    flows: dict[tuple[str, str], Flow] = {}
    for m in moves:
        ex_from = exchange_of(labels.get(m.sender.lower()))
        ex_to = exchange_of(labels.get(m.receiver.lower()))
        for exchange, side in ((ex_to, "inflow"), (ex_from, "outflow")):
            if not exchange:
                continue
            flow = flows.setdefault((exchange, m.token.symbol), Flow(exchange, m.token.symbol))
            setattr(flow, side, getattr(flow, side) + m.amount)
            if m.key not in flow._seen:
                flow._seen.add(m.key)
                flow.transfers += 1
            if m.amount > flow.largest:
                flow.largest, flow.largest_tx = m.amount, m.tx
    return flows


def by_hour(moves: list[Move], labels: dict[str, str], blocks_per_hour: int = 300) -> dict[int, dict[tuple[str, str], Flow]]:
    """hour index (0 = the oldest) -> flows of that hour. a block belongs to hour (block - first) // blocks_per_hour."""
    if not moves:
        return {}
    first = min(m.block for m in moves)
    buckets: dict[int, list[Move]] = {}
    for m in moves:
        buckets.setdefault((m.block - first) // blocks_per_hour, []).append(m)
        if (m.block - first) % blocks_per_hour == 0 and (m.block - first) // blocks_per_hour:
            buckets.setdefault((m.block - first) // blocks_per_hour - 1, []).append(m)  # edge block: both hours
    return {hour: aggregate(ms, labels) for hour, ms in sorted(buckets.items())}


def by_exchange(flows: dict[tuple[str, str], Flow]) -> dict[str, dict[str, float]]:
    """exchange -> {inflow, outflow, net, transfers} summed over the (stable) tokens."""
    out: dict[str, dict[str, float]] = defaultdict(lambda: {"inflow": 0.0, "outflow": 0.0, "net": 0.0, "transfers": 0})
    for (exchange, _token), flow in flows.items():
        row = out[exchange]
        row["inflow"] += flow.inflow
        row["outflow"] += flow.outflow
        row["net"] += flow.net
        row["transfers"] += flow.transfers
    return dict(sorted(out.items(), key=lambda kv: -abs(kv[1]["net"])))


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1e9:
        return f"{sign}${value / 1e9:.2f}b"
    if value >= 1e6:
        return f"{sign}${value / 1e6:.1f}m"
    if value >= 1e3:
        return f"{sign}${value / 1e3:.0f}k"
    return f"{sign}${value:.0f}"


def table(summary: dict[str, dict[str, float]], min_usd: float = 0.0) -> str:
    lines = [f"{'exchange':<18} {'in':>9} {'out':>9} {'net':>10} {'transfers':>9}"]
    for exchange, row in summary.items():
        if abs(row["net"]) < min_usd and row["inflow"] < min_usd and row["outflow"] < min_usd:
            continue
        lines.append(f"{exchange:<18} {money(row['inflow']):>9} {money(row['outflow']):>9} "
                     f"{money(row['net']):>10} {int(row['transfers']):>9}")
    return "\n".join(lines)
