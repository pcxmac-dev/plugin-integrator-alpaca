"""What Alpaca's plugin attaches to (plugin API 2.2, liminal_libs.sources.apis): Alpaca's Market Data API, its Trading
API (an asset's record) and its market data stream (IEX's trades), as Alpaca's pages said on 2026-11-11
(docs.alpaca.markets/us and its index, docs.alpaca.markets/us/llms.txt; alpaca.markets/data). One set of cards for the
whole plugin, its day sessions (`alpaca`) and Blue Ocean's nights (`boats`) alike: the app draws a plugin's APIs and
its parts' once each, by name.

The user, 2026-11-11: "each plugin should reflect the the API its attached to, and present links that provide
documentation, the plugin interface should more or less contain what it already has, BUT, it should also expose more of
what the API is about". So every part of each API is named (`areas`), each said used here or not, and the calls the
plugin makes (`used`) beside the notable ones it does not."""
from __future__ import annotations

from liminal_libs.sources.apis import Api, Area, Call, Link

from .client import DATA_URL, TRADING_URLS

DOCS = "https://docs.alpaca.markets/us/docs"
REF = "https://docs.alpaca.markets/us/reference"
DASHBOARD = "https://app.alpaca.markets"  # where the keys are made (the plugin's `signup`)
PRICING = "https://alpaca.markets/data"
STATUS = "https://status.alpaca.markets/"
PLANS = f"{DOCS}/about-market-data-api#subscription-plans"
STREAM_URL = "wss://stream.data.alpaca.markets/v2/iex"  # AlpacaIexStream.url
STOCKS, CRYPTO, CLOCK = "Stocks", "Crypto", "Clock and calendar"


def _doc(page: str) -> str:
    return f"{DOCS}/{page}"


def _ref(page: str) -> str:
    return f"{REF}/{page}"


