"""What Alpaca's plugin attaches to (plugin API 2.2, apis.py): three sound cards (the Market Data API, the Trading API,
the market data stream) for its day sessions and Blue Ocean's nights alike, their calls the ones the plugin really makes
(a recording session answers every request; the stream's messages are its own), and nothing asked to say what it
learned (api_facts). With LIMINAL_VENDOR_PAGES=1, every address on the cards is asked once: the one test here that
sends anything (the plugins' page check)."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import pytest

from liminal_libs.sources import registry, stream
from liminal_libs.sources.apis import dead_links, problems, urls
from plugin_integrator_alpaca import ALPACA, BOATS, AlpacaIexStream
from plugin_integrator_alpaca.apis import APIS, DASHBOARD, MARKET_DATA, STREAM, STREAM_URL, TRADING
from plugin_integrator_alpaca.client import DATA_URL, TRADING_URLS, AlpacaClient, AlpacaSource, BoatsSource

from .conftest import FakeResponse

NOW = datetime(2026, 11, 10, 17, 0, tzinfo=timezone.utc)  # 12:00 in New York
TRADING_HOSTS = {urlparse(u).netloc for u in TRADING_URLS.values()}


class Recording:
    """Answers every request (an asset's record on the Trading API, the exchange codes, an empty page otherwise) and
    records it with its parameters."""

    def __init__(self):
        self.asked: list[tuple[str, str, dict]] = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.asked.append(("GET", url, dict(params or {})))
        if urlparse(url).netloc in TRADING_HOSTS:
            body = {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "status": "active"}
        elif url.endswith("/v2/stocks/meta/exchanges"):
            body = {"V": "IEX"}
        else:
            body = {"bars": {}, "trades": {}, "next_page_token": None}
        return FakeResponse(200, body)


def _pattern(template: str) -> re.Pattern:
    """A call's path as a pattern: each {placeholder} one path segment."""
    return re.compile("[^/]+".join(re.escape(part) for part in re.split(r"\{[^}]*\}", template)))


def _call_of(method: str, url: str) -> tuple[str, str] | None:
    """(the card, the call) a request is, by its host and path; None when no card names it."""
    host, path = urlparse(url).netloc, urlparse(url).path
    api = MARKET_DATA if host == urlparse(DATA_URL).netloc else TRADING if host in TRADING_HOSTS else None
    for call in api.calls if api else ():
        verb, _, template = call.name.partition(" ")
        if verb == method and _pattern(template).fullmatch(path):
            return api.name, call.name
    return None


def _every_request(session: Recording) -> None:
    """Every request the two feeds make, each kind once: bars, trades, the exchanges, a record, the scans."""
    client = AlpacaClient("KID", "SECRET", session=session, sleep=lambda s: None)
    day, ns = NOW.date(), lambda t: int(t.timestamp() * 1e9)
    src = AlpacaSource(client, now=lambda: NOW)
    list(src.bar_pages("AAPL", day - timedelta(days=1), day, "minute"))
    list(src.bar_pages("X:BTCUSD", day - timedelta(days=1), day, "day", asset="crypto"))
    list(src.trade_pages("AAPL", gte_ns=ns(NOW - timedelta(hours=2)), lt_ns=ns(NOW - timedelta(hours=1))))
    list(src.trade_pages("X:BTCUSD", gte_ns=ns(NOW - timedelta(hours=2)), lt_ns=ns(NOW - timedelta(hours=1))))
    src.exchanges()
    src.instrument("AAPL")
    ALPACA.scan(src)  # the tape's minutes, crypto's, the latest 15 minutes
    nights = BoatsSource(client, now=lambda: NOW)
    list(nights.bar_pages("AAPL", day - timedelta(days=1), day, "minute"))
    BOATS.scan(nights)


def test_its_cards_name_every_call_it_makes_and_none_it_does_not():
    session = Recording()
    _every_request(session)
    unnamed = [f"{m} {u}" for m, u, _ in session.asked if _call_of(m, u) is None]
    assert unnamed == []  # every request it made is a call on a card, on the card of its host
    made = {_call_of(m, u) for m, u, _ in session.asked}
    used = {(api.name, c.name) for api in (MARKET_DATA, TRADING) for c in api.used}
    assert made == used  # and every call the cards say it makes, it makes
    assert {p.get("feed") for m, u, p in session.asked if u.endswith("/v2/stocks/bars")} >= {"sip", "boats"}


TRADE = {"T": "t", "S": "AAPL", "i": 1, "x": "V", "p": 230.0, "s": 100, "c": ["@"], "t": "2026-11-10T15:00:01Z", "z": "C"}
SAMPLES = {  # a message of each kind the stream's card names (its docs' types)
    "success": {"T": "success", "msg": "authenticated"},
    "subscription": {"T": "subscription", "trades": ["AAPL"]},
    "t": TRADE,
    "c": {"T": "c", "S": "AAPL", "x": "V", "oi": 3, "op": 10.0, "os": 5, "oc": ["@"], "ci": 4, "cp": 10.5, "cs": 5,
          "cc": ["@"], "t": "2026-11-10T15:00:02Z", "z": "C"},
    "x": {**TRADE, "T": "x", "a": "C"},
    "error": {"T": "error", "code": 406, "msg": "connection limit exceeded"},
    "q": {"T": "q", "S": "AAPL", "bp": 229.9, "ap": 230.1, "t": "2026-11-10T15:00:01Z"},
    "b": {"T": "b", "S": "AAPL", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1, "t": "2026-11-10T15:00:00Z"},
    "d": {"T": "d", "S": "AAPL", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1, "t": "2026-11-10T05:00:00Z"},
    "u": {"T": "u", "S": "AAPL", "o": 1, "h": 1, "l": 1, "c": 1, "v": 1, "t": "2026-11-10T15:00:00Z"},
    "l": {"T": "l", "S": "AAPL", "u": 240.0, "d": 220.0, "t": "2026-11-10T15:00:00Z"},
    "s": {"T": "s", "S": "AAPL", "sc": "H", "t": "2026-11-10T15:00:00Z"},
    "i": {"T": "i", "S": "AAPL", "p": 230.0, "t": "2026-11-10T15:00:00Z"},
}


def _acts_on(message: dict) -> bool:
    """Whether the stream does anything with a message: a trade out, its state changed, or the session ended."""
    s = AlpacaIexStream("KID", "SECRET")
    try:
        out = s.parse([message])
    except (stream.Refused, stream.Notice):
        return True
    return bool(out) or s.authed or bool(s.confirmed)


def test_the_stream_card_names_what_it_sends_and_what_it_reads():
    s = AlpacaIexStream("KID", "SECRET")
    assert s.url == STREAM_URL == STREAM.base and STREAM.kind == "stream"
    sent = [json.loads(m) for m in (*s.subscribe(()), *s.change({"TSLA"}, {"MSFT"}))]
    names = {" ".join(["send", m["action"], *sorted(k for k in m if k not in ("action", "key", "secret"))]) for m in sent}
    sends = {c.name for c in STREAM.calls if c.name.startswith("send ")}
    assert names == {c.name for c in STREAM.used if c.name in sends} == {"send auth", "send subscribe trades",
                                                                         "send unsubscribe trades"}
    for call in STREAM.calls:
        if call.name.startswith("message "):
            kind = call.name.removeprefix("message ").split(":")[0]
            assert _acts_on(SAMPLES[kind]) == bool(call.used), call.name  # read when the card says so, else let by


def test_three_sound_cards_for_its_two_feeds():
    assert APIS == (MARKET_DATA, TRADING, STREAM) and ALPACA.apis is APIS and BOATS.apis is APIS
    assert problems(APIS, today=NOW.date()) == []
    assert MARKET_DATA.base == DATA_URL and TRADING.base.startswith(TRADING_URLS[True])
    assert MARKET_DATA.docs == "https://docs.alpaca.markets/us/docs/about-market-data-api"
    assert ALPACA.signup == DASHBOARD == MARKET_DATA.link("console") == TRADING.link("console") == BOATS.signup
    for api in APIS:
        assert {"docs", "pricing" if api is not TRADING else "guide", "status"} <= {x.kind for x in api.links}
        parts = {a.name for a in api.areas}
        assert all(c.area in parts for c in api.calls) and api.verified == "2026-11-11"
    assert {a.name for a in MARKET_DATA.areas} >= {"Stocks", "Crypto", "Options", "News", "Corporate actions"}
    costly = [(api.name, c.name) for api in APIS for c in api.calls if c.costs]
    assert costly == [("Alpaca Trading API", "POST /v2/orders"), ("Alpaca Trading API", "DELETE /v2/positions/{symbol_or_asset_id}")]
    assert not [c for api in APIS for c in api.used if c.writes or c.costs]  # it only reads: no order, nothing billed
    assert all(u.startswith("https://") for u in urls(APIS))


def test_it_asks_nothing_to_say_what_it_learned():
    assert ALPACA.api_facts() == {} and BOATS.api_facts() == {}  # the instances hold no run's state
    registry.reload()
    p, nights = registry.providers()["alpaca"], registry.providers()["boats"]
    assert p.apis == APIS == nights.apis
    assert p.interface()["apis"] == ["Alpaca Market Data API", "Alpaca Trading API", "Alpaca market data stream"]


@pytest.mark.skipif(os.environ.get("LIMINAL_VENDOR_PAGES") != "1", reason="asks Alpaca's pages (LIMINAL_VENDOR_PAGES=1)")
def test_every_address_on_its_cards_answers():
    assert dead_links(APIS) == []
