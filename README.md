# liminal-plugin-alpaca

Alpaca (alpaca.markets) for [Liminal](https://github.com/pcxmac-dev/liminal-app): one plugin, two feeds on
one account's keys:

- `alpaca`: US stocks on the consolidated tape (SIP) from 2016, minute and day bars, the session up
  to 15 minutes ago on the free Basic plan (real time on Algo Trader Plus; the plugin's scan tells
  them apart), and IEX's trades live for the symbols open on a chart (`iex`, alpaca (iex)); crypto
  minute and day bars from Kraken's book without any key;
- `boats` (Blue Ocean): US stocks overnight, 20:00-04:00 ET, Sunday to Thursday nights, Blue Ocean
  ATS through Alpaca's API, a feed of its own on the same keys and limits.

Both feeds share the account's limits: one rate window, one daily cap.

A Liminal provider plugin released on its own. The app finds it through the entry point group
`liminal.providers` and lists it on the Plugins view and in `liminal plugins`
as `package: liminal-plugin-alpaca`, with this package's version.

## Settings

User environment variables, saved with the app's `tools/set-key.ps1` or on the Plugins view; keys
are only ever read from the environment and never written to a file. They are the plugin's own
settings (plugin API 1.11), read when the app's settings load:

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
.venv\Scripts\python.exe -m pip install "liminal-plugin-alpaca @ git+https://github.com/pcxmac-dev/liminal-plugin-alpaca@v1.4.1"
```

or with the app's plugins (`pip install -e ".[plugins]"` in liminal-app). The app loads it on its next
start.

## Compatibility

It is written for plugin API 1.11 (`PLUGIN.api`: a plugin's own settings). An app offering 1.11 or a
later 1.x loads it; an app of another major, or one older than 1.11, leaves it out and says why on
the Plugins view.

## Develop

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install "liminal-lib @ git+https://github.com/pcxmac-dev/liminal-lib@main"
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest -q
```

Tests never send requests (a fake session answers) and never read your keys.
