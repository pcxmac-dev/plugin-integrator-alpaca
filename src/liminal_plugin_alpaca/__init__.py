"""Alpaca (alpaca.markets) for Liminal: US stocks with keys (SIP from 2016, IEX live), crypto without;
and Blue Ocean's overnight session through the same keys, a feed of its own (BOATS).

A Liminal plugin released on its own (liminal.sources.registry: Provider), registered under the entry
point group `liminal.providers` as `alpaca`: one plugin, two feeds (PLUGINS: `alpaca`, `boats`). Its
keys, plan, feed, crypto venue, paper or live host and request caps are its own settings
(AlpacaSettings, from the variables the app read: Provider.settings, plugin API 1.11), reached with
`settings.plugin("alpaca")` by both feeds. It relies on plugin API 1.11 and nothing of the app
outside the contract (docs/ARCHITECTURE.md in liminal: "Providers are plugins"); its version is this
distribution's (pyproject.toml), so the records' versions are left empty.

Its scan finds the plan: Algo Trader Plus serves the consolidated tape's latest 15 minutes, Basic
refuses them; it sets ALPACA_PLAN where you have not.

Blue Ocean ATS (blueocean-tech.io) through Alpaca (the user, 2026-10-29: "the Blue Ocean plugin is
part of alpaca"): US stocks overnight, 20:00-04:00 ET, Sunday to Thursday nights; the fourth session
(the app's sessions.py). Its own market, the only venue trading then, so its own feed (`boats`: its
database, ledgers and watchlist rows), listed and rescanned inside this plugin (Provider.part_of). It
uses Alpaca's keys and shares Alpaca's limits (the same account): one rate window and one daily cap
for both feeds, so together they stay within the free Basic plan. (Tiingo has it too, as a paid
add-on: the Tiingo plugin's scan reports it.)

Settings (user environment variables; keys are only ever read from the environment):
    ALPACA_API_KEY_ID, ALPACA_API_SECRET_KEY   (Alpaca's own APCA_API_KEY_ID / APCA_API_SECRET_KEY
                      also work). Without them only crypto is collected (it needs no key).
    ALPACA_PLAN       basic | algo_trader_plus   (default: basic; the scan finds it)
    ALPACA_RPM        override the plan's requests-per-minute limit
    ALPACA_FEED       sip (all US exchanges, default) | iex
    ALPACA_CRYPTO_LOC us-1 (Kraken, default) | eu-1 (Kraken EU) | us (Alpaca's own venue)
    ALPACA_PAPER      1 (default): keys are paper-trading keys; 0: live keys (decides the host
                      asked for reference data; market data is the same either way)
    ALPACA_MAX_REQUESTS_PER_RUN / ALPACA_MAX_REQUESTS_PER_DAY   hard caps (default: 3000 / 30000)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Mapping

from liminal.config import ConfigError, Tier
from liminal.sources.registry import KeyVar, Provider, Scanned, limiter, machine_caps
from liminal.sources.stream import PING, Live, Notice, Refused
from .client import PAGE_LIMIT, TRADING_URLS, AlpacaClient, AlpacaSource, BoatsSource, normalize_trade

IEX_FEED = "iex"  # its live stream's feed: IEX's trades, one venue's share (alpaca (iex))

# Alpaca market data plans (docs.alpaca.markets, Oct 2026). Basic is free: every US exchange (SIP)
# except the latest 15 minutes, 200 requests/min; both plans go back to 2016. A little under the
# published rate so the limiter never meets a 429.
ALPACA_TIERS: dict[str, Tier] = {
    "basic": Tier("alpaca-basic", requests_per_minute=190, history_years=None, history_start=date(2016, 1, 1)),
    "algo_trader_plus": Tier("alpaca-plus", requests_per_minute=9500, history_years=None,
                             history_start=date(2016, 1, 1)),
}
ALPACA_FEEDS = ("sip", "iex")
ALPACA_CRYPTO_LOCS = ("us-1", "eu-1", "us")


@dataclass(frozen=True)
class AlpacaSettings:
    """The plugin's own settings (Settings.plugin("alpaca")): its keys, plan, feed, crypto venue, host
    and caps, from the variables the app read (settings_of)."""
    key_id: str | None
    secret_key: str | None
    tier: Tier
    feed: str = "sip"
    crypto_loc: str = "us-1"
    paper: bool = True
    max_requests_per_run: int = 3000
    max_requests_per_day: int = 30000

    @property
    def has_keys(self) -> bool:
        return bool(self.key_id and self.secret_key)

    def __repr__(self) -> str:  # never print the keys
        return (f"AlpacaSettings(keys={'set' if self.has_keys else 'not set'}, tier={self.tier.name}, "
                f"feed={self.feed}, crypto_loc={self.crypto_loc}, paper={self.paper})")


def _key(variables: Mapping[str, str], *names: str) -> str | None:
    """A key's value from the first of its variables set, spaces and line breaks around it taken off
    (one pasted with a newline made every request fail, the key repeated in the error)."""
    for name in names:
        value = (variables.get(name) or "").strip()
        if value:
            return value
    return None


def _int(variables: Mapping[str, str], name: str) -> int | None:
    raw = (variables.get(name) or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError as e:
        raise ConfigError(f"{name} must be a whole number, got {raw!r}") from e
    if value < 0:
        raise ConfigError(f"{name} must not be negative")
    return value


def settings_of(variables: Mapping[str, str]) -> AlpacaSettings:
    """Provider.settings (plugin API 1.11): the plugin's settings from every variable the app read;
    a value it refuses is a ConfigError, which stops the app as any setting's does."""
    plan = (variables.get("ALPACA_PLAN") or "basic").strip().lower()
    if plan not in ALPACA_TIERS:
        raise ConfigError(f"Unknown ALPACA_PLAN {plan!r}; choose one of {', '.join(ALPACA_TIERS)}")
    tier = ALPACA_TIERS[plan]
    rpm = _int(variables, "ALPACA_RPM")
    if rpm is not None:
        tier = replace(tier, requests_per_minute=rpm or None)
    feed = (variables.get("ALPACA_FEED") or "sip").strip().lower()
    if feed not in ALPACA_FEEDS:
        raise ConfigError(f"Unknown ALPACA_FEED {feed!r}; choose one of {', '.join(ALPACA_FEEDS)}")
    loc = (variables.get("ALPACA_CRYPTO_LOC") or "us-1").strip().lower()
    if loc not in ALPACA_CRYPTO_LOCS:
        raise ConfigError(f"Unknown ALPACA_CRYPTO_LOC {loc!r}; choose one of {', '.join(ALPACA_CRYPTO_LOCS)}")
    per_run = _int(variables, "ALPACA_MAX_REQUESTS_PER_RUN")
    per_day = _int(variables, "ALPACA_MAX_REQUESTS_PER_DAY")
    return AlpacaSettings(
        key_id=_key(variables, "ALPACA_API_KEY_ID", "APCA_API_KEY_ID"),
        secret_key=_key(variables, "ALPACA_API_SECRET_KEY", "APCA_API_SECRET_KEY"),
        tier=tier, feed=feed, crypto_loc=loc,
        paper=(variables.get("ALPACA_PAPER") or "1").strip().lower() not in ("0", "false", "no"),
        max_requests_per_run=3000 if per_run is None else per_run,
        max_requests_per_day=30000 if per_day is None else per_day,
    )


