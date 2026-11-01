# Changelog

## 1.4.0 (2026-11-01)

- Released as its own package, `liminal-plugin-alpaca`, registered under the entry point group
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
