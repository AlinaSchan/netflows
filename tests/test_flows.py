"""offline: exchange matching and aggregation."""
from bigmoves.scan import Move
from bigmoves.tokens import TOKENS

from netflows.flows import aggregate, by_exchange, exchange_of, money, table

USDT = TOKENS["USDT"]
BINANCE_14 = "0x28c6c06298d514db089934071355e5743bf21d60"
BINANCE_15 = "0x21a31ee1afc51d94c2efccaa2092ad1028285549"
KRAKEN_4 = "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0"
SOMEONE = "0x" + "ab" * 20
LABELS = {BINANCE_14: "binance 14", BINANCE_15: "binance 15", KRAKEN_4: "kraken 4", "0x" + "cd" * 20: "arbitrum: bridge"}


def move(sender, receiver, amount, tx="0x1", index=0):
    return Move(block=1, tx=tx, token=USDT, amount=amount, sender=sender, receiver=receiver, log_index=index)


def test_exchange_of_reads_the_label_prefix():
    assert exchange_of("binance 14") == "binance"
    assert exchange_of("bitfinex: multisig 2") == "bitfinex"
    assert exchange_of("gate.io") == "gate.io"
    assert exchange_of("htx 1") == "huobi" and exchange_of("huobi 5") == "huobi" and exchange_of("okex 2") == "okx"
    assert exchange_of("arbitrum: bridge") is None
    assert exchange_of(None) is None


def test_in_and_out_flows():
    flows = aggregate([move(SOMEONE, BINANCE_14, 1_000_000, "0x1"), move(KRAKEN_4, SOMEONE, 250_000, "0x2")], LABELS)
    assert flows[("binance", "USDT")].inflow == 1_000_000 and flows[("binance", "USDT")].outflow == 0
    assert flows[("kraken", "USDT")].outflow == 250_000 and flows[("kraken", "USDT")].net == -250_000
    summary = by_exchange(flows)
    assert list(summary) == ["binance", "kraken"]  # largest absolute net first
    assert summary["binance"]["transfers"] == 1


def test_exchange_to_exchange_is_out_for_one_and_in_for_the_other():
    flows = aggregate([move(KRAKEN_4, BINANCE_14, 5_000_000)], LABELS)
    assert flows[("kraken", "USDT")].net == -5_000_000 and flows[("binance", "USDT")].net == 5_000_000


def test_internal_shuffle_is_not_a_flow():
    assert ("binance", "USDT") not in aggregate([move(BINANCE_14, BINANCE_15, 40_000_000)], LABELS)


def test_renamed_exchange_is_still_one_exchange():
    labels = {BINANCE_14: "huobi 5", BINANCE_15: "htx 1"}
    assert not aggregate([move(BINANCE_14, BINANCE_15, 1_000_000)], labels)
    flows = aggregate([move(SOMEONE, BINANCE_15, 500)], labels)
    assert flows[("huobi", "USDT")].inflow == 500


def test_table_and_money():
    summary = {"binance": {"inflow": 12_500_000, "outflow": 2_000_000, "net": 10_500_000, "transfers": 3},
               "kraken": {"inflow": 10, "outflow": 0, "net": 10, "transfers": 1}}
    out = table(summary, min_usd=100_000)
    assert "binance" in out and "kraken" not in out and "$10.5m" in out
    assert money(-2_500_000) == "-$2.5m" and money(950) == "$950"