def _own(settings) -> AlpacaSettings:
    a = settings.plugin("alpaca")
    if a is None:
        raise ConfigError("Alpaca settings missing")
    return a


def build(settings, request_budget):
    """Builds without keys too: crypto needs none, and stock requests are refused before sending."""
    a = _own(settings)
    client = AlpacaClient(a.key_id, a.secret_key, trading_url=TRADING_URLS[a.paper],
                          rate_limiter=limiter("alpaca", settings, a.key_id), request_budget=request_budget)
    return AlpacaSource(machine_caps(client, "alpaca", settings, a.key_id), feed=a.feed, crypto_loc=a.crypto_loc,
                        realtime=a.tier.name == "alpaca-plus")


def view(base):
    a = base.plugin("alpaca")
    if a is None:
        return base
    return replace(base, tier=a.tier, max_requests_per_run=a.max_requests_per_run,
                   max_requests_per_day=a.max_requests_per_day, origin=base)


def markets(settings):
    a = settings.plugin("alpaca")
    loc = a.crypto_loc if a else "us-1"
    return {"stock": a.feed if a else "sip", "crypto": "alpaca" if loc == "us" else "kraken"}


def has_keys(settings) -> bool:
    a = settings.plugin("alpaca")
    return bool(a and a.has_keys)