MARKET_DATA = Api(
    name="Alpaca Market Data API",
    maker="Alpaca",
    about=("Alpaca's Market Data API serves US stocks (the consolidated tape, IEX, Blue Ocean's overnight session and "
           "OTC venues), options, crypto, news, corporate actions, a screener and logos: historical bars, trades, quotes "
           "and snapshots over HTTPS, live data over WebSocket streams (the stream's card). The free Basic plan holds the "
           "consolidated tape back 15 minutes; Algo Trader Plus serves it live."),
    kind="rest",
    base=DATA_URL,
    version="v2 (stocks), v1beta3 (crypto)",
    auth=("an API key ID and secret key (a paper or a live account's, made on its dashboard), sent as the "
          "APCA-API-KEY-ID and APCA-API-SECRET-KEY headers (or HTTP Basic); crypto history needs none"),
    limits=("Basic (free): 200 historical requests a minute, the consolidated tape (SIP) up to 15 minutes ago; Algo "
            "Trader Plus: 10,000 a minute, no restriction; up to 10,000 data points a page, for all symbols asked; its "
            "answers carry X-RateLimit-Limit, -Remaining and -Reset (the scan checks the window kept against them)"),
    costs=("Basic is free; Algo Trader Plus $99 a month (every US exchange live, no 15 minutes held back, OPRA options). "
           "A paper account's keys serve the same data as a live one's"),
    links=(
        Link("About the Market Data API", _doc("about-market-data-api"), "docs"),
        Link("API reference: historical bars", _ref("stockbars"), "reference"),
        Link("Historical stock data", _doc("historical-stock-data-1"), "guide"),
        Link("Market data FAQ", _doc("market-data-faq"), "guide"),
        Link("Authentication", _doc("authentication"), "auth"),
        Link("Subscription plans", PLANS, "limits"),
        Link("Plans and pricing", PRICING, "pricing"),
        Link("Status", STATUS, "status"),
        Link("Dashboard (API keys)", DASHBOARD, "console"),
        Link("alpaca-py", "https://github.com/alpacahq/alpaca-py", "sdk"),
    ),
    areas=(
        Area(STOCKS, "US stocks' bars, trades, quotes, snapshots and auctions since 2016, from the consolidated tape "
             "(sip), IEX, Blue Ocean (boats) or OTC venues (feed=)", _doc("historical-stock-data-1"),
             covered="minute and daily bars and trades of US stocks (sip, or iex: ALPACA_FEED), split-adjusted; Blue "
                     "Ocean's overnight minutes (feed=boats: the boats feed); the exchange codes"),
        Area(CRYPTO, "crypto pairs' bars, trades, quotes and order books on Alpaca's venue or Kraken (US, EU)",
             _doc("historical-crypto-data-1"),
             covered="crypto pairs' minute and daily bars and trades, no key (Kraken US by default: ALPACA_CRYPTO_LOC)"),
        Area("Options", "options' bars, trades, quotes, snapshots and chains (OPRA on Algo Trader Plus, indicative on "
             "Basic)", _doc("historical-option-data")),
        Area("News", "news articles on stocks and crypto", _doc("historical-news-data")),
        Area("Corporate actions", "dividends, splits, spin-offs, mergers, redemptions and name changes",
             _ref("corporateactions-1")),
        Area("Screener", "the day's top movers and most active stocks", _ref("movers-1")),
        Area("Logos", "companies' logos", _ref("logos-5")),
        Area("Fixed income", "the latest prices and quotes of fixed income", _ref("fixedincomelatestprices")),
        Area("Real-time streams", "trades, quotes and bars pushed over WebSockets: stocks, crypto, options, news",
             _doc("streaming-market-data"), covered="IEX's trades live: the stream's own card"),
    ),
    calls=(
        Call("GET /v2/stocks/bars", "stocks' bars over a range, by feed (sip, iex, boats, otc) and adjustment", STOCKS,
             used="the stocks' minute and daily bars (split-adjusted), up to 15 minutes ago on Basic; Blue Ocean's "
                  "nights (feed=boats); the plan scan (the latest 15 minutes tell Algo Trader Plus)",
             docs=_ref("stockbars")),
        Call("GET /v2/stocks/trades", "stocks' trades over a range, by feed", STOCKS,
             used="a stock's trades (sip or iex), up to 15 minutes ago on Basic", docs=_ref("stocktrades-1")),
        Call("GET /v2/stocks/meta/exchanges", "the exchange codes trades carry, with their names", STOCKS,
             used="the exchanges table", docs=_ref("stockmetaexchanges-1")),
        Call("GET /v1beta3/crypto/{loc}/bars", "crypto pairs' bars on a venue (us, us-1, eu-1)", CRYPTO,
             used="crypto pairs' minute and daily bars, no key", docs=_ref("cryptobars-1")),
        Call("GET /v1beta3/crypto/{loc}/trades", "crypto pairs' trades on a venue", CRYPTO,
             used="a crypto pair's trades, no key", docs=_ref("cryptotrades-1")),
        Call("GET /v2/stocks/quotes", "stocks' quotes over a range", STOCKS, docs=_ref("stockquotes-1")),
        Call("GET /v2/stocks/snapshots", "stocks' latest trade, quote and minute, day and previous day's bars", STOCKS,
             docs=_ref("stocksnapshots-1")),
        Call("GET /v2/stocks/bars/latest", "stocks' latest minute bars", STOCKS, docs=_ref("stocklatestbars-1")),
        Call("GET /v2/stocks/auctions", "stocks' opening and closing auctions", STOCKS, docs=_ref("stockauctions-1")),
        Call("GET /v2/stocks/meta/conditions/{ticktype}", "the trade and quote condition codes", STOCKS,
             docs=_ref("stockmetaconditions-1")),
        Call("GET /v1beta3/crypto/{loc}/latest/orderbooks", "crypto pairs' latest order books", CRYPTO,
             docs=_ref("cryptolatestorderbooks-1")),
        Call("GET /v1beta1/options/bars", "options contracts' bars", "Options", docs=_ref("optionbars")),
        Call("GET /v1beta1/options/snapshots/{underlying_symbol}", "an underlying's option chain", "Options",
             docs=_ref("optionchain")),
        Call("GET /v1beta1/news", "news articles, newest first", "News", docs=_ref("news-3")),
        Call("GET /v1/corporate-actions", "corporate actions by symbol, type and date", "Corporate actions",
             docs=_ref("corporateactions-1")),
        Call("GET /v1beta1/screener/{market_type}/movers", "the top gainers and losers, stocks or crypto", "Screener",
             docs=_ref("movers-1")),
        Call("GET /v1beta1/screener/stocks/most-actives", "the most active stocks", "Screener",
             docs=_ref("mostactives-1")),
        Call("GET /v1beta1/logos/{symbol}", "a company's logo (PNG)", "Logos", docs=_ref("logos-5")),
    ),
    verified="2026-11-11",
)

