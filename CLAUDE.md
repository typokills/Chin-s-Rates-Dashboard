# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This directory is a sandbox for developing and testing changes to the Fixed Income Dashboard before applying them to the production file at `../Fixed Income Dashboard/fixed_income_dashboard.py`.

## Running

```bash
python fixed_income_dashboard.py
# App runs at http://127.0.0.1:8050/
```

## Architecture

See `../Fixed Income Dashboard/CLAUDE.md` for full architecture documentation. Key points:

- All Bloomberg data is fetched **once at startup** via `get_data()` and stored in `dcc.Store(id="store-data")` — callbacks never call Bloomberg directly
- When Bloomberg is unavailable, the app returns empty dicts — charts show N/A (IND fallback dict was removed)
- Hedge costs are computed as `JPYI3M − foreign 3M rate` (negative = cost to JPY investor)
- 7 tabs: Ideas, Yields, Macro, FX/Hedging, Spreads, Breakeven, Tickers

## Dependencies

```bash
pip install dash dash-bootstrap-components plotly pandas numpy
```

## Environment — Compatibility Notes (Python 3.13, Dash 4.x, dbc 2.x)

- Legacy imports (`dash_core_components`, `dash_html_components`, `dash_table`, `dash.dependencies`) don't exist in Dash 4.x — use `from dash import dcc, html, dash_table, Input, Output, State, callback_context`
- `app.run_server()` → `app.run()` in Dash 4.x
- `dbc.Input(bs_size="sm")` → `dbc.Input(size="sm")` in dash-bootstrap-components 2.x
- Open files with `encoding='utf-8'` — emoji/unicode in source files causes `cp1252` errors on Windows