def scan(source) -> list[tuple[str, bool, str]] | Scanned:
    """What the plan gives (one request each): the consolidated tape's minute bars, crypto's, and
    with keys its latest 15 minutes, which tell the plans apart."""
    stocks = source.is_entitled("minute", "AAPL", "stock")
    crypto = source.is_entitled("minute", "BTCUSD", "crypto")
    rows = [("stock minute bars, every exchange (SIP), from 2016", stocks,
             "" if stocks else "refused (keys or plan)"),
            ("crypto minute bars, no key", crypto, "")]
    if not stocks:
        return rows  # no keys, or refused: nothing tells the plan
    recent = source.recent_allowed("AAPL")
    plan = "algo_trader_plus" if recent else "basic"
    rows.append(("stock bars of the latest 15 minutes (Algo Trader Plus)", recent,
                 f"plan: {'Algo Trader Plus' if recent else 'Basic (free)'}"))
    return Scanned(tuple(rows), {"ALPACA_PLAN": plan})


# Alpaca stream errors that end the session, and the seconds to wait before connecting again:
# 401 not authenticated, 402 auth failed, 404 auth timeout, 406 connection limit exceeded (another
# connection on the account), 407 slow client, 409 insufficient subscription, 500 internal error.
ALPACA_REFUSALS = {401: 60, 402: 600, 404: 60, 406: 120, 407: 60, 409: 3600, 500: 60}


@dataclass
class AlpacaIexStream:
    """Alpaca's free real-time stock stream (v2/iex): every trade on IEX, with cancels and
    corrections (the trades they withdraw are marked `withdrawn`). The keys go in the auth
    message only, never in a log. Its symbols change while it is connected (`change`), once the
    server has accepted the keys; `confirmed` holds those the server says it streams."""
    key_id: str = field(default="", repr=False)
    secret_key: str = field(default="", repr=False)
    source: str = IEX_FEED
    url: str = "wss://stream.data.alpaca.markets/v2/iex"
    keepalive: str | None = PING
    dynamic: bool = True  # symbols from the charts (and watchlists: wanted_stocks), not LIVE_COINS
    asset: str = "stock"
    tape_rules: bool = True  # bars by the consolidated tape's rules per trade condition (the app's ticks.py)
    method: str = ("IEX's trades from Alpaca's real-time stream: one exchange, a few per cent of US volume; "
                   "bars rebuilt as trades arrive (a forming bar changes until it closes), by the consolidated "
                   "tape's rules per trade condition; a feed of the whole market (SIP) ranks above them")
    authed: bool = False
    confirmed: frozenset = frozenset()

    def subscribe(self, symbols) -> list[str]:
        """The first messages on a new connection: the keys (symbols follow once accepted)."""
        self.authed, self.confirmed = False, frozenset()
        return [json.dumps({"action": "auth", "key": self.key_id, "secret": self.secret_key})]

    def change(self, add, drop) -> list[str]:
        out = []
        if drop:
            out.append(json.dumps({"action": "unsubscribe", "trades": sorted(drop)}))
        if add:
            out.append(json.dumps({"action": "subscribe", "trades": sorted(add)}))
        return out

    def parse(self, msg) -> list[tuple[str, dict]]:
        out = []
        for m in msg if isinstance(msg, list) else [msg]:
            kind = m.get("T")
            if kind == "t":
                t = normalize_trade(m)
                if t:
                    out.append((m["S"], t))
            elif kind == "x":  # a trade withdrawn: canceled, or an error
                out.append((m["S"], {**normalize_trade(m), "withdrawn": True}))
            elif kind == "c":  # a correction: the original trade withdrawn, the corrected one in its place
                base = {"x": m["x"], "t": m["t"], "z": m.get("z")}
                was = normalize_trade({**base, "i": m["oi"], "p": m["op"], "s": m["os"], "c": m.get("oc")})
                out.append((m["S"], {**was, "withdrawn": True}))
                out.append((m["S"], normalize_trade({**base, "i": m["ci"], "p": m["cp"], "s": m["cs"], "c": m.get("cc")})))
            elif kind == "subscription":
                self.confirmed = frozenset(m.get("trades") or [])
            elif kind == "success" and m.get("msg") == "authenticated":
                self.authed = True
            elif kind == "error":
                code = int(m.get("code") or 0)
                text = f"alpaca {code}: {m.get('msg')}"
                if code in ALPACA_REFUSALS:
                    raise Refused(text, ALPACA_REFUSALS[code])
                raise Notice(text)
        return out