TRADING = Api(
    name="Alpaca Trading API",
    maker="Alpaca",
    about=("Alpaca's Trading API is a brokerage account's: its assets, orders, positions, activities, watchlists, option "
           "contracts, crypto wallets and the market's clock and calendar, on a paper (simulated) account or a live one, "
           "each with keys of its own. The plugin reads only an asset's record here."),
    kind="rest",
    base=f"{TRADING_URLS[True]} (paper; live: {TRADING_URLS[False]})",
    version="v2",
    auth=("the same headers, APCA-API-KEY-ID and APCA-API-SECRET-KEY: a paper account's keys on the paper host, a live "
          "account's on the live host (ALPACA_PAPER), never the one's on the other"),
    limits="none published for a single account in its docs; asked here once for each stock's record",
    costs="reading costs nothing; an order or a closed position on a live account trades real money (the plugin makes "
          "neither)",
    links=(
        Link("About the Trading API", _doc("trading-api"), "docs"),
        Link("API reference: get an asset", _ref("get-v2-assets-symbol_or_asset_id"), "reference"),
        Link("Working with assets", _doc("working-with-assets"), "guide"),
        Link("Paper trading", _doc("paper-trading"), "guide"),
        Link("Authentication", _doc("authentication"), "auth"),
        Link("Status", STATUS, "status"),
        Link("Dashboard (API keys)", DASHBOARD, "console"),
    ),
    areas=(
        Area("Assets", "the tradable assets (US stocks and ETFs, options, crypto) with their exchange and status",
             _doc("working-with-assets"), covered="a stock's record: its name, primary exchange and whether it is active"),
        Area("Paper trading", "a simulated account with keys and a host of its own", _doc("paper-trading"),
             covered="the host asked: paper by default (ALPACA_PAPER=1), live with ALPACA_PAPER=0"),
        Area("Account", "the account's cash, buying power and status", _doc("working-with-account")),
        Area("Orders", "placing, changing and cancelling orders", _doc("working-with-orders")),
        Area("Positions", "the open positions, and closing them", _doc("working-with-positions")),
        Area("Account activities", "fills, dividends, transfers and the account's other activities",
             _doc("account-activities")),
        Area("Portfolio history", "the account's value over time", _ref("getaccountportfoliohistory-1")),
        Area("Watchlists", "the account's watchlists", _ref("getwatchlists-1")),
        Area("Options contracts", "option contracts by underlying and expiry", _ref("get-options-contracts")),
        Area("Corporate announcements", "dividends, splits and mergers announced",
             _ref("get-v2-corporate_actions-announcements-1")),
        Area("Crypto funding", "crypto wallets, transfers and whitelisted addresses", _ref("listcryptofundingwallets")),
        Area(CLOCK, "whether the market is open, and its trading days and hours", _ref("clock-1")),
    ),
    calls=(
        Call("GET /v2/assets/{symbol_or_asset_id}", "an asset's record: class, exchange, symbol, name, status", "Assets",
             used="a stock's record (its instrument): name, primary exchange, whether active",
             docs=_ref("get-v2-assets-symbol_or_asset_id")),
        Call("GET /v2/assets", "every asset, by class, exchange and status", "Assets", docs=_ref("get-v2-assets-1")),
        Call("GET /v2/account", "the account: cash, buying power, status", "Account", docs=_ref("getaccount-1")),
        Call("POST /v2/orders", "places an order (on a live account, a trade with real money)", "Orders",
             docs=_ref("postorder"), writes=True, costs=True),
        Call("GET /v2/orders", "the account's orders", "Orders", docs=_ref("getallorders-1")),
        Call("DELETE /v2/orders/{order_id}", "cancels an order", "Orders", docs=_ref("deleteorderbyorderid-1"),
             writes=True),
        Call("GET /v2/positions", "the open positions", "Positions", docs=_ref("getallopenpositions")),
        Call("DELETE /v2/positions/{symbol_or_asset_id}", "closes a position at the market (on a live account, a trade "
             "with real money)", "Positions", docs=_ref("deleteopenposition-1"), writes=True, costs=True),
        Call("GET /v3/clock", "whether the market is open, the next open and close", CLOCK, docs=_ref("clock-1")),
        Call("GET /v3/calendar/{market}", "a market's trading days and hours", CLOCK, docs=_ref("calendar-2")),
    ),
    verified="2026-11-11",
)

