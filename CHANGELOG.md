# Changelog

## 0.3.0 (2026-11-11)

Its APIs on its page (plugin API 2.2, liminal-libs 1.49.0; the user: "each plugin should reflect the the API its
attached to, and present links that provide documentation, the plugin interface should more or less contain what it
already has, BUT, it should also expose more of what the API is about"). Both feeds declare the same three cards
(`apis`, from `apis.py`, set on `AlpacaFeed`), as Alpaca's pages said on 2026-11-11: the Market Data API
(`MARKET_DATA`: its limits, 200 requests a minute on Basic and 10,000 on Algo Trader Plus, its prices, 9 parts of
which 3 are used here, 18 calls of which the 5 made here), the Trading API (`TRADING`: an asset's record the one call
of its 10 made here, the order and position calls that would trade real money marked as such and never made) and the
market data stream (`STREAM`: its feeds and other streams, 8 parts, and its messages, 23, the 9 sent or read here).
Each card has Alpaca's pages: the documentation, the reference, guides, authentication, the subscription plans,
pricing, status, the dashboard, the Python SDK. The IEX stream's address is the stream card's (`STREAM_URL`).
`signup` is the dashboard's address (a link on the Plugins view). `api_facts` says nothing (the contract's): the
plugin holds no run's state. Tests: the cards name every request the feeds make, by host, and none they do not; the
stream's card names the messages it sends and exactly the kinds it reads; every address on them answers (with
`LIMINAL_VENDOR_PAGES=1`). Nothing it fetches changed. Requires liminal-libs 1.49.0.

## 0.2.0 (2026-11-03)

Renamed `plugin-integrator-alpaca` (the package `plugin_integrator_alpaca`; it was `liminal-plugin-alpaca`) on 2026-11-03: the naming by system (plugins are `plugin-<app>-<name>`), on liminal-libs 1.4.0 (`liminal_libs`, the library renamed with it).

Classes on plugin API 2.0 (liminal-libs 1.3.0; the user: "all the plugins under liminal should basically
follow inheritance/oop paradigm"), versioned 0.2.0 with Liminal's release (every distribution at 0.2.0 on
a `release/0.2.0` branch). The two feeds are `AlpacaPlugin` (`ALPACA`) and `BlueOcean` (`BOATS`, the
part: `part_of`, `partial`), both `AlpacaFeed`, the base holding what they declare and do alike (the
account's keys, `view`, `has_keys`, the plans' publication delays); what each declares is a class
attribute of the record field's name, what it does a method of the callback's (Alpaca's `settings`,
`build`, `markets`, `scan`, its IEX stream a `live` property signed in with `stream_keys`; Blue Ocean's
`build`, `rate`, `markets`, `scan`, once `build_boats` and `boats_scan`). The feeds declare what the
library's `freshness.py` held for them: `AlpacaFeed.delays` (the alpaca-basic and alpaca-plus rows) and
`BlueOcean.hours` (its market's overnight hours). Nothing they do changed: the same settings, requests,
scans, strings and limits.

## 1.4.1 (2026-11-02)

The plugin imports the library as `liminal_libs` and depends on liminal-libs (the app, renamed liminal-charts, is no longer needed to run the tests; the user, 2026-11-02: "lets rename the app to liminal-charts").

## 1.4.0 (2026-11-01)

- Released as its own package, `plugin-integrator-alpaca`, registered under the entry point group
  `liminal.providers` (a module of two feeds: `alpaca`, `boats`); its version is the distribution's.
- Its settings are its own (plugin API 1.11, `Provider.settings`): the keys, plan (`ALPACA_TIERS`),
  feed, crypto venue, paper or live host and request caps once in the app's `config.py`
  (`AlpacaSettings`, `settings.alpaca`) are read from the variables the app loads and reached with
  `settings.plugin("alpaca")`.

## 1.3.0 (2026-10-31)

- Built into the app (then massive-collate): its IEX stream and its client in its module (plugin
  API 1.6).

## 1.2.0 and before

- Built into the app (then massive-collate); Blue Ocean's overnight feed joined it (plugin API
  1.5); see the app's history.