def stream_keys(settings) -> tuple[str, str] | None:
    """Alpaca's keys for the IEX stream: None without keys, with LIVE_STOCKS=off, or offline."""
    a = settings.plugin("alpaca")
    if settings.offline or not settings.live_stocks or not (a and a.has_keys):
        return None
    return a.key_id, a.secret_key


ALPACA = Provider(
    api="1.11",  # the contract it needs (its own settings: Provider.settings); its version: the distribution's
    name="alpaca", title="Alpaca", build=build, assets=frozenset({"stock", "crypto"}), order=10,
    about="US stocks (SIP from 2016, the session up to 15 min ago, IEX live; overnight on Blue Ocean) with keys; "
          "crypto without",
    keys=(KeyVar("ALPACA_API_KEY_ID", "key ID", ("APCA_API_KEY_ID",)),
          KeyVar("ALPACA_API_SECRET_KEY", "secret key", ("APCA_API_SECRET_KEY",))),
    keyless=frozenset({"crypto"}), signup="alpaca.markets: a paper account's API keys",
    plan_vars=("ALPACA_PLAN",), limits="Basic (free): 200 requests per minute; Algo Trader Plus: 10,000",
    plan_choices={"ALPACA_PLAN": tuple(ALPACA_TIERS)},
    kind="exchange", kind_by_asset={"stock": "consolidated"},  # its stocks are the consolidated tape (SIP)
    venue_notes={"crypto": "one exchange's book (Kraken)"}, bulk_resolution="minute",
    provides={"stock": ("day", "minute"), "crypto": ("day", "minute")},  # no 1-second bars
    per_request={"day": 10_000, "minute": 10_000},  # PAGE_LIMIT
    streams={"stock": "real time, IEX's trades only (a few per cent of US volume), symbols open on a chart"},
    live=(Live(IEX_FEED, "stock", stream=AlpacaIexStream, credentials=stream_keys, label="alpaca (iex)",
               partial=True),),
    missing_keys_note="keys not set: US stocks (SIP from 2016, IEX live), options and news wait for "
                      "ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY; crypto needs no key and is collected",
    missing_keys_chip="stocks need keys",
    settings=settings_of, view=view, has_keys=has_keys, markets=markets, scan=scan,
)


def build_boats(settings, request_budget):
    a = _own(settings)
    # Alpaca's window and day cap, held for the machine under Alpaca's name: one account's limits
    client = AlpacaClient(a.key_id, a.secret_key, trading_url=TRADING_URLS[a.paper],
                          rate_limiter=limiter("alpaca", settings, a.key_id), request_budget=request_budget)
    return BoatsSource(machine_caps(client, "alpaca", settings, a.key_id), realtime=a.tier.name == "alpaca-plus")


def boats_scan(source) -> list[tuple[str, bool, str]]:
    """What the plan gives Blue Ocean (one request): last week's overnight minute bars of a busy stock."""
    ok = source.is_entitled("minute", "AAPL", "stock")
    return [("stock minute bars overnight (feed=boats)", ok,
             "Alpaca Basic: history up to 15 minutes ago" if ok else "refused by the plan")]


BOATS = Provider(
    api="1.11",  # this plugin's contract (part_of; partial; Alpaca's settings); its version: the distribution's
    name="boats", title="Blue Ocean", build=build_boats, assets=frozenset({"stock"}), order=15, account="alpaca",
    part_of="alpaca", partial=True,  # one venue's nights: never the whole market's
    about="US stocks overnight, 20:00-04:00 ET, Blue Ocean ATS through Alpaca (your Alpaca keys and limits)",
    keys=ALPACA.keys, signup=ALPACA.signup, kind="exchange",
    provides={"stock": ("minute",)}, per_request={"minute": PAGE_LIMIT},
    limits="shares Alpaca's: 200 requests per minute (Basic) for both feeds",
    missing_keys_note="keys not set: Blue Ocean's overnight bars come through Alpaca, with ALPACA_API_KEY_ID "
                      "and ALPACA_API_SECRET_KEY",
    view=view, rate=lambda settings: ALPACA.rate_window(settings),
    has_keys=has_keys,
    markets=lambda settings: {"stock": "boats"},
    scan=boats_scan,
)

PLUGINS = (ALPACA, BOATS)  # one plugin, two feeds: the day sessions (and crypto), and Blue Ocean's nights
