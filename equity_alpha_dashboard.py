#!/usr/bin/env python3
"""
Global Equity Alpha Dashboard

Run:
    python equity_alpha_dashboard.py

Dependencies:
    pip install dash dash-bootstrap-components plotly pandas numpy

Bloomberg:
    Optional. If blpapi is unavailable or a field/ticker fails, the dashboard
    shows N/A and records the issue in the Data Health tab. No fallback market
    data is generated.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dash
from dash import Input, Output, State, dash_table, dcc, html
import dash_bootstrap_components as dbc

warnings.filterwarnings("ignore")

try:
    import blpapi  # type: ignore

    HAS_BBG = True
except ImportError:
    blpapi = None
    HAS_BBG = False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APP_TITLE = "Global Equity Alpha Dashboard"
FONT = "'Inter', 'Segoe UI', Arial, sans-serif"
BG = "#0B0F14"
PANEL = "#111821"
PANEL_2 = "#17202B"
BORDER = "#263241"
TEXT = "#DDE7F3"
MUTED = "#8BA0B8"
ACCENT = "#4EA1FF"
GREEN = "#25C26E"
RED = "#F05252"
YELLOW = "#EAB308"
TEAL = "#19C2B8"
PURPLE = "#9B7CFF"

GRAPH_CFG = {"displayModeBar": False, "responsive": True}
NA = "N/A"


MARKETS: List[Dict[str, str]] = [
    {"name": "United States", "region": "DM Americas", "bucket": "DM", "ccy": "USD", "index": "MXUS Index"},
    {"name": "Canada", "region": "DM Americas", "bucket": "DM", "ccy": "CAD", "index": "MXCA Index"},
    {"name": "United Kingdom", "region": "DM Europe", "bucket": "DM", "ccy": "GBP", "index": "MXGB Index"},
    {"name": "Germany", "region": "DM Europe", "bucket": "DM", "ccy": "EUR", "index": "MXDE Index"},
    {"name": "France", "region": "DM Europe", "bucket": "DM", "ccy": "EUR", "index": "MXFR Index"},
    {"name": "Italy", "region": "DM Europe", "bucket": "DM", "ccy": "EUR", "index": "MXIT Index"},
    {"name": "Japan", "region": "DM Asia", "bucket": "DM", "ccy": "JPY", "index": "MXJP Index"},
    {"name": "Australia", "region": "DM Asia", "bucket": "DM", "ccy": "AUD", "index": "MXAU Index"},
    {"name": "Hong Kong", "region": "DM Asia", "bucket": "DM", "ccy": "HKD", "index": "MXHK Index"},
    {"name": "Singapore", "region": "DM Asia", "bucket": "DM", "ccy": "SGD", "index": "MXSG Index"},
    {"name": "China", "region": "EM Asia", "bucket": "EM", "ccy": "CNY", "index": "MXCN Index"},
    {"name": "India", "region": "EM Asia", "bucket": "EM", "ccy": "INR", "index": "MXIN Index"},
    {"name": "Korea", "region": "EM Asia", "bucket": "EM", "ccy": "KRW", "index": "MXKR Index"},
    {"name": "Taiwan", "region": "EM Asia", "bucket": "EM", "ccy": "TWD", "index": "MXTW Index"},
    {"name": "Brazil", "region": "EM LatAm", "bucket": "EM", "ccy": "BRL", "index": "MXBR Index"},
    {"name": "Mexico", "region": "EM LatAm", "bucket": "EM", "ccy": "MXN", "index": "MXMX Index"},
    {"name": "South Africa", "region": "EM EMEA", "bucket": "EM", "ccy": "ZAR", "index": "MXZA Index"},
    {"name": "Saudi Arabia", "region": "EM EMEA", "bucket": "EM", "ccy": "SAR", "index": "MXSA Index"},
]

SECTORS: Dict[str, str] = {
    "Energy": "MXWO0EN Index",
    "Materials": "MXWO0MT Index",
    "Industrials": "MXWO0IN Index",
    "Consumer Discretionary": "MXWO0CD Index",
    "Consumer Staples": "MXWO0CS Index",
    "Health Care": "MXWO0HC Index",
    "Financials": "MXWO0FN Index",
    "Information Technology": "MXWO0IT Index",
    "Communication Services": "MXWO0TC Index",
    "Utilities": "MXWO0UT Index",
    "Real Estate": "MXWO0RE Index",
}

STYLES: Dict[str, str] = {
    "Value": "MXWO000V Index",
    "Growth": "MXWO000G Index",
    "Quality": "M1WDQU Index",
    "Momentum": "M1WDMO Index",
    "Minimum Volatility": "M1WDMV Index",
    "Small Cap": "MXWOSC Index",
    "High Dividend": "M1WDHD Index",
}

MACRO_TICKERS: Dict[str, Dict[str, str]] = {
    "United States": {"rate": "FDTR Index", "y10": "USGG10YR Index", "fx": "DXY Curncy", "pmi": "NAPMPMI Index"},
    "Canada": {"rate": "CABROVER Index", "y10": "GCAN10YR Index", "fx": "CAD Curncy", "pmi": "MPMICA Index"},
    "United Kingdom": {"rate": "UKBRBASE Index", "y10": "GUKG10 Index", "fx": "GBP Curncy", "pmi": "MPMIGBMA Index"},
    "Germany": {"rate": "EURR002W Index", "y10": "GDBR10 Index", "fx": "EUR Curncy", "pmi": "MPMIDEMA Index"},
    "France": {"rate": "EURR002W Index", "y10": "GFRN10 Index", "fx": "EUR Curncy", "pmi": "MPMIFRMA Index"},
    "Italy": {"rate": "EURR002W Index", "y10": "GBTPGR10 Index", "fx": "EUR Curncy", "pmi": "MPMIITMA Index"},
    "Japan": {"rate": "BOJDTR Index", "y10": "GJGB10 Index", "fx": "JPY Curncy", "pmi": "MPMIJPMA Index"},
    "Australia": {"rate": "RBATCTR Index", "y10": "GACGB10 Index", "fx": "AUD Curncy", "pmi": "MPMIAUMA Index"},
    "China": {"rate": "CHLR1T Index", "y10": "GCNY10YR Index", "fx": "CNY Curncy", "pmi": "CPMINDX Index"},
    "India": {"rate": "RBINREPO Index", "y10": "GIND10YR Index", "fx": "INR Curncy", "pmi": "MPMIINMA Index"},
    "Brazil": {"rate": "BZSTSETA Index", "y10": "GEBR10Y Index", "fx": "BRL Curncy", "pmi": "MPMIBRMA Index"},
    "Mexico": {"rate": "MXONBR Index", "y10": "GMXN10YR Index", "fx": "MXN Curncy", "pmi": "MPMIMXMA Index"},
    "South Africa": {"rate": "SARBPRT Index", "y10": "GSAB10YR Index", "fx": "ZAR Curncy", "pmi": "MPMIZAMA Index"},
}

COUNTRY_FIELDS = {
    "PX_LAST": "price",
    "CHG_PCT_1D": "ret_1d",
    "CHG_PCT_5D": "ret_1w",
    "CHG_PCT_1M": "ret_1m",
    "CHG_PCT_3M": "ret_3m",
    "CHG_PCT_YTD": "ret_ytd",
    "CHG_PCT_1YR": "ret_1y",
    "BEST_PE_RATIO": "fwd_pe",
    "PX_TO_BOOK_RATIO": "pb",
    "EQY_DVD_YLD_IND": "div_yield",
    "RETURN_COM_EQY": "roe",
    "BEST_EPS_NXT_YR": "eps_next",
    "BEST_EPS_NXT_YR_REV_4W": "eps_rev_4w",
    "BEST_EPS_NXT_YR_REV_3M": "eps_rev_3m",
    "VOLATILITY_30D": "vol_30d",
}

INDEX_FIELDS = {
    "PX_LAST": "price",
    "CHG_PCT_1D": "ret_1d",
    "CHG_PCT_1M": "ret_1m",
    "CHG_PCT_3M": "ret_3m",
    "CHG_PCT_YTD": "ret_ytd",
    "CHG_PCT_1YR": "ret_1y",
    "BEST_PE_RATIO": "fwd_pe",
    "PX_TO_BOOK_RATIO": "pb",
    "EQY_DVD_YLD_IND": "div_yield",
    "BEST_EPS_NXT_YR_REV_3M": "eps_rev_3m",
}


@dataclass
class FetchResult:
    data: Dict[str, Any]
    health: List[Dict[str, str]]
    source: str


# ---------------------------------------------------------------------------
# Bloomberg fetcher
# ---------------------------------------------------------------------------


class BloombergClient:
    def __init__(self) -> None:
        self.ok = False
        self.session = None
        self.error = ""
        if HAS_BBG:
            self._connect()
        else:
            self.error = "blpapi is not installed"

    def _connect(self) -> None:
        try:
            options = blpapi.SessionOptions()
            options.setServerHost("localhost")
            options.setServerPort(8194)
            if hasattr(options, "setConnectTimeout"):
                options.setConnectTimeout(2000)
            if hasattr(options, "setNumStartAttempts"):
                options.setNumStartAttempts(1)
            session = blpapi.Session(options)
            if not session.start():
                self.error = "Bloomberg session failed to start"
                return
            if not session.openService("//blp/refdata"):
                self.error = "Bloomberg refdata service unavailable"
                return
            self.session = session
            self.ok = True
        except Exception as exc:
            self.error = str(exc)
            self.ok = False

    def bdp(self, tickers: Iterable[str], fields: Iterable[str]) -> Tuple[pd.DataFrame, List[Dict[str, str]]]:
        tickers = list(dict.fromkeys([t for t in tickers if t]))
        fields = list(dict.fromkeys([f for f in fields if f]))
        health: List[Dict[str, str]] = []
        if not tickers or not fields:
            return pd.DataFrame(), health
        if not self.ok or self.session is None:
            for ticker in tickers:
                health.append({"ticker": ticker, "field": ",".join(fields), "status": "N/A", "message": self.error or "Bloomberg unavailable"})
            return pd.DataFrame(index=tickers, columns=fields), health

        try:
            service = self.session.getService("//blp/refdata")
            request = service.createRequest("ReferenceDataRequest")
            for ticker in tickers:
                request.getElement("securities").appendValue(ticker)
            for field in fields:
                request.getElement("fields").appendValue(field)
            self.session.sendRequest(request)

            rows: Dict[str, Dict[str, Any]] = {ticker: {} for ticker in tickers}
            while True:
                event = self.session.nextEvent(5000)
                for msg in event:
                    if not msg.hasElement("securityData"):
                        continue
                    sec_data = msg.getElement("securityData")
                    for i in range(sec_data.numValues()):
                        sec = sec_data.getValueAsElement(i)
                        ticker = sec.getElementAsString("security")
                        if sec.hasElement("securityError"):
                            health.append({"ticker": ticker, "field": ",".join(fields), "status": "N/A", "message": "security error"})
                            continue
                        fdata = sec.getElement("fieldData")
                        for field in fields:
                            if fdata.hasElement(field):
                                rows.setdefault(ticker, {})[field] = _element_value(fdata.getElement(field))
                            else:
                                rows.setdefault(ticker, {})[field] = None
                                health.append({"ticker": ticker, "field": field, "status": "N/A", "message": "field missing"})
                if event.eventType() == blpapi.Event.RESPONSE:
                    break
            return pd.DataFrame.from_dict(rows, orient="index"), health
        except Exception as exc:
            for ticker in tickers:
                health.append({"ticker": ticker, "field": ",".join(fields), "status": "N/A", "message": str(exc)})
            return pd.DataFrame(index=tickers, columns=fields), health


def _element_value(element: Any) -> Any:
    try:
        return element.getValue()
    except Exception:
        try:
            return element.getValueAsString()
        except Exception:
            return None


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except Exception:
        return None


def fmt(value: Any, digits: int = 1, suffix: str = "") -> str:
    val = safe_float(value)
    if val is None:
        return NA
    sign = "+" if val > 0 and suffix == "%" else ""
    return f"{sign}{val:.{digits}f}{suffix}"


def pct_color(value: Any) -> str:
    val = safe_float(value)
    if val is None:
        return MUTED
    return GREEN if val >= 0 else RED


def score_to_color(value: Any) -> str:
    val = safe_float(value)
    if val is None:
        return MUTED
    if val >= 65:
        return GREEN
    if val <= 35:
        return RED
    return YELLOW


def zscore(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.count() < 3 or s.std(skipna=True) == 0:
        return pd.Series([np.nan] * len(series), index=series.index)
    z = (s - s.mean(skipna=True)) / s.std(skipna=True)
    return z if higher_is_better else -z


def percentile_score(z: Any) -> Optional[float]:
    val = safe_float(z)
    if val is None:
        return None
    return max(0.0, min(100.0, 50.0 + 18.0 * val))


# ---------------------------------------------------------------------------
# Data pipeline
# ---------------------------------------------------------------------------


def fetch_all_data() -> FetchResult:
    client = BloombergClient()
    health: List[Dict[str, str]] = []

    country_tickers = [m["index"] for m in MARKETS]
    country_df, h = client.bdp(country_tickers, COUNTRY_FIELDS.keys())
    health.extend(h)

    sector_df, h = client.bdp(SECTORS.values(), INDEX_FIELDS.keys())
    health.extend(h)

    style_df, h = client.bdp(STYLES.values(), INDEX_FIELDS.keys())
    health.extend(h)

    macro_pairs = []
    for country, tickers in MACRO_TICKERS.items():
        for kind, ticker in tickers.items():
            macro_pairs.append((country, kind, ticker))
    macro_df, h = client.bdp([ticker for _, _, ticker in macro_pairs], ["PX_LAST", "CHG_PCT_1M", "CHG_PCT_3M"])
    health.extend(h)

    countries = build_country_rows(country_df, macro_df, macro_pairs)
    sectors = build_simple_rows(sector_df, SECTORS)
    styles = build_simple_rows(style_df, STYLES)
    countries = score_countries(countries)
    sectors = score_simple(sectors)
    styles = score_simple(styles)
    ideas = generate_ideas(countries, sectors, styles)
    pairs = generate_relative_value_pairs(countries, sectors, styles)

    source = "Bloomberg Live" if client.ok else f"Bloomberg unavailable: {client.error or 'N/A'}"
    if not client.ok and not health:
        health.append({"ticker": "ALL", "field": "ALL", "status": "N/A", "message": source})

    return FetchResult(
        data={
            "as_of": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "countries": countries,
            "sectors": sectors,
            "styles": styles,
            "ideas": ideas,
            "pairs": pairs,
            "health": health,
        },
        health=health,
        source=source,
    )


def build_country_rows(country_df: pd.DataFrame, macro_df: pd.DataFrame, macro_pairs: List[Tuple[str, str, str]]) -> List[Dict[str, Any]]:
    ticker_to_market = {m["index"]: m for m in MARKETS}
    macro_lookup = {(country, kind): ticker for country, kind, ticker in macro_pairs}
    rows = []
    for ticker, meta in ticker_to_market.items():
        row: Dict[str, Any] = {
            "name": meta["name"],
            "bucket": meta["bucket"],
            "region": meta["region"],
            "ccy": meta["ccy"],
            "ticker": ticker,
        }
        if ticker in country_df.index:
            for bbg_field, key in COUNTRY_FIELDS.items():
                row[key] = safe_float(country_df.loc[ticker].get(bbg_field))
        for kind in ["rate", "y10", "fx", "pmi"]:
            mticker = macro_lookup.get((meta["name"], kind))
            row[f"{kind}_ticker"] = mticker
            row[kind] = safe_float(macro_df.loc[mticker].get("PX_LAST")) if mticker in macro_df.index else None
            row[f"{kind}_mom_1m"] = safe_float(macro_df.loc[mticker].get("CHG_PCT_1M")) if mticker in macro_df.index else None
        row["real_yield_proxy"] = row["y10"]
        rows.append(row)
    return rows


def build_simple_rows(df: pd.DataFrame, mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    rows = []
    for name, ticker in mapping.items():
        row: Dict[str, Any] = {"name": name, "ticker": ticker}
        if ticker in df.index:
            for bbg_field, key in INDEX_FIELDS.items():
                row[key] = safe_float(df.loc[ticker].get(bbg_field))
        rows.append(row)
    return rows


def score_countries(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    df = pd.DataFrame(rows)
    if df.empty:
        return rows

    signals = {
        "momentum": zscore(df.get("ret_3m", pd.Series(dtype=float)), True),
        "revision": zscore(df.get("eps_rev_3m", pd.Series(dtype=float)), True),
        "valuation": zscore(df.get("fwd_pe", pd.Series(dtype=float)), False),
        "quality": zscore(df.get("roe", pd.Series(dtype=float)), True),
        "risk": zscore(df.get("vol_30d", pd.Series(dtype=float)), False),
        "macro": zscore(df.get("pmi", pd.Series(dtype=float)), True),
        "fx": zscore(df.get("fx_mom_1m", pd.Series(dtype=float)), True),
    }
    weights = {
        "momentum": 0.18,
        "revision": 0.24,
        "valuation": 0.16,
        "quality": 0.12,
        "risk": 0.10,
        "macro": 0.12,
        "fx": 0.08,
    }
    total_z = pd.Series(0.0, index=df.index)
    available_weight = pd.Series(0.0, index=df.index)
    for key, sig in signals.items():
        valid = sig.notna()
        total_z.loc[valid] += sig.loc[valid] * weights[key]
        available_weight.loc[valid] += weights[key]
        df[f"{key}_score"] = sig.map(percentile_score)
    final_z = total_z / available_weight.replace(0, np.nan)
    df["alpha_score"] = final_z.map(percentile_score)
    df["confidence"] = (available_weight / sum(weights.values()) * 100).round(0)
    df["rank"] = df["alpha_score"].rank(ascending=False, method="min", na_option="bottom").astype("Int64")
    return df.replace({np.nan: None}).to_dict("records")


def score_simple(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    df = pd.DataFrame(rows)
    if df.empty:
        return rows
    signals = {
        "momentum": zscore(df.get("ret_3m", pd.Series(dtype=float)), True),
        "revision": zscore(df.get("eps_rev_3m", pd.Series(dtype=float)), True),
        "valuation": zscore(df.get("fwd_pe", pd.Series(dtype=float)), False),
    }
    weights = {"momentum": 0.40, "revision": 0.40, "valuation": 0.20}
    total_z = pd.Series(0.0, index=df.index)
    available_weight = pd.Series(0.0, index=df.index)
    for key, sig in signals.items():
        valid = sig.notna()
        total_z.loc[valid] += sig.loc[valid] * weights[key]
        available_weight.loc[valid] += weights[key]
        df[f"{key}_score"] = sig.map(percentile_score)
    df["alpha_score"] = (total_z / available_weight.replace(0, np.nan)).map(percentile_score)
    df["confidence"] = (available_weight / sum(weights.values()) * 100).round(0)
    df["rank"] = df["alpha_score"].rank(ascending=False, method="min", na_option="bottom").astype("Int64")
    return df.replace({np.nan: None}).to_dict("records")


def generate_ideas(countries: List[Dict[str, Any]], sectors: List[Dict[str, Any]], styles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ideas: List[Dict[str, Any]] = []
    sorted_countries = sorted([r for r in countries if safe_float(r.get("alpha_score")) is not None], key=lambda r: r["alpha_score"], reverse=True)
    sorted_sectors = sorted([r for r in sectors if safe_float(r.get("alpha_score")) is not None], key=lambda r: r["alpha_score"], reverse=True)
    sorted_styles = sorted([r for r in styles if safe_float(r.get("alpha_score")) is not None], key=lambda r: r["alpha_score"], reverse=True)

    for row in sorted_countries[:5]:
        ideas.append({
            "idea": f"Overweight {row['name']} equities",
            "type": "Country",
            "score": row.get("alpha_score"),
            "confidence": row.get("confidence"),
            "rationale": idea_rationale(row),
            "risk": idea_risk(row),
            "invalidation": "EPS revisions roll over, relative momentum breaks, or FX/rates move against the market.",
        })
    for row in sorted_sectors[:4]:
        ideas.append({
            "idea": f"Overweight {row['name']} sector",
            "type": "Sector",
            "score": row.get("alpha_score"),
            "confidence": row.get("confidence"),
            "rationale": simple_rationale(row),
            "risk": "Crowding, valuation compression, or earnings disappointment.",
            "invalidation": "3M relative momentum and EPS revision signals turn negative.",
        })
    for row in sorted_styles[:4]:
        ideas.append({
            "idea": f"Overweight {row['name']} style",
            "type": "Style",
            "score": row.get("alpha_score"),
            "confidence": row.get("confidence"),
            "rationale": simple_rationale(row),
            "risk": "Regime shift, factor crowding, or macro shock.",
            "invalidation": "Factor trend loses breadth and valuation support disappears.",
        })
    ideas.sort(key=lambda r: safe_float(r.get("score")) or -1, reverse=True)
    return ideas


def idea_rationale(row: Dict[str, Any]) -> str:
    parts = []
    if safe_float(row.get("revision_score")) is not None:
        parts.append(f"EPS revision score {fmt(row.get('revision_score'), 0)}")
    if safe_float(row.get("momentum_score")) is not None:
        parts.append(f"momentum score {fmt(row.get('momentum_score'), 0)}")
    if safe_float(row.get("valuation_score")) is not None:
        parts.append(f"valuation score {fmt(row.get('valuation_score'), 0)}")
    return "; ".join(parts) if parts else "N/A - insufficient Bloomberg fields."


def simple_rationale(row: Dict[str, Any]) -> str:
    parts = []
    for key in ["momentum_score", "revision_score", "valuation_score"]:
        if safe_float(row.get(key)) is not None:
            parts.append(f"{key.replace('_score', '')} {fmt(row.get(key), 0)}")
    return "; ".join(parts) if parts else "N/A - insufficient Bloomberg fields."


def idea_risk(row: Dict[str, Any]) -> str:
    risks = []
    if safe_float(row.get("vol_30d")) is not None:
        risks.append(f"30D vol {fmt(row.get('vol_30d'), 1, '%')}")
    if safe_float(row.get("fx_mom_1m")) is not None:
        risks.append(f"FX 1M {fmt(row.get('fx_mom_1m'), 1, '%')}")
    if safe_float(row.get("y10")) is not None:
        risks.append(f"10Y yield {fmt(row.get('y10'), 2, '%')}")
    return "; ".join(risks) if risks else "N/A - missing risk fields."


def generate_relative_value_pairs(countries: List[Dict[str, Any]], sectors: List[Dict[str, Any]], styles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    pairs: List[Dict[str, Any]] = []
    for universe, label in [(countries, "Country"), (sectors, "Sector"), (styles, "Style")]:
        ranked = sorted([r for r in universe if safe_float(r.get("alpha_score")) is not None], key=lambda r: r["alpha_score"], reverse=True)
        if len(ranked) < 2:
            continue
        for long_row, short_row in zip(ranked[:4], list(reversed(ranked[-4:]))):
            score_gap = safe_float(long_row.get("alpha_score")) - safe_float(short_row.get("alpha_score"))
            pairs.append({
                "pair": f"Long {long_row['name']} / Short {short_row['name']}",
                "universe": label,
                "score_gap": round(score_gap, 1),
                "long_score": long_row.get("alpha_score"),
                "short_score": short_row.get("alpha_score"),
                "rationale": f"Long side has stronger composite signal by {round(score_gap, 1)} points.",
            })
    pairs.sort(key=lambda r: r["score_gap"], reverse=True)
    return pairs


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------


def panel(children: Any, title: Optional[str] = None, subtitle: Optional[str] = None) -> html.Div:
    body = []
    if title:
        body.append(html.Div([
            html.Div(title, style={"fontWeight": 700, "color": TEXT, "fontSize": "15px"}),
            html.Div(subtitle or "", style={"color": MUTED, "fontSize": "12px", "marginTop": "2px"}),
        ], style={"marginBottom": "10px"}))
    body.append(children)
    return html.Div(body, style={
        "backgroundColor": PANEL,
        "border": f"1px solid {BORDER}",
        "borderRadius": "8px",
        "padding": "14px",
        "height": "100%",
    })


def kpi(label: str, value: str, color: str = TEXT) -> html.Div:
    return html.Div([
        html.Div(label, style={"fontSize": "11px", "color": MUTED, "textTransform": "uppercase"}),
        html.Div(value, style={"fontSize": "22px", "fontWeight": 750, "color": color, "lineHeight": "1.2"}),
    ], style={"backgroundColor": PANEL, "border": f"1px solid {BORDER}", "borderRadius": "8px", "padding": "12px"})


def make_table(
    rows: List[Dict[str, Any]],
    columns: List[Dict[str, str]],
    page_size: int = 12,
    style_data_conditional: Optional[List[Dict[str, Any]]] = None,
) -> dash_table.DataTable:
    conditional_styles = [
        {"if": {"filter_query": "{alpha_score} >= 65", "column_id": "alpha_score"}, "color": GREEN, "fontWeight": "bold"},
        {"if": {"filter_query": "{alpha_score} <= 35", "column_id": "alpha_score"}, "color": RED, "fontWeight": "bold"},
        {"if": {"filter_query": "{score} >= 65", "column_id": "score"}, "color": GREEN, "fontWeight": "bold"},
        {"if": {"filter_query": "{score} <= 35", "column_id": "score"}, "color": RED, "fontWeight": "bold"},
        {"if": {"filter_query": "{status} contains 'N/A'"}, "color": YELLOW},
    ]
    if style_data_conditional:
        conditional_styles.extend(style_data_conditional)

    return dash_table.DataTable(
        data=rows,
        columns=columns,
        page_size=page_size,
        sort_action="native",
        filter_action="native",
        style_as_list_view=True,
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": PANEL_2, "color": ACCENT, "fontWeight": "bold", "border": f"1px solid {BORDER}"},
        style_cell={
            "backgroundColor": BG,
            "color": TEXT,
            "border": f"1px solid {BORDER}",
            "fontFamily": FONT,
            "fontSize": "12px",
            "padding": "7px",
            "minWidth": "90px",
            "maxWidth": "260px",
            "whiteSpace": "normal",
        },
        style_data_conditional=conditional_styles,
    )


def score_heatmap_styles(columns: List[str]) -> List[Dict[str, Any]]:
    styles: List[Dict[str, Any]] = []
    bands = [
        (75, 100, "rgba(37, 194, 110, 0.34)"),
        (60, 75, "rgba(37, 194, 110, 0.22)"),
        (50, 60, "rgba(37, 194, 110, 0.12)"),
        (40, 50, "rgba(240, 82, 82, 0.12)"),
        (25, 40, "rgba(240, 82, 82, 0.22)"),
        (0, 25, "rgba(240, 82, 82, 0.34)"),
    ]
    for column in columns:
        for low, high, color in bands:
            if high == 100:
                query = f"{{{column}}} >= {low} && {{{column}}} <= {high}"
            else:
                query = f"{{{column}}} >= {low} && {{{column}}} < {high}"
            styles.append({
                "if": {"filter_query": query, "column_id": column},
                "backgroundColor": color,
                "color": TEXT,
            })
    return styles


def dark_fig(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=dict(color=TEXT, family=FONT),
        margin=dict(l=40, r=20, t=55, b=45),
        height=height,
        legend=dict(orientation="h", y=-0.18),
    )
    fig.update_xaxes(gridcolor="#223044", zerolinecolor="#34465F")
    fig.update_yaxes(gridcolor="#223044", zerolinecolor="#34465F")
    return fig


def empty_fig(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font=dict(color=MUTED, size=14))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return dark_fig(fig)


def df_from_rows(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows or [])


def bar_chart(rows: List[Dict[str, Any]], x: str, y: str, title: str, suffix: str = "", limit: int = 20) -> go.Figure:
    df = df_from_rows(rows)
    if df.empty or x not in df or y not in df:
        return empty_fig("N/A - missing Bloomberg data")
    df[y] = pd.to_numeric(df[y], errors="coerce")
    df = df.dropna(subset=[y]).sort_values(y, ascending=False).head(limit)
    if df.empty:
        return empty_fig("N/A - missing Bloomberg data")
    colors = [score_to_color(v) if "score" in y else pct_color(v) for v in df[y]]
    fig = go.Figure(go.Bar(
        x=df[x],
        y=df[y],
        marker_color=colors,
        text=[fmt(v, 1, suffix) for v in df[y]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:.2f}<extra></extra>",
    ))
    fig.update_layout(title=title, yaxis_title=y.replace("_", " ").title())
    return dark_fig(fig)


def leadership_bar_chart(rows: List[Dict[str, Any]], y: str, title: str, suffix: str = "%", limit: int = 12) -> go.Figure:
    df = df_from_rows(rows)
    if df.empty or "name" not in df or y not in df:
        return empty_fig("N/A - missing Bloomberg data")
    df[y] = pd.to_numeric(df[y], errors="coerce")
    df = df.dropna(subset=[y]).sort_values(y, ascending=False).head(limit).sort_values(y, ascending=True)
    if df.empty:
        return empty_fig("N/A - missing Bloomberg data")
    fig = go.Figure(go.Bar(
        x=df[y],
        y=df["name"],
        orientation="h",
        marker_color=[pct_color(v) for v in df[y]],
        text=[fmt(v, 1, suffix) for v in df[y]],
        textposition="auto",
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:.2f}%<extra></extra>",
    ))
    fig.update_layout(title=title, xaxis_title="Return", yaxis_title=None)
    fig = dark_fig(fig, 440)
    fig.update_layout(margin=dict(l=128, r=28, t=55, b=42))
    return fig


def return_matrix_rows(rows: List[Dict[str, Any]], metrics: List[Tuple[str, str]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    countries = [row.get("name") for row in rows if row.get("name")]
    table_rows: List[Dict[str, Any]] = []
    for key, label in metrics:
        item: Dict[str, Any] = {"return_window": label}
        for row in rows:
            country = row.get("name")
            if not country:
                continue
            item[country] = fmt(row.get(key), 1, "%")
        table_rows.append(item)
    columns = [{"name": "Return", "id": "return_window"}] + [{"name": country, "id": country} for country in countries]
    return table_rows, columns


def heatmap(rows: List[Dict[str, Any]], row_key: str, metrics: List[str], title: str) -> go.Figure:
    df = df_from_rows(rows)
    if df.empty:
        return empty_fig("N/A - missing Bloomberg data")
    labels = df[row_key].tolist()
    z = []
    text = []
    for metric in metrics:
        vals = [safe_float(v) for v in df.get(metric, [])]
        z.append(vals)
        text.append([fmt(v, 1) for v in vals])
    if not z:
        return empty_fig("N/A - missing Bloomberg data")
    fig = go.Figure(go.Heatmap(
        z=z,
        x=labels,
        y=[m.replace("_", " ").title() for m in metrics],
        text=text,
        texttemplate="%{text}",
        colorscale=[[0, RED], [0.5, PANEL_2], [1, GREEN]],
        zmid=50 if "score" in ",".join(metrics) else 0,
        hovertemplate="<b>%{x}</b><br>%{y}: %{z}<extra></extra>",
    ))
    fig.update_layout(title=title)
    return dark_fig(fig, 410)


def scatter_value_quality(rows: List[Dict[str, Any]], title: str) -> go.Figure:
    df = df_from_rows(rows)
    if df.empty or "fwd_pe" not in df or "roe" not in df:
        return empty_fig("N/A - missing Bloomberg data")
    df["fwd_pe"] = pd.to_numeric(df["fwd_pe"], errors="coerce")
    df["roe"] = pd.to_numeric(df["roe"], errors="coerce")
    df["alpha_score"] = pd.to_numeric(df.get("alpha_score"), errors="coerce")
    df = df.dropna(subset=["fwd_pe", "roe"])
    if df.empty:
        return empty_fig("N/A - missing Bloomberg data")
    fig = go.Figure(go.Scatter(
        x=df["fwd_pe"],
        y=df["roe"],
        mode="markers+text",
        text=df["name"],
        textposition="top center",
        marker=dict(size=12, color=df["alpha_score"], colorscale=[[0, RED], [0.5, YELLOW], [1, GREEN]], cmin=0, cmax=100, showscale=True),
        hovertemplate="<b>%{text}</b><br>Fwd P/E: %{x:.1f}<br>ROE: %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(title=title, xaxis_title="Forward P/E", yaxis_title="ROE")
    return dark_fig(fig)


def display_rows(rows: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    out = []
    for row in rows:
        item = {}
        for key in keys:
            val = row.get(key)
            if isinstance(val, float):
                item[key] = round(val, 2)
            elif val is None:
                item[key] = NA
            else:
                item[key] = val
        out.append(item)
    return out


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------


def tab_idea_hub(data: Dict[str, Any]) -> html.Div:
    ideas = data.get("ideas", [])
    top_score = ideas[0]["score"] if ideas else None
    country_count = len([r for r in data.get("countries", []) if safe_float(r.get("alpha_score")) is not None])
    return html.Div([
        dbc.Row([
            dbc.Col(kpi("Top Idea Score", fmt(top_score, 0), score_to_color(top_score)), md=3),
            dbc.Col(kpi("Scored Markets", str(country_count)), md=3),
            dbc.Col(kpi("Data Source", data.get("source", NA)), md=3),
            dbc.Col(kpi("As Of", data.get("as_of", NA)), md=3),
        ], className="g-3 mb-3"),
        panel(make_table(
            display_rows(ideas, ["idea", "type", "score", "confidence", "rationale", "risk", "invalidation"]),
            [{"name": c.replace("_", " ").title(), "id": c} for c in ["idea", "type", "score", "confidence", "rationale", "risk", "invalidation"]],
            page_size=10,
        ), "Ranked Alpha Ideas", "Country, sector, and style ideas built from valuation, revisions, momentum, macro, FX, and risk signals."),
    ])


def tab_market_map(data: Dict[str, Any]) -> html.Div:
    countries = data.get("countries", [])
    return_metrics = [
        ("ret_1d", "1D"),
        ("ret_1w", "1W"),
        ("ret_1m", "1M"),
        ("ret_3m", "3M"),
        ("ret_ytd", "YTD"),
        ("ret_1y", "1Y"),
    ]
    return_rows, return_columns = return_matrix_rows(countries, return_metrics)
    return html.Div([
        dbc.Row([
            dbc.Col(panel(dcc.Graph(figure=leadership_bar_chart(countries, "ret_1m", "Country Index 1M Returns"), config=GRAPH_CFG), "1M Leadership"), md=6),
            dbc.Col(panel(dcc.Graph(figure=leadership_bar_chart(countries, "ret_ytd", "Country Index YTD Returns"), config=GRAPH_CFG), "YTD Leadership"), md=6),
        ], className="g-3"),
        html.Div(style={"height": "12px"}),
        panel(dcc.Graph(figure=heatmap(countries, "name", [key for key, _ in return_metrics], "Global Country Return Map"), config=GRAPH_CFG), "Return Heatmap"),
        html.Div(style={"height": "12px"}),
        panel(make_table(return_rows, return_columns, page_size=len(return_rows) or 6), "Return Table", "Countries are columns; return windows are rows."),
    ])


def tab_country_scorecard(data: Dict[str, Any], bucket: str = "All") -> html.Div:
    countries = data.get("countries", [])
    if bucket != "All":
        countries = [r for r in countries if r.get("bucket") == bucket]
    keys = ["rank", "name", "bucket", "region", "alpha_score", "confidence", "momentum_score", "revision_score", "valuation_score", "quality_score", "risk_score", "macro_score", "fx_score"]
    score_keys = ["alpha_score", "momentum_score", "revision_score", "valuation_score", "quality_score", "risk_score", "macro_score", "fx_score"]
    columns = [{"name": c.replace("_", " ").title(), "id": c} for c in keys]
    score_styles = score_heatmap_styles(score_keys)
    dm_rows = sorted([r for r in countries if r.get("bucket") == "DM"], key=lambda r: safe_float(r.get("alpha_score")) or -1, reverse=True)
    em_rows = sorted([r for r in countries if r.get("bucket") == "EM"], key=lambda r: safe_float(r.get("alpha_score")) or -1, reverse=True)

    footnote = (
        "Score methodology: raw Bloomberg fields are converted into cross-sectional z-scores across the country universe. "
        "Higher is better for 3M momentum, 3M EPS revisions, ROE quality, PMI/growth, and 1M FX momentum; lower is better for forward P/E valuation and 30D volatility risk. "
        "Signal scores are scaled as 50 + 18 x z-score and capped between 0 and 100. "
        "The alpha score is the available-weight composite of momentum 18%, revisions 24%, valuation 16%, quality 12%, risk 10%, macro 12%, and FX 8%. "
        "Confidence is the percent of the total signal weight with valid Bloomberg data; missing fields are shown as N/A and excluded from the composite."
    )

    return html.Div([
        dbc.Row([
            dbc.Col(panel(dcc.Graph(figure=bar_chart(dm_rows, "name", "alpha_score", "DM Country Allocation Scores"), config=GRAPH_CFG), "DM Country Ranking"), md=6),
            dbc.Col(panel(dcc.Graph(figure=bar_chart(em_rows, "name", "alpha_score", "EM Country Allocation Scores"), config=GRAPH_CFG), "EM Country Ranking"), md=6),
        ], className="g-3"),
        html.Div(style={"height": "12px"}),
        dbc.Row([
            dbc.Col(panel(make_table(display_rows(dm_rows, keys), columns, style_data_conditional=score_styles), "DM Signal Detail"), md=6),
            dbc.Col(panel(make_table(display_rows(em_rows, keys), columns, style_data_conditional=score_styles), "EM Signal Detail"), md=6),
        ], className="g-3"),
        html.Div(style={"height": "12px"}),
        html.Div(footnote, style={"color": MUTED, "fontSize": "12px", "lineHeight": "1.45", "padding": "0 2px 4px"}),
    ])


def tab_earnings(data: Dict[str, Any]) -> html.Div:
    countries = data.get("countries", [])
    sectors = data.get("sectors", [])
    return html.Div([
        dbc.Row([
            dbc.Col(panel(dcc.Graph(figure=bar_chart(countries, "name", "eps_rev_3m", "Country 3M EPS Revision", "%"), config=GRAPH_CFG), "Country Revisions"), md=6),
            dbc.Col(panel(dcc.Graph(figure=bar_chart(sectors, "name", "eps_rev_3m", "Sector 3M EPS Revision", "%"), config=GRAPH_CFG), "Sector Revisions"), md=6),
        ], className="g-3"),
        html.Div(style={"height": "12px"}),
        panel(dcc.Graph(figure=heatmap(countries, "name", ["eps_rev_4w", "eps_rev_3m", "ret_3m"], "Earnings Revision And Price Confirmation"), config=GRAPH_CFG), "Revision Breadth"),
    ])


def tab_valuation(data: Dict[str, Any]) -> html.Div:
    countries = data.get("countries", [])
    return html.Div([
        dbc.Row([
            dbc.Col(panel(dcc.Graph(figure=scatter_value_quality(countries, "Country Value vs Quality"), config=GRAPH_CFG), "P/E vs ROE"), md=6),
            dbc.Col(panel(dcc.Graph(figure=bar_chart(countries, "name", "valuation_score", "Valuation Signal Score"), config=GRAPH_CFG), "Valuation Score"), md=6),
        ], className="g-3"),
        html.Div(style={"height": "12px"}),
        panel(make_table(display_rows(countries, ["name", "fwd_pe", "pb", "div_yield", "roe", "valuation_score", "alpha_score"]), [{"name": c.replace("_", " ").title(), "id": c} for c in ["name", "fwd_pe", "pb", "div_yield", "roe", "valuation_score", "alpha_score"]]), "Valuation Table"),
    ])


def tab_macro_regime(data: Dict[str, Any]) -> html.Div:
    countries = data.get("countries", [])
    return html.Div([
        dbc.Row([
            dbc.Col(panel(dcc.Graph(figure=bar_chart(countries, "name", "pmi", "PMI / Growth Proxy"), config=GRAPH_CFG), "Growth"), md=6),
            dbc.Col(panel(dcc.Graph(figure=bar_chart(countries, "name", "y10", "10Y Yield"), config=GRAPH_CFG), "Rates"), md=6),
        ], className="g-3"),
        html.Div(style={"height": "12px"}),
        panel(dcc.Graph(figure=heatmap(countries, "name", ["macro_score", "risk_score", "fx_score", "alpha_score"], "Macro Regime Signal Matrix"), config=GRAPH_CFG), "Regime Matrix"),
    ])


def tab_cross_asset(data: Dict[str, Any]) -> html.Div:
    countries = data.get("countries", [])
    return html.Div([
        dbc.Row([
            dbc.Col(panel(dcc.Graph(figure=bar_chart(countries, "name", "fx_mom_1m", "Currency 1M Momentum", "%"), config=GRAPH_CFG), "FX"), md=6),
            dbc.Col(panel(dcc.Graph(figure=bar_chart(countries, "name", "rate", "Policy Rate Proxy"), config=GRAPH_CFG), "Policy Rates"), md=6),
        ], className="g-3"),
        html.Div(style={"height": "12px"}),
        panel(make_table(display_rows(countries, ["name", "ccy", "fx", "fx_mom_1m", "rate", "y10", "real_yield_proxy", "vol_30d"]), [{"name": c.replace("_", " ").title(), "id": c} for c in ["name", "ccy", "fx", "fx_mom_1m", "rate", "y10", "real_yield_proxy", "vol_30d"]]), "Rates, FX, Risk"),
    ])


def tab_sector_rotation(data: Dict[str, Any]) -> html.Div:
    sectors = data.get("sectors", [])
    return html.Div([
        dbc.Row([
            dbc.Col(panel(dcc.Graph(figure=bar_chart(sectors, "name", "alpha_score", "Global Sector Alpha Scores"), config=GRAPH_CFG), "Sector Scores"), md=6),
            dbc.Col(panel(dcc.Graph(figure=bar_chart(sectors, "name", "ret_3m", "Global Sector 3M Returns", "%"), config=GRAPH_CFG), "Sector Momentum"), md=6),
        ], className="g-3"),
        html.Div(style={"height": "12px"}),
        panel(make_table(display_rows(sectors, ["rank", "name", "alpha_score", "confidence", "ret_1m", "ret_3m", "eps_rev_3m", "fwd_pe", "div_yield"]), [{"name": c.replace("_", " ").title(), "id": c} for c in ["rank", "name", "alpha_score", "confidence", "ret_1m", "ret_3m", "eps_rev_3m", "fwd_pe", "div_yield"]]), "Sector Detail"),
    ])


def tab_style_factor(data: Dict[str, Any]) -> html.Div:
    styles = data.get("styles", [])
    return html.Div([
        dbc.Row([
            dbc.Col(panel(dcc.Graph(figure=bar_chart(styles, "name", "alpha_score", "Style / Factor Alpha Scores"), config=GRAPH_CFG), "Style Scores"), md=6),
            dbc.Col(panel(dcc.Graph(figure=bar_chart(styles, "name", "ret_3m", "Style / Factor 3M Returns", "%"), config=GRAPH_CFG), "Factor Momentum"), md=6),
        ], className="g-3"),
        html.Div(style={"height": "12px"}),
        panel(make_table(display_rows(styles, ["rank", "name", "alpha_score", "confidence", "ret_1m", "ret_3m", "eps_rev_3m", "fwd_pe", "div_yield"]), [{"name": c.replace("_", " ").title(), "id": c} for c in ["rank", "name", "alpha_score", "confidence", "ret_1m", "ret_3m", "eps_rev_3m", "fwd_pe", "div_yield"]]), "Style Detail"),
    ])


def tab_em_deep_dive(data: Dict[str, Any]) -> html.Div:
    em = [r for r in data.get("countries", []) if r.get("bucket") == "EM"]
    return html.Div([
        dbc.Row([
            dbc.Col(panel(dcc.Graph(figure=bar_chart(em, "name", "alpha_score", "EM Country Scores"), config=GRAPH_CFG), "EM Ranking"), md=6),
            dbc.Col(panel(dcc.Graph(figure=bar_chart(em, "name", "fx_mom_1m", "EM FX 1M Momentum", "%"), config=GRAPH_CFG), "EM FX"), md=6),
        ], className="g-3"),
        html.Div(style={"height": "12px"}),
        panel(make_table(display_rows(em, ["rank", "name", "region", "ccy", "alpha_score", "ret_3m", "eps_rev_3m", "fwd_pe", "rate", "y10", "fx_mom_1m"]), [{"name": c.replace("_", " ").title(), "id": c} for c in ["rank", "name", "region", "ccy", "alpha_score", "ret_3m", "eps_rev_3m", "fwd_pe", "rate", "y10", "fx_mom_1m"]]), "EM Detail"),
    ])


def tab_flows_positioning(data: Dict[str, Any]) -> html.Div:
    return html.Div([
        panel(html.Div([
            html.Div("N/A", style={"fontSize": "28px", "fontWeight": 750, "color": YELLOW}),
            html.Div("Flow and positioning fields are intentionally not backfilled. Add Bloomberg flow, ETF, futures positioning, short interest, or options-skew tickers to enable this tab.", style={"color": MUTED}),
        ]), "Flows And Positioning"),
        html.Div(style={"height": "12px"}),
        panel(make_table([], [{"name": c, "id": c} for c in ["Asset", "Flow 1W", "Flow 1M", "Positioning", "Skew", "Signal"]]), "Flow Monitor"),
    ])


def tab_relative_value(data: Dict[str, Any]) -> html.Div:
    pairs = data.get("pairs", [])
    return html.Div([
        panel(make_table(display_rows(pairs, ["pair", "universe", "score_gap", "long_score", "short_score", "rationale"]), [{"name": c.replace("_", " ").title(), "id": c} for c in ["pair", "universe", "score_gap", "long_score", "short_score", "rationale"]], page_size=14), "Relative Value Lab"),
        html.Div(style={"height": "12px"}),
        panel(dcc.Graph(figure=bar_chart(pairs, "pair", "score_gap", "Top Long / Short Signal Gaps"), config=GRAPH_CFG), "Pair Score Gaps"),
    ])


def tab_portfolio_risk(data: Dict[str, Any]) -> html.Div:
    return html.Div([
        panel(html.Div([
            html.Div("N/A", style={"fontSize": "28px", "fontWeight": 750, "color": YELLOW}),
            html.Div("Portfolio holdings were not provided. Upload or wire active weights to calculate active risk, beta, country/sector/style exposures, and stress scenarios.", style={"color": MUTED}),
        ]), "Portfolio Risk"),
        html.Div(style={"height": "12px"}),
        panel(make_table([], [{"name": c, "id": c} for c in ["Scenario", "Portfolio P/L", "Worst Contributors", "Hedge Candidates"]]), "Scenario Results"),
    ])


def tab_data_health(data: Dict[str, Any]) -> html.Div:
    health = data.get("health", [])
    country_tickers = [{"Asset": m["name"], "Ticker": m["index"], "Type": "Country Index"} for m in MARKETS]
    sector_tickers = [{"Asset": k, "Ticker": v, "Type": "Sector"} for k, v in SECTORS.items()]
    style_tickers = [{"Asset": k, "Ticker": v, "Type": "Style"} for k, v in STYLES.items()]
    macro_tickers = [{"Asset": country, "Ticker": ticker, "Type": kind} for country, d in MACRO_TICKERS.items() for kind, ticker in d.items()]
    return html.Div([
        panel(make_table(display_rows(health, ["ticker", "field", "status", "message"]), [{"name": c.title(), "id": c} for c in ["ticker", "field", "status", "message"]], page_size=14), "Data Health", data.get("source", NA)),
        html.Div(style={"height": "12px"}),
        panel(make_table(country_tickers + sector_tickers + style_tickers + macro_tickers, [{"name": c, "id": c} for c in ["Asset", "Ticker", "Type"]], page_size=16), "Ticker Map"),
    ])


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


FETCH = fetch_all_data()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = APP_TITLE

app.layout = html.Div([
    dcc.Store(id="store-data", data=FETCH.data),
    html.Div([
        html.Div([
            html.H1(APP_TITLE, style={"margin": 0, "fontWeight": 800, "fontSize": "26px", "color": TEXT}),
            html.Div("Alpha idea generation across DM, EM, sectors, and styles", style={"color": MUTED, "fontSize": "13px"}),
        ]),
        html.Div([
            dbc.Button("Refresh", id="btn-refresh", color="primary", size="sm"),
            html.Div(id="refresh-status", style={"color": MUTED, "fontSize": "12px", "marginTop": "6px", "textAlign": "right"}),
        ]),
    ], style={"display": "flex", "justifyContent": "space-between", "gap": "16px", "alignItems": "center", "marginBottom": "14px"}),
    dbc.Tabs(
        id="tabs",
        active_tab="ideas",
        children=[
            dbc.Tab(label="Alpha Ideas", tab_id="ideas"),
            dbc.Tab(label="Market Map", tab_id="market-map"),
            dbc.Tab(label="Country Scorecard", tab_id="country"),
            dbc.Tab(label="Earnings", tab_id="earnings"),
            dbc.Tab(label="Valuation", tab_id="valuation"),
            dbc.Tab(label="Macro Regime", tab_id="macro"),
            dbc.Tab(label="Rates FX Cross-Asset", tab_id="cross-asset"),
            dbc.Tab(label="Sector Rotation", tab_id="sectors"),
            dbc.Tab(label="Styles Factors", tab_id="styles"),
            dbc.Tab(label="EM Deep Dive", tab_id="em"),
            dbc.Tab(label="Flows Positioning", tab_id="flows"),
            dbc.Tab(label="Relative Value", tab_id="relative-value"),
            dbc.Tab(label="Portfolio Risk", tab_id="portfolio"),
            dbc.Tab(label="Data Health", tab_id="health"),
        ],
        style={"marginBottom": "14px"},
    ),
    html.Div(id="tab-content"),
], style={"backgroundColor": BG, "minHeight": "100vh", "padding": "18px", "fontFamily": FONT})


@app.callback(
    Output("store-data", "data"),
    Output("refresh-status", "children"),
    Input("btn-refresh", "n_clicks"),
    prevent_initial_call=True,
)
def refresh_data(_n_clicks: int) -> Tuple[Dict[str, Any], str]:
    result = fetch_all_data()
    return result.data, f"Updated {result.data.get('as_of', NA)}"


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab"),
    State("store-data", "data"),
)
def render_tab(active_tab: str, data: Dict[str, Any]) -> html.Div:
    data = data or FETCH.data
    if active_tab == "ideas":
        return tab_idea_hub(data)
    if active_tab == "market-map":
        return tab_market_map(data)
    if active_tab == "country":
        return tab_country_scorecard(data)
    if active_tab == "earnings":
        return tab_earnings(data)
    if active_tab == "valuation":
        return tab_valuation(data)
    if active_tab == "macro":
        return tab_macro_regime(data)
    if active_tab == "cross-asset":
        return tab_cross_asset(data)
    if active_tab == "sectors":
        return tab_sector_rotation(data)
    if active_tab == "styles":
        return tab_style_factor(data)
    if active_tab == "em":
        return tab_em_deep_dive(data)
    if active_tab == "flows":
        return tab_flows_positioning(data)
    if active_tab == "relative-value":
        return tab_relative_value(data)
    if active_tab == "portfolio":
        return tab_portfolio_risk(data)
    return tab_data_health(data)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8051)