STREAM = Api(
    name="Alpaca market data stream",
    maker="Alpaca",
    about=("Alpaca's market data streams push trades, quotes and bars as they happen, over a WebSocket: a stream for "
           "each stock feed (IEX, the consolidated tape, its 15-minute delayed copy, Blue Ocean, overnight) and others "
           "for crypto, options and news. A connection signs in with the keys, then subscribes symbols to channels."),
    kind="stream",
    base=STREAM_URL,
    version="v2",
    auth="the key ID and secret in the first message (action auth), a few seconds after connecting at the latest",
    limits=("on most subscriptions one connection per endpoint (a second: error 406); Basic: 30 symbols, IEX only (error "
            "405 past a plan's symbols, 409 for a feed it lacks)"),
    costs="IEX's stream is free (Basic); the consolidated tape live (v2/sip) needs Algo Trader Plus ($99 a month)",
    links=(
        Link("WebSocket streaming", _doc("streaming-market-data"), "docs"),
        Link("Real-time stock data", _doc("real-time-stock-pricing-data"), "reference"),
        Link("Subscription plans", PLANS, "limits"),
        Link("Plans and pricing", PRICING, "pricing"),
        Link("Status", STATUS, "status"),
    ),
    areas=(
        Area("IEX (v2/iex)", "IEX's trades, quotes and bars live, on every plan", _doc("real-time-stock-pricing-data"),
             covered="IEX's trades of the stocks open on a chart (alpaca (iex)), with their corrections and cancels"),
        Area("SIP (v2/sip)", "every US exchange live (Algo Trader Plus)", _doc("real-time-stock-pricing-data")),
        Area("Delayed SIP (v2/delayed_sip)", "every US exchange, 15 minutes delayed", _doc("real-time-stock-pricing-data")),
        Area("Blue Ocean (v1beta1/boats)", "Blue Ocean ATS's overnight session", _doc("real-time-stock-pricing-data")),
        Area("Overnight (v1beta1/overnight)", "derived from Blue Ocean: cheaper, 15 minutes delayed",
             _doc("real-time-stock-pricing-data")),
        Area("Crypto", "crypto trades, quotes, bars and order books live", _doc("real-time-crypto-pricing-data")),
        Area("Options", "options' trades and quotes live", _doc("real-time-option-data")),
        Area("News", "news articles as they are published", _doc("streaming-real-time-news")),
    ),
    calls=(
        Call("send auth", "signs in with the key ID and secret", "IEX (v2/iex)",
             used="the first message of every connection (the keys go nowhere else)"),
        Call("send subscribe trades", "adds symbols to the trades channel (their corrections and cancels with them)",
             "IEX (v2/iex)", used="the stocks open on a chart, once signed in"),
        Call("send unsubscribe trades", "drops symbols from the trades channel", "IEX (v2/iex)",
             used="a stock no longer open on a chart"),
        Call("message success", "connected, then authenticated", "IEX (v2/iex)", used="signed in: subscribing may start"),
        Call("message subscription", "the channels and symbols now streamed", "IEX (v2/iex)",
             used="the symbols the server says it streams"),
        Call("message t: trade", "a trade", "IEX (v2/iex)",
             used="a trade, into the bars it forms by the consolidated tape's rules"),
        Call("message c: correction", "a trade corrected", "IEX (v2/iex)",
             used="the original trade withdrawn, the corrected one in its place"),
        Call("message x: cancel or error", "a trade withdrawn", "IEX (v2/iex)", used="the trade withdrawn"),
        Call("message error", "a refusal with its code", "IEX (v2/iex)",
             used="the session ended and retried after a wait its code sets (406: another connection; 409: not in the "
                  "plan)"),
        Call("send subscribe quotes", "adds symbols to the quotes channel", "IEX (v2/iex)"),
        Call("send subscribe bars", "adds symbols to the minute bars channel", "IEX (v2/iex)"),
        Call("send subscribe dailyBars", "adds symbols to the daily bars channel", "IEX (v2/iex)"),
        Call("send subscribe updatedBars", "adds symbols to the updated bars channel", "IEX (v2/iex)"),
        Call("send subscribe statuses", "adds symbols to the trading status channel", "IEX (v2/iex)"),
        Call("send subscribe imbalances", "adds symbols to the order imbalances channel", "IEX (v2/iex)"),
        Call("send subscribe lulds", "adds symbols to the limit up, limit down bands channel", "IEX (v2/iex)"),
        Call("message q: quote", "a quote", "IEX (v2/iex)"),
        Call("message b: minute bar", "a minute bar", "IEX (v2/iex)"),
        Call("message d: daily bar", "a daily bar", "IEX (v2/iex)"),
        Call("message u: updated bar", "a minute bar updated", "IEX (v2/iex)"),
        Call("message l: LULD bands", "a stock's limit up, limit down bands", "IEX (v2/iex)"),
        Call("message s: trading status", "a stock's trading status (a halt, a resumption)", "IEX (v2/iex)"),
        Call("message i: order imbalance", "an auction's order imbalance", "IEX (v2/iex)"),
    ),
    verified="2026-11-11",
)

APIS = (MARKET_DATA, TRADING, STREAM)  # the plugin's, its day sessions' and Blue Ocean's alike (the app draws each once)
