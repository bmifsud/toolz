# Blueberry Markets MT5 read-only NAS100 exporter

1. Open Blueberry Markets MT5 on a supported desktop or VPS and sign in to the intended **demo** account.
2. In **Market Watch**, locate the actual Nasdaq-100 CFD symbol (broker suffixes vary). Open its chart.
3. In MT5, choose **File → Open Data Folder**, then place `BlueberryNAS100Exporter.mq5` in `MQL5/Experts/`.
4. Open MetaEditor, compile the file, and attach the EA to the correct chart. Leave **Algo Trading disabled**; this EA uses only market-data and file functions. Confirm the Experts tab reports initialization.
5. Set `InpSymbol` to the exact broker symbol if it differs from the chart symbol.
6. MT5 writes two snapshot files to **Terminal → Common Data Folder → Files** (accessible from MetaEditor/MT5's shared files folder): `blueberry_nas100_quotes.csv` and `blueberry_nas100_specs.csv`.
7. Transfer both CSV files to the Debian trading directory manually over a trusted channel. Do not transfer login credentials. Repeated transfer is needed for an ongoing feed.
8. Verify timestamps, bid/ask spread, symbol, currency, minimum lot and tick value before paper simulation. Market-hours and server time zones must be confirmed with the broker.

The exporter overwrites a snapshot every interval; it does not stream historical candles or store tick history. Files are not atomically replaced; avoid reading during writes. No live order functionality is included. The MQL5 file has **not** been compiled in MetaEditor or tested against a Blueberry account in this environment.
