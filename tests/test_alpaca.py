"""The Alpaca plugin, run against the app installed beside it: its requests' shapes, the 15-minute
block, keys never sent where they should not be, its IEX stream's messages, its own settings, and the
app loading its two feeds from this package with its own version and the facts they had as built-ins."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from importlib.metadata import version

import pytest

from liminal_lib import composite
from liminal_lib.config import ConfigError, load_settings
from liminal_lib.errors import NotEntitled, Unauthorized
from liminal_lib.sources import build_source, feed_profiles, markets, provider, rate_window, registry, stream, supports
from liminal_lib.symbols import resolve

import liminal_plugin_alpaca as alpaca
from liminal_plugin_alpaca import ALPACA_TIERS, AlpacaIexStream, settings_of
from liminal_plugin_alpaca.client import AlpacaClient, AlpacaSource, _ns, normalize_trade

from .conftest import FakeResponse, FakeSession

NOW = datetime(2026, 10, 21, 16, 0, tzinfo=timezone.utc)  # 12:00 ET
T0 = 1_792_764_000_000  # 2026-10-23 14:00 UTC (10:00 in New York), ms
KEYS = {"ALPACA_API_KEY_ID": "abc", "ALPACA_API_SECRET_KEY": "xyz"}


def _source(responses, keys=True, **kw):
    session = FakeSession(responses)
    client = AlpacaClient("KID", "SECRET", session=session, sleep=lambda s: None) if keys else \
        AlpacaClient(None, None, session=session, sleep=lambda s: None)
    return AlpacaSource(client, now=lambda: NOW, **kw), session


def test_stocks_without_keys_send_nothing():
    src, session = _source([], keys=False)
    with pytest.raises(NotEntitled):
        next(iter(src.bar_pages("AAPL", date(2026, 10, 20), date(2026, 10, 21), "minute")))
    assert session.calls == [] and not src.serves("stock") and src.serves("crypto")
    assert src.is_entitled("minute", "AAPL") is False and session.calls == []


def test_crypto_needs_no_key_and_asks_kraken_by_default():
    src, session = _source([FakeResponse(200, {"bars": {"BTC/USD": [
        {"t": "2026-10-20T00:00:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 3, "n": 4, "vw": 1.2}]},
        "next_page_token": None})], keys=False)
    pages = list(src.bar_pages("X:BTCUSD", date(2026, 10, 20), date(2026, 10, 20), "day", asset="crypto"))
    assert pages == [[{"t": 1792454400000, "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 3, "vw": 1.2, "n": 4}]]
    url, params, headers = session.calls[0]
    assert url == "https://data.alpaca.markets/v1beta3/crypto/us-1/bars"
    assert params["symbols"] == "BTC/USD" and params["timeframe"] == "1Day" and not headers
    assert params["start"] == "2026-10-20T00:00:00.000000Z" and params["end"] == "2026-10-21T00:00:00.000000Z"


def test_stock_window_stops_before_the_latest_15_minutes_and_pages_follow_tokens():
    src, session = _source([
        FakeResponse(200, {"bars": {"AAPL": [{"t": "2026-10-21T13:30:00Z", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1,
                                              "n": 1, "vw": 1}]}, "next_page_token": "TOKEN"}),
        FakeResponse(200, {"bars": {}, "next_page_token": None}),
    ])
    pages = list(src.bar_pages("AAPL", date(2026, 10, 21), date(2026, 10, 21), "minute", descending=True))
    assert len(pages) == 2 and len(session.calls) == 2
    (_, p1, h1), (_, p2, _) = session.calls
    assert h1 == {"APCA-API-KEY-ID": "KID", "APCA-API-SECRET-KEY": "SECRET"}
    assert "KID" not in str(p1) and "SECRET" not in str(p1)  # keys only ever in headers
    assert p1["end"] == "2026-10-21T15:44:00.000000Z"  # now - 16 min (plan blocks the latest 15)
    assert p1["feed"] == "sip" and p1["adjustment"] == "split" and p1["sort"] == "desc" and p1["limit"] == 10000
    assert p2["page_token"] == "TOKEN"


def test_window_entirely_inside_the_block_sends_nothing():
    src, session = _source([])
    assert list(src.bar_pages("AAPL", NOW - timedelta(minutes=5), NOW, "minute")) == []
    assert session.calls == []


def test_realtime_plan_has_no_block():
    src, session = _source([FakeResponse(200, {"bars": {}, "next_page_token": None})], realtime=True)
    list(src.bar_pages("AAPL", NOW - timedelta(minutes=5), NOW, "minute"))
    assert session.calls[0][1]["end"] == "2026-10-21T16:00:00.000000Z"


def test_trades_keep_nanoseconds_and_drop_withdrawn_ones():
    assert _ns("2022-01-03T09:00:00.086175744Z") == 1641200400086175744
    t = normalize_trade({"t": "2022-01-03T09:00:00.086175744Z", "x": "V", "p": 178.2, "s": 100, "c": ["@", "I"],
                         "i": 52983525034, "z": "C"})
    assert t["sip_timestamp"] == 1641200400086175744 and t["exchange"] == ord("V") and t["tape"] == 3
    other = normalize_trade({"t": "2022-01-03T09:00:00.086175744Z", "x": "Q", "p": 1, "s": 1, "i": 52983525034})
    assert other["sequence_number"] != t["sequence_number"]  # same id on another exchange stays distinct
    assert normalize_trade({"t": "2022-01-03T09:00:00Z", "x": "V", "p": 1, "s": 1, "i": 1, "u": "canceled"}) is None


def test_crypto_ticks_need_no_key():
    session = FakeSession([FakeResponse(200, {"trades": {"BTC/USD": [
        {"i": 7, "p": 81658, "s": 0.0004, "t": "2026-10-22T12:00:00.200261576Z", "tks": "B"}]}, "next_page_token": None})])
    src = AlpacaSource(AlpacaClient(None, None, session=session, sleep=lambda s: None),
                       now=lambda: datetime(2026, 10, 22, 13, 0, tzinfo=timezone.utc))
    s = 1_000_000_000
    pages = list(src.trade_pages("X:BTCUSD", gte_ns=1792670400 * s, lt_ns=1792674000 * s, descending=True))
    assert pages[0][0]["conditions"] == ["taker=B"] and pages[0][0]["tape"] is None
    assert pages[0][0]["sip_timestamp"] == 1792670400200261576


def test_reference_uses_the_trading_api_host_and_crypto_needs_none():
    src, session = _source([FakeResponse(200, {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ",
                                               "status": "active"})])
    inst = src.instrument("aapl")
    assert inst.name == "Apple Inc." and inst.primary_exchange.mic == "XNAS" and inst.active
    assert session.calls[0][0] == "https://paper-api.alpaca.markets/v2/assets/AAPL"
    pair = src.instrument("X:BTCUSD")
    assert pair.name == "BTC/USD on Kraken (US)" and len(session.calls) == 1


def test_keys_the_trading_api_refuses_lose_the_reference_record_only():
    session = FakeSession([FakeResponse(401, {"message": "unauthorized."}), FakeResponse(200, {"bars": {}}),
                           FakeResponse(401, {"message": "unauthorized."})])
    client = AlpacaClient("KID", "SECRET", session=session, sleep=lambda s: None)
    with pytest.raises(NotEntitled, match="ALPACA_PAPER"):  # paper keys on the live API, or the reverse
        client.get(f"{client.trading_url}/v2/assets/AAPL")
    with pytest.raises(NotEntitled, match="nothing sent"):
        client.get(f"{client.trading_url}/v2/assets/MSFT")
    assert client.get("/v2/stocks/bars") == {"bars": {}}  # the data API still answers
    with pytest.raises(Unauthorized):  # the data API refusing them is the keys refused
        client.get("/v2/stocks/bars")
    assert len(session.calls) == 3


def _trade(i: int, price: float, size: int, iso: str) -> dict:
    return {"T": "t", "S": "AAPL", "i": i, "x": "V", "p": price, "s": size, "c": ["@"], "t": iso, "z": "C"}


def test_iex_messages_become_trades_withdrawals_and_refusals():
    s = AlpacaIexStream("PKTESTKEY", "test-secret")
    (auth,) = s.subscribe(())
    assert json.loads(auth) == {"action": "auth", "key": "PKTESTKEY", "secret": "test-secret"}
    assert "test-secret" not in repr(s) and "PKTESTKEY" not in repr(s)  # never printed
    assert s.parse([{"T": "success", "msg": "connected"}, {"T": "success", "msg": "authenticated"}]) == [] and s.authed
    s.parse([{"T": "subscription", "trades": ["AAPL", "MSFT"], "quotes": [], "bars": []}])
    assert s.confirmed == {"AAPL", "MSFT"}
    assert [json.loads(m)["action"] for m in s.change({"TSLA"}, {"MSFT"})] == ["unsubscribe", "subscribe"]

    ((ticker, t),) = s.parse([_trade(1, 230.0, 100, "2026-10-23T14:00:01.123456789Z")])
    assert ticker == "AAPL" and t["sip_timestamp"] == (T0 + 1123) * 1_000_000 + 456_789
    assert t["exchange"] == ord("V") and t["tape"] == 3 and t["sequence_number"] == (1 << 6) | (ord("V") & 63)

    ((_, gone),) = s.parse({"T": "x", "S": "AAPL", "i": 1, "x": "V", "p": 230.0, "s": 100, "a": "C",
                            "t": "2026-10-23T14:00:01.123456789Z", "z": "C"})
    assert gone["withdrawn"] and gone["sequence_number"] == t["sequence_number"]
    was, now = s.parse({"T": "c", "S": "AAPL", "x": "V", "oi": 3, "op": 10.0, "os": 5, "oc": ["@"], "ci": 4,
                        "cp": 10.5, "cs": 5, "cc": ["@"], "t": "2026-10-23T14:00:02Z", "z": "C"})
    assert was[1]["withdrawn"] and was[1]["price"] == 10.0 and not now[1].get("withdrawn") and now[1]["price"] == 10.5

    with pytest.raises(stream.Refused) as refused:
        s.parse([{"T": "error", "code": 402, "msg": "auth failed"}])
    assert refused.value.wait == 600  # bad keys: not tried again for ten minutes
    with pytest.raises(stream.Notice):
        s.parse([{"T": "error", "code": 405, "msg": "symbol limit exceeded"}])  # the connection stays


def test_its_settings_are_its_own_read_with_the_apps_and_a_bad_value_stops_the_app():
    s = load_settings(env={**KEYS, "ALPACA_PAPER": "0"}, env_file=None)
    own = s.plugin("alpaca")
    assert own.has_keys and not own.paper and own.tier.name == "alpaca-basic" and own.feed == "sip"
    assert "abc" not in repr(own) and "xyz" not in repr(own)  # never printed
    assert s.plugin("boats") is None and s.for_source("boats").plugin("alpaca") is own  # the part reads Alpaca's
    feed = s.for_source("alpaca")
    assert feed.tier.name == "alpaca-basic" and feed.max_requests_per_day == 30000 and s.tier.name != "alpaca-basic"
    src = build_source("alpaca", s, request_budget=5)
    assert src.client.trading_url == "https://api.alpaca.markets" and src.client.request_budget == 5
    assert src.feed == "sip" and src.crypto_loc == "us-1" and not src.realtime
    plus = settings_of({**KEYS, "ALPACA_PLAN": "algo_trader_plus", "ALPACA_RPM": "500", "ALPACA_CRYPTO_LOC": "us",
                        "ALPACA_MAX_REQUESTS_PER_DAY": "99"})
    assert (plus.tier.name, plus.tier.requests_per_minute, plus.crypto_loc, plus.max_requests_per_day) == ("alpaca-plus", 500, "us", 99)
    assert settings_of({"APCA_API_KEY_ID": " a\n", "APCA_API_SECRET_KEY": "b"}).key_id == "a"  # Alpaca's own names; stripped
    for bad in ({"ALPACA_FEED": "nasdaq"}, {"ALPACA_PLAN": "platinum"}, {"ALPACA_CRYPTO_LOC": "mars"},
                {"ALPACA_MAX_REQUESTS_PER_RUN": "-1"}):
        with pytest.raises(ConfigError):
            settings_of(bad)
        with pytest.raises(ConfigError):
            load_settings(env=bad, env_file=None)  # the app's settings refuse it too, as they load


def test_the_app_loads_its_two_feeds_from_this_package_with_its_own_version():
    registry.reload()
    assert [p.name for p in alpaca.PLUGINS] == ["alpaca", "boats"] and not hasattr(alpaca, "PLUGIN")
    for name in ("alpaca", "boats"):
        p = provider(name)
        assert p is not None, dict(registry.errors())
        assert p.origin in {"package: liminal-plugin-alpaca (liminal_plugin_alpaca)", "plugins/liminal-plugin-alpaca (liminal_plugin_alpaca)"}  # its package, or its checkout in the workspace\'s plugin directory
        assert p.version == version("liminal-plugin-alpaca") and p.api == "1.11"
        assert registry.api_refusal(p.api) is None
    assert alpaca.ALPACA.version == "" and alpaca.BOATS.version == "" and alpaca.ALPACA.settings is settings_of
    assert not [why for where, why in registry.errors() if "alpaca" in where or "alpaca" in why]
    row = {r["name"]: r for r in registry.menu()}["alpaca"]
    assert (row["version"], row["api"]) == (version("liminal-plugin-alpaca"), "1.11")
    assert registry.plugin_feeds("alpaca") == ["alpaca", "boats"] and registry.plugin_of("boats") == "alpaca"


def test_it_keeps_the_facts_it_had_built_in():
    registry.reload()
    s = load_settings(env=KEYS, env_file=None)
    view = s.for_source("alpaca")
    assert (view.tier, view.max_requests_per_run, view.max_requests_per_day) == (ALPACA_TIERS["basic"], 3000, 30000)
    assert rate_window("alpaca", s) == (190, 60.0) and rate_window("boats", s) == rate_window("alpaca", s)
    assert s.for_source("boats").max_requests_per_day == 30000  # one account: Alpaca's caps and window
    assert markets("alpaca", s) == {"stock": "sip", "crypto": "kraken"} and markets("boats", s) == {"stock": "boats"}
    assert supports("alpaca", resolve("AAPL")) and supports("alpaca", resolve("BTCUSD"))
    assert composite.feed_kind("alpaca", "stock") == "consolidated" and composite.feed_kind("alpaca", "crypto") == "exchange"
    none = feed_profiles(load_settings(env={}, env_file=None))
    assert none["alpaca"].assets == {"crypto"} and not none["boats"].assets  # crypto needs no key
    keyed = feed_profiles(s)
    assert keyed["alpaca"].assets == {"stock", "crypto"} and keyed["alpaca"].venues == {"stock": "sip", "crypto": "kraken"}
    p, boats = provider("alpaca"), provider("boats")
    assert [k.name for k in p.keys] == ["ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY"] and p.keys[0].aliases == ("APCA_API_KEY_ID",)
    assert p.keyless == {"crypto"} and p.plan_choices == {"ALPACA_PLAN": ("basic", "algo_trader_plus")}
    assert (boats.title, boats.part_of, boats.account, boats.partial) == ("Blue Ocean", "alpaca", "alpaca", True)
    assert [(f.name, f.asset, f.partial) for f in p.live] == [("iex", "stock", True)]
    assert p.live[0].credentials(s) == ("abc", "xyz") and p.live[0].credentials(load_settings(env={}, env_file=None)) is None

    class Scanned:  # the plan from what the account is served: the latest 15 minutes tell Algo Trader Plus
        def __init__(self, recent):
            self.recent = recent

        def is_entitled(self, resolution, ticker, asset="stock"):
            return True

        def recent_allowed(self, ticker="AAPL"):
            return self.recent

    assert p.run_scan(Scanned(True)).plan == {"ALPACA_PLAN": "algo_trader_plus"}
    assert p.run_scan(Scanned(False)).plan == {"ALPACA_PLAN": "basic"}
