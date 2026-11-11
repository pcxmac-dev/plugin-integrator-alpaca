# plugin-integrator-alpaca

Alpaca (alpaca.markets) for [Liminal](https://github.com/pcxmac-dev/liminal-charts): one plugin, two feeds on
one account's keys:

- `alpaca`: US stocks on the consolidated tape (SIP) from 2016, minute and day bars, the session up
  to 15 minutes ago on the free Basic plan (real time on Algo Trader Plus; the plugin's scan tells
  them apart), and IEX's trades live for the symbols open on a chart (`iex`, alpaca (iex)); crypto
  minute and day bars from Kraken's book without any key;
- `boats` (Blue Ocean): US stocks overnight, 20:00-04:00 ET, Sunday to Thursday nights, Blue Ocean
  ATS through Alpaca's API, a feed of its own on the same keys and limits.

Both feeds share the account's limits: one rate window, one daily cap.

A Liminal provider plugin released on its own: a class each on the class contract (plugin API 2.2),
`AlpacaPlugin` and `BlueOcean`, both `AlpacaFeed` (a `FeedPlugin`, what the two share). The app finds it
through the entry point group `liminal.providers` and lists it on the Plugins view and in
`liminal-charts plugins` as `package: plugin-integrator-alpaca`, with this package's version.

## Its API

Both feeds attach to three of Alpaca's APIs, the keys sent as the `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`
headers: the Market Data API at `https://data.alpaca.markets` (bars, trades, the exchange codes), the Trading API at
`https://paper-api.alpaca.markets` or `https://api.alpaca.markets` (an asset's record, nothing else), and the market
data stream at `wss://stream.data.alpaca.markets/v2/iex` (IEX's trades). The cards on its page in every app (`apis`,
plugin API 2.2: `src/plugin_integrator_alpaca/apis.py`, read from Alpaca's pages on 2026-11-11) say what each API is,
its limits and prices, every part of it and every call or message used here:

- Documentation: <https://docs.alpaca.markets/us/docs/about-market-data-api>, the reference from
  <https://docs.alpaca.markets/us/reference/stockbars>, the Trading API at
  <https://docs.alpaca.markets/us/docs/trading-api>, the streams at
  <https://docs.alpaca.markets/us/docs/streaming-market-data>
- Plans and pricing: <https://alpaca.markets/data> (Basic, free: 200 requests a minute, the consolidated tape up to
  15 minutes ago; Algo Trader Plus, $99 a month: 10,000 a minute, all of it live)
- Status: <https://status.alpaca.markets/>
- Dashboard (API keys): <https://app.alpaca.markets>

Used here: stocks' bars and trades (SIP or IEX; Blue Ocean's nights with `feed=boats`), crypto's bars and trades, the
exchange codes, an asset's record, and IEX's trades live. Not used: quotes, snapshots, auctions, options, news,
corporate actions, the screener, logos, fixed income, the other streams, and everything of the Trading API but the
assets (no order is ever placed).

## Settings

User environment variables, saved with the app's `tools/set-key.ps1` or on the Plugins view; keys
are only ever read from the environment and never written to a file. They are the plugin's own
settings (the plugin's `settings` hook), read when the app's settings load:

| Variable | Meaning |
| --- | --- |
| `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY` | a paper account's API keys (Alpaca's own `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` also work); without them only crypto is collected |
| `ALPACA_PLAN` | `basic` (default) or `algo_trader_plus`; the scan finds it where you set none |
| `ALPACA_RPM` | override the plan's requests a minute |
| `ALPACA_FEED` | `sip` (every US exchange, default) or `iex` |
| `ALPACA_CRYPTO_LOC` | `us-1` (Kraken, default), `eu-1` (Kraken EU) or `us` (Alpaca's own venue) |
| `ALPACA_PAPER` | `1` (default): paper-trading keys; `0`: live keys (the host asked for reference data) |
| `ALPACA_MAX_REQUESTS_PER_RUN`, `ALPACA_MAX_REQUESTS_PER_DAY` | hard caps (default 3000 / 30000) |

## Install

Into the app's environment, from the app's folder:

```powershell
.venv\Scripts\python.exe -m pip install "plugin-integrator-alpaca @ git+https://github.com/pcxmac-dev/plugin-integrator-alpaca@v0.3.0"
```

or with the app's plugins (`pip install -e ".[plugins]"` in liminal-charts). The app loads it on its next
start.

## Compatibility

It is written for plugin API 2.2 (each feed's `api`: the class contract of liminal-libs 1.3.0, a plugin
an instance of a `FeedPlugin` subclass, with the API cards of liminal-libs 1.49.0). An app offering 2.2 or a
later 2.x loads it; an app offering an older 2.x, or another major, leaves it out and says why on the Plugins
view.

## Develop

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install "liminal-libs @ git+https://github.com/pcxmac-dev/liminal-libs@release/0.2.0"
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest -q
```

Tests never send requests (a fake session answers) and never read your keys. One test asks every address on the
APIs' cards, only with `LIMINAL_VENDOR_PAGES=1` set.
