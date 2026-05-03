#!/usr/bin/env python3
"""

==========================================================================
  GLOBAL FIXED INCOME DASHBOARD — JPY Denominated
  DM Sovereign Focus | Global Multi Asset
==========================================================================
Run:    python fixed_income_dashboard.py
Deps:   pip install dash dash-bootstrap-components plotly pandas numpy

Bloomberg:

    - Bloomberg Terminal must be open and blpapi installed
    - If unavailable, dashboard loads with indicative Q1-2026 data
==========================================================================

#TODO: Add in return decomposition waterfall for yield changes (carry, roll, curve shift, spread change)

"""


import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dash
from dash import dcc, html, dash_table, Input, Output, State, ctx
import dash_bootstrap_components as dbc

warnings.filterwarnings("ignore")

# ── Optional: Bloomberg ───────────────────────────────────────────────────
try:

    import blpapi
    HAS_BBG = True
except ImportError:

    HAS_BBG = False

# ==========================================================================
#  BLOOMBERG TICKER DEFINITIONS
# ==========================================================================
#  Legend:  ✅ Standard/reliable  |  ⚠️ Please verify in BBG terminal
# ==========================================================================

YIELD_TICKERS = {
    "2Y": {
        "US":        "USGG2YR Index",     # ✅
        "Singapore": "MASB2Y Index",      # ✅
        "Australia": "GACGB2 Index",      # ✅
        "UK":        "GUKG2 Index",       # ✅
        "Germany":   "GDBR2 Index",       # ✅
        "France":    "GFRN2 Index",       # ⚠️ Verify — OAT 2Y benchmark
        "Italy":     "GBTPGR2 Index",     # ✅
        "Japan":     "JGBS2 Index",       # ✅
        "Canada":    "GCAN2YR Index",     # ✅
    },
    "5Y": {
        "US":        "USGG5YR Index",     # ✅
        "Singapore": "MASB5Y Index",      # ✅
        "Australia": "GACGB5 Index",      # ✅
        "UK":        "GUKG5 Index",       # ✅
        "Germany":   "GDBR5 Index",       # ✅
        "France":    "GFRN5 Index",       # ⚠️ Verify — OAT 5Y benchmark
        "Italy":     "GBTPGR5 Index",     # ✅
        "Japan":     "JGBS5 Index",       # ✅
        "Canada":    "GCAN5YR Index",     # ✅
    },
    "10Y": {
        "US":        "USGG10YR Index",    # ✅
        "Singapore": "MASB10Y Index",     # ✅
        "Australia": "GACGB10 Index",     # ✅
        "UK":        "GUKG10 Index",      # ✅
        "Germany":   "GDBR10 Index",      # ✅
        "France":    "GFRN10 Index",      # ⚠️ Verify — OAT 10Y benchmark
        "Italy":     "GBTPGR10 Index",    # ✅
        "Japan":     "JGBS10 Index",      # ✅
        "Canada":    "GCAN10YR Index",    # ✅
    },
    "30Y": {
        "US":        "USGG30YR Index",    # ✅
        "Australia": "GACGB30 Index",     # ✅
        "UK":        "GUKG30 Index",      # ✅
        "Germany":   "GDBR30 Index",      # ✅
        "France":    "GFRN30 Index",      # ⚠️ Verify — OAT 30Y benchmark
        "Italy":     "GBTPGR30 Index",    # ✅
        "Japan":     "JGBS30 Index",      # ✅
        "Canada":    "GCAN30YR Index",    # ✅
        "Singapore": "MASB30Y Index",
        # Singapore 30Y SGS: ⚠️ INPUT REQUIRED — no liquid 30Y benchmark
    },
}

MACRO_TICKERS = {
    "CPI_YOY": {
        "US":        "CPI YOY Index",     # ✅ Bloomberg CPI YoY calc
        "Australia": "AUCPIYOY Index",    # ✅
        "UK":        "UKRPCJYR Index",    # ✅ RPI; use UKCPIYOY for CPI
        "Euro Area": "ECCPEMUY Index",    # ✅
        "Germany":   "GRCP20YY Index",    # ⚠️ Verify — or GRCP2000 Index
        "France":    "FRCPIYOY Index",    # ⚠️ Verify — French CPI YoY
        "Italy":     "ITCPNICY Index",    # ⚠️ Verify
        "Japan":     "JNCPIYOY Index",    # ✅
        "Canada":    "CACPIYOY Index",    # ✅
        "Singapore": "SICPIYOY Index",    # ⚠️ Verify — or SICP YOY Index
    },
    "GDP_YOY": {
        "US":        "GDP CYOY Index",    # ✅ User verified
        "Australia": "AUNAGDPY Index",    # ✅ User verified
        "UK":        "UKGRYBZY Index",    # ✅ User verified
        "Euro Area": "EUGNEMUY Index",    # ✅ User verified
        "Germany":   "EHGDDE Index",      # ✅ User verified
        "France":    "FRGDPYOY Index",    # ⚠️ Verify — French GDP YoY
        "Italy":     "ITPIRLYS Index",    # ✅ User verified
        "Japan":     "JGDPNSAQ Index",    # ✅ User verified
        "Canada":    "CGE9YOY Index",     # ✅ User verified
        "Singapore": "SGDPYOY Index",     # ✅ User verified
    },
    "UNEMPLOYMENT": {
        "US":        "EHUPUS Index",     # ✅
        "Australia": "AULFUNEM Index",    # ✅
        "UK":        "UKUEILOR Index",    # ✅
        "Euro Area": "UMRTEMU Index",     # ✅
        "Germany":   "GRUEPR Index",      # ⚠️ Verify — or GRUETOTL Index
        "France":    "UMRTEMU Index",    # ⚠️ Verify — French unemployment rate
        "Italy":     "UMRTIT Index",      # ⚠️ Verify — or ITMUNEMP Index
        "Japan":     "JNUE Index",        # ✅
        "Canada":    "CANLXEMR Index",        # ✅
        "Singapore": "EHUPSG Index",      # ⚠️ INPUT REQUIRED
    },
    "PMI_MFG": {
        "US":        "NAPMPMI Index",     # ✅ ISM Manufacturing
        "Australia": "MPMIAUMA Index",    # ✅
        "UK":        "PMITMGE Index",     # ✅ S&P Global UK Mfg PMI
        "Euro Area": "MPMIEZMA Index",    # ✅
        "Germany":   "MPMIDEMA Index",    # ✅
        "France":    "MPMIFRMA Index",    # ✅ S&P Global France Mfg PMI
        "Italy":     "MPMIITMA Index",    # ✅
        "Japan":     "MPMIJPMA Index",    # ✅
        "Canada":    "IVEYSA Index",      # ✅ Ivey PMI (SA)
        "Singapore": "SPMINDX  Index",    # ⚠️ INPUT REQUIRED
    },
    "POLICY_RATE": {
        "US":          "FDTR Index",      # ✅ Fed Funds Target
        "Australia":   "RBATCTR Index",   # ✅ RBA Target Cash Rate
        "UK":          "UKBRBASE Index",  # ✅ BOE Base Rate
        "ECB":         "EURR002W Index",  # ✅ ECB Main Refi Rate
        "Japan":       "BOJDTR Index",     # ✅ BOJ Policy Rate
        "Canada":      "CCLR Index",      # ✅ BOC Overnight Rate
        "Singapore":   "SIBCSORA Index",    # ⚠️ Verify — MAS uses SORA; try SOFRS1D Index
    },
    "BREAKEVEN_1Y": {
        "US":      "USGGBE01 Index",      # ✅
        "UK":      "UKGGBE01 Index",      # ✅
        "Germany": "GTDEM1Y GOVT",      # ✅
        "Australia": "ADGGBE01 Index",
        "France":"FRGG01EB Index"
    },
    "BREAKEVEN_2Y": {
        "US":      "USGGBE02 Index",      # ✅
        "Germany": "GTDEM2Y GOVT",      # ✅
        "Australia": "ADGGBE02 Index",
        "France": "FRGG02EB Index"
    },
    "BREAKEVEN_3Y": {
        "Germany": "DEGGBE5 INDEX",      # ✅
    },
    "BREAKEVEN_5Y": {
        "US":        "USGGBE05 Index",    # ✅ TIPS-derived
        "Australia": "ADGGBE05 Index",    # ✅
        "UK":        "UKGGBE05 Index",    # ✅
        "Canada":    "CDGGBE05 Index",    # ✅
        "Germany":   "DEGGBE05 Index",    # ✅
        "France":    "FRGGBE05 Index",    # ⚠️ Verify — OATi-derived 5Y breakeven
        "Italy":     "ITGGBE5 Index",    # ✅
    },
    "BREAKEVEN_7Y": {
        "US":      "USGGBE07 Index",      # ✅
        "Germany": "DEGGBE07 Index",      # ✅
    },
    "BREAKEVEN_10Y": {
        "US":        "USGGBE10 Index",    # ✅ TIPS-derived
        "Australia": "ADGGBE10 Index",    # ✅
        "UK":        "UKGGBE10 Index",    # ✅
        "Canada":    "CDGGBE10 Index",    # ✅
        "Japan":     "JYGGBE10 Index",    # ✅ JGBi-derived
        "Germany":   "DEGGBE10 Index",    # ✅
        "France":    "FRGGBE10 Index",    # ⚠️ Verify — OATi-derived 10Y breakeven
        "Italy":     "ITGGBE10 Index",    # ✅
    },
    "BREAKEVEN_15Y": {
        "Australia": "ADGGBE15 Index",    # ✅
    },
    "BREAKEVEN_20Y": {
        "US":        "USGGBE20 Index",    # ✅
        "Australia": "ADGGBE20 Index",    # ✅
    },
    "BREAKEVEN_25Y": {
        "Germany": "DEGGBE25 Index",      # ✅
    },
    "BREAKEVEN_30Y": {
        "US":     "USGGBE30 Index",       # ✅
        "UK":     "UKGGBE30 Index",       # ✅
        "Canada": "CDGGBE30 Index",       # ✅
    },
    "TERM_PREMIUM": {
        "US 10Y ACM": "ACMTP10 Index",    # ✅ NY Fed ACM Term Premium
    },
    "CA_GDP": {
        "US":          "EHCAUS Index",    # ✅ Current Account % GDP
        "Singapore":   "EHCASG Index",    # ✅
        "Australia":   "EHCAAU Index",    # ✅
        "UK":          "EHCAGB Index",    # ✅
        "Germany":     "EHCADE Index",    # ✅
        "France":      "EHCAFR Index",    # ✅
        "Italy":       "EHCAIT Index",    # ✅
        "Japan":       "EHCAJP Index",    # ✅
        "Canada":      "EHCACA Index",    # ✅
    },
}

# ==========================================================================
# MACRO TIME SERIES EXPLORER — options for interactive chart
# ==========================================================================

_MACRO_TS_DISPLAY = {
    "CPI_YOY":        "CPI YoY (%)",
    "GDP_YOY":        "GDP YoY (%)",
    "UNEMPLOYMENT":   "Unemployment (%)",
    "PMI_MFG":        "PMI Mfg",
    "POLICY_RATE":    "Policy Rate (%)",
    "CA_GDP":         "CA / GDP (%)",
    "BREAKEVEN_1Y":   "Breakeven 1Y",
    "BREAKEVEN_2Y":   "Breakeven 2Y",
    "BREAKEVEN_3Y":   "Breakeven 3Y",
    "BREAKEVEN_5Y":   "Breakeven 5Y",
    "BREAKEVEN_7Y":   "Breakeven 7Y",
    "BREAKEVEN_10Y":  "Breakeven 10Y",
    "BREAKEVEN_15Y":  "Breakeven 15Y",
    "BREAKEVEN_20Y":  "Breakeven 20Y",
    "BREAKEVEN_25Y":  "Breakeven 25Y",
    "BREAKEVEN_30Y":  "Breakeven 30Y",
    "TERM_PREMIUM":   "Term Premium (US 10Y ACM)",
}

MACRO_TS_INDICATOR_OPTIONS = [
    {"label": _MACRO_TS_DISPLAY.get(k, k), "value": k}
    for k in MACRO_TICKERS.keys()
]

_MACRO_TS_ALL_COUNTRIES = sorted(set(
    c for tmap in MACRO_TICKERS.values() for c in tmap.keys()
))


# Bloomberg Economics fiscal balance (% GDP) — annual IMF/BBG series
# Pattern: EHFB{CC} Index  ⚠️ verify all in terminal
FISCAL_GDP_TICKERS = {
    "US":        "EHFBUS Index",    # ⚠️ Verify
    "Singapore": "EHFBSG Index",    # ⚠️ Verify
    "Australia": "EHFBAU Index",    # ⚠️ Verify
    "UK":        "EHFBGB Index",    # ⚠️ Verify
    "Germany":   "EHFBDE Index",    # ⚠️ Verify
    "France":    "EHFBFR Index",    # ⚠️ Verify
    "Italy":     "EHFBIT Index",    # ⚠️ Verify
    "Japan":     "EHFBJP Index",    # ⚠️ Verify
    "Canada":    "EHFBCA Index",    # ⚠️ Verify
}

# Bloomberg Economics general government debt (% GDP) — annual IMF/BBG series
# Pattern: EHGD{CC} Index  ⚠️ verify all in terminal
DEBT_GDP_TICKERS = {
    "US":        "EHGDUS Index",    # ⚠️ Verify
    "Singapore": "EHGDSG Index",    # ⚠️ Verify
    "Australia": "EHGDAU Index",    # ⚠️ Verify
    "UK":        "EHGDGB Index",    # ⚠️ Verify
    "Germany":   "EHGDDE Index",    # ⚠️ Verify
    "France":    "EHGDFR Index",    # ⚠️ Verify
    "Italy":     "EHGDIT Index",    # ⚠️ Verify
    "Japan":     "EHGDJP Index",    # ⚠️ Verify
    "Canada":    "EHGDCA Index",    # ⚠️ Verify
}

FX_TICKERS = {
    "USDJPY": "USDJPY Curncy",  # ✅
    "AUDJPY": "AUDJPY Curncy",  # ✅
    "GBPJPY": "GBPJPY Curncy",  # ✅
    "EURJPY": "EURJPY Curncy",  # ✅
    "SGDJPY": "SGDJPY Curncy",  # ✅
    "CADJPY": "CADJPY Curncy",  # ✅
}

# JPY hedge cost = JPYI3M CURNCY minus the foreign 3M rate
JPY_HEDGE_COST_TICKERS = {
    "US":        "TSFR3M Index",    # SOFR 3M compounded
    "Singapore": "SGDI3M Curncy",   # SGD 3M interbank
    "Germany":   "EURI3M Curncy",   # EURIBOR 3M
    "France":    "EURI3M Curncy",   # same EUR rate
    "Italy":     "EURI3M Curncy",   # same EUR rate
    "UK":        "GBPI3M Curncy",   # SONIA 3M
    "Australia": "AUDI3M Curncy",   # BBSW 3M
    "Canada":    "CADI3M Curncy",   # CDOR/CORRA 3M
}
JPY_3M_RATE_TICKER = "JPYI3M Curncy"

SGD_HEDGE_COST_TICKERS = {
    "US":        "TSFR3M Index",
    "Australia": "AUDI3M Curncy",
    "UK":        "GBPI3M Curncy",
    "Germany":   "EURI3M Curncy",
    "France":    "EURI3M Curncy",
    "Italy":     "EURI3M Curncy",
    "Canada":    "CADI3M Curncy",
    "Japan":     "JPYI3M Curncy",
}

# ── Real Yields (TIPS / Index-Linked Gilts / Bunds Linker / JGBi) ─────────
# ⚠️ US TIPS tickers (USGGT__Y) are confirmed. All non-US tickers need
#    terminal verification — real-yield series naming is less standardised.
REAL_YIELD_TICKERS = {
    "5Y": {
        "US":        "USGGT05Y Index",    # ✅ 5Y TIPS real yield
        "UK":        "UKGT05YR Index",    # ⚠️ Verify — 5Y UK index-linked gilt
        "Germany":   "DEIRGGT5 Index",    # ⚠️ Verify — German ILB 5Y
        "Australia": "GTAUD5L GOVT",      # ⚠️ Verify — Aus Capital Indexed Bond 5Y
        "Canada":    "GCAN5YRR Index",    # ⚠️ Verify — Canadian Real Return Bond 5Y
        "France":    "GFRN5YRR Index",    # ⚠️ Verify — OATi 5Y real yield
        "Japan":     "JYGGRY05 Index",    # ⚠️ Verify — JGBi 5Y real yield
    },
    "10Y": {
        "US":        "USGGT10Y Index",    # ✅ 10Y TIPS real yield
        "UK":        "UKGT10YR Index",    # ⚠️ Verify — 10Y UK index-linked gilt
        "Germany":   "DEIRGGT10 Index",   # ⚠️ Verify — German ILB 10Y
        "Australia": "GTAUD10L GOVT",     # ⚠️ Verify — Aus Capital Indexed Bond 10Y
        "Canada":    "GCAN10YRR Index",   # ⚠️ Verify — Canadian RRB 10Y
        "France":    "GFRN10YRR Index",   # ⚠️ Verify — OATi 10Y real yield
        "Japan":     "JYGGRY10 Index",    # ⚠️ Verify — JGBi 10Y real yield
    },
}

# ── Inflation Swap Rates (zero-coupon, annualised) ────────────────────────
# These are market-implied inflation expectations, not breakevens.
# US tickers confirmed; EUR and UK tickers need terminal verification.
INFL_SWAP_TICKERS = {
    "1Y": {
        "US":  "USSWIT1 Curncy",    # ✅ US CPI 1Y zero-coupon inflation swap
        "EUR": "EUSWI1 Curncy",     # ⚠️ Verify — EUR HICP 1Y swap
        "UK":  "BPSWI1 Curncy",     # ⚠️ Verify — UK RPI 1Y swap
    },
    "2Y": {
        "US":  "USSWIT2 Curncy",    # ✅
        "EUR": "EUSWI2 Curncy",     # ⚠️ Verify
        "UK":  "BPSWI2 Curncy",     # ⚠️ Verify
    },
    "5Y": {
        "US":  "USSWIT5 Curncy",    # ✅ US CPI 5Y zero-coupon swap
        "EUR": "EUSWI5 Curncy",     # ⚠️ Verify — EUR HICP 5Y swap
        "UK":  "BPSWI5 Curncy",     # ⚠️ Verify — UK RPI 5Y swap
    },
    "10Y": {
        "US":  "USSWIT10 Curncy",   # ✅ US CPI 10Y swap
        "EUR": "EUSWI10 Curncy",    # ⚠️ Verify
        "UK":  "BPSWI10 Curncy",    # ⚠️ Verify
    },
    "5Y5Y": {
        "US":  "USSWIF5 Curncy",    # ✅ US 5Y5Y forward inflation swap (key Fed watcher)
        "EUR": "EUSWE5F5 Curncy",   # ⚠️ Verify — EUR 5Y5Y (key ECB watcher)
        "UK":  "BPSWIF5 Curncy",    # ⚠️ Verify — UK 5Y5Y
    },
}

# ==========================================================================
#  OIS POLICY PATH TICKERS
#  ⚠️ All tickers require terminal verification — OIS naming is non-standard
#  Pattern: {CCY}SO{TENOR} Curncy or {CCY}SW{TENOR} Curncy depending on CB
# ==========================================================================

OIS_PATH_TICKERS = {
    "US": {           # USD SOFR OIS swaps
        "3M":  "USSO3M Curncy",    # ⚠️ Verify — USD SOFR OIS 3M
        "6M":  "USSO6M Curncy",    # ⚠️ Verify
        "12M": "USSO1 Curncy",     # ⚠️ Verify — USD SOFR OIS 1Y
        "18M": "USSO18M Curncy",   # ⚠️ Verify — USD SOFR OIS 18M
        "24M": "USSO2 Curncy",     # ⚠️ Verify — USD SOFR OIS 2Y
    },
    "ECB": {          # EUR ESTR OIS swaps
        "3M":  "EESW3M Curncy",    # ⚠️ Verify — EUR ESTR OIS 3M
        "6M":  "EESW6M Curncy",    # ⚠️ Verify
        "12M": "EESW1 Curncy",     # ⚠️ Verify — EUR ESTR OIS 1Y
        "18M": "EESW18M Curncy",   # ⚠️ Verify
        "24M": "EESW2 Curncy",     # ⚠️ Verify — EUR ESTR OIS 2Y
    },
    "UK": {           # GBP SONIA OIS swaps
        "3M":  "BPSW3M Curncy",    # ⚠️ Verify — GBP SONIA OIS 3M
        "6M":  "BPSW6M Curncy",    # ⚠️ Verify
        "12M": "BPSW1 Curncy",     # ⚠️ Verify — GBP SONIA OIS 1Y
        "18M": "BPSW18M Curncy",   # ⚠️ Verify
        "24M": "BPSW2 Curncy",     # ⚠️ Verify — GBP SONIA OIS 2Y
    },
    "Australia": {    # AUD AONIA OIS swaps
        "3M":  "ADSWAP3M Curncy",  # ⚠️ Verify — AUD AONIA OIS 3M
        "6M":  "ADSWAP6M Curncy",  # ⚠️ Verify
        "12M": "ADSWAP1 Curncy",   # ⚠️ Verify — AUD AONIA OIS 1Y
        "18M": "ADSWAP18M Curncy", # ⚠️ Verify
        "24M": "ADSWAP2 Curncy",   # ⚠️ Verify — AUD AONIA OIS 2Y
    },
    "Japan": {        # JPY TONA OIS swaps
        "3M":  "JYSW3M Curncy",    # ⚠️ Verify — JPY TONA OIS 3M
        "6M":  "JYSW6M Curncy",    # ⚠️ Verify
        "12M": "JYSW1 Curncy",     # ⚠️ Verify — JPY TONA OIS 1Y
        "18M": "JYSW18M Curncy",   # ⚠️ Verify
        "24M": "JYSW2 Curncy",     # ⚠️ Verify — JPY TONA OIS 2Y
    },
    "Canada": {       # CAD CORRA OIS swaps
        "3M":  "CDSW3M Curncy",    # ⚠️ Verify — CAD CORRA OIS 3M
        "6M":  "CDSW6M Curncy",    # ⚠️ Verify
        "12M": "CDSW1 Curncy",     # ⚠️ Verify — CAD CORRA OIS 1Y
        "18M": "CDSW18M Curncy",   # ⚠️ Verify
        "24M": "CDSW2 Curncy",     # ⚠️ Verify — CAD CORRA OIS 2Y
    },
}

# Maps OIS CB key → MACRO_TICKERS["POLICY_RATE"] key
OIS_CB_POLICY_MAP = {
    "US":        "US",
    "ECB":       "ECB",
    "UK":        "UK",
    "Australia": "Australia",
    "Japan":     "Japan",
    "Canada":    "Canada",
}

OIS_CB_FLAGS = {
    "US":        "🇺🇸",
    "ECB":       "🇪🇺",
    "UK":        "🇬🇧",
    "Australia": "🇦🇺",
    "Japan":     "🇯🇵",
    "Canada":    "🇨🇦",
}

OIS_CB_COLORS = {
    "US":        "#3B82F6",
    "ECB":       "#8B5CF6",
    "UK":        "#EF4444",
    "Australia": "#10B981",
    "Japan":     "#EC4899",
    "Canada":    "#A78BFA",
}

OIS_CB_UNDERLYING = {
    "US":        "SOFR (Secured Overnight Financing Rate)",
    "ECB":       "€STR (Euro Short-Term Rate)",
    "UK":        "SONIA (Sterling Overnight Index Average)",
    "Australia": "AONIA (Australian Overnight Index Average)",
    "Japan":     "TONA (Tokyo Overnight Average Rate)",
    "Canada":    "CORRA (Canadian Overnight Repo Rate Average)",
}

# ==========================================================================
#  STYLE CONSTANTS
# ==========================================================================

COUNTRIES    = ["US", "Singapore", "Australia", "UK", "Germany", "France", "Italy", "Japan", "Canada"]
FLAGS        = {"US": "🇺🇸", "Singapore": "🇸🇬", "Australia": "🇦🇺", "UK": "🇬🇧",
                "Germany": "🇩🇪", "France": "🇫🇷", "Italy": "🇮🇹", "Japan": "🇯🇵", "Canada": "🇨🇦"}
CCOLORS      = {"US": "#3B82F6", "Singapore": "#F59E0B", "Australia": "#10B981",
                "UK": "#EF4444", "Germany": "#8B5CF6", "France": "#F97316",
                "Italy": "#06B6D4", "Japan": "#EC4899", "Canada": "#A78BFA"}

BG_DEEP     = "#07090F"
BG_CARD     = "#0E1117"
BG_CARD2    = "#141821"
BORDER      = "#1E2535"
BORDER_LT   = "#2A3347"
TEXT        = "#CDD9EF"
TEXT_MUT    = "#5E7190"
ACCENT      = "#4F8EF7"
ACCENT2     = "#7C3AED"
GREEN       = "#22C55E"
GREEN_DIM   = "#166534"
RED         = "#EF4444"
RED_DIM     = "#7F1D1D"
YELLOW      = "#EAB308"
ORANGE      = "#F97316"
TEAL        = "#14B8A6"

FONT_FAMILY = "'IBM Plex Mono', 'JetBrains Mono', 'Courier New', monospace"

_MACRO_TS_FLAGS = {**FLAGS, "Euro Area": "🇪🇺", "ECB": "🇪🇺"}

MACRO_TS_COUNTRY_OPTIONS = [
    {"label": f"{_MACRO_TS_FLAGS.get(c, '')} {c}", "value": c}
    for c in _MACRO_TS_ALL_COUNTRIES
]
# ==========================================================================
#  BLOOMBERG FETCHER
# ==========================================================================


class BBGFetcher:

    def __init__(self):
        self.session = None
        self.ok = False
        if HAS_BBG:
            self._connect()
    def _connect(self):
        try:
            opts = blpapi.SessionOptions()
            opts.setServerHost("localhost")
            opts.setServerPort(8194)
            self.session = blpapi.Session(opts)
            if self.session.start() and self.session.openService("//blp/refdata"):
                self.ok = True
                print("✅ Bloomberg API connected")
        except Exception as e:
            print(f"⚠️  Bloomberg connection: {e}")
    def bdp(self, tickers: List[str], fields: List[str]) -> pd.DataFrame:
        """BDP — current reference data"""
        if not self.ok:
            return pd.DataFrame()
        try:
            svc = self.session.getService("//blp/refdata")
            req = svc.createRequest("ReferenceDataRequest")
            for t in tickers:
                req.getElement("securities").appendValue(t)
            for f in fields:
                req.getElement("fields").appendValue(f)
            self.session.sendRequest(req)
            rows = {}
            while True:
                ev = self.session.nextEvent(3000)
                for msg in ev:
                    if msg.hasElement("securityData"):
                        arr = msg.getElement("securityData")
                        for i in range(arr.numValues()):
                            sd  = arr.getValue(i)
                            sec = sd.getElementAsString("security")
                            fd  = sd.getElement("fieldData")
                            rows[sec] = {}
                            for f in fields:
                                try:    rows[sec][f] = fd.getElementAsFloat(f)
                                except Exception:
                                    try:    rows[sec][f] = fd.getElementAsString(f)
                                    except Exception: rows[sec][f] = None
                if ev.eventType() == blpapi.Event.RESPONSE:
                    break
            return pd.DataFrame(rows).T
        except Exception as e:
            print(f"  BDP error: {e}")
            return pd.DataFrame()
    def bdh(self, tickers: List[str], field: str,
            start: str, end: str, freq: str = "DAILY") -> pd.DataFrame:
        """BDH — historical time series"""
        if not self.ok:
            return pd.DataFrame()
        try:
            svc = self.session.getService("//blp/refdata")
            req = svc.createRequest("HistoricalDataRequest")
            for t in tickers:
                req.getElement("securities").appendValue(t)
            req.getElement("fields").appendValue(field)
            req.set("startDate", start)
            req.set("endDate", end)
            req.set("periodicitySelection", freq)
            self.session.sendRequest(req)
            data = {}
            while True:
                ev = self.session.nextEvent(3000)
                for msg in ev:
                    if msg.hasElement("securityData"):
                        sd  = msg.getElement("securityData")
                        tkr = sd.getElementAsString("security")
                        fda = sd.getElement("fieldData")
                        dates, vals = [], []
                        for i in range(fda.numValues()):
                            pt = fda.getValue(i)
                            dates.append(pt.getElementAsDatetime("date"))
                            try:    vals.append(pt.getElementAsFloat(field))
                            except Exception: vals.append(np.nan)
                        data[tkr] = pd.Series(vals, index=pd.DatetimeIndex(dates))
                if ev.eventType() == blpapi.Event.RESPONSE:
                    break
            return pd.DataFrame(data) if data else pd.DataFrame()
        except Exception as e:
            print(f"  BDH error: {e}")
            return pd.DataFrame()

bbg = BBGFetcher()

# ==========================================================================
# ==========================================================================
#  DATA LAYER
# ==========================================================================


def fetch_yields_bbg() -> Dict:

    result = {t: {} for t in YIELD_TICKERS}
    for tenor, tmap in YIELD_TICKERS.items():
        tickers = list(tmap.values())
        df = bbg.bdp(tickers, ["PX_LAST"])
        for country, tkr in tmap.items():
            if df.empty:
                print(f"  ⚠️ BBG yields [{tenor}]: empty DataFrame returned")
                continue
            if tkr not in df.index:
                print(f"  ⚠️ BBG yields [{tenor}] {country}: ticker '{tkr}' not in response index {list(df.index)}")
                continue
            raw = df.loc[tkr, "PX_LAST"]
            if raw is None:
                print(f"  ⚠️ BBG yields [{tenor}] {country} ({tkr}): PX_LAST returned None — try YLD_YTM_MID or LAST_PRICE")
                continue
            try:
                result[tenor][country] = float(raw)
            except Exception as e:
                print(f"  ⚠️ BBG yields [{tenor}] {country} ({tkr}): could not cast '{raw}' to float: {e}")
    return result


def fetch_macro_bbg() -> Dict:

    result = {}
    for indicator, tmap in MACRO_TICKERS.items():
        tickers = list(tmap.values())
        df = bbg.bdp(tickers, ["PX_LAST"])
        result[indicator] = {}
        for country, tkr in tmap.items():
            if df.empty:
                print(f"  ⚠️ BBG macro [{indicator}]: empty DataFrame returned")
                continue
            if tkr not in df.index:
                print(f"  ⚠️ BBG macro [{indicator}] {country}: ticker '{tkr}' not in response")
                continue
            raw = df.loc[tkr, "PX_LAST"]
            if raw is None:
                print(f"  ⚠️ BBG macro [{indicator}] {country} ({tkr}): PX_LAST returned None")
                continue
            try:
                result[indicator][country] = float(raw)
            except Exception as e:
                print(f"  ⚠️ BBG macro [{indicator}] {country} ({tkr}): could not cast '{raw}' to float: {e}")
    return result


def fetch_macro_prev_bbg() -> Dict:

    """Fetch the previous period value for CPI, GDP, Unemployment, PMI via bdh."""
    result  = {ind: {} for ind in ["CPI_YOY", "GDP_YOY", "UNEMPLOYMENT", "PMI_MFG", "CA_GDP"]}
    freq_map    = {"CPI_YOY": "MONTHLY", "GDP_YOY": "QUARTERLY",
                   "UNEMPLOYMENT": "MONTHLY", "PMI_MFG": "MONTHLY",
                   "CA_GDP": "YEARLY"}
    lookback_map = {"CPI_YOY": 90, "GDP_YOY": 210,
                    "UNEMPLOYMENT": 90, "PMI_MFG": 90,
                    "CA_GDP": 800}
    end = datetime.today().strftime("%Y%m%d")
    for indicator in result:
        tmap    = MACRO_TICKERS.get(indicator, {})
        tickers = list(tmap.values())
        start   = (datetime.today() - timedelta(days=lookback_map[indicator])).strftime("%Y%m%d")
        df      = bbg.bdh(tickers, "PX_LAST", start, end, freq=freq_map[indicator])
        if df is None or df.empty or len(df) < 2:
            print(f"  ⚠️ BBG macro prev [{indicator}]: insufficient history returned")
            continue
        rev        = {v: k for k, v in tmap.items()}
        df.columns = [rev.get(c, c) for c in df.columns]
        prev_row   = df.iloc[-2]
        for country, tkr in tmap.items():
            if country not in prev_row.index or pd.isna(prev_row[country]):
                print(f"  ⚠️ BBG macro prev [{indicator}] {country} ({tkr}): no previous period value")
            else:
                result[indicator][country] = float(prev_row[country])
    return result


def fetch_fiscal_debt_bbg() -> Dict:
    """
    Fetch fiscal balance (% GDP) and government debt (% GDP) from Bloomberg Economics.
    Uses bdp PX_LAST for current year, then bdh with YEARLY frequency for prev year.
    Returns: {"fiscal_gdp": {...}, "fiscal_gdp_prev": {...}, "debt_gdp": {...}}
    """
    result = {"fiscal_gdp": {}, "fiscal_gdp_prev": {}, "debt_gdp": {}}

    # ── Current values ────────────────────────────────────────────────────
    fiscal_tickers = list(FISCAL_GDP_TICKERS.values())
    debt_tickers   = list(DEBT_GDP_TICKERS.values())

    df_fiscal = bbg.bdp(fiscal_tickers, ["PX_LAST"])
    df_debt   = bbg.bdp(debt_tickers,   ["PX_LAST"])

    for country, tkr in FISCAL_GDP_TICKERS.items():
        if df_fiscal.empty:
            print(f"  ⚠️ BBG fiscal GDP: empty DataFrame"); break
        if tkr not in df_fiscal.index:
            print(f"  ⚠️ BBG fiscal GDP {country}: ticker '{tkr}' not in response"); continue
        raw = df_fiscal.loc[tkr, "PX_LAST"]
        if raw is None:
            print(f"  ⚠️ BBG fiscal GDP {country} ({tkr}): PX_LAST returned None"); continue
        try:
            result["fiscal_gdp"][country] = float(raw)
        except Exception as e:
            print(f"  ⚠️ BBG fiscal GDP {country} ({tkr}): could not cast '{raw}' to float: {e}")

    for country, tkr in DEBT_GDP_TICKERS.items():
        if df_debt.empty:
            print(f"  ⚠️ BBG debt GDP: empty DataFrame"); break
        if tkr not in df_debt.index:
            print(f"  ⚠️ BBG debt GDP {country}: ticker '{tkr}' not in response"); continue
        raw = df_debt.loc[tkr, "PX_LAST"]
        if raw is None:
            print(f"  ⚠️ BBG debt GDP {country} ({tkr}): PX_LAST returned None"); continue
        try:
            result["debt_gdp"][country] = float(raw)
        except Exception as e:
            print(f"  ⚠️ BBG debt GDP {country} ({tkr}): could not cast '{raw}' to float: {e}")

    # ── Previous year fiscal balance ──────────────────────────────────────
    end   = datetime.today().strftime("%Y%m%d")
    start = (datetime.today() - timedelta(days=800)).strftime("%Y%m%d")
    df_fh = bbg.bdh(fiscal_tickers, "PX_LAST", start, end, freq="YEARLY")
    if df_fh is not None and not df_fh.empty and len(df_fh) >= 2:
        rev = {v: k for k, v in FISCAL_GDP_TICKERS.items()}
        df_fh.columns = [rev.get(c, c) for c in df_fh.columns]
        prev_row = df_fh.iloc[-2]
        for country in FISCAL_GDP_TICKERS:
            if country in prev_row.index and not pd.isna(prev_row[country]):
                result["fiscal_gdp_prev"][country] = float(prev_row[country])
            else:
                print(f"  ⚠️ BBG fiscal GDP prev {country}: no previous year value")
    else:
        print("  ⚠️ BBG fiscal GDP prev: insufficient history returned")

    return result


def fetch_fx_bbg() -> Dict:

    tickers = list(FX_TICKERS.values())
    df = bbg.bdp(tickers, ["PX_LAST"])
    result = {}
    for pair, tkr in FX_TICKERS.items():
        if df.empty:
            print(f"  ⚠️ BBG FX: empty DataFrame returned")
            break
        if tkr not in df.index:
            print(f"  ⚠️ BBG FX {pair}: ticker '{tkr}' not in response")
            continue
        raw = df.loc[tkr, "PX_LAST"]
        if raw is None:
            print(f"  ⚠️ BBG FX {pair} ({tkr}): PX_LAST returned None")
            continue
        try:
            result[pair] = float(raw)
        except Exception as e:
            print(f"  ⚠️ BBG FX {pair} ({tkr}): could not cast '{raw}' to float: {e}")
    return result


def fetch_jpy_hedge_costs_bbg() -> Dict:

    """Hedge cost for JPY investor = JPYI3M - foreign 3M rate, annualised."""
    all_tickers = list(set(JPY_HEDGE_COST_TICKERS.values())) + [JPY_3M_RATE_TICKER]
    df = bbg.bdp(all_tickers, ["PX_LAST"])
    result = {}
    if df.empty:
        print(f"  ⚠️ BBG JPY hedge costs: empty DataFrame returned")
        return result
    try:
        jpy3m = float(df.loc[JPY_3M_RATE_TICKER, "PX_LAST"])
    except (KeyError, ValueError):
        print(f"  ⚠️ BBG JPY hedge costs: could not fetch JPY 3M rate ({JPY_3M_RATE_TICKER})")
        return result
    for country, tkr in JPY_HEDGE_COST_TICKERS.items():
        try:
            foreign3m = float(df.loc[tkr, "PX_LAST"])
            result[country] = round(jpy3m - foreign3m, 4)
        except (KeyError, ValueError):
            print(f"  ⚠️ BBG JPY hedge costs {country}: ticker '{tkr}' failed")
    return result


def fetch_xccy_basis_bbg() -> Dict:

    """Xccy basis vs JPY = JPYI3M minus the foreign 3M rate."""
    all_tickers = list(set(_XCCY_JPY_PAIR_MAP.values())) + [JPY_3M_RATE_TICKER]
    df = bbg.bdp(all_tickers, ["PX_LAST"])
    result = {}
    if df.empty:
        print(f"  ⚠️ BBG xccy basis (JPY): empty DataFrame returned")
        return result
    try:
        jpy3m = float(df.loc[JPY_3M_RATE_TICKER, "PX_LAST"])
    except (KeyError, ValueError):
        print(f"  ⚠️ BBG xccy basis (JPY): could not fetch JPY 3M rate ({JPY_3M_RATE_TICKER})")
        return result
    for pair, tkr in _XCCY_JPY_PAIR_MAP.items():
        try:
            foreign3m = float(df.loc[tkr, "PX_LAST"])
            result[pair] = round(jpy3m - foreign3m, 4)
        except (KeyError, ValueError):
            print(f"  ⚠️ BBG xccy basis {pair}: ticker '{tkr}' failed")
    return result

SGD_3M_RATE_TICKER = "SGDI3M Curncy"

# Xccy basis pair maps — single source of truth used by fetch functions and Ticker Reference tab
_XCCY_JPY_PAIR_MAP = {
    "USD/JPY 3M": "TSFR3M Index",
    "SGD/JPY 3M": "SGDI3M Curncy",
    "EUR/JPY 3M": "EURI3M Curncy",
    "GBP/JPY 3M": "GBPI3M Curncy",
    "AUD/JPY 3M": "AUDI3M Curncy",
    "CAD/JPY 3M": "CADI3M Curncy",
}
_XCCY_SGD_PAIR_MAP = {
    "USD/SGD 3M": "TSFR3M Index",
    "JPY/SGD 3M": "JPYI3M Curncy",
    "EUR/SGD 3M": "EURI3M Curncy",
    "GBP/SGD 3M": "GBPI3M Curncy",
    "AUD/SGD 3M": "AUDI3M Curncy",
    "CAD/SGD 3M": "CADI3M Curncy",
}


def fetch_xccy_basis_sgd_bbg() -> Dict:

    """Xccy basis vs SGD = SGDI3M minus the foreign 3M rate."""
    all_tickers = list(set(_XCCY_SGD_PAIR_MAP.values())) + [SGD_3M_RATE_TICKER]
    df = bbg.bdp(all_tickers, ["PX_LAST"])
    result = {}
    if df.empty:
        print(f"  ⚠️ BBG xccy basis (SGD): empty DataFrame returned")
        return result
    try:
        sgd3m = float(df.loc[SGD_3M_RATE_TICKER, "PX_LAST"])
    except (KeyError, ValueError):
        print(f"  ⚠️ BBG xccy basis (SGD): could not fetch SGD 3M rate ({SGD_3M_RATE_TICKER})")
        return result
    for pair, tkr in _XCCY_SGD_PAIR_MAP.items():
        try:
            foreign3m = float(df.loc[tkr, "PX_LAST"])
            result[pair] = round(sgd3m - foreign3m, 4)
        except (KeyError, ValueError):
            print(f"  ⚠️ BBG xccy basis {pair}: ticker '{tkr}' failed")
    return result


def fetch_sgd_hedge_costs_bbg() -> Dict:
    """Hedge cost for SGD investor = SGDI3M − foreign 3M rate, annualised."""
    all_tickers = list(set(SGD_HEDGE_COST_TICKERS.values())) + [SGD_3M_RATE_TICKER]
    df = bbg.bdp(all_tickers, ["PX_LAST"])
    result = {}
    if df.empty:
        print(f"  ⚠️ BBG SGD hedge costs: empty DataFrame returned")
        print(f"     Need: {SGD_3M_RATE_TICKER} | PX_LAST")
        return result
    try:
        sgd3m = float(df.loc[SGD_3M_RATE_TICKER, "PX_LAST"])
    except (KeyError, ValueError):
        print(f"  ⚠️ BBG SGD hedge costs: could not fetch SGD 3M rate")
        print(f"     Need: {SGD_3M_RATE_TICKER} | PX_LAST")
        return result
    for country, tkr in SGD_HEDGE_COST_TICKERS.items():
        try:
            foreign3m = float(df.loc[tkr, "PX_LAST"])
            result[country] = round(sgd3m - foreign3m, 4)
        except (KeyError, ValueError):
            print(f"  ⚠️ BBG SGD hedge costs {country}: ticker '{tkr}' | PX_LAST failed")
    return result


def fetch_ois_path_bbg() -> Dict:
    """
    Fetch OIS (overnight indexed swap) rates for major central banks at
    3M, 6M, 12M, 18M, 24M. Returns market-implied policy rate path.
    All tickers marked ⚠️ require terminal verification.
    """
    result = {cb: {} for cb in OIS_PATH_TICKERS}
    all_tickers = list({tkr for cb_map in OIS_PATH_TICKERS.values() for tkr in cb_map.values()})
    df = bbg.bdp(all_tickers, ["PX_LAST"])
    if df.empty:
        print("  ⚠️ BBG OIS path: empty DataFrame returned — verify tickers in terminal")
        return result
    for cb, tenor_map in OIS_PATH_TICKERS.items():
        for tenor, tkr in tenor_map.items():
            if tkr not in df.index:
                print(f"  ⚠️ BBG OIS path [{cb}] {tenor}: ticker '{tkr}' not in response")
                continue
            raw = df.loc[tkr, "PX_LAST"]
            if raw is None:
                print(f"  ⚠️ BBG OIS path [{cb}] {tenor} ({tkr}): PX_LAST returned None")
                continue
            try:
                result[cb][tenor] = float(raw)
            except Exception as e:
                print(f"  ⚠️ BBG OIS path [{cb}] {tenor} ({tkr}): cast failed: {e}")
    return result


def fetch_real_yields_bbg() -> Dict:
    """Fetch real yields (TIPS/linker) at 5Y and 10Y from Bloomberg."""
    result = {tenor: {} for tenor in REAL_YIELD_TICKERS}
    for tenor, tmap in REAL_YIELD_TICKERS.items():
        tickers = list(tmap.values())
        df = bbg.bdp(tickers, ["PX_LAST"])
        for country, tkr in tmap.items():
            if df.empty:
                print(f"  ⚠️ BBG real yields [{tenor}]: empty DataFrame returned")
                continue
            if tkr not in df.index:
                print(f"  ⚠️ BBG real yields [{tenor}] {country}: ticker '{tkr}' not in response")
                continue
            raw = df.loc[tkr, "PX_LAST"]
            if raw is None:
                print(f"  ⚠️ BBG real yields [{tenor}] {country} ({tkr}): PX_LAST returned None")
                continue
            try:
                result[tenor][country] = float(raw)
            except Exception as e:
                print(f"  ⚠️ BBG real yields [{tenor}] {country} ({tkr}): cast failed: {e}")
    return result


def fetch_infl_swaps_bbg() -> Dict:
    """Fetch zero-coupon inflation swap rates at 1Y, 2Y, 5Y, 10Y, 5Y5Y from Bloomberg."""
    result = {tenor: {} for tenor in INFL_SWAP_TICKERS}
    for tenor, tmap in INFL_SWAP_TICKERS.items():
        tickers = list(tmap.values())
        df = bbg.bdp(tickers, ["PX_LAST"])
        for region, tkr in tmap.items():
            if df.empty:
                print(f"  ⚠️ BBG infl swaps [{tenor}]: empty DataFrame returned")
                continue
            if tkr not in df.index:
                print(f"  ⚠️ BBG infl swaps [{tenor}] {region}: ticker '{tkr}' not in response")
                continue
            raw = df.loc[tkr, "PX_LAST"]
            if raw is None:
                print(f"  ⚠️ BBG infl swaps [{tenor}] {region} ({tkr}): PX_LAST returned None")
                continue
            try:
                result[tenor][region] = float(raw)
            except Exception as e:
                print(f"  ⚠️ BBG infl swaps [{tenor}] {region} ({tkr}): cast failed: {e}")
    return result


def fetch_real_yield_history_bbg(tenor: str = "10Y", days: int = 504) -> Optional[pd.DataFrame]:
    """Fetch historical TIPS/linker real yield time series from Bloomberg."""
    if not bbg.ok:
        return None
    tmap = REAL_YIELD_TICKERS.get(tenor, {})
    if not tmap:
        return None
    tickers  = list(tmap.values())
    end      = datetime.today().strftime("%Y%m%d")
    cal_days = int(days * 1.45)
    start    = (datetime.today() - timedelta(days=cal_days)).strftime("%Y%m%d")
    df       = bbg.bdh(tickers, "PX_LAST", start, end)
    if df.empty:
        print(f"  ⚠️ BBG real yield history [{tenor}]: empty response")
        return None
    rev        = {v: k for k, v in tmap.items()}
    df.columns = [rev.get(c, c) for c in df.columns]
    return df


def fetch_breakeven_history_bbg(tenor: str = "10Y", days: int = 730) -> Optional[pd.DataFrame]:
    """Fetch historical breakeven inflation time series from Bloomberg."""
    if not bbg.ok:
        return None
    key  = f"BREAKEVEN_{tenor}"
    tmap = MACRO_TICKERS.get(key, {})
    if not tmap:
        print(f"  ⚠️ BBG breakeven history: no tickers defined for {key}")
        return None
    tickers  = list(tmap.values())
    end      = datetime.today().strftime("%Y%m%d")
    cal_days = int(days * 1.45)
    start    = (datetime.today() - timedelta(days=cal_days)).strftime("%Y%m%d")
    df       = bbg.bdh(tickers, "PX_LAST", start, end)
    if df.empty:
        print(f"  ⚠️ BBG breakeven history [{tenor}]: empty response")
        return None
    rev        = {v: k for k, v in tmap.items()}
    df.columns = [rev.get(c, c) for c in df.columns]
    return df


def fetch_hist_yields_bbg(tenor: str = "10Y", days: int = 504) -> Optional[pd.DataFrame]:

    tmap    = YIELD_TICKERS.get(tenor, {})
    tickers = list(tmap.values())
    end     = datetime.today().strftime("%Y%m%d")
    # days is in trading days; convert to calendar days (×1.45) so the date
    # range always covers the full requested period
    cal_days = int(days * 1.45)
    start   = (datetime.today() - timedelta(days=cal_days)).strftime("%Y%m%d")
    df      = bbg.bdh(tickers, "PX_LAST", start, end)
    if not df.empty:
        rev    = {v: k for k, v in tmap.items()}
        df.columns = [rev.get(c, c) for c in df.columns]
    return df if not df.empty else None


def get_data() -> Dict:

    """Master data fetch — Bloomberg if live, else all fields empty (N/A)"""
    if bbg.ok:
        print("📡 Fetching live Bloomberg data …")
        yields        = fetch_yields_bbg()
        macro         = fetch_macro_bbg()
        fx            = fetch_fx_bbg()
        hc            = fetch_jpy_hedge_costs_bbg()
        sgd_hc        = fetch_sgd_hedge_costs_bbg()
        xccy_live     = fetch_xccy_basis_bbg()
        xccy_sgd_live = fetch_xccy_basis_sgd_bbg()
        macro_prev    = fetch_macro_prev_bbg()
        real_yields   = fetch_real_yields_bbg()
        infl_swaps    = fetch_infl_swaps_bbg()
        fiscal_debt   = fetch_fiscal_debt_bbg()
        ois_path      = fetch_ois_path_bbg()
        source        = "Bloomberg Live"
    else:
        yields        = {t: {} for t in YIELD_TICKERS}
        macro         = {ind: {} for ind in MACRO_TICKERS}
        fx            = {}
        hc            = {}
        sgd_hc        = {}
        xccy_live     = {}
        xccy_sgd_live = {}
        macro_prev    = {}
        real_yields   = {tenor: {} for tenor in REAL_YIELD_TICKERS}
        infl_swaps    = {tenor: {} for tenor in INFL_SWAP_TICKERS}
        fiscal_debt   = {"fiscal_gdp": {}, "fiscal_gdp_prev": {}, "debt_gdp": {}}
        ois_path      = {cb: {} for cb in OIS_PATH_TICKERS}
        source        = "⚠️ Bloomberg not connected — all market data N/A (connect terminal for live data)"
        print("⚠️  Bloomberg not connected — dashboard will render with N/A values for all market data.")
    y10 = yields.get("10Y", {})
    y2  = yields.get("2Y",  {})
    slopes = {c: round(y10[c] - y2[c], 2)
              for c in COUNTRIES if c in y10 and c in y2}
    hedged_10y = {
        c: round(y10[c] + hc[c], 2)
        for c in COUNTRIES if c != "Japan" and c in y10 and c in hc
    }
    spread_vs_jgb = {
        c: round(y10[c] - y10["Japan"], 2)
        for c in COUNTRIES if c != "Japan" and c in y10 and "Japan" in y10
    }
    return {
        "yields":          yields,
        "macro":           macro,
        "macro_prev":      macro_prev,
        "fx":              fx,
        "slopes":          slopes,
        "hedge_costs":     hc,
        "sgd_hedge_costs": sgd_hc,
        "hedged_10y":      hedged_10y,
        "spread_vs_jgb":   spread_vs_jgb,
        "xccy_basis":      xccy_live,
        "xccy_basis_sgd":  xccy_sgd_live,
        "ca_gdp":          macro.get("CA_GDP", {}),
        "ca_gdp_prev":     macro_prev.get("CA_GDP", {}),
        "debt_gdp":        fiscal_debt["debt_gdp"],
        "fiscal_gdp":      fiscal_debt["fiscal_gdp"],
        "fiscal_gdp_prev": fiscal_debt["fiscal_gdp_prev"],
        "ratings":         {},
        "rate_cycle":      {},
        "real_yields":     real_yields,
        "infl_swaps":      infl_swaps,
        "ois_path":        ois_path,
        "source":          source,
        "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


_HIST_DF_CACHE: Dict[tuple, pd.DataFrame] = {}
_HIST_DF_CACHE_TS: Dict[tuple, float] = {}
_CACHE_TTL_SECONDS = 4 * 3600  # 4 hours

def get_hist_df(tenor: str = "10Y", days: int = 504) -> pd.DataFrame:
    """Get historical yield DF from Bloomberg. Caches results so callbacks
    never make redundant BBG bdh calls after the first fetch. Cache expires
    after 4 hours to prevent stale data in long-running sessions."""
    if not bbg.ok:
        return pd.DataFrame()
    key = (tenor, days)
    now = datetime.now().timestamp()
    if key in _HIST_DF_CACHE and (now - _HIST_DF_CACHE_TS.get(key, 0)) < _CACHE_TTL_SECONDS:
        return _HIST_DF_CACHE[key]
    df = fetch_hist_yields_bbg(tenor, days)
    result = df if df is not None else pd.DataFrame()
    _HIST_DF_CACHE[key] = result
    _HIST_DF_CACHE_TS[key] = now
    return result


_REAL_YIELD_CACHE: Dict[tuple, pd.DataFrame] = {}
_REAL_YIELD_CACHE_TS: Dict[tuple, float] = {}

def get_real_yield_hist_df(tenor: str = "10Y", days: int = 504) -> pd.DataFrame:
    """Cached wrapper for fetch_real_yield_history_bbg. Prevents direct Bloomberg
    calls inside chart render functions by caching with a 4-hour TTL."""
    key = (tenor, days)
    now = datetime.now().timestamp()
    if key in _REAL_YIELD_CACHE and (now - _REAL_YIELD_CACHE_TS.get(key, 0)) < _CACHE_TTL_SECONDS:
        return _REAL_YIELD_CACHE[key]
    df = fetch_real_yield_history_bbg(tenor, days)
    result = df if df is not None else pd.DataFrame()
    _REAL_YIELD_CACHE[key] = result
    _REAL_YIELD_CACHE_TS[key] = now
    return result


def fetch_macro_history_bbg(lookback_years: int = 50) -> Dict[str, Dict[str, pd.Series]]:

    """
    Fetch 10Y monthly history for each macro indicator × country from Bloomberg.
    Returns: {indicator: {country: pd.Series}}
    """
    if not bbg.ok:
        return {}
    end   = datetime.today().strftime("%Y%m%d")
    start = (datetime.today() - timedelta(days=lookback_years * 365)).strftime("%Y%m%d")
    result = {}
    for indicator, tmap in MACRO_TICKERS.items():
        tickers = list(tmap.values())
        df = bbg.bdh(tickers, "PX_LAST", start, end, freq="MONTHLY")
        if df.empty:
            continue
        rev = {v: k for k, v in tmap.items()}
        df.columns = [rev.get(c, c) for c in df.columns]
        result[indicator] = {c: df[c].dropna() for c in df.columns}
    return result

# Indicative 10Y historical means and stds (approximate, based on 2015-2025 distributions)
# Used as fallback when Bloomberg history is unavailable
IND_HIST_STATS = {
    "CPI_YOY": {
        "US":        (2.4, 1.8), "Singapore": (1.8, 1.2), "Australia": (2.3, 1.5),
        "UK":        (2.8, 1.9), "Germany":   (2.0, 2.0), "France":    (1.2, 1.5),
        "Italy":     (1.2, 1.8), "Japan":     (0.6, 1.4), "Canada":    (2.2, 1.7),
        "Euro Area": (1.9, 1.8),
    },
    "GDP_YOY": {
        "US":        (2.3, 1.8), "Singapore": (3.5, 3.5), "Australia": (2.2, 1.8),
        "UK":        (1.4, 2.2), "Germany":   (1.0, 2.5), "France":    (0.8, 2.0),
        "Italy":     (0.5, 2.3), "Japan":     (0.8, 2.0), "Canada":    (1.8, 2.0),
        "Euro Area": (1.2, 2.2),
    },
    "UNEMPLOYMENT": {
        "US":        (5.2, 1.8), "Singapore": (2.3, 0.5), "Australia": (5.3, 1.0),
        "UK":        (4.6, 0.9), "Germany":   (4.2, 0.9), "France":    (9.0, 1.2),
        "Italy":     (9.8, 2.2), "Japan":     (2.8, 0.4), "Canada":    (6.8, 1.5),
        "Euro Area": (8.5, 1.8),
    },
    "PMI_MFG": {
        "US":        (52.5, 3.0), "Singapore": (51.5, 2.5), "Australia": (51.0, 3.5),
        "UK":        (51.5, 4.5), "Germany":   (51.0, 5.5), "France":    (50.0, 4.5),
        "Italy":     (50.5, 4.8), "Japan":     (50.5, 2.8), "Canada":    (51.5, 3.5),
        "Euro Area": (50.5, 5.0),
    },
    "POLICY_RATE": {
        "US":        (1.8, 2.0), "Australia": (1.5, 1.8), "UK":        (1.2, 1.8),
        "ECB":       (0.5, 1.2), "Japan":     (0.0, 0.2), "Canada":    (1.5, 1.8),
        "Singapore": (1.5, 1.5),
    },
    # Real rate = Policy Rate − CPI YoY; approx 10Y historical mean & std (2015-2025)
    "REAL_RATE": {
        "US":        (0.2, 1.8), "Singapore": (1.2, 1.5), "Australia": (0.5, 1.7),
        "UK":        (0.1, 1.7), "Germany":   (-0.3, 1.5), "France":   (-0.5, 1.4),
        "Italy":     (-0.8, 1.5), "Japan":    (-0.5, 0.8), "Canada":   (0.3, 1.8),
    },
    # Current Account % GDP: approx 10Y mean & std (2015-2025)
    "CA_GDP": {
        "US":        (-2.5, 1.2), "Singapore": (18.0, 4.0), "Australia": (-2.8, 2.0),
        "UK":        (-3.5, 1.5), "Germany":   (6.5,  2.5), "France":   (-0.5, 1.5),
        "Italy":     (1.5,  1.5), "Japan":     (3.0,  1.0), "Canada":   (-1.5, 2.0),
    },
    # TIPS/Linker 10Y real yield: approx 10Y historical mean & std (2015-2025)
    "REAL_YIELD_10Y": {
        "US":        (0.38, 0.90), "UK":        (-0.18, 0.85),
        "Germany":   (-0.80, 0.80), "Australia": (0.80, 0.85),
        "Canada":    (0.85, 0.85), "France":    (-0.35, 0.78),
        "Japan":     (-0.85, 0.45),
    },
    # Breakeven 10Y: approx 10Y historical mean & std (2015-2025)
    "BREAKEVEN_10Y": {
        "US":        (2.05, 0.42), "UK":        (3.00, 0.52),
        "Germany":   (1.65, 0.42), "Australia": (2.25, 0.42),
        "Canada":    (1.95, 0.42), "France":    (1.65, 0.40),
        "Japan":     (0.72, 0.28),
    },
}


def compute_zscores(data: Dict, macro_history: Dict) -> Dict[str, Dict[str, float]]:

    """
    Compute z-score for each current macro value vs its 10Y history.
    Bloomberg history used if available; falls back to IND_HIST_STATS.
    REAL_RATE is a derived indicator (Policy Rate − CPI YoY).
    """
    zscores = {}
    indicators = ["CPI_YOY", "GDP_YOY", "UNEMPLOYMENT", "PMI_MFG", "POLICY_RATE", "REAL_RATE", "CA_GDP"]
    for ind in indicators:
        zscores[ind] = {}
        for country in COUNTRIES:
            if ind == "CA_GDP":
                curr = data.get("ca_gdp", {}).get(country)
                if curr is None:
                    zscores[ind][country] = np.nan
                    continue
                if macro_history and ind in macro_history and country in macro_history[ind]:
                    hist = macro_history[ind][country].dropna()
                    if len(hist) >= 4:
                        mu, sigma = hist.mean(), hist.std()
                        zscores[ind][country] = round((curr - mu) / sigma, 2) if sigma > 0 else 0.0
                        continue
                stats = IND_HIST_STATS.get("CA_GDP", {})
                if country in stats:
                    mu, sigma = stats[country]
                    zscores[ind][country] = round((curr - mu) / sigma, 2) if sigma > 0 else 0.0
                else:
                    zscores[ind][country] = np.nan
                continue
            if ind == "REAL_RATE":
                rate_key = "ECB" if country in ["Germany", "France", "Italy"] else country
                rate = data["macro"].get("POLICY_RATE", {}).get(rate_key)
                cpi  = data["macro"].get("CPI_YOY",    {}).get(country)
                if rate is None or cpi is None:
                    zscores[ind][country] = np.nan
                    continue
                curr = rate - cpi
                stats = IND_HIST_STATS.get("REAL_RATE", {})
                if country in stats:
                    mu, sigma = stats[country]
                    zscores[ind][country] = round((curr - mu) / sigma, 2) if sigma > 0 else 0.0
                else:
                    zscores[ind][country] = np.nan
                continue
            current_vals = data["macro"].get(ind, {})
            lookup = "ECB" if (country in ["Germany", "France", "Italy"] and ind == "POLICY_RATE") else country
            curr = current_vals.get(lookup)
            if curr is None:
                zscores[ind][country] = np.nan
                continue
            # Try Bloomberg history first
            if macro_history and ind in macro_history and country in macro_history[ind]:
                hist = macro_history[ind][country].dropna()
                if len(hist) >= 12:
                    mu, sigma = hist.mean(), hist.std()
                    zscores[ind][country] = round((curr - mu) / sigma, 2) if sigma > 0 else 0.0
                    continue
            # Fallback to indicative stats
            stats    = IND_HIST_STATS.get(ind, {})
            stat_key = "ECB" if (country in ["Germany", "France", "Italy"] and ind == "POLICY_RATE") else country
            if stat_key in stats:
                mu, sigma = stats[stat_key]
                zscores[ind][country] = round((curr - mu) / sigma, 2) if sigma > 0 else 0.0
            else:
                zscores[ind][country] = np.nan
    return zscores

# ==========================================================================
#  CLAUDE API — INVESTMENT IDEA GENERATOR
# ==========================================================================

# ==========================================================================
#  RULE-BASED INVESTMENT IDEA SCREENER
# ==========================================================================


def _fmt(val, spec: str, na: str = "N/A") -> str:

    """Format val with spec, returning na if val is None."""
    if val is None:
        return na
    return format(val, spec)


def _get_rate(macro: Dict, country: str) -> Optional[float]:

    """Get policy rate, mapping DE/IT to ECB"""
    pr = macro.get("POLICY_RATE", {})
    return pr.get(country, pr.get("ECB" if country in ["Germany", "France", "Italy"] else country))


def _get_cpi(macro: Dict, country: str) -> Optional[float]:

    cpi = macro.get("CPI_YOY", {})
    return cpi.get(country, cpi.get("Euro Area" if country in ["Germany", "France", "Italy"] else country))


def _get_gdp(macro: Dict, country: str) -> Optional[float]:

    gdp = macro.get("GDP_YOY", {})
    return gdp.get(country, gdp.get("Euro Area" if country in ["Germany", "France", "Italy"] else country))


def generate_ideas_from_data(data: Dict) -> List[Dict]:

    """
    Rule-based screener that generates investment ideas from market data.
    Scores each opportunity on: hedged pickup, rate cycle, real rate, curve slope,
    fiscal sustainability, and macro momentum.
    """
    y10    = data["yields"].get("10Y", {})
    y2     = data["yields"].get("2Y",  {})
    y30    = data["yields"].get("30Y", {})
    macro  = data["macro"]
    slopes = data["slopes"]
    hy     = data["hedged_10y"]
    hc     = data["hedge_costs"]
    jgb10  = y10.get("Japan")
    if jgb10 is None:
        print("  ⚠️ generate_ideas: Japan 10Y yield N/A — need: JGBS10 Index | PX_LAST")
    ideas  = []
    # ── Score each non-Japan country for long/short duration opportunity ──
    for country in [c for c in COUNTRIES if c != "Japan"]:
        y10v  = y10.get(country)
        y2v   = y2.get(country)
        hyv   = hy.get(country)
        if y10v is None or hyv is None or jgb10 is None:
            continue
        rate      = _get_rate(macro, country)
        cpi       = _get_cpi(macro, country)
        gdp       = _get_gdp(macro, country)
        pmi       = macro.get("PMI_MFG",  {}).get(country)
        slope     = slopes.get(country, 0)
        pickup    = round((hyv - jgb10) * 100, 0)  # bps vs JGB
        debt_gdp  = data["debt_gdp"].get(country)
        fiscal    = data["fiscal_gdp"].get(country)
        cycle     = data["rate_cycle"].get(country, "")
        rating    = data["ratings"].get(country)
        real_rate = (rate - cpi) if (rate is not None and cpi is not None) else None
        # ── Scoring ──────────────────────────────────────────────────────
        score = 0
        # Pickup vs JGB (most important for JPY mandate)
        if pickup > 80:   score += 3
        elif pickup > 50: score += 2
        elif pickup > 20: score += 1
        elif pickup < 0:  score -= 2
        # Rate cycle: cutting = bullish duration
        if "Cutting" in cycle:  score += 2
        elif "Hiking" in cycle: score -= 2
        # Real rate: positive real rate = room to cut = bullish
        if real_rate is not None:
            if real_rate > 1.5:   score += 2
            elif real_rate > 0.5: score += 1
            elif real_rate < 0:   score -= 1
        # Growth momentum: weak GDP + low PMI = bullish duration
        if gdp is not None and gdp < 1.0:  score += 1
        if pmi is not None and pmi < 49:   score += 1
        if pmi is not None and pmi > 52:   score -= 1
        # Fiscal: high debt + wide deficit = risk premium risk
        if debt_gdp is not None and debt_gdp > 120: score -= 1
        if fiscal   is not None and fiscal < -5:    score -= 1
        # Curve: steep curve = carry + roll opportunity on 10Y
        if slope > 0.3:  score += 1
        if slope < -0.1: score -= 1
        # Credit quality
        if "AAA" in (rating or ""): score += 1
        if "BBB" in (rating or ""): score -= 1
        # ── Determine direction ───────────────────────────────────────────
        direction  = "LONG DURATION" if score >= 3 else ("SHORT DURATION" if score <= -2 else "LONG DURATION")
        conviction = "HIGH" if abs(score) >= 5 else ("MEDIUM" if abs(score) >= 3 else "LOW")
        outlook    = "BULLISH" if direction == "LONG DURATION" else ("BEARISH" if direction == "SHORT DURATION" else "NEUTRAL")
        # Entry / stop / target based on current yield + conviction buffer
        buf_stop = 0.30 if conviction == "HIGH" else (0.20 if conviction == "MEDIUM" else 0.15)
        buf_tp   = 0.35 if conviction == "HIGH" else (0.25 if conviction == "MEDIUM" else 0.15)
        if direction == "LONG DURATION":
            stop_yield   = round(y10v + buf_stop, 2)
            target_yield = round(y10v - buf_tp,   2)
            rationale    = (
                f"{FLAGS.get(country,'')} {country} 10Y offers a hedged pickup of {_fmt(pickup, '+.0f')} bps vs JGB. "
                f"Rate cycle is {cycle.lower()} with policy rate at {_fmt(rate, '.2f')}% vs CPI {_fmt(cpi, '.1f')}% "
                f"({'positive' if (real_rate or 0) > 0 else 'negative'} real rate of {(real_rate or 0):+.2f}%). "
                f"GDP growth of {(gdp or 0):.1f}% and PMI at {(pmi or 0):.1f} support duration bias. "
                f"2s10s slope of {slope:+.2f}% provides carry and roll pickup."
            )
            stop_trigger   = f"{country} CPI re-accelerates above {_fmt(cpi, '.1f')}% or CB turns hawkish; yield breaks {stop_yield:.2f}%"
            profit_trigger = f"CB cuts rates; GDP disappoints; yield falls through {target_yield:.2f}%; {_fmt(pickup, '+.0f')} bps pickup narrows with spread compression"
            key_risk       = f"Upside inflation surprise or fiscal deterioration (Debt/GDP: {_fmt(debt_gdp, '.0f', 'N/A')}%)"
        else:
            stop_yield   = round(y10v - buf_stop, 2)
            target_yield = round(y10v + buf_tp,   2)
            rationale    = (
                f"{FLAGS.get(country,'')} {country} 10Y at {y10v:.2f}% looks rich given hiking cycle ({cycle.lower()}). "
                f"Real rate of {(real_rate or 0):+.2f}% may not adequately compensate for inflation risk ({_fmt(cpi, '.1f')}% CPI). "
                f"Debt/GDP at {_fmt(debt_gdp, '.0f', 'N/A')}% and fiscal deficit of {_fmt(fiscal, '.1f', 'N/A')}% GDP add supply/premium risk. "
                f"Short duration or underweight vs peers on relative value grounds."
            )
            stop_trigger   = f"Growth slows sharply; central bank pivots dovish; yield breaks below {stop_yield:.2f}%"
            profit_trigger = f"Inflation stays sticky; additional supply announced; yield rises to {target_yield:.2f}%"
            key_risk       = f"Growth collapse forcing policy easing; safe-haven demand"
        ideas.append({
            "score":          score,
            "rank":           0,   # filled in after sorting
            "idea_name":      f"{country} {direction.replace(' DURATION','')} Duration",
            "country":        country,
            "tenor":          "10Y",
            "direction":      direction,
            "conviction":     conviction,
            "rationale":      rationale,
            "entry_yield":    f"{y10v:.2f}%",
            "stop_loss_yield": f"{stop_yield:.2f}%",
            "take_profit_yield": f"{target_yield:.2f}%",
            "hedged_pickup_bps": f"{_fmt(pickup, '+.0f')} bps vs JGB",
            "time_horizon":   "3–6 months",
            "key_risks":      key_risk,
            "stop_loss_triggers":  stop_trigger,
            "take_profit_triggers": profit_trigger,
            "outlook":        outlook,
        })
    # ── Special curve trades ──────────────────────────────────────────────
    # US 2s10s steepener: if curve is flat/inverted and rate cuts expected
    us_slope = slopes.get("US")
    us_cycle = data["rate_cycle"].get("US", "")
    _us_y2v  = y2.get("US")
    _us_y10v = y10.get("US")
    if (us_slope is not None and us_slope < 0.30 and "Cutting" in us_cycle
            and _us_y2v is not None and _us_y10v is not None):
        ideas.append({
            "score":          4,
            "rank":           0,
            "idea_name":      "US 2s10s Steepener",
            "country":        "US",
            "tenor":          "2s10s",
            "direction":      "CURVE STEEPENER",
            "conviction":     "MEDIUM",
            "rationale":      (
                f"US 2s10s slope at {us_slope:+.2f}% is historically flat/inverted while the Fed is in a cutting cycle. "
                f"Front-end 2Y ({_us_y2v:.2f}%) should rally faster than 10Y as cuts materialise. "
                f"Duration-neutral: short 2Y, long 10Y; positive carry if curve normalises."
            ),
            "entry_yield":    f"2Y: {_us_y2v:.2f}% / 10Y: {_us_y10v:.2f}%",
            "stop_loss_yield": f"Slope narrows below {us_slope-0.20:.2f}%",
            "take_profit_yield": f"Slope widens to {us_slope+0.50:.2f}%",
            "hedged_pickup_bps": "Duration neutral — carry from re-steepening",
            "time_horizon":   "3–9 months",
            "key_risks":      "Stagflation causes long end to sell off faster than front end",
            "stop_loss_triggers": "CPI re-accelerates; Fed pauses cuts; 10Y sells off > 2Y",
            "take_profit_triggers": "Fed accelerates cuts; 2Y rallies 25+ bps vs 10Y flat; slope > target",
            "outlook":        "BULLISH",
        })
    # ── BTP-Bund spread trade ─────────────────────────────────────────────
    _italy   = y10.get("Italy")
    _germany = y10.get("Germany")
    btp_bund = round((_italy - _germany) * 100, 0) if (_italy is not None and _germany is not None) else None
    if btp_bund is not None and btp_bund > 100:
        _it_fiscal = data["fiscal_gdp"].get("Italy")
        ideas.append({
            "score":          3,
            "rank":           0,
            "idea_name":      "BTP–Bund Compression",
            "country":        "Italy",
            "tenor":          "10Y spread",
            "direction":      "SPREAD COMPRESSION",
            "conviction":     "MEDIUM" if btp_bund < 150 else "LOW",
            "rationale":      (
                f"BTP–Bund spread at {btp_bund:.0f} bps offers carry vs Germany under the ECB cutting cycle. "
                f"Spread has compressed from crisis wides (2022: ~250 bps, 2012: ~550 bps). "
                f"ECB QT pace and Italian fiscal outlook (deficit {_fmt(_it_fiscal, '.1f', 'N/A')}% GDP) are key variables to monitor."
            ),
            "entry_yield":    f"IT: {_italy:.2f}% / DE: {_germany:.2f}%",
            "stop_loss_yield": f"Spread widens beyond {btp_bund+40:.0f} bps",
            "take_profit_yield": f"Spread compresses to {max(btp_bund-40,80):.0f} bps",
            "hedged_pickup_bps": f"Carry: {btp_bund:.0f} bps vs Bund",
            "time_horizon":   "2–4 months",
            "key_risks":      "Italian fiscal slippage or ECB QT acceleration triggers spread widening",
            "stop_loss_triggers": "Italian CDS widens; Moody's/S&P negative action; coalition instability",
            "take_profit_triggers": "ECB maintains supportive stance; spread compresses to target level",
            "outlook":        "NEUTRAL",
        })
    # ── RV trades between all country pairs ──────────────────────────────
    all_c = [c for c in COUNTRIES if y10.get(c) is not None]
    for idx_a, ca in enumerate(all_c):
        for cb in all_c[idx_a + 1:]:
            y10a = y10.get(ca);  y10b = y10.get(cb)
            if y10a is None or y10b is None:
                continue
            rate_a  = _get_rate(macro, ca);   rate_b  = _get_rate(macro, cb)
            cpi_a   = _get_cpi(macro, ca);    cpi_b   = _get_cpi(macro, cb)
            gdp_a   = _get_gdp(macro, ca);    gdp_b   = _get_gdp(macro, cb)
            pmi_a   = macro.get("PMI_MFG", {}).get(ca)
            pmi_b   = macro.get("PMI_MFG", {}).get(cb)
            rr_a    = (rate_a - cpi_a) if (rate_a is not None and cpi_a is not None) else None
            rr_b    = (rate_b - cpi_b) if (rate_b is not None and cpi_b is not None) else None
            cyc_a   = data["rate_cycle"].get(ca, "")
            cyc_b   = data["rate_cycle"].get(cb, "")
            fisc_a  = data["fiscal_gdp"].get(ca)
            fisc_b  = data["fiscal_gdp"].get(cb)
            # Score from ca's perspective (positive = long ca / short cb)
            rv = 0
            spread = round((y10a - y10b) * 100, 0)
            if spread > 50:    rv += 2
            elif spread > 20:  rv += 1
            elif spread < -20: rv -= 1
            elif spread < -50: rv -= 2
            if rr_a is not None and rr_b is not None:
                rr_diff = rr_a - rr_b
                if   rr_diff >  1.0: rv += 2
                elif rr_diff >  0.5: rv += 1
                elif rr_diff < -0.5: rv -= 1
                elif rr_diff < -1.0: rv -= 2
            if "Cutting" in cyc_a and "Hiking"  in cyc_b: rv += 2
            elif "Cutting" in cyc_a:                        rv += 1
            elif "Hiking"  in cyc_a and "Cutting" in cyc_b: rv -= 2
            elif "Hiking"  in cyc_a:                        rv -= 1
            if gdp_a is not None and gdp_b is not None:
                if gdp_a < gdp_b - 0.5: rv += 1
                if gdp_a > gdp_b + 0.5: rv -= 1
            if pmi_a is not None and pmi_b is not None:
                if pmi_a < 49 and pmi_b > 50: rv += 1
                if pmi_a > 50 and pmi_b < 49: rv -= 1
            if fisc_a is not None and fisc_b is not None:
                if fisc_a > fisc_b + 1.0: rv += 1
                if fisc_a < fisc_b - 1.0: rv -= 1
            if abs(rv) < 3:
                continue
            long_c, short_c, rv_score, sp = (ca, cb, rv, spread) if rv > 0 else (cb, ca, -rv, -spread)
            y10l = y10.get(long_c, 0);  y10s = y10.get(short_c, 0)
            rr_l = (rr_a if long_c == ca else rr_b) or 0
            rr_s = (rr_b if long_c == ca else rr_a) or 0
            gdp_l = (gdp_a if long_c == ca else gdp_b) or 0
            gdp_s = (gdp_b if long_c == ca else gdp_a) or 0
            cyc_l = data["rate_cycle"].get(long_c, "")
            cyc_s = data["rate_cycle"].get(short_c, "")
            conviction = "HIGH" if rv_score >= 5 else ("MEDIUM" if rv_score >= 3 else "LOW")
            ideas.append({
                "score":               rv_score,
                "rank":                0,
                "idea_name":           f"Long {long_c} / Short {short_c} 10Y RV",
                "country":             f"{long_c} vs {short_c}",
                "tenor":               "10Y RV",
                "direction":           "RV LONG/SHORT",
                "conviction":          conviction,
                "rationale":           (
                    f"Long {FLAGS.get(long_c,'')} {long_c} / Short {FLAGS.get(short_c,'')} {short_c} 10Y. "
                    f"Yield spread: {long_c} {y10l:.2f}% vs {short_c} {y10s:.2f}% ({sp:+.0f} bps). "
                    f"Rate cycles: {long_c} {cyc_l} vs {short_c} {cyc_s}. "
                    f"Real rates: {long_c} {rr_l:+.2f}% vs {short_c} {rr_s:+.2f}%. "
                    f"GDP: {long_c} {gdp_l:.1f}% vs {short_c} {gdp_s:.1f}%."
                ),
                "entry_yield":         f"{long_c}: {y10l:.2f}% / {short_c}: {y10s:.2f}%",
                "stop_loss_yield":     f"Spread widens beyond {sp + 30:.0f} bps",
                "take_profit_yield":   f"Spread compresses to {max(sp - 40, 0):.0f} bps",
                "hedged_pickup_bps":   f"{sp:+.0f} bps {long_c} vs {short_c}",
                "time_horizon":        "2–4 months",
                "key_risks":           f"Policy reversal or macro surprise in {long_c} or {short_c}",
                "stop_loss_triggers":  f"Spread widens materially; {long_c} CB turns hawkish",
                "take_profit_triggers": f"Spread compresses to target; cyclical divergence narrows",
                "outlook":             "NEUTRAL",
            })
    # ── Sort by score desc, take top 10, re-rank ──────────────────────────
    ideas.sort(key=lambda x: x["score"], reverse=True)
    ideas = ideas[:10]
    for i, idea in enumerate(ideas, 1):
        idea["rank"] = i
    return ideas

# ==========================================================================
#  CHART BUILDERS — shared dark theme
# ==========================================================================


def _ind_tag(data: Dict) -> str:

    """Returns a warning tag string when data is indicative (Bloomberg not connected)."""
    if not bbg.ok:
        return "  ⚠️ IND"
    return ""


def _dark(fig: go.Figure, height: int = None) -> go.Figure:

    upd = dict(
        paper_bgcolor=BG_CARD, plot_bgcolor=BG_DEEP,
        font=dict(color=TEXT, family=FONT_FAMILY, size=11),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=52, r=18, t=42, b=38),
    )
    if height:
        upd["height"] = height
    fig.update_layout(**upd)
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER_LT)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER_LT)
    return fig


def _empty_fig(msg: str = "Data unavailable") -> go.Figure:

    """Return a styled empty figure with a centred N/A message."""
    fig = go.Figure()
    fig.add_annotation(
        text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False, font=dict(color=TEXT_MUT, size=13, family=FONT_FAMILY),
    )
    return _dark(fig)


def _safe_chart(fn, *args, **kwargs) -> go.Figure:

    """Call a chart function; return an empty figure if it raises."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        print(f"  ⚠️  Chart '{fn.__name__}' failed: {e}")
        return _empty_fig(f"N/A — {fn.__name__}")


def _add_cell_annotations(fig, z_matrix, x_labels, y_labels, text_matrix,
                           font_color: str = "white", font_size: int = 10,
                           force_show: bool = False):
    """
    Add explicit text annotations to each non-None heatmap cell.
    More reliable than texttemplate across Plotly versions.
    force_show=True: show text even when z-score is None (e.g. spread bps always visible).
    """
    for i, y_label in enumerate(y_labels):
        for j, x_label in enumerate(x_labels):
            val = z_matrix[i][j] if (i < len(z_matrix) and j < len(z_matrix[i])) else None
            if val is None and not force_show:
                continue
            cell_text = (text_matrix[i][j]
                         if (text_matrix and i < len(text_matrix) and j < len(text_matrix[i]))
                         else "")
            if not cell_text or cell_text in ("—",):
                continue
            fig.add_annotation(
                x=x_label, y=y_label,
                text=str(cell_text),
                showarrow=False,
                font=dict(color=font_color, family=FONT_FAMILY, size=font_size),
                xref="x", yref="y",
                align="center",
                bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(0,0,0,0)",
                borderpad=0,
            )
    return fig


def chart_yield_bar(data: Dict, tenor: str = "10Y") -> go.Figure:

    y = data["yields"].get(tenor, {})
    cs = [c for c in COUNTRIES if c in y and y[c] is not None]
    vs = [y[c] for c in cs]
    fig = go.Figure(go.Bar(
        x=[f"{FLAGS.get(c,'')} {c}" for c in cs], y=vs,
        marker_color=[CCOLORS.get(c, TEXT_MUT) for c in cs],
        text=[f"{v:.2f}%" for v in vs], textposition="outside",
        hovertemplate="<b>%{x}</b><br>Yield: %{y:.3f}%<extra></extra>",
    ))
    fig.update_layout(title=f"Current {tenor} Sovereign Yields (%){_ind_tag(data)}", yaxis_title="Yield (%)")
    return _dark(fig)


def chart_yield_curve(data: Dict, countries_sel: List[str] = None) -> go.Figure:

    sel     = countries_sel or COUNTRIES
    tenors  = ["2Y", "5Y", "10Y", "30Y"]
    x_vals  = [2, 5, 10, 30]
    fig = go.Figure()
    for c in sel:
        xs, ys = [], []
        for t, x in zip(tenors, x_vals):
            v = data["yields"].get(t, {}).get(c)
            if v is not None:
                xs.append(x); ys.append(v)
        if ys:
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines+markers",
                name=f"{FLAGS.get(c,'')} {c}",
                line=dict(color=CCOLORS.get(c, TEXT_MUT), width=2),
                marker=dict(size=7),
                hovertemplate=f"<b>{c}</b><br>%{{x}}Y: %{{y:.3f}}%<extra></extra>",
            ))
    fig.update_layout(
        title=f"Yield Curves by Country{_ind_tag(data)}",
        xaxis=dict(title="Tenor (Yrs)", tickvals=[2,5,10,30], ticktext=["2Y","5Y","10Y","30Y"]),
        yaxis_title="Yield (%)", hovermode="x unified",
    )
    return _dark(fig)


def chart_hist_yields(tenor: str = "10Y", days: int = 504,

                      countries_sel: List[str] = None) -> go.Figure:
    df  = get_hist_df(tenor, days)
    sel = countries_sel or COUNTRIES
    fig = go.Figure()
    for c in sel:
        if c in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[c], mode="lines",
                name=f"{FLAGS.get(c,'')} {c}",
                line=dict(color=CCOLORS.get(c, TEXT_MUT), width=1.5),
                hovertemplate=f"<b>{c}</b><br>%{{x|%d %b %Y}}: %{{y:.3f}}%<extra></extra>",
            ))
    yr = {252: "1Y", 504: "2Y", 1260: "5Y"}.get(days, f"{days}d")
    fig.update_layout(
        title=f"Historical {tenor} Sovereign Yields — {yr}",
        yaxis_title="Yield (%)", hovermode="x unified",
    )
    return _dark(fig)


def chart_slope_bar(data: Dict) -> go.Figure:

    sl = data["slopes"]
    cs = list(sl.keys()); vs = list(sl.values())
    cols = [GREEN if v >= 0 else RED for v in vs]
    fig = go.Figure(go.Bar(
        x=[f"{FLAGS.get(c,'')} {c}" for c in cs], y=vs,
        marker_color=cols,
        text=[f"{v:+.2f}%" for v in vs], textposition="outside",
        hovertemplate="<b>%{x}</b><br>2s10s: %{y:+.3f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER_LT)
    fig.update_layout(title="2s10s Curve Slope", yaxis_title="Spread (%)")
    return _dark(fig)


def chart_hedged_yield(data: Dict) -> go.Figure:

    hy  = data["hedged_10y"]
    jgb = data["yields"]["10Y"].get("Japan")
    if jgb is None:
        print("  ⚠️ chart_hedged_yield: Japan 10Y yield N/A — need: JGBS10 Index | PX_LAST")
        return _empty_fig("JPY-Hedged Yield — Japan 10Y N/A (Bloomberg not connected)")
    cs  = list(hy.keys()); vs = list(hy.values())
    cols = [GREEN if v > jgb else RED for v in vs]
    fig = go.Figure(go.Bar(
        x=[f"{FLAGS.get(c,'')} {c}" for c in cs], y=vs,
        marker_color=cols,
        text=[f"{v:.2f}%" for v in vs], textposition="outside",
        hovertemplate="<b>%{x}</b><br>JPY-Hedged 10Y: %{y:.3f}%<extra></extra>",
    ))
    fig.add_hline(y=jgb, line_dash="dash", line_color=YELLOW,
                  annotation_text=f"JGB 10Y: {jgb:.2f}%",
                  annotation_position="top right")
    fig.update_layout(title="JPY-Hedged 10Y Yields (After 3M FX Hedge Cost)", yaxis_title="%")
    return _dark(fig)


def chart_hedge_table(data: Dict) -> go.Figure:

    y10 = data["yields"]["10Y"]
    hc  = data["hedge_costs"]
    hy  = data["hedged_10y"]
    jgb = y10.get("Japan")
    if jgb is None:
        print("  ⚠️ chart_hedge_table: Japan 10Y yield N/A — need: JGBS10 Index | PX_LAST")
        return _empty_fig("Hedge Table — Japan 10Y N/A (Bloomberg not connected)")
    cs  = [c for c in COUNTRIES if c != "Japan" and c in y10]
    gross  = [y10.get(c, 0) for c in cs]
    cost   = [hc.get(c, 0)  for c in cs]
    hedged = [hy.get(c, 0)  for c in cs]
    pickup = [round((h - jgb) * 100, 0) for h in hedged]
    pcol   = [GREEN if p > 0 else RED for p in pickup]
    fig = go.Figure(go.Table(
        header=dict(
            values=["Country", "Gross 10Y", "Hedge Cost", "Hedged Yield",
                    f"Pickup vs JGB ({jgb:.2f}%)"],
            fill_color=BG_CARD2,
            font=dict(color=ACCENT, family=FONT_FAMILY, size=11),
            align="center", line_color=BORDER, height=32,
        ),
        cells=dict(
            values=[
                [f"{FLAGS.get(c,'')} {c}" for c in cs],
                [f"{v:.2f}%" for v in gross],
                [f"{v:.2f}%" for v in cost],
                [f"{v:.2f}%" for v in hedged],
                [f"{p:+.0f} bps" for p in pickup],
            ],
            fill_color=[
                [BG_DEEP] * len(cs),
                [BG_DEEP] * len(cs),
                [BG_DEEP] * len(cs),
                [BG_DEEP] * len(cs),
                [GREEN_DIM if p > 0 else RED_DIM for p in pickup],
            ],
            font=dict(color=[TEXT, TEXT, TEXT, TEXT, "white"],
                      family=FONT_FAMILY, size=11),
            align="center", line_color=BORDER, height=28,
        ),
    ))
    fig.update_layout(title="JPY Hedge-Adjusted Yield Table")
    return _dark(fig)


def chart_yield_comparison(base: str = "US", other: str = "Germany",

                           tenor: str = "10Y", days: int = 504) -> go.Figure:
    """
    Line chart comparing two country yields over time with filled area:
    green when base > other, red when base < other.
    """
    df = get_hist_df(tenor, days)
    fig = go.Figure()
    if base not in df.columns or other not in df.columns:
        fig.update_layout(title=f"No data available for {base} or {other} {tenor}")
        return _dark(fig)
    s_base  = df[base].dropna()
    s_other = df[other].dropna()
    idx     = s_base.index.intersection(s_other.index)
    s_base  = s_base.loc[idx]
    s_other = s_other.loc[idx]
    dates  = idx.tolist()
    y_base = s_base.tolist()
    y_othr = s_other.tolist()
    # Build fill segments: split wherever sign of (base - other) changes
    diffs = [b - o for b, o in zip(y_base, y_othr)]
    i = 0
    while i < len(dates):
        j = i + 1
        while j < len(dates) and ((diffs[j] >= 0) == (diffs[i] >= 0)):
            j += 1
        seg_x = dates[i:j]
        seg_b = y_base[i:j]
        seg_o = y_othr[i:j]
        above = diffs[i] >= 0
        fill_color = "rgba(34,197,94,0.18)" if above else "rgba(239,68,68,0.18)"
        line_color  = "rgba(34,197,94,0.5)"  if above else "rgba(239,68,68,0.5)"
        # Lower boundary
        fig.add_trace(go.Scatter(
            x=seg_x, y=seg_o, mode="lines",
            line=dict(width=0), showlegend=False,
            hoverinfo="skip",
        ))
        # Upper boundary with fill
        fig.add_trace(go.Scatter(
            x=seg_x, y=seg_b, mode="lines",
            fill="tonexty", fillcolor=fill_color,
            line=dict(width=0, color=line_color),
            showlegend=False, hoverinfo="skip",
        ))
        i = j
    # Main yield lines on top
    cb = CCOLORS.get(base,  ACCENT)
    co = CCOLORS.get(other, TEXT_MUT)
    fig.add_trace(go.Scatter(
        x=dates, y=y_base, mode="lines",
        name=f"{FLAGS.get(base,'')} {base} {tenor}",
        line=dict(color=cb, width=2),
        hovertemplate=f"<b>{base} {tenor}</b>: %{{y:.3f}}%<br>%{{x|%d %b %Y}}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=y_othr, mode="lines",
        name=f"{FLAGS.get(other,'')} {other} {tenor}",
        line=dict(color=co, width=2),
        hovertemplate=f"<b>{other} {tenor}</b>: %{{y:.3f}}%<br>%{{x|%d %b %Y}}<extra></extra>",
    ))
    yr_label = {252: "1Y", 504: "2Y", 756: "3Y", 1260: "5Y",
                2520: "10Y", 3780: "15Y", 5040: "20Y", 7560: "30Y"}.get(days, f"{days}d")
    spread_now = round((y_base[-1] - y_othr[-1]) * 100, 1) if y_base and y_othr else 0
    spread_color = GREEN if spread_now >= 0 else RED
    # ── Annotations: max/min spread for each direction ───────────────────
    max_pos_idx = max_neg_idx = None
    min_pos_idx = min_neg_idx = None
    max_pos_val = max_neg_val = None
    min_pos_val = min_neg_val = None
    for k, d in enumerate(diffs):
        bps = d * 100
        if bps >= 0:
            if max_pos_val is None or bps > max_pos_val:
                max_pos_val = bps; max_pos_idx = k
            if min_pos_val is None or bps < min_pos_val:
                min_pos_val = bps; min_pos_idx = k
        else:
            if max_neg_val is None or bps < max_neg_val:
                max_neg_val = bps; max_neg_idx = k
            if min_neg_val is None or bps > min_neg_val:
                min_neg_val = bps; min_neg_idx = k
    if max_pos_idx is not None:
        fig.add_annotation(
            x=dates[max_pos_idx], y=y_base[max_pos_idx],
            text=f"<b>Max {base} lead</b><br>{max_pos_val:+.0f} bps",
            showarrow=True, arrowhead=2, arrowwidth=1.5, arrowcolor=GREEN,
            font=dict(color=GREEN, size=10, family=FONT_FAMILY),
            bgcolor=BG_DEEP, bordercolor=GREEN, borderpad=4, borderwidth=1,
            ax=0, ay=-44,
        )
    if (min_pos_idx is not None
            and min_pos_idx != max_pos_idx):   # skip if same point as max
        fig.add_annotation(
            x=dates[min_pos_idx], y=y_base[min_pos_idx],
            text=f"<b>Min {base} lead</b><br>{min_pos_val:+.0f} bps",
            showarrow=True, arrowhead=2, arrowwidth=1.5,
            arrowcolor="rgba(34,197,94,0.55)",
            font=dict(color="rgba(34,197,94,0.85)", size=10, family=FONT_FAMILY),
            bgcolor=BG_DEEP, bordercolor="rgba(34,197,94,0.55)",
            borderpad=4, borderwidth=1,
            ax=0, ay=-30,
        )
    if max_neg_idx is not None:
        fig.add_annotation(
            x=dates[max_neg_idx], y=y_base[max_neg_idx],
            text=f"<b>Max {other} lead</b><br>{max_neg_val:+.0f} bps",
            showarrow=True, arrowhead=2, arrowwidth=1.5, arrowcolor=RED,
            font=dict(color=RED, size=10, family=FONT_FAMILY),
            bgcolor=BG_DEEP, bordercolor=RED, borderpad=4, borderwidth=1,
            ax=0, ay=44,
        )
    if (min_neg_idx is not None
            and min_neg_idx != max_neg_idx):   # skip if same point as max
        fig.add_annotation(
            x=dates[min_neg_idx], y=y_base[min_neg_idx],
            text=f"<b>Min {other} lead</b><br>{min_neg_val:+.0f} bps",
            showarrow=True, arrowhead=2, arrowwidth=1.5,
            arrowcolor="rgba(239,68,68,0.55)",
            font=dict(color="rgba(239,68,68,0.85)", size=10, family=FONT_FAMILY),
            bgcolor=BG_DEEP, bordercolor="rgba(239,68,68,0.55)",
            borderpad=4, borderwidth=1,
            ax=0, ay=30,
        )
    # ── Annotation: current spread at rightmost point ────────────────────
    if y_base and y_othr:
        mid_y = (y_base[-1] + y_othr[-1]) / 2
        ay_offset = -40 if spread_now >= 0 else 40
        fig.add_annotation(
            x=dates[-1], y=mid_y,
            text=f"<b>Now: {spread_now:+.0f} bps</b>",
            showarrow=True, arrowhead=2, arrowwidth=1.5, arrowcolor=spread_color,
            font=dict(color=spread_color, size=11, family=FONT_FAMILY),
            bgcolor=BG_DEEP, bordercolor=spread_color, borderpad=4, borderwidth=1,
            xanchor="right", ax=-50, ay=ay_offset,
        )
    fig.update_layout(
        title=(f"{FLAGS.get(base,'')} {base} vs {FLAGS.get(other,'')} {other} — "
               f"{tenor} Yield Spread  "
               f"<span style='color:{spread_color}'>{spread_now:+.0f} bps</span>  "
               f"<sup>({yr_label})</sup>"),
        yaxis_title="Yield (%)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return _dark(fig)


def chart_spread_vs_jgb(data: Dict) -> go.Figure:

    sp = data["spread_vs_jgb"]
    cs = list(sp.keys()); vs = list(sp.values())
    fig = go.Figure(go.Bar(
        x=[f"{FLAGS.get(c,'')} {c}" for c in cs], y=vs,
        marker_color=[CCOLORS.get(c, TEXT_MUT) for c in cs],
        text=[f"{v*100:+.0f} bps" for v in vs], textposition="outside",
        hovertemplate="<b>%{x}</b><br>Spread vs JGB: %{y*100:.0f} bps<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER_LT)
    fig.update_layout(title="10Y Spread vs JGB (raw, unhedged)", yaxis_title="%")
    return _dark(fig)


def chart_xccy_basis(data: Dict) -> go.Figure:

    basis  = data["xccy_basis"]
    pairs  = list(basis.keys()); vs = list(basis.values())
    cols   = [GREEN if v > 0 else RED for v in vs]
    fig = go.Figure(go.Bar(
        x=pairs, y=vs, marker_color=cols,
        text=[f"{v:+.2f}%" for v in vs], textposition="outside",
        hovertemplate="<b>%{x}</b><br>3M Basis: %{y:+.3f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER_LT)
    fig.update_layout(
        title="3M Cross-Currency Basis vs JPY  (JPYI3M − foreign 3M rate)",
        yaxis_title="Basis (%)",
    )
    return _dark(fig)


def chart_xccy_basis_sgd(data: Dict) -> go.Figure:

    basis  = data["xccy_basis_sgd"]
    pairs  = list(basis.keys()); vs = list(basis.values())
    cols   = [GREEN if v > 0 else RED for v in vs]
    fig = go.Figure(go.Bar(
        x=pairs, y=vs, marker_color=cols,
        text=[f"{v:+.2f}%" for v in vs], textposition="outside",
        hovertemplate="<b>%{x}</b><br>3M Basis: %{y:+.3f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER_LT)
    fig.update_layout(
        title="3M Cross-Currency Basis vs SGD  (SGDI3M − foreign 3M rate)",
        yaxis_title="Basis (%)",
    )
    return _dark(fig)


def chart_hedged_yield_heatmap(data: Dict) -> go.Figure:

    """
    Heatmap: countries (rows) × tenors (cols) showing JPY-hedged yield.
    Hedge cost is tenor-agnostic (3M FX forward cost applied uniformly).
    Green = high hedged yield vs JGB; Red = low / negative pickup.
    """
    tenors   = ["2Y", "5Y", "10Y",]
    hc       = data["hedge_costs"]
    jgb_by_t = {t: data["yields"].get(t, {}).get("Japan") for t in tenors}
    z, text, hover = [], [], []
    countries_avail = []
    for c in [ct for ct in COUNTRIES if ct != "Japan"]:
        row_z, row_t, row_h = [], [], []
        for t in tenors:
            raw  = data["yields"].get(t, {}).get(c)
            cost = hc.get(c)
            if raw is not None and cost is not None:
                hedged  = round(raw + cost, 2)
                jgb_ref = jgb_by_t.get(t)
                pickup_str = f"({(hedged - jgb_ref) * 100:+.0f} bps)" if jgb_ref is not None else ""
                row_z.append(hedged)
                row_t.append(f"{hedged:.2f}%<br>{pickup_str}")
                row_h.append(f"<b>{FLAGS.get(c,'')} {c} {t}</b><br>"
                             f"Gross: {raw:.2f}%<br>"
                             f"Hedge cost: {cost:.2f}%<br>"
                             f"Hedged: {hedged:.2f}%"
                             + (f"<br>Pickup vs JGB {t}: {(hedged - jgb_ref) * 100:+.0f} bps" if jgb_ref is not None else ""))
            else:
                row_z.append(None)
                row_t.append("N/A")
                row_h.append(f"<b>{c} {t}</b><br>No data")
        z.append(row_z)
        text.append(row_t)
        hover.append(row_h)
        countries_avail.append(f"{FLAGS.get(c,'')} {c}")
    # ── JGB reference row (domestic, no hedge cost) ───────────────────────
    jgb_row_z, jgb_row_t, jgb_row_h = [], [], []
    for t in tenors:
        jgb_y = jgb_by_t.get(t)
        if jgb_y is not None:
            jgb_row_z.append(round(jgb_y, 2))
            jgb_row_t.append(f"{jgb_y:.2f}%<br>(ref)")
            jgb_row_h.append(f"<b>{FLAGS.get('Japan','')} JGB {t}</b><br>"
                             f"Yield: {jgb_y:.2f}%<br>Reference benchmark (0 bps pickup)")
        else:
            jgb_row_z.append(None)
            jgb_row_t.append("N/A")
            jgb_row_h.append(f"<b>JGB {t}</b><br>No data")
    z.append(jgb_row_z)
    text.append(jgb_row_t)
    hover.append(jgb_row_h)
    countries_avail.append(f"{FLAGS.get('Japan', '🇯🇵')} JGB (ref)")
    fig = go.Figure(go.Heatmap(
        z=z,
        x=tenors,
        y=countries_avail,
        customdata=hover,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale=[
            [0.0,  "#7F1D1D"],   # deep red   → -2%
            [0.25, "#EF4444"],   # red        → -1%
            [0.5,  "#1a1a2e"],   # dark base  →  0%
            [0.75, "#166534"],   # dark green → +1%
            [1.0,  "#22C553"],   # bright green → +2%
        ],
        zmin=-2.5,                  # ← fixes the low end at -2%
        zmax=2.5,                   # ← fixes the high end at +2%
        zmid=0,                   # ← centres the scale at 0%
        colorbar=dict(
            title=dict(text="Hedged<br>Yield (%)", font=dict(family=FONT_FAMILY, size=10)),
            tickfont=dict(family=FONT_FAMILY, size=10),
        ),
        zsmooth=False,
    ))
    _add_cell_annotations(fig, z, tenors, countries_avail, text, font_size=10)
    jgb10 = data["yields"].get("10Y", {}).get("Japan")
    jgb10_str = f"{jgb10:.2f}%" if jgb10 is not None else "N/A"
    fig.update_layout(
        title=f"JPY-Hedged Yield Heatmap by Country & Tenor  (JGB 10Y ref: {jgb10_str}){_ind_tag(data)}<br>"
              f"<sup>Hedge cost = 3M FX fwd, annualised. Green = positive pickup vs JGB same tenor.</sup>",
        xaxis=dict(title="Tenor", side="top"),
        yaxis=dict(title=""),
        height=360,
    )
    return _dark(fig)


def chart_hedged_yield_heatmap_sgd(data: Dict) -> go.Figure:

    """
    Heatmap: countries (rows) × tenors (cols) showing SGD-hedged yield.
    Hedge cost is tenor-agnostic (3M FX forward cost applied uniformly).
    """
    tenors   = ["2Y", "5Y", "10Y", ]
    hc       = data["sgd_hedge_costs"]
    sgs_by_t = {t: data["yields"].get(t, {}).get("Singapore") for t in tenors}
    z, text, hover = [], [], []
    countries_avail = []
    for c in COUNTRIES:
        row_z, row_t, row_h = [], [], []
        for t in tenors:
            raw  = data["yields"].get(t, {}).get(c)
            cost = hc.get(c)
            if raw is not None and cost is not None:
                hedged  = round(raw + cost, 2)
                sgs_ref = sgs_by_t.get(t)
                pickup_str = f"({(hedged - sgs_ref) * 100:+.0f} bps)" if sgs_ref is not None else ""
                row_z.append(hedged)
                row_t.append(f"{hedged:.2f}%<br>{pickup_str}")
                row_h.append(f"<b>{FLAGS.get(c,'')} {c} {t}</b><br>"
                             f"Gross: {raw:.2f}%<br>"
                             f"Hedge cost: {cost:.2f}%<br>"
                             f"Hedged: {hedged:.2f}%"
                             + (f"<br>Pickup vs SGS {t}: {(hedged - sgs_ref) * 100:+.0f} bps" if sgs_ref is not None else ""))
            else:
                row_z.append(None)
                row_t.append("N/A")
                row_h.append(f"<b>{c} {t}</b><br>No data")
        z.append(row_z)
        text.append(row_t)
        hover.append(row_h)
        countries_avail.append(f"{FLAGS.get(c,'')} {c}")
    fig = go.Figure(go.Heatmap(
        z=z,
        x=tenors,
        y=countries_avail,
        customdata=hover,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale=[
            [0.0,  "#7F1D1D"],   # deep red   → -2%
            [0.25, "#EF4444"],   # red        → -1%
            [0.5,  "#1a1a2e"],   # dark base  →  0%
            [0.75, "#166534"],   # dark green → +1%
            [1.0,  "#22C55E"],   # bright green → +2%
        ],
        zmin=-2.5,                  # ← fixes the low end at -2%
        zmax=2.5,                   # ← fixes the high end at +2%
        zmid=0,                   # ← centres the scale at 0%
        colorbar=dict(
            title=dict(text="Hedged<br>Yield (%)", font=dict(family=FONT_FAMILY, size=10)),
            tickfont=dict(family=FONT_FAMILY, size=10),
        ),
        zsmooth=False,
    ))
    _add_cell_annotations(fig, z, tenors, countries_avail, text, font_size=10)
    sgs10 = data["yields"].get("10Y", {}).get("Singapore")
    sgs10_str = f"{sgs10:.2f}%" if sgs10 is not None else "N/A"
    fig.update_layout(
        title=f"SGD-Hedged Yield Heatmap by Country & Tenor  (SGS 10Y ref: {sgs10_str}){_ind_tag(data)}<br>"
              f"<sup>Hedge cost = 3M FX fwd, annualised. Green = positive pickup vs SGS same tenor.</sup>",
        xaxis=dict(title="Tenor", side="top"),
        yaxis=dict(title=""),
        height=360,
    )
    return _dark(fig)


def chart_macro_heatmap(data: Dict, zscores: Dict = None, countries: List[str] = None) -> go.Figure:

    if zscores is None:
        zscores = INITIAL_ZSCORES
    if not countries:
        countries = COUNTRIES
    indicators = ["CPI_YOY", "GDP_YOY", "UNEMPLOYMENT", "PMI_MFG", "POLICY_RATE", "REAL_RATE", "CA_GDP"]
    labels     = ["CPI YoY %", "GDP YoY %", "Unemp %", "PMI Mfg", "Policy Rate %", "Real Rate %", "Curr Acct % GDP"]
    z_matrix, text_matrix, hover_matrix = [], [], []
    for ind, label in zip(indicators, labels):
        z_row, t_row, h_row = [], [], []
        for c in countries:
            if ind == "REAL_RATE":
                rate_key = "ECB" if c in ["Germany", "France", "Italy"] else c
                rate = data["macro"].get("POLICY_RATE", {}).get(rate_key)
                cpi  = data["macro"].get("CPI_YOY",    {}).get(c)
                val  = round(rate - cpi, 2) if (rate is not None and cpi is not None) else None
            elif ind == "CA_GDP":
                val = data.get("ca_gdp", {}).get(c)
            else:
                lookup = "ECB" if (c in ["Germany", "France", "Italy"] and ind == "POLICY_RATE") else c
                val = data["macro"].get(ind, {}).get(lookup)
            zscore = zscores.get(ind, {}).get(c, np.nan)
            z_row.append(zscore if not np.isnan(zscore) else None)
            t_row.append(
                f"{val:.1f}<br><span style='font-size:9px'>z={zscore:+.1f}</span>"
                if val is not None and not np.isnan(zscore) else
                (f"{val:.1f}" if val is not None else "N/A")
            )
            h_row.append(
                f"<b>{FLAGS.get(c,'')} {c} — {label}</b><br>"
                f"Current: {val:.2f}<br>"
                f"Z-score: {zscore:+.2f} (vs 10Y avg)<br>"
                f"{'Above' if zscore > 0 else 'Below'} 10Y avg by {abs(zscore):.1f}σ"
                if val is not None and not np.isnan(zscore) else
                f"<b>{c} — {label}</b><br>No data"
            )
        z_matrix.append(z_row)
        text_matrix.append(t_row)
        hover_matrix.append(h_row)
    x_labels = [f"{FLAGS.get(c,'')} {c}" for c in countries]
    fig = go.Figure(go.Heatmap(
        z=z_matrix,
        x=x_labels,
        y=labels,
        customdata=hover_matrix,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale=[
            [0.00, "#1a7c1a"],  # dark green  (z ≤ -3)
            [0.50, "#1a1a2e"],  # neutral dark(z =  0)
            [1.00, "#8b0000"],  # dark red    (z ≥ +3)
        ],
        zmid=0,
        zmin=-2,
        zmax=2,
        colorbar=dict(
            title=dict(text="Z-Score<br>(10Y)", font=dict(family=FONT_FAMILY, size=10)),
            tickfont=dict(family=FONT_FAMILY, size=10),
            tickvals=[-3, -2, -1, 0, 1, 2, 3],
            ticktext=["-3σ", "-2σ", "-1σ", "0", "+1σ", "+2σ", "+3σ"],
        ),
    ))
    _add_cell_annotations(fig, z_matrix, x_labels, labels, text_matrix, font_size=10)
    fig.update_layout(
        title="Macro Heatmap — Colour = Z-Score vs 10Y History  |  Cell = Actual Value",
    )
    return _dark(fig)


def chart_macro_panels(data: Dict) -> go.Figure:

    m    = data["macro"]
    prev = data.get("macro_prev", {})
    fig  = make_subplots(
        rows=2, cols=2,
        subplot_titles=["CPI YoY (%)", "GDP YoY (%)", "Unemployment (%)", "PMI Manufacturing"],
        vertical_spacing=0.16, horizontal_spacing=0.08,
    )
    panels = [
        ("CPI_YOY",      1, 1, YELLOW),
        ("GDP_YOY",      1, 2, GREEN),
        ("UNEMPLOYMENT", 2, 1, RED),
        ("PMI_MFG",      2, 2, ACCENT),
    ]
    for ind, r, col, _ in panels:
        d  = m.get(ind, {})
        cs = [c for c in COUNTRIES if d.get(c) is not None]
        vs = [d[c] for c in cs]
        xlabels = [f"{FLAGS.get(c,'')} {c}" for c in cs]
        fig.add_trace(go.Bar(
            x=xlabels, y=vs,
            marker_color=[CCOLORS.get(c, TEXT_MUT) for c in cs],
            text=[f"{v:.1f}" for v in vs], textposition="outside",
            showlegend=False,
            hovertemplate=f"<b>%{{x}}</b><br>{ind}: %{{y:.2f}}<extra></extra>",
        ), row=r, col=col)
        # ── Previous period stars ─────────────────────────────────────────
        pd_ = prev.get(ind, {})
        star_x, star_y, star_hover = [], [], []
        for c, xl in zip(cs, xlabels):
            pv = pd_.get(c)
            if pv is not None:
                star_x.append(xl)
                star_y.append(pv)
                star_hover.append(f"<b>{c} prev</b>: {pv:.2f}")
        if star_x:
            fig.add_trace(go.Scatter(
                x=star_x, y=star_y, mode="markers",
                name="Previous period",
                marker=dict(symbol="star", size=10, color=TEXT,
                            line=dict(width=1, color=BG_DEEP)),
                showlegend=(r == 1 and col == 1),
                hovertemplate="%{customdata}<extra></extra>",
                customdata=star_hover,
            ), row=r, col=col)
        if ind == "PMI_MFG":
            fig.add_hline(y=50, line_dash="dash", line_color=YELLOW,
                          annotation_text="50", row=r, col=col)
    fig.update_layout(title="Macro Dashboard — Country Comparison", height=560)
    return _dark(fig)


def chart_current_account(data: Dict) -> go.Figure:

    ca      = data.get("ca_gdp", {})
    ca_prev = data.get("ca_gdp_prev", {})
    cs      = [c for c in COUNTRIES if ca.get(c) is not None]
    vs      = [ca[c] for c in cs]
    xlabels = [f"{FLAGS.get(c,'')} {c}" for c in cs]
    cols    = [GREEN if v >= 0 else RED for v in vs]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=xlabels, y=vs, marker_color=cols,
        text=[f"{v:+.1f}%" for v in vs], textposition="outside",
        showlegend=False,
        hovertemplate="<b>%{x}</b><br>Curr Acct: %{y:+.2f}% GDP<extra></extra>",
    ))
    star_x, star_y, star_hover = [], [], []
    for c, xl in zip(cs, xlabels):
        pv = ca_prev.get(c)
        if pv is not None:
            star_x.append(xl)
            star_y.append(pv)
            star_hover.append(f"<b>{c} prev year</b>: {pv:+.1f}%")
    if star_x:
        fig.add_trace(go.Scatter(
            x=star_x, y=star_y, mode="markers",
            name="Previous year",
            marker=dict(symbol="star", size=10, color=TEXT,
                        line=dict(width=1, color=BG_DEEP)),
            showlegend=True,
            hovertemplate="%{customdata}<extra></extra>",
            customdata=star_hover,
        ))
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER_LT)
    fig.update_layout(
        title="Current Account Balance (% GDP)  ★ = Previous Year",
        yaxis_title="% GDP",
    )
    return _dark(fig)


def chart_fiscal_balance(data: Dict) -> go.Figure:

    fb      = data.get("fiscal_gdp", {})
    fb_prev = data.get("fiscal_gdp_prev", {})
    cs      = [c for c in COUNTRIES if fb.get(c) is not None]
    vs      = [fb[c] for c in cs]
    xlabels = [f"{FLAGS.get(c,'')} {c}" for c in cs]
    cols    = [GREEN if v >= 0 else RED for v in vs]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=xlabels, y=vs, marker_color=cols,
        text=[f"{v:+.1f}%" for v in vs], textposition="outside",
        showlegend=False,
        hovertemplate="<b>%{x}</b><br>Fiscal Balance: %{y:+.2f}% GDP<extra></extra>",
    ))
    star_x, star_y, star_hover = [], [], []
    for c, xl in zip(cs, xlabels):
        pv = fb_prev.get(c)
        if pv is not None:
            star_x.append(xl)
            star_y.append(pv)
            star_hover.append(f"<b>{c} prev year</b>: {pv:+.1f}%")
    if star_x:
        fig.add_trace(go.Scatter(
            x=star_x, y=star_y, mode="markers",
            name="Previous year",
            marker=dict(symbol="star", size=10, color=TEXT,
                        line=dict(width=1, color=BG_DEEP)),
            showlegend=True,
            hovertemplate="%{customdata}<extra></extra>",
            customdata=star_hover,
        ))
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER_LT)
    fig.update_layout(
        title="Fiscal Balance (% GDP)  ★ = Previous Year",
        yaxis_title="% GDP",
    )
    return _dark(fig)


def chart_policy_vs_inflation(data: Dict) -> go.Figure:

    m   = data["macro"]
    fig = go.Figure()
    for c in COUNTRIES:
        rate = m.get("POLICY_RATE", {}).get(
            c, m.get("POLICY_RATE", {}).get("ECB" if c in ["Germany", "France", "Italy"] else c))
        cpi  = m.get("CPI_YOY", {}).get(c)
        if rate is None or cpi is None:
            continue
        rr = round(rate - cpi, 2)
        fig.add_trace(go.Scatter(
            x=[cpi], y=[rate], mode="markers+text",
            name=c, text=[f"{FLAGS.get(c,'')} {c}"],
            textposition="top center",
            marker=dict(size=13, color=CCOLORS.get(c, TEXT_MUT),
                        line=dict(width=1.5, color="white")),
            hovertemplate=f"<b>{c}</b><br>CPI: {cpi:.1f}%<br>Rate: {rate:.2f}%<br>Real Rate: {rr:+.2f}%<extra></extra>",
            showlegend=False,
        ))
    fig.add_shape(type="line", x0=0, y0=0, x1=6, y1=6,
                  line=dict(dash="dash", color=YELLOW, width=1))
    fig.add_annotation(x=5.2, y=5.5, text="Real Rate = 0",
                       showarrow=False, font=dict(color=YELLOW, size=10))
    fig.update_layout(
        title="Policy Rate vs CPI  (Real Rate Positioning)",
        xaxis_title="CPI YoY (%)", yaxis_title="Policy Rate (%)",
    )
    return _dark(fig)


def chart_fiscal_sustainability(data: Dict) -> go.Figure:

    fig = go.Figure()
    for c in COUNTRIES:
        fiscal = data["fiscal_gdp"].get(c)
        debt   = data["debt_gdp"].get(c)
        rating = data["ratings"].get(c, "")
        if fiscal is None or debt is None:
            continue
        fig.add_trace(go.Scatter(
            x=[debt], y=[fiscal], mode="markers+text",
            name=c, text=[f"{FLAGS.get(c,'')} {c}"],
            textposition="top center",
            marker=dict(size=14, color=CCOLORS.get(c, TEXT_MUT),
                        line=dict(width=1.5, color="white")),
            customdata=[[rating]],
            hovertemplate=f"<b>{c}</b><br>Debt/GDP: {debt}%<br>Fiscal: {fiscal}% GDP<br>Rating: {rating}<extra></extra>",
            showlegend=False,
        ))
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER_LT)
    fig.add_vline(x=60, line_dash="dash", line_color=BORDER_LT,
                  annotation_text="60% (Maastricht)", annotation_position="top")
    fig.update_layout(
        title="Fiscal Balance vs Debt/GDP  (Sovereign Sustainability)",
        xaxis_title="Debt/GDP (%)", yaxis_title="Fiscal Balance (% GDP)",
    )
    return _dark(fig)


def chart_fx_bar(data: Dict) -> go.Figure:

    fx = data["fx"]
    ps = list(fx.keys()); vs = list(fx.values())
    ctry_map = {"USDJPY": "US", "AUDJPY": "Australia", "GBPJPY": "UK",
                "EURJPY": "Germany", "SGDJPY": "Singapore", "CADJPY": "Canada"}
    fig = go.Figure(go.Bar(
        x=ps, y=vs,
        marker_color=[CCOLORS.get(ctry_map.get(p, ""), TEXT_MUT) for p in ps],
        text=[f"{v:.1f}" for v in vs], textposition="outside",
        hovertemplate="<b>%{x}</b><br>Spot: %{y:.2f}<extra></extra>",
    ))
    fig.update_layout(title="FX vs JPY — Spot Rates", yaxis_title="JPY per 1 unit")
    return _dark(fig)


def chart_breakeven(data: Dict) -> go.Figure:

    be = data["macro"].get("BREAKEVEN_10Y", {})
    cs = list(be.keys()); vs = list(be.values())
    pol = {c: data["macro"].get("POLICY_RATE", {}).get(
               c, data["macro"].get("POLICY_RATE", {}).get("ECB" if c == "Germany" else c))
           for c in cs}
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=cs, y=vs, name="10Y Breakeven",
        marker_color=[CCOLORS.get(c, ACCENT) for c in cs],
        text=[f"{v:.2f}%" for v in vs], textposition="outside",
    ))
    cpi_vals = [data["macro"].get("CPI_YOY", {}).get(c) for c in cs]
    fig.add_trace(go.Scatter(
        x=cs, y=cpi_vals, mode="markers", name="CPI YoY",
        marker=dict(symbol="diamond", size=12, color=YELLOW,
                    line=dict(width=2, color="white")),
    ))
    fig.update_layout(
        title="10Y Breakeven Inflation vs Actual CPI YoY",
        yaxis_title="%", barmode="group",
    )
    return _dark(fig)


def chart_breakeven_curve(data: Dict) -> go.Figure:

    """
    Breakeven inflation term structure — small-multiples grid.
    One subplot per country; each panel shows the breakeven curve (line+markers)
    and a horizontal dashed line at the current CPI YoY level.
    """
    TENOR_MAP = [
        ("1Y",  1,  "BREAKEVEN_1Y"),
        ("2Y",  2,  "BREAKEVEN_2Y"),
        ("3Y",  3,  "BREAKEVEN_3Y"),
        ("5Y",  5,  "BREAKEVEN_5Y"),
        ("7Y",  7,  "BREAKEVEN_7Y"),
        ("10Y", 10, "BREAKEVEN_10Y"),
        ("15Y", 15, "BREAKEVEN_15Y"),
        ("20Y", 20, "BREAKEVEN_20Y"),
        ("25Y", 25, "BREAKEVEN_25Y"),
        ("30Y", 30, "BREAKEVEN_30Y"),
    ]
    TICK_VALS = [1, 2, 3, 5, 7, 10, 15, 20, 25, 30]
    TICK_TEXT = ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "25Y", "30Y"]
    macro = data["macro"]
    cpi_data = macro.get("CPI_YOY", {})
    # Countries that have at least one breakeven tenor
    be_countries = set()
    for *_, key in TENOR_MAP:
        be_countries.update(macro.get(key, {}).keys())
    countries = [c for c in COUNTRIES if c in be_countries]
    n = len(countries)
    ncols = 4
    nrows = (n + ncols - 1) // ncols  # ceil division
    subplot_titles = [f"{FLAGS.get(c, '')} {c}" for c in countries]
    # Pad to fill grid
    subplot_titles += [""] * (nrows * ncols - n)
    fig = make_subplots(
        rows=nrows, cols=ncols,
        subplot_titles=subplot_titles,
        shared_yaxes=False,
        horizontal_spacing=0.08,
        vertical_spacing=0.14,
    )
    for idx, c in enumerate(countries):
        row = idx // ncols + 1
        col = idx % ncols + 1
        color = CCOLORS.get(c, TEXT_MUT)
        # Build (x, y) pairs for available tenors
        xs, ys = [], []
        for _, yr, key in TENOR_MAP:
            val = macro.get(key, {}).get(c)
            if val is not None:
                xs.append(yr)
                ys.append(val)
        if not ys:
            continue
        # Breakeven curve
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys,
                mode="lines+markers",
                name=c,
                showlegend=False,
                line=dict(color=color, width=2),
                marker=dict(size=5, color=color),
                hovertemplate="<b>%{x}Y Breakeven</b>: %{y:.2f}%<extra></extra>",
            ),
            row=row, col=col,
        )
        # CPI horizontal reference line
        cpi_val = cpi_data.get(c)
        if cpi_val is not None and xs:
            x_min, x_max = min(xs), max(xs)
            fig.add_trace(
                go.Scatter(
                    x=[x_min, x_max],
                    y=[cpi_val, cpi_val],
                    mode="lines",
                    name=f"{c} CPI",
                    showlegend=False,
                    line=dict(color=color, width=1.5, dash="dash"),
                    hovertemplate=f"<b>CPI YoY</b>: {cpi_val:.2f}%<extra></extra>",
                ),
                row=row, col=col,
            )
            # CPI label annotation inside the panel
            fig.add_annotation(
                x=x_max, y=cpi_val,
                text=f"CPI {cpi_val:.1f}%",
                showarrow=False,
                xanchor="right",
                yanchor="bottom",
                font=dict(size=9, color=color),
                row=row, col=col,
            )
        # Per-subplot axis styling
        axis_idx = "" if idx == 0 else str(idx + 1)
        fig.update_layout(**{
            f"xaxis{axis_idx}": dict(
                tickvals=TICK_VALS,
                ticktext=TICK_TEXT,
                tickfont=dict(size=8),
                showgrid=True,
                gridcolor=BORDER_LT,
            ),
            f"yaxis{axis_idx}": dict(
                tickfont=dict(size=8),
                showgrid=True,
                gridcolor=BORDER_LT,
                tickformat=".1f",
            ),
        })
    fig.update_layout(
        title=dict(text="Breakeven Inflation Term Structure  (dashed line = current CPI YoY)", x=0.5),
        height=260 * nrows,
        margin=dict(t=60, b=40, l=40, r=20),
        hovermode="x",
    )
    # Style the subplot title annotations
    for ann in fig.layout.annotations:
        ann.font = dict(size=11, color=TEXT)
    return _dark(fig)


def chart_breakeven_spread(data: Dict) -> go.Figure:

    """Bar chart: 10Y breakeven minus CPI YoY = inflation risk premium per country."""
    be10 = data["macro"].get("BREAKEVEN_10Y", {})
    cpi  = data["macro"].get("CPI_YOY", {})
    countries = [c for c in COUNTRIES if c in be10 and c in cpi]
    labels = [f"{FLAGS.get(c,'')} {c}" for c in countries]
    spreads = [round(be10[c] - cpi[c], 2) for c in countries]
    cols = [GREEN if v >= 0 else RED for v in spreads]
    fig = go.Figure(go.Bar(
        x=labels, y=spreads,
        marker_color=cols,
        text=[f"{v:+.2f}%" for v in spreads],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>BE − CPI: %{y:+.2f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER_LT)
    fig.update_layout(
        title="Inflation Risk Premium  (10Y Breakeven − CPI YoY)",
        yaxis_title="Spread (%)",
    )
    return _dark(fig)


# ==========================================================================
#  TIPS ANALYTICS — ENHANCED CHART FUNCTIONS
# ==========================================================================

TIPS_COUNTRIES = ["US", "UK", "Germany", "Australia", "Canada", "France", "Japan"]


def chart_real_yield_carry(data: Dict) -> go.Figure:
    """
    Enhanced real yield snapshot.
    Primary bars = 10Y real yield. Secondary bars = estimated 3M carry + rolldown (bps).
    Carry  = real yield × 0.25 (3M coupon accrual, in bps).
    Rolldown = (ry10 − ry5) / 5 × 0.25 × 100 bps  (slope per year × 3M horizon).
    Shadow real rate (Policy Rate − CPI) overlaid as diamond markers.
    """
    ry5   = data.get("real_yields", {}).get("5Y",  {})
    ry10  = data.get("real_yields", {}).get("10Y", {})
    cpi   = data["macro"].get("CPI_YOY", {})
    pol   = data["macro"].get("POLICY_RATE", {})
    countries = [c for c in TIPS_COUNTRIES if c in ry10 and ry10[c] is not None]
    if not countries:
        return _empty_fig("No real yield data — N/A (Bloomberg not connected or tickers unresolved)")
    labels = [f"{FLAGS.get(c, '')} {c}" for c in countries]

    def _shadow(c: str) -> Optional[float]:
        pk  = "ECB" if c in ("Germany", "France", "Italy") else c
        p   = pol.get(pk);  ci = cpi.get(c)
        return round(p - ci, 2) if (p is not None and ci is not None) else None

    def _carry_roll(c: str) -> Optional[float]:
        r10 = ry10.get(c);  r5 = ry5.get(c)
        if r10 is None:
            return None
        carry_bps = r10 * 0.25 * 100
        if r5 is not None:
            slope_per_yr = (r10 - r5) / 5.0
            rolldown_bps = slope_per_yr * 0.25 * 100
        else:
            rolldown_bps = 0.0
        return round(carry_bps + rolldown_bps, 1)

    y10_vals    = [ry10.get(c) for c in countries]
    shadow_vals = [_shadow(c) for c in countries]
    cr_vals     = [_carry_roll(c) for c in countries]

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.72, 0.28],
        subplot_titles=["10Y Real Yield (%)", "3M Carry + Rolldown (bps)"],
        horizontal_spacing=0.06,
    )
    # Real yield bars
    fig.add_trace(go.Bar(
        name="10Y Real Yield",
        x=labels, y=y10_vals,
        marker_color=[CCOLORS.get(c, ACCENT) for c in countries],
        text=[f"{v:.2f}%" if v is not None else "N/A" for v in y10_vals],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>10Y Real Yield: %{y:.2f}%<extra></extra>",
    ), row=1, col=1)
    # Shadow real rate overlay
    valid_sh = [(l, s) for l, s in zip(labels, shadow_vals) if s is not None]
    if valid_sh:
        sl, sv = zip(*valid_sh)
        fig.add_trace(go.Scatter(
            name="Shadow Real Rate (Policy−CPI)",
            x=list(sl), y=list(sv), mode="markers",
            marker=dict(symbol="diamond", size=11, color=YELLOW,
                        line=dict(width=2, color="white")),
            hovertemplate="<b>%{x}</b><br>Shadow Real Rate: %{y:.2f}%<extra></extra>",
        ), row=1, col=1)
    fig.add_hline(y=0, line_dash="dash", line_color=RED, opacity=0.6,
                  annotation_text="0% repression boundary",
                  annotation_font_size=9, annotation_font_color=RED,
                  row=1, col=1)
    # Carry + rolldown bars
    cr_colors = [GREEN if (v is not None and v >= 0) else RED for v in cr_vals]
    fig.add_trace(go.Bar(
        name="3M Carry+Roll",
        x=labels, y=cr_vals,
        marker_color=cr_colors,
        text=[f"{v:+.0f}" if v is not None else "N/A" for v in cr_vals],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>3M Carry+Rolldown: %{y:+.0f} bps<extra></extra>",
    ), row=1, col=2)
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER_LT, row=1, col=2)
    fig.update_layout(
        title=f"Global Real Yields — TIPS / Linkers  ⚠️ Non-US tickers need BBG verification{_ind_tag(data)}",
        showlegend=True,
        legend=dict(orientation="h", y=-0.22, x=0.0),
    )
    return _dark(fig)


def chart_tips_table_enhanced(data: Dict) -> go.Figure:
    """
    Enhanced TIPS vs Nominal comparison table.
    Added columns: Real Yield z-score (vs 10Y history), BE Richness z-score,
    3M Carry Score (real yield × 0.25 × 100 bps).
    BE richness = current BE vs IND_HIST_STATS mean, shown as z-score.
    """
    ry10  = data.get("real_yields", {}).get("10Y", {})
    ry5   = data.get("real_yields", {}).get("5Y", {})
    nom10 = data["yields"].get("10Y", {})
    be10  = data["macro"].get("BREAKEVEN_10Y", {})
    cpi   = data["macro"].get("CPI_YOY", {})
    sw5   = data.get("infl_swaps", {}).get("5Y", {})
    hc    = data.get("hedge_costs", {})

    ry_stats = IND_HIST_STATS.get("REAL_YIELD_10Y", {})
    be_stats = IND_HIST_STATS.get("BREAKEVEN_10Y",  {})

    rows = []
    for c in TIPS_COUNTRIES:
        nom   = nom10.get(c)
        real  = ry10.get(c)
        be    = be10.get(c)
        ci    = cpi.get(c)
        r5    = ry5.get(c)
        sw    = (sw5.get("US") if c == "US"
                 else sw5.get("EUR") if c in ("Germany", "France")
                 else sw5.get("UK") if c == "UK"
                 else None)
        hcost = hc.get(c)

        be_prem_bps = round((be - ci) * 100) if (be is not None and ci is not None) else None
        hry         = round(real + hcost, 2)  if (real is not None and hcost is not None) else None

        # Carry + rolldown (bps, 3M)
        if real is not None:
            carry_roll = real * 0.25 * 100
            if r5 is not None:
                carry_roll += (real - r5) / 5.0 * 0.25 * 100
            carry_roll = round(carry_roll, 1)
        else:
            carry_roll = None

        # Real yield z-score vs 10Y history
        if real is not None and c in ry_stats:
            mu, sigma = ry_stats[c]
            ry_z = round((real - mu) / sigma, 2) if sigma > 0 else None
        else:
            ry_z = None

        # BE richness z-score vs 10Y history (positive = rich, negative = cheap)
        if be is not None and c in be_stats:
            mu, sigma = be_stats[c]
            be_z = round((be - mu) / sigma, 2) if sigma > 0 else None
        else:
            be_z = None

        rows.append({
            "Country":         f"{FLAGS.get(c, '')} {c}",
            "Nom 10Y (%)":     f"{nom:.2f}"  if nom        is not None else "N/A",
            "Real Yld 10Y":    f"{real:.2f}" if real       is not None else "N/A",
            "Real Yld z":      f"{ry_z:+.2f}" if ry_z     is not None else "N/A",
            "Breakeven (%)":   f"{be:.2f}"   if be         is not None else "N/A",
            "BE Rich/Cheap z": f"{be_z:+.2f}" if be_z     is not None else "N/A",
            "CPI YoY (%)":     f"{ci:.1f}"   if ci         is not None else "N/A",
            "BE Prem (bps)":   f"{be_prem_bps:+d}" if be_prem_bps is not None else "N/A",
            "Carry+Roll (bps)":f"{carry_roll:+.0f}" if carry_roll is not None else "N/A",
            "Hdgd Real (JPY)": f"{hry:.2f}"  if hry        is not None else "N/A",
        })

    if not rows:
        return _empty_fig("No TIPS / linker data — N/A (Bloomberg not connected)")

    COLS = ["Country", "Nom 10Y (%)", "Real Yld 10Y", "Real Yld z",
            "Breakeven (%)", "BE Rich/Cheap z", "CPI YoY (%)",
            "BE Prem (bps)", "Carry+Roll (bps)", "Hdgd Real (JPY)"]

    def _col_colors(col: str) -> List[str]:
        out = []
        for r in rows:
            v_str = r.get(col, "N/A")
            if v_str == "N/A":
                out.append(BG_DEEP); continue
            if col in ("Real Yld 10Y", "Hdgd Real (JPY)"):
                try:
                    v = float(v_str)
                    out.append("rgba(26,124,26,0.30)" if v > 0 else "rgba(139,0,0,0.30)")
                except ValueError:
                    out.append(BG_DEEP)
            elif col == "Real Yld z":
                try:
                    v = float(v_str)
                    # >+1σ = historically rich (amber warning); <−1σ = cheap (green)
                    if v > 1.0:   out.append("rgba(234,179,8,0.20)")
                    elif v < -1.0: out.append("rgba(26,124,26,0.20)")
                    else:          out.append(BG_DEEP)
                except ValueError:
                    out.append(BG_DEEP)
            elif col == "BE Rich/Cheap z":
                try:
                    v = float(v_str)
                    # >+1σ = BEs rich (expensive inflation insurance)
                    # <−1σ = BEs cheap (inflation under-priced)
                    if v > 1.0:    out.append("rgba(239,68,68,0.20)")
                    elif v < -1.0: out.append("rgba(26,124,26,0.20)")
                    else:          out.append(BG_DEEP)
                except ValueError:
                    out.append(BG_DEEP)
            elif col == "BE Prem (bps)":
                try:
                    v = int(v_str.replace("+", ""))
                    out.append("rgba(234,179,8,0.20)" if abs(v) > 50 else BG_DEEP)
                except ValueError:
                    out.append(BG_DEEP)
            elif col == "Carry+Roll (bps)":
                try:
                    v = float(v_str)
                    out.append("rgba(26,124,26,0.25)" if v > 0 else "rgba(139,0,0,0.20)")
                except ValueError:
                    out.append(BG_DEEP)
            else:
                out.append(BG_DEEP)
        return out

    cell_fill = [_col_colors(c) for c in COLS]
    fig = go.Figure(go.Table(
        columnwidth=[115, 85, 90, 75, 90, 100, 80, 90, 105, 110],
        header=dict(
            values=[f"<b>{c}</b>" for c in COLS],
            fill_color=BG_CARD2,
            font=dict(color=ACCENT, family=FONT_FAMILY, size=9),
            align="center", line_color=BORDER_LT, height=24,
        ),
        cells=dict(
            values=[[r[c] for r in rows] for c in COLS],
            fill_color=cell_fill,
            font=dict(color=TEXT, family=FONT_FAMILY, size=9),
            align=["left"] + ["center"] * (len(COLS) - 1),
            line_color=BORDER, height=22,
        ),
    ))
    fig.update_layout(
        title=f"TIPS / Linker vs Nominal — Enhanced Comparison Table  (z-scores vs ~10Y history){_ind_tag(data)}",
        margin=dict(l=10, r=10, t=42, b=10),
    )
    return _dark(fig)


def chart_infl_swap_enhanced(data: Dict) -> go.Figure:
    """
    Enhanced inflation swap curve panel.
    Separate explicit 5Y5Y forward marker on each panel.
    Inversion signal annotation (front > back-end = near-term spike priced).
    5Y5Y displayed as a standalone series so it's not buried in annotation text.
    """
    swaps = data.get("infl_swaps", {})
    cpi   = data["macro"].get("CPI_YOY", {})
    TENOR_MAP = [("1Y", 1), ("2Y", 2), ("5Y", 5), ("10Y", 10)]
    REGIONS = [
        ("US",  "🇺🇸 US CPI Swap",    CCOLORS["US"],      cpi.get("US")),
        ("EUR", "🇪🇺 EUR HICP Swap",  CCOLORS["Germany"], cpi.get("Euro Area")),
        ("UK",  "🇬🇧 UK RPI Swap",    CCOLORS["UK"],      cpi.get("UK")),
    ]
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=[r[1] for r in REGIONS],
        shared_yaxes=False,
        horizontal_spacing=0.09,
    )
    for col_idx, (region, title, color, cpi_val) in enumerate(REGIONS, start=1):
        xs, ys = [], []
        for label, yr in TENOR_MAP:
            v = swaps.get(label, {}).get(region)
            if v is not None:
                xs.append(yr); ys.append(v)
        if not ys:
            continue
        x_min, x_max = min(xs), max(xs)
        # Inversion signal: 1Y > 10Y
        inversion = (len(ys) >= 2 and ys[0] > ys[-1])
        inv_text  = "⚠️ Inverted — near-term CPI spike priced" if inversion else "Normal — expectations anchored"
        inv_color = YELLOW if inversion else GREEN

        # Main swap curve
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers",
            name=title, showlegend=False,
            line=dict(color=color, width=2.5),
            marker=dict(size=7, color=color),
            hovertemplate=f"<b>{title}</b><br>%{{x}}Y: %{{y:.2f}}%<extra></extra>",
        ), row=1, col=col_idx)

        # 2% CB target
        fig.add_trace(go.Scatter(
            x=[x_min, x_max], y=[2.0, 2.0], mode="lines",
            showlegend=False, line=dict(color=TEXT_MUT, width=1.2, dash="dot"),
            hoverinfo="skip",
        ), row=1, col=col_idx)

        # CPI overlay
        if cpi_val is not None:
            fig.add_trace(go.Scatter(
                x=[x_min, x_max], y=[cpi_val, cpi_val], mode="lines",
                showlegend=False, line=dict(color=YELLOW, width=1.5, dash="dash"),
                hovertemplate=f"CPI YoY: {cpi_val:.1f}%<extra></extra>",
            ), row=1, col=col_idx)
            fig.add_annotation(
                x=x_max, y=cpi_val, text=f"CPI {cpi_val:.1f}%",
                showarrow=False, xanchor="right", yanchor="bottom",
                font=dict(size=9, color=YELLOW, family=FONT_FAMILY),
                row=1, col=col_idx,
            )

        # Explicit 5Y5Y forward marker
        v5y5y = swaps.get("5Y5Y", {}).get(region)
        if v5y5y is not None:
            fig.add_trace(go.Scatter(
                x=[10], y=[v5y5y], mode="markers+text",
                name="5Y5Y fwd", showlegend=(col_idx == 1),
                marker=dict(symbol="star", size=13, color=TEAL,
                            line=dict(width=1.5, color="white")),
                text=[f"5Y5Y: {v5y5y:.2f}%"],
                textposition="top center",
                textfont=dict(size=9, color=TEAL, family=FONT_FAMILY),
                hovertemplate=f"5Y5Y Fwd: {v5y5y:.2f}%<extra></extra>",
            ), row=1, col=col_idx)

        # Inversion annotation
        # Plotly xref/yref: first subplot is "x domain" (no number), subsequent are "x2 domain" etc.
        _xref = "x domain" if col_idx == 1 else f"x{col_idx} domain"
        _yref = "y domain" if col_idx == 1 else f"y{col_idx} domain"
        fig.add_annotation(
            x=0.5, y=0.04, xref=_xref, yref=_yref,
            text=inv_text, showarrow=False, xanchor="center",
            font=dict(size=8, color=inv_color, family=FONT_FAMILY),
            bgcolor="rgba(0,0,0,0.4)", borderpad=3,
            row=1, col=col_idx,
        )
        fig.add_annotation(
            x=x_max, y=2.0, text="2% target", showarrow=False,
            xanchor="right", yanchor="top",
            font=dict(size=8, color=TEXT_MUT, family=FONT_FAMILY),
            row=1, col=col_idx,
        )

    fig.update_xaxes(tickvals=[1, 2, 5, 10], ticktext=["1Y", "2Y", "5Y", "10Y"],
                     title_text="Tenor")
    fig.update_yaxes(title_text="Swap Rate (%)")
    fig.update_layout(
        title=f"Inflation Swap Curves — Forward Expectations  ⚠️ EUR & UK tickers need BBG verification{_ind_tag(data)}",
        height=400, legend=dict(orientation="h", y=-0.22),
    )
    return _dark(fig)


def chart_real_rate_regime(data: Dict) -> go.Figure:
    """
    Real rate regime panel for US and Germany.
    Shows current 10Y real yield vs its approximate 2Y historical range band.
    Uses IND_HIST_STATS as reference; shaded band = ±1σ around long-run mean.
    When BBG history is available the band is derived from live data.
    """
    ry10    = data.get("real_yields", {}).get("10Y", {})
    PANEL_C = ["US", "Germany", "UK", "Australia"]
    avail   = [c for c in PANEL_C if c in ry10 and ry10[c] is not None]
    if not avail:
        return _empty_fig("No real yield data — N/A (Bloomberg not connected)")

    ry_stats = IND_HIST_STATS.get("REAL_YIELD_10Y", {})
    n = len(avail)
    fig = make_subplots(rows=1, cols=n,
                        subplot_titles=[f"{FLAGS.get(c,'')} {c}" for c in avail],
                        horizontal_spacing=0.08)

    for i, c in enumerate(avail, start=1):
        curr = ry10[c]
        mu, sigma = ry_stats.get(c, (curr, 0.5))
        lo, hi    = mu - sigma, mu + sigma

        # Shaded ±1σ band
        fig.add_trace(go.Scatter(
            x=["Range", "Range"], y=[lo, hi],
            fill=None, mode="lines", showlegend=False,
            line=dict(width=0), hoverinfo="skip",
        ), row=1, col=i)
        fig.add_shape(
            type="rect", xref=f"x{i}", yref=f"y{i}",
            x0=-0.4, x1=0.4, y0=lo, y1=hi,
            fillcolor="rgba(79,142,247,0.12)", line=dict(width=0),
            row=1, col=i,
        )
        # Long-run mean line
        fig.add_shape(
            type="line", xref=f"x{i}", yref=f"y{i}",
            x0=-0.4, x1=0.4, y0=mu, y1=mu,
            line=dict(color=ACCENT, width=1.5, dash="dot"),
            row=1, col=i,
        )
        # Zero line
        fig.add_shape(
            type="line", xref=f"x{i}", yref=f"y{i}",
            x0=-0.5, x1=0.5, y0=0, y1=0,
            line=dict(color=RED, width=1, dash="dash"),
            row=1, col=i,
        )
        # Current level marker
        col_curr = GREEN if curr > 0 else RED
        fig.add_trace(go.Scatter(
            x=["Now"], y=[curr], mode="markers+text",
            marker=dict(symbol="diamond", size=14, color=col_curr,
                        line=dict(width=2, color="white")),
            text=[f"{curr:.2f}%"], textposition="top center",
            textfont=dict(size=10, color=col_curr, family=FONT_FAMILY),
            showlegend=False,
            hovertemplate=f"<b>{c} 10Y Real Yield</b><br>Current: {curr:.2f}%<br>"
                          f"LT Mean: {mu:.2f}%  ±1σ: [{lo:.2f}%, {hi:.2f}%]<extra></extra>",
        ), row=1, col=i)
        fig.add_annotation(
            x="Now", y=mu, text=f"μ={mu:.2f}%",
            showarrow=False, xanchor="left", yanchor="middle",
            font=dict(size=8, color=ACCENT, family=FONT_FAMILY),
            xshift=12, row=1, col=i,
        )
        fig.update_xaxes(showticklabels=False, row=1, col=i)

    fig.update_layout(
        title=f"Real Rate Regime — Current Level vs Long-Run Range  (shaded = ±1σ, 2015–2025){_ind_tag(data)}",
        height=320,
    )
    return _dark(fig)


def chart_tips_rv_matrix(data: Dict) -> go.Figure:
    """
    Cross-market TIPS RV matrix.
    Rows = countries. Columns = Real Yield 10Y z-score, BE 10Y z-score, Carry+Roll (bps).
    Green = cheap / attractive. Red = rich / unattractive.
    """
    ry10 = data.get("real_yields", {}).get("10Y", {})
    ry5  = data.get("real_yields", {}).get("5Y",  {})
    be10 = data["macro"].get("BREAKEVEN_10Y", {})

    ry_stats = IND_HIST_STATS.get("REAL_YIELD_10Y", {})
    be_stats = IND_HIST_STATS.get("BREAKEVEN_10Y",  {})

    countries = [c for c in TIPS_COUNTRIES
                 if ry10.get(c) is not None or be10.get(c) is not None]
    if not countries:
        return _empty_fig("No TIPS RV data — N/A (Bloomberg not connected)")

    labels  = [f"{FLAGS.get(c,'')} {c}" for c in countries]
    metrics = ["Real Yld z", "BE Rich/Cheap z", "Carry+Roll\n(bps)"]

    z_matrix, text_matrix, hover_matrix = [], [], []
    for m in metrics:
        z_row, t_row, h_row = [], [], []
        for c in countries:
            if m == "Real Yld z":
                val = ry10.get(c)
                if val is not None and c in ry_stats:
                    mu, sigma = ry_stats[c]
                    z = (val - mu) / sigma if sigma > 0 else 0
                    z_row.append(round(z, 2))
                    t_row.append(f"{z:+.2f}σ")
                    h_row.append(f"{c} Real Yld z: {z:+.2f}σ (curr {val:.2f}%)")
                else:
                    z_row.append(None); t_row.append("N/A"); h_row.append(f"{c}: N/A")
            elif m == "BE Rich/Cheap z":
                val = be10.get(c)
                if val is not None and c in be_stats:
                    mu, sigma = be_stats[c]
                    z = (val - mu) / sigma if sigma > 0 else 0
                    z_row.append(round(-z, 2))  # invert: cheap BE = positive score
                    t_row.append(f"{z:+.2f}σ")
                    h_row.append(f"{c} BE z: {z:+.2f}σ (curr {val:.2f}%) — +ve = rich")
                else:
                    z_row.append(None); t_row.append("N/A"); h_row.append(f"{c}: N/A")
            else:  # Carry + rolldown
                r10 = ry10.get(c); r5 = ry5.get(c)
                if r10 is not None:
                    cr = r10 * 0.25 * 100
                    if r5 is not None:
                        cr += (r10 - r5) / 5.0 * 0.25 * 100
                    z_row.append(round(cr, 1))
                    t_row.append(f"{cr:+.0f}")
                    h_row.append(f"{c} Carry+Roll: {cr:+.0f} bps (3M)")
                else:
                    z_row.append(None); t_row.append("N/A"); h_row.append(f"{c}: N/A")
        z_matrix.append(z_row)
        text_matrix.append(t_row)
        hover_matrix.append(h_row)

    z_arr = np.array([[v if v is not None else np.nan for v in row] for row in z_matrix],
                     dtype=float)
    fig = go.Figure(go.Heatmap(
        z=z_arr, x=labels, y=metrics,
        colorscale=[[0, RED], [0.5, BG_CARD2], [1, GREEN]],
        zmid=0,
        text=np.array(text_matrix), texttemplate="%{text}",
        hovertext=np.array(hover_matrix),
        hovertemplate="%{hovertext}<extra></extra>",
        showscale=True,
        colorbar=dict(title="Score", tickfont=dict(size=9, family=FONT_FAMILY)),
    ))
    fig.update_layout(
        title=f"Cross-Market TIPS RV Matrix  (green = cheap/attractive, red = rich/expensive){_ind_tag(data)}",
        height=280,
        xaxis=dict(side="bottom"),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=130, r=80, t=46, b=60),
    )
    return _dark(fig)


def chart_real_yield_vs_pmi(data: Dict, macro_history: Dict) -> go.Figure:
    """
    US 10Y real yield vs ISM Manufacturing PMI scatterplot.
    Trailing 24 months of history (if available from BBG) with current point circled.
    Regression line shows the expected real yield at current PMI.
    """
    curr_ry  = data.get("real_yields", {}).get("10Y", {}).get("US")
    curr_pmi = data["macro"].get("PMI_MFG", {}).get("US")

    # Historical data from BBG macro history
    hist_ry_df  = None
    hist_pmi_s  = None
    if macro_history:
        hist_pmi_s = macro_history.get("PMI_MFG", {}).get("US")
    # Historical real yields — use cached wrapper to avoid live BBG call in chart renderer
    hist_ry_df = get_real_yield_hist_df("10Y", days=504)

    if hist_ry_df is None or hist_pmi_s is None or hist_pmi_s.empty:
        # No history: simple scatter with just current point
        if curr_ry is None or curr_pmi is None:
            return _empty_fig("No US real yield / PMI data — N/A (Bloomberg not connected)")
        fig = go.Figure(go.Scatter(
            x=[curr_pmi], y=[curr_ry], mode="markers+text",
            marker=dict(symbol="circle", size=16, color=ACCENT,
                        line=dict(width=2, color="white")),
            text=["Now"], textposition="top center",
            hovertemplate=f"Now — PMI: {curr_pmi:.1f} | Real Yield: {curr_ry:.2f}%<extra></extra>",
        ))
        fig.add_annotation(
            x=0.5, y=0.5, xref="paper", yref="paper",
            text="⚠️ Historical series unavailable — connect Bloomberg for scatter history",
            showarrow=False, font=dict(color=TEXT_MUT, size=10, family=FONT_FAMILY),
        )
    else:
        # Align history
        ry_s = hist_ry_df["US"].dropna() if "US" in hist_ry_df.columns else pd.Series(dtype=float)
        pmi_m = hist_pmi_s.resample("MS").last().dropna()
        ry_m  = ry_s.resample("MS").last().dropna()
        aligned = pd.concat([pmi_m.rename("pmi"), ry_m.rename("ry")], axis=1).dropna().tail(24)

        fig = go.Figure()
        # Historical scatter
        fig.add_trace(go.Scatter(
            x=aligned["pmi"], y=aligned["ry"],
            mode="markers",
            marker=dict(size=7, color=ACCENT, opacity=0.55),
            hovertemplate="PMI: %{x:.1f}<br>Real Yield: %{y:.2f}%<br>%{text}<extra></extra>",
            text=[str(d.strftime("%b %Y")) for d in aligned.index],
            name="History (24M)",
        ))
        # Regression line
        if len(aligned) >= 4:
            coeffs = np.polyfit(aligned["pmi"], aligned["ry"], 1)
            pmi_rng = np.linspace(aligned["pmi"].min(), aligned["pmi"].max(), 50)
            ry_fit  = np.polyval(coeffs, pmi_rng)
            fig.add_trace(go.Scatter(
                x=pmi_rng, y=ry_fit, mode="lines",
                line=dict(color=TEXT_MUT, width=1.5, dash="dot"),
                name="OLS Fit", showlegend=True,
                hovertemplate="PMI: %{x:.1f}<br>Fitted Real Yield: %{y:.2f}%<extra></extra>",
            ))
        # Current point
        if curr_ry is not None and curr_pmi is not None:
            fig.add_trace(go.Scatter(
                x=[curr_pmi], y=[curr_ry], mode="markers+text",
                marker=dict(symbol="star", size=16, color=YELLOW,
                            line=dict(width=2, color="white")),
                text=["Now"], textposition="top center",
                textfont=dict(size=10, color=YELLOW, family=FONT_FAMILY),
                name="Current",
                hovertemplate=f"Now — PMI: {curr_pmi:.1f} | Real Yield: {curr_ry:.2f}%<extra></extra>",
            ))

    fig.update_layout(
        title=f"US 10Y Real Yield vs ISM Manufacturing — Growth Proxy Signal{_ind_tag(data)}",
        xaxis_title="ISM Manufacturing PMI", yaxis_title="US 10Y Real Yield (%)",
        height=340, legend=dict(orientation="h", y=-0.22),
    )
    return _dark(fig)


def chart_be_seasonality(data: Dict) -> go.Figure:
    """
    US 10Y Breakeven seasonality: average monthly change over the last 5Y of history.
    Overlays the current BE level on the seasonal pattern.
    Requires Bloomberg history; shows informative N/A message when offline.
    """
    be_hist = fetch_breakeven_history_bbg("10Y", days=1826)  # 5Y
    curr_be = data["macro"].get("BREAKEVEN_10Y", {}).get("US")

    if be_hist is None or "US" not in be_hist.columns:
        return _empty_fig(
            "Breakeven seasonality — N/A\n"
            "Connect Bloomberg to enable seasonal analysis (requires 5Y of BE history)"
        )

    us_be = be_hist["US"].dropna()
    if len(us_be) < 60:
        return _empty_fig("Breakeven seasonality — insufficient history (need 60+ observations)")

    # Compute average monthly change by calendar month
    df = us_be.resample("MS").last().dropna()
    df_chg = df.diff().dropna()
    # Group by month integer without reassigning the index (avoids numpy scalar type issues)
    _month_ints = df_chg.index.month
    monthly_avg = df_chg.groupby(_month_ints).mean() * 100  # bps
    monthly_std = df_chg.groupby(_month_ints).std()  * 100

    months  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    avg_bps = [float(monthly_avg.get(m, np.nan)) for m in range(1, 13)]
    std_bps = [float(monthly_std.get(m, np.nan)) for m in range(1, 13)]

    bar_cols = [GREEN if pd.notna(v) and v > 0 else RED for v in avg_bps]
    err_pos  = [s if pd.notna(s) else 0.0 for s in std_bps]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=months, y=avg_bps, marker_color=bar_cols,
        error_y=dict(type="data", array=err_pos, color=TEXT_MUT, thickness=1.5),
        text=[f"{v:+.1f}" if pd.notna(v) else "" for v in avg_bps],
        textposition="outside",
        name="Avg Monthly ΔBE (bps)",
        hovertemplate="<b>%{x}</b><br>Avg change: %{y:+.1f} bps<extra></extra>",
    ))
    # Current month marker
    curr_month_idx = datetime.today().month - 1
    if curr_be is not None:
        fig.add_vline(x=months[curr_month_idx], line_dash="dash",
                      line_color=YELLOW, opacity=0.7,
                      annotation_text=f"Now ({curr_be:.2f}%)",
                      annotation_font_color=YELLOW, annotation_font_size=9)
    fig.add_hline(y=0, line_dash="dot", line_color=BORDER_LT)
    fig.update_layout(
        title=f"US 10Y Breakeven Seasonality — Avg Monthly Change (bps, 5Y history){_ind_tag(data)}",
        yaxis_title="Avg Monthly ΔBE (bps)", height=320,
    )
    return _dark(fig)


# ==========================================================================
#  TIPS SIMULATION ENGINE
# ==========================================================================

SIM_INSTRUMENTS = {
    "US TIPS 10Y":          {"country": "US",        "maturity": 10.0, "coupon": 1.50},
    "US TIPS 5Y":           {"country": "US",        "maturity":  5.0, "coupon": 1.20},
    "UK IL Gilt 10Y":       {"country": "UK",        "maturity": 10.0, "coupon": 0.125},
    "German Linker 10Y":    {"country": "Germany",   "maturity": 10.0, "coupon": 0.10},
    "Australian CIB 10Y":   {"country": "Australia", "maturity": 10.0, "coupon": 1.00},
    "Canadian RRB 10Y":     {"country": "Canada",    "maturity": 10.0, "coupon": 0.25},
    "French OATi 10Y":      {"country": "France",    "maturity": 10.0, "coupon": 0.10},
}


def _tips_mod_dur(real_yield_pct: float, maturity_years: float,
                  coupon_pct: float, horizon_years: float = 0.0) -> float:
    """Approximate modified duration of a TIPS/linker bond (real duration)."""
    rem  = max(maturity_years - horizon_years, 0.01)
    ry   = max(real_yield_pct / 100, -0.05)
    coup = coupon_pct / 100
    if coup < 1e-4:
        return rem / (1 + ry)
    # Macaulay duration via closed form (semi-annual coupons)
    n   = rem * 2
    r2  = ry / 2
    c2  = coup / 2
    try:
        mac = ((1 + r2) / r2
               - (n * (c2 - r2) + (1 + r2))
               / (c2 * ((1 + r2) ** n - 1) + r2))
    except (ZeroDivisionError, OverflowError):
        mac = rem
    return mac / (1 + r2)


def compute_tips_scenario(
    real_yield_start: float, real_yield_end: float,
    be_start: float, be_end: float,
    horizon_months: int,
    coupon_pct: float, maturity_years: float,
    rolldown_bps: float = 0.0,
) -> Dict:
    """
    Compute total TIPS return over horizon.
    All yields/BEs in percent (e.g. 2.0 = 2%).
    Returns decomposition: price, accrual, coupon_carry, rolldown, total (all in %).
    """
    T    = horizon_months / 12.0
    d_ry = (real_yield_end - real_yield_start) / 100.0
    mod_dur   = _tips_mod_dur(real_yield_start, maturity_years, coupon_pct)
    convexity = mod_dur ** 2 / 100.0
    # Price return from real yield change
    price_ret = (-mod_dur * d_ry + 0.5 * convexity * d_ry ** 2) * 100.0
    # CPI accrual on principal (approximated by starting breakeven rate)
    infl_accrual = be_start * T
    # Real coupon carry on inflation-adjusted principal
    coupon_carry = coupon_pct * T * (1.0 + infl_accrual / 100.0)
    # Rolldown (bps → %)
    rolldown_ret = rolldown_bps / 100.0
    total = price_ret + infl_accrual + coupon_carry + rolldown_ret
    return {
        "price":    round(price_ret,    2),
        "accrual":  round(infl_accrual, 2),
        "coupon":   round(coupon_carry, 2),
        "rolldown": round(rolldown_ret, 2),
        "total":    round(total,        2),
        "mod_dur":  round(mod_dur,      2),
    }


def compute_nominal_scenario(
    nom_yield_start: float, nom_yield_end: float,
    horizon_months: int, coupon_pct: float, maturity_years: float,
) -> Dict:
    """Total return for an equivalent nominal bond."""
    T      = horizon_months / 12.0
    d_ny   = (nom_yield_end - nom_yield_start) / 100.0
    # Use same duration formula but with nominal yield
    rem    = max(maturity_years - T, 0.01)
    ny     = max(nom_yield_start / 100, 0.001)
    coup   = coupon_pct / 100
    if coup < 1e-4:
        mod_dur = rem / (1 + ny)
    else:
        n, r2, c2 = rem * 2, ny / 2, coup / 2
        try:
            mac = ((1 + r2) / r2
                   - (n * (c2 - r2) + (1 + r2))
                   / (c2 * ((1 + r2) ** n - 1) + r2))
        except (ZeroDivisionError, OverflowError):
            mac = rem
        mod_dur = mac / (1 + r2)
    convexity  = mod_dur ** 2 / 100.0
    price_ret  = (-mod_dur * d_ny + 0.5 * convexity * d_ny ** 2) * 100.0
    coupon_ret = coupon_pct * T
    total      = price_ret + coupon_ret
    return {
        "price":   round(price_ret,  2),
        "coupon":  round(coupon_ret, 2),
        "total":   round(total,      2),
        "mod_dur": round(mod_dur,    2),
    }


def chart_tips_sim_decomp(tips_res: Dict, nom_res: Dict, horizon_months: int) -> go.Figure:
    """Stacked horizontal bar: TIPS vs nominal return decomposition."""
    tips_comps = [
        ("Price",      tips_res["price"],    ACCENT),
        ("Infl Accrl", tips_res["accrual"],  YELLOW),
        ("Cpn Carry",  tips_res["coupon"],   GREEN),
        ("Rolldown",   tips_res["rolldown"], TEAL),
    ]
    nom_comps = [
        ("Price",     nom_res["price"],  "#6B7280"),
        ("Cpn Carry", nom_res["coupon"], "#4B5563"),
    ]
    fig = go.Figure()
    labels = [f"Nominal Bond<br>{horizon_months}M", f"TIPS/Linker<br>{horizon_months}M"]
    # Build TIPS bar
    for name, val, color in tips_comps:
        fig.add_trace(go.Bar(
            name=name, x=[val], y=["TIPS/Linker"], orientation="h",
            marker_color=color,
            hovertemplate=f"<b>{name}</b>: {val:+.2f}%<extra></extra>",
        ))
    # Build Nominal bar
    for name, val, color in nom_comps:
        fig.add_trace(go.Bar(
            name=f"{name} (Nom)", x=[val], y=["Nominal"], orientation="h",
            marker_color=color,
            hovertemplate=f"<b>{name} (Nominal)</b>: {val:+.2f}%<extra></extra>",
        ))
    # Total annotations
    fig.add_annotation(
        x=tips_res["total"], y="TIPS/Linker",
        text=f"  Total: {tips_res['total']:+.2f}%",
        showarrow=False, xanchor="left", font=dict(color=TEXT, size=11, family=FONT_FAMILY),
    )
    fig.add_annotation(
        x=nom_res["total"], y="Nominal",
        text=f"  Total: {nom_res['total']:+.2f}%",
        showarrow=False, xanchor="left", font=dict(color=TEXT, size=11, family=FONT_FAMILY),
    )
    fig.add_vline(x=0, line_dash="dash", line_color=BORDER_LT)
    fig.update_layout(
        barmode="relative",
        title=f"Return Decomposition — TIPS vs Nominal  ({horizon_months}M horizon)",
        xaxis_title="Return (%)",
        height=260,
        legend=dict(orientation="h", y=-0.30, x=0.0),
    )
    return _dark(fig)


def chart_tips_sim_heatmap(
    ry_start: float, be_start: float, horizon_months: int,
    coupon: float, maturity: float,
) -> go.Figure:
    """
    TIPS total return heatmap: X = BE change (bps), Y = real yield change (bps).
    Shows breakeven vs rates scenario grid.
    """
    be_deltas  = np.arange(-150, 151, 25)   # bps
    ry_deltas  = np.arange(-150, 151, 25)   # bps
    z = np.zeros((len(ry_deltas), len(be_deltas)))
    for i, ry_d in enumerate(ry_deltas):
        for j, be_d in enumerate(be_deltas):
            res = compute_tips_scenario(
                ry_start, ry_start + ry_d / 100.0,
                be_start, be_start + be_d / 100.0,
                horizon_months, coupon, maturity,
            )
            z[i, j] = res["total"]
    # Color: clamp at ±10% for readability
    zmax = min(np.nanmax(np.abs(z)), 10.0)
    x_labels = [f"{v:+d}" for v in be_deltas]
    y_labels = [f"{v:+d}" for v in ry_deltas]
    text_arr = [[f"{z[i,j]:+.1f}%" for j in range(len(be_deltas))]
                for i in range(len(ry_deltas))]
    fig = go.Figure(go.Heatmap(
        z=z, x=x_labels, y=y_labels,
        colorscale=[[0.0, RED], [0.5, BG_CARD2], [1.0, GREEN]],
        zmid=0, zmin=-zmax, zmax=zmax,
        text=text_arr, texttemplate="%{text}",
        hovertemplate="BE Δ: %{x} bps | RY Δ: %{y} bps<br>Return: %{z:+.2f}%<extra></extra>",
        showscale=True,
        colorbar=dict(title="Return (%)", tickfont=dict(size=9, family=FONT_FAMILY)),
    ))
    # Highlight base case (no change)
    zero_be_idx = list(be_deltas).index(0) if 0 in be_deltas else None
    zero_ry_idx = list(ry_deltas).index(0) if 0 in ry_deltas else None
    if zero_be_idx is not None and zero_ry_idx is not None:
        fig.add_shape(
            type="rect", xref="x", yref="y",
            x0=zero_be_idx - 0.5, x1=zero_be_idx + 0.5,
            y0=zero_ry_idx - 0.5, y1=zero_ry_idx + 0.5,
            line=dict(color="white", width=2),
        )
    fig.update_layout(
        title=f"TIPS Total Return Heatmap — {horizon_months}M  (X=BE Δ bps, Y=Real Yield Δ bps)",
        xaxis_title="Breakeven Change (bps)",
        yaxis_title="Real Yield Change (bps)",
        height=460,
    )
    return _dark(fig)


def chart_tips_sim_path(
    ry_start: float, ry_end: float,
    be_start: float, be_end: float,
    horizon_months: int, coupon: float, maturity: float,
    path_shape: str = "linear",
    rolldown_bps: float = 0.0,
) -> go.Figure:
    """
    Cumulative return path: TIPS vs Nominal vs TIPS no-change base case.
    X = months. Path shapes: linear, front-loaded, back-loaded.
    """
    months = list(range(0, horizon_months + 1))
    nom_yield_start = ry_start + be_start
    nom_yield_end   = ry_end   + be_end

    def _interp(t: int, val_start: float, val_end: float) -> float:
        frac = t / horizon_months if horizon_months > 0 else 0
        if path_shape == "front":
            frac = 1 - (1 - frac) ** 2
        elif path_shape == "back":
            frac = frac ** 2
        return val_start + (val_end - val_start) * frac

    tips_cum, nom_cum, base_cum = [0.0], [0.0], [0.0]
    for t in range(1, horizon_months + 1):
        ry_t  = _interp(t, ry_start, ry_end)
        be_t  = _interp(t, be_start, be_end)
        ny_t  = _interp(t, nom_yield_start, nom_yield_end)
        # TIPS cumulative (scenario)
        r_tips  = compute_tips_scenario(ry_start, ry_t, be_start, be_t,
                                        t, coupon, maturity, rolldown_bps * t / horizon_months)
        # Nominal cumulative (scenario)
        nom_coup = coupon + be_start  # approximate nominal coupon = real + BE
        r_nom   = compute_nominal_scenario(nom_yield_start, ny_t, t, nom_coup, maturity)
        # TIPS base case (no change)
        r_base  = compute_tips_scenario(ry_start, ry_start, be_start, be_start,
                                        t, coupon, maturity, rolldown_bps * t / horizon_months)
        tips_cum.append(r_tips["total"])
        nom_cum.append(r_nom["total"])
        base_cum.append(r_base["total"])

    tips_edge = round(tips_cum[-1] - nom_cum[-1], 2)
    edge_col  = GREEN if tips_edge >= 0 else RED

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months, y=tips_cum, mode="lines+markers", name="TIPS — Scenario",
        line=dict(color=ACCENT, width=2.5), marker=dict(size=5),
        hovertemplate="Month %{x}<br>TIPS Return: %{y:+.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=months, y=nom_cum, mode="lines", name="Nominal — Scenario",
        line=dict(color=ORANGE, width=2, dash="dash"),
        hovertemplate="Month %{x}<br>Nominal Return: %{y:+.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=months, y=base_cum, mode="lines", name="TIPS — No Change",
        line=dict(color=TEXT_MUT, width=1.5, dash="dot"),
        hovertemplate="Month %{x}<br>TIPS Base: %{y:+.2f}%<extra></extra>",
    ))
    # Shaded TIPS edge vs nominal
    fig.add_trace(go.Scatter(
        x=months + months[::-1],
        y=tips_cum + nom_cum[::-1],
        fill="toself",
        fillcolor="rgba(79,142,247,0.10)" if tips_edge >= 0 else "rgba(239,68,68,0.10)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=BORDER_LT)
    fig.add_annotation(
        x=horizon_months, y=tips_cum[-1],
        text=f"TIPS edge: {tips_edge:+.2f}%",
        showarrow=True, arrowhead=2, ax=40, ay=-25,
        font=dict(color=edge_col, size=10, family=FONT_FAMILY),
    )
    path_label = {"linear": "Linear", "front": "Front-loaded", "back": "Back-loaded"}.get(
        path_shape, "Linear")
    fig.update_layout(
        title=f"Cumulative Return Path — {horizon_months}M  ({path_label})",
        xaxis_title="Month", yaxis_title="Cumulative Return (%)",
        height=340, legend=dict(orientation="h", y=-0.25),
    )
    return _dark(fig)


def _build_sim_summary(tips_res: Dict, nom_res: Dict, horizon_months: int,
                        ry_start: float, ry_end: float,
                        be_start: float, be_end: float) -> go.Figure:
    """Small table summarising the scenario return attribution."""
    tips_edge = round(tips_res["total"] - nom_res["total"], 2)
    ann_factor = 12.0 / horizon_months
    rows_data = [
        ["Metric",               "TIPS / Linker",                 "Nominal Bond",              "TIPS Edge"],
        ["Modified Duration",    f"{tips_res['mod_dur']:.1f}",    f"{nom_res['mod_dur']:.1f}",  ""],
        ["Price Return",         f"{tips_res['price']:+.2f}%",    f"{nom_res['price']:+.2f}%",  ""],
        ["Carry / Accrual",      f"{tips_res['accrual']+tips_res['coupon']:+.2f}%",
                                  f"{nom_res['coupon']:+.2f}%",    ""],
        ["Rolldown",             f"{tips_res['rolldown']:+.2f}%", "—",                          ""],
        ["Total Return",         f"{tips_res['total']:+.2f}%",    f"{nom_res['total']:+.2f}%",
         f"{tips_edge:+.2f}%"],
        ["Annualised Return",
         f"{tips_res['total']*ann_factor:+.2f}%",
         f"{nom_res['total']*ann_factor:+.2f}%",
         f"{tips_edge*ann_factor:+.2f}% ann"],
        ["Scenario",
         f"RY: {ry_start:.2f}% → {ry_end:.2f}%",
         f"Nom: {ry_start+be_start:.2f}% → {ry_end+be_end:.2f}%",
         f"BE: {be_start:.2f}% → {be_end:.2f}%"],
    ]
    header_vals = [f"<b>{v}</b>" for v in rows_data[0]]
    cell_vals   = [[rows_data[r][c] for r in range(1, len(rows_data))]
                   for c in range(4)]
    edge_col_vals = []
    for v in cell_vals[3]:
        try:
            f = float(v.replace("%","").replace(" ann","").replace("+",""))
            edge_col_vals.append("rgba(34,197,94,0.25)" if f > 0 else
                                  "rgba(239,68,68,0.25)" if f < 0 else BG_DEEP)
        except (ValueError, AttributeError):
            edge_col_vals.append(BG_DEEP)
    fill = [
        [BG_CARD2]  * (len(rows_data)-1),
        [BG_DEEP]   * (len(rows_data)-1),
        [BG_DEEP]   * (len(rows_data)-1),
        edge_col_vals,
    ]
    fig = go.Figure(go.Table(
        columnwidth=[130, 120, 120, 120],
        header=dict(
            values=header_vals,
            fill_color=BG_CARD2,
            font=dict(color=ACCENT, family=FONT_FAMILY, size=10),
            align="center", line_color=BORDER_LT, height=24,
        ),
        cells=dict(
            values=cell_vals, fill_color=fill,
            font=dict(color=TEXT, family=FONT_FAMILY, size=10),
            align=["left","center","center","center"],
            line_color=BORDER, height=22,
        ),
    ))
    fig.update_layout(
        title=f"Scenario Summary — {horizon_months}M Horizon",
        margin=dict(l=10, r=10, t=38, b=10),
        height=260,
    )
    return _dark(fig)


# ==========================================================================
#  BOND RETURN SIMULATION — ENGINE
# ==========================================================================

def _bond_roll_bps(data: Dict, country: str, tenor: str, horizon_months: int) -> float:
    """
    Estimate roll-down return in bps for a bond rolling down the curve
    over horizon_months. Uses tenor-appropriate slope derived from live yields.
    All approximations assume a smooth, locally-linear curve.
    Returns positive bps when rolling down a normal (upward-sloping) curve.
    """
    T     = horizon_months / 12.0
    yields = data.get("yields", {})

    def _y(t: str) -> Optional[float]:
        return yields.get(t, {}).get(country)

    y2  = _y("2Y")
    y5  = _y("5Y")
    y10 = _y("10Y")
    y30 = _y("30Y")

    if tenor == "2Y":
        # Roll from 2Y toward overnight; use 2s10s / 8 as proxy for local slope
        slope_pct_yr = (data.get("slopes", {}).get(country) or 0) / 8.0
    elif tenor == "5Y":
        # Use 2s5s slope (3-year span)
        if y5 is not None and y2 is not None:
            slope_pct_yr = (y5 - y2) / 3.0
        else:
            slope_pct_yr = (data.get("slopes", {}).get(country) or 0) / 8.0
    elif tenor == "10Y":
        # Use 2s10s / 8 — already stored in data["slopes"]
        slope_pct_yr = (data.get("slopes", {}).get(country) or 0) / 8.0
    else:  # 30Y
        # Use 10s30s slope (20-year span)
        if y30 is not None and y10 is not None:
            slope_pct_yr = (y30 - y10) / 20.0
        elif y30 is not None and y2 is not None:
            slope_pct_yr = (y30 - y2) / 28.0
        else:
            slope_pct_yr = (data.get("slopes", {}).get(country) or 0) / 8.0

    # Roll yield drop (%) = slope_per_year × horizon; convert to bps
    return round(slope_pct_yr * T * 100, 1)


def compute_bond_scenario(
    yield_start: float,
    delta_yield_bps: float,
    horizon_months: int,
    coupon_pct: float,
    maturity_years: float,
    rolldown_bps: float = 0.0,
) -> Dict:
    """
    Decompose nominal sovereign bond total return into carry, roll-down, and price return.
    All yields / coupons in percent (e.g. 4.35 = 4.35%).
    delta_yield_bps = parallel_shift + spread_change (bps).
    Returns all components in percent.
    """
    T          = horizon_months / 12.0
    rem        = max(maturity_years - T, 0.01)
    ny         = max(yield_start / 100.0, 0.001)
    coup       = coupon_pct / 100.0

    # Modified duration (Macaulay / (1 + y/2)) with convexity
    if coup < 1e-4:
        mod_dur = rem / (1 + ny)
    else:
        n, r2, c2 = rem * 2, ny / 2, coup / 2
        try:
            mac = ((1 + r2) / r2
                   - (n * (c2 - r2) + (1 + r2))
                   / (c2 * ((1 + r2) ** n - 1) + r2))
        except (ZeroDivisionError, OverflowError):
            mac = rem
        mod_dur = mac / (1 + r2)

    convexity = mod_dur ** 2 / 100.0

    # Carry = coupon income over the holding period
    carry = coupon_pct * T

    # Roll-down price appreciation from yield falling as bond ages along curve
    roll_dy     = rolldown_bps / 10000.0   # positive = yield falls = price up
    rolldown_ret = (mod_dur * roll_dy + 0.5 * convexity * roll_dy ** 2) * 100.0

    # Price return from scenario yield change
    d_y      = delta_yield_bps / 10000.0
    price_ret = (-mod_dur * d_y + 0.5 * convexity * d_y ** 2) * 100.0

    total     = carry + rolldown_ret + price_ret
    ann_factor = 12.0 / horizon_months if horizon_months > 0 else 1.0

    return {
        "carry":      round(carry,        2),
        "rolldown":   round(rolldown_ret, 2),
        "price":      round(price_ret,    2),
        "total":      round(total,        2),
        "annualised": round(total * ann_factor, 2),
        "mod_dur":    round(mod_dur,      2),
        "convexity":  round(convexity,    3),
    }


def chart_bond_sim_waterfall(result: Dict, horizon_months: int,
                              country: str, tenor: str) -> go.Figure:
    """
    Vertical waterfall bar chart decomposing nominal bond total return into
    carry, roll-down, and price return components.
    """
    carry    = result["carry"]
    rolldown = result["rolldown"]
    price    = result["price"]
    total    = result["total"]

    labels  = ["Carry", "Roll-down", "Price Return", "Total"]
    values  = [carry, rolldown, price, total]
    bases   = [0.0, carry, carry + rolldown, 0.0]
    colors  = [
        GREEN,
        TEAL,
        GREEN if price >= 0 else RED,
        YELLOW,
    ]
    bar_widths = [0.5, 0.5, 0.5, 0.4]

    fig = go.Figure()
    for i, (lbl, val, base, col, bw) in enumerate(
            zip(labels, values, bases, colors, bar_widths)):
        is_total = (lbl == "Total")
        fig.add_trace(go.Bar(
            x=[lbl], y=[val if not is_total else total],
            base=[base if not is_total else 0.0],
            marker_color=col,
            marker_line=dict(color="white", width=1.5) if is_total else dict(width=0),
            marker_opacity=1.0 if not is_total else 0.85,
            width=bw,
            name=lbl,
            showlegend=False,
            hovertemplate=f"<b>{lbl}</b><br>{val:+.2f}%<extra></extra>",
            text=[f"{val:+.2f}%"],
            textposition="outside",
            textfont=dict(color=col, size=10, family=FONT_FAMILY),
        ))

    fig.add_hline(y=0, line_dash="dot", line_color=BORDER_LT, line_width=1)

    flag  = FLAGS.get(country, "")
    fig.update_layout(
        title=(f"Return Decomposition — {flag} {country} {tenor}  "
               f"({horizon_months}M horizon)<br>"
               f"<sup>Carry + Roll-down + Price Return  |  "
               f"Total: {total:+.2f}%  |  Ann: {result['annualised']:+.2f}%</sup>"),
        barmode="overlay",
        xaxis=dict(title="", tickfont=dict(size=10, family=FONT_FAMILY)),
        yaxis=dict(title="Return (%)", tickfont=dict(size=10, family=FONT_FAMILY),
                   zeroline=False),
        height=310,
        margin=dict(t=60, b=30),
    )
    return _dark(fig)


def chart_bond_sim_heatmap(
    yield_start: float,
    rolldown_bps: float,
    carry: float,
    horizon_months: int,
    maturity_years: float,
) -> go.Figure:
    """
    Total return heatmap: X = parallel shift (bps), Y = spread change (bps).
    Carry and roll-down are constant across the grid; only price return varies.
    White box highlights the zero-change base case.
    """
    par_deltas  = np.arange(-300, 301, 25)
    spd_deltas  = np.arange(-200, 201, 25)
    coupon_pct  = yield_start  # at-par assumption

    z = np.zeros((len(spd_deltas), len(par_deltas)))
    for i, spd_d in enumerate(spd_deltas):
        for j, par_d in enumerate(par_deltas):
            res = compute_bond_scenario(
                yield_start,
                delta_yield_bps=float(par_d + spd_d),
                horizon_months=horizon_months,
                coupon_pct=coupon_pct,
                maturity_years=maturity_years,
                rolldown_bps=rolldown_bps,
            )
            z[i, j] = res["total"]

    zmax = min(float(np.nanmax(np.abs(z))), 15.0)
    x_labels = [f"{v:+d}" for v in par_deltas]
    y_labels = [f"{v:+d}" for v in spd_deltas]
    text_arr = [[f"{z[i,j]:+.1f}%" for j in range(len(par_deltas))]
                for i in range(len(spd_deltas))]

    fig = go.Figure(go.Heatmap(
        z=z, x=x_labels, y=y_labels,
        colorscale=[[0.0, RED], [0.5, BG_CARD2], [1.0, GREEN]],
        zmid=0, zmin=-zmax, zmax=zmax,
        text=text_arr, texttemplate="%{text}",
        textfont=dict(size=8, family=FONT_FAMILY),
        hovertemplate="Par Δ: %{x} bps | Spd Δ: %{y} bps<br>Return: %{z:+.2f}%<extra></extra>",
        showscale=True,
        colorbar=dict(
            title=dict(text="Return (%)", font=dict(size=9, family=FONT_FAMILY)),
            tickfont=dict(size=9, family=FONT_FAMILY),
        ),
    ))

    # Highlight zero-change base case
    zero_par = list(par_deltas).index(0) if 0 in par_deltas else None
    zero_spd = list(spd_deltas).index(0) if 0 in spd_deltas else None
    if zero_par is not None and zero_spd is not None:
        fig.add_shape(
            type="rect", xref="x", yref="y",
            x0=zero_par - 0.5, x1=zero_par + 0.5,
            y0=zero_spd - 0.5, y1=zero_spd + 0.5,
            line=dict(color="white", width=2),
        )

    fig.update_layout(
        title=f"Total Return Heatmap — {horizon_months}M  (X = Par Shift bps, Y = Spread Δ bps)",
        xaxis_title="Parallel Shift (bps)",
        yaxis_title="Spread Change (bps)",
        xaxis=dict(tickfont=dict(size=8, family=FONT_FAMILY)),
        yaxis=dict(tickfont=dict(size=8, family=FONT_FAMILY)),
        height=390,
    )
    return _dark(fig)


def _build_bond_sim_summary(result: Dict, horizon_months: int,
                             yield_start: float, parallel_bps: float,
                             spread_bps: float, policy_bps: float,
                             country: str, tenor: str) -> go.Figure:
    """Summary table for the bond return scenario."""
    total_col = "rgba(34,197,94,0.25)" if result["total"] >= 0 else "rgba(239,68,68,0.25)"
    ann_col   = "rgba(34,197,94,0.25)" if result["annualised"] >= 0 else "rgba(239,68,68,0.25)"
    rows = [
        ("Country / Tenor",    f"{FLAGS.get(country,'')} {country}  {tenor}"),
        ("Horizon",            f"{horizon_months}M"),
        ("Modified Duration",  f"{result['mod_dur']:.2f}"),
        ("Convexity",          f"{result['convexity']:.3f}"),
        ("Yield at Start",     f"{yield_start:.3f}%"),
        ("Parallel Shift",     f"{parallel_bps:+.0f} bps"),
        ("Spread Change",      f"{spread_bps:+.0f} bps"),
        ("Policy Δ (context)", f"{policy_bps:+.0f} bps"),
        ("─" * 18,             "─" * 14),
        ("Carry",              f"{result['carry']:+.2f}%"),
        ("Roll-down",          f"{result['rolldown']:+.2f}%"),
        ("Price Return",       f"{result['price']:+.2f}%"),
        ("Total Return",       f"{result['total']:+.2f}%"),
        ("Annualised Return",  f"{result['annualised']:+.2f}%"),
    ]
    metrics = [r[0] for r in rows]
    values  = [r[1] for r in rows]
    n = len(rows)
    fill_vals = [BG_CARD2] * n
    fill_vals[12] = total_col
    fill_vals[13] = ann_col

    fig = go.Figure(go.Table(
        columnwidth=[140, 110],
        header=dict(
            values=["<b>Metric</b>", "<b>Value</b>"],
            fill_color=BG_CARD2,
            font=dict(color=ACCENT2, family=FONT_FAMILY, size=10),
            align=["left", "center"],
            line_color=BORDER_LT, height=24,
        ),
        cells=dict(
            values=[metrics, values],
            fill_color=[fill_vals, fill_vals],
            font=dict(color=TEXT, family=FONT_FAMILY, size=10),
            align=["left", "center"],
            line_color=BORDER, height=22,
        ),
    ))
    fig.update_layout(
        title=f"Scenario Summary — {horizon_months}M",
        margin=dict(l=8, r=8, t=38, b=8),
        height=310,
    )
    return _dark(fig)


def chart_bond_sim_path(
    yield_start: float,
    delta_yield_bps: float,
    horizon_months: int,
    coupon_pct: float,
    maturity_years: float,
    rolldown_bps: float = 0.0,
    path_shape: str = "linear",
) -> go.Figure:
    """
    Cumulative return path month-by-month.
    Three lines: scenario, base case (no yield change), and carry-only.
    Path shapes: linear, front-loaded (fast early), back-loaded (slow early).
    """
    months   = list(range(0, horizon_months + 1))
    y_end    = yield_start + delta_yield_bps / 100.0   # final yield in %

    def _frac(t: int) -> float:
        f = t / horizon_months if horizon_months > 0 else 0.0
        if path_shape == "front":
            return 1.0 - (1.0 - f) ** 2
        elif path_shape == "back":
            return f ** 2
        return f

    scenario_cum, base_cum, carry_cum = [0.0], [0.0], [0.0]
    for t in range(1, horizon_months + 1):
        frac     = _frac(t)
        # Scenario: yield moves proportionally along path shape
        delta_t  = (y_end - yield_start) * frac * 100   # bps at month t
        roll_t   = rolldown_bps * t / horizon_months
        res_scen = compute_bond_scenario(yield_start, delta_t, t,
                                         coupon_pct, maturity_years, roll_t)
        # Base case: no yield change, just carry + roll
        res_base = compute_bond_scenario(yield_start, 0.0, t,
                                         coupon_pct, maturity_years, roll_t)
        # Carry-only: no yield change, no roll (pure coupon income)
        res_carry = compute_bond_scenario(yield_start, 0.0, t,
                                          coupon_pct, maturity_years, 0.0)
        scenario_cum.append(res_scen["total"])
        base_cum.append(res_base["total"])
        carry_cum.append(res_carry["carry"])

    final_ret = scenario_cum[-1]
    edge_vs_base = round(final_ret - base_cum[-1], 2)
    edge_col     = GREEN if edge_vs_base >= 0 else RED

    path_label = {"linear": "Linear", "front": "Front-loaded",
                  "back": "Back-loaded"}.get(path_shape, "Linear")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months, y=scenario_cum, mode="lines+markers", name="Scenario",
        line=dict(color=ACCENT2, width=2.5), marker=dict(size=4),
        hovertemplate="Month %{x}<br>Return: %{y:+.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=months, y=base_cum, mode="lines", name="No Δ Yield (carry+roll)",
        line=dict(color=TEAL, width=1.8, dash="dash"),
        hovertemplate="Month %{x}<br>Base: %{y:+.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=months, y=carry_cum, mode="lines", name="Carry only",
        line=dict(color=TEXT_MUT, width=1.2, dash="dot"),
        hovertemplate="Month %{x}<br>Carry: %{y:+.2f}%<extra></extra>",
    ))
    # Shaded area between scenario and base
    fig.add_trace(go.Scatter(
        x=months + months[::-1],
        y=scenario_cum + base_cum[::-1],
        fill="toself",
        fillcolor="rgba(124,58,237,0.10)" if edge_vs_base >= 0 else "rgba(239,68,68,0.10)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=BORDER_LT, line_width=1)
    fig.add_annotation(
        x=horizon_months, y=final_ret,
        text=f"vs base: {edge_vs_base:+.2f}%",
        showarrow=True, arrowhead=2, ax=40, ay=-25,
        font=dict(color=edge_col, size=10, family=FONT_FAMILY),
    )
    fig.update_layout(
        title=f"Cumulative Return Path — {horizon_months}M  ({path_label})<br>"
              f"<sup>Δy = {delta_yield_bps:+.0f} bps total  |  "
              f"Scenario total: {final_ret:+.2f}%</sup>",
        xaxis_title="Month",
        yaxis_title="Cumulative Return (%)",
        height=370,
        legend=dict(orientation="h", y=-0.22, x=0.0,
                    font=dict(size=9, family=FONT_FAMILY)),
    )
    return _dark(fig)


def chart_bond_sim_country_bar(
    data: Dict,
    tenor: str,
    horizon_months: int,
    parallel_bps: float,
    spread_bps: float,
    coupon_override: Optional[float] = None,
) -> go.Figure:
    """
    Stacked horizontal bar showing carry / roll-down / price return for every
    country at the selected tenor and scenario, sorted by total return descending.
    Countries with no live yield data are excluded.
    """
    delta_bps = parallel_bps + spread_bps
    maturity  = _BOND_TENOR_MATURITY.get(tenor, 10.0)
    rows: List[Dict] = []

    for c in COUNTRIES:
        y = data.get("yields", {}).get(tenor, {}).get(c)
        if y is None:
            continue
        coup     = coupon_override if coupon_override is not None else y
        roll_bps = _bond_roll_bps(data, c, tenor, horizon_months)
        res      = compute_bond_scenario(y, delta_bps, horizon_months,
                                         coup, maturity, roll_bps)
        rows.append({
            "country":  c,
            "label":    f"{FLAGS.get(c,'')} {c}",
            "carry":    res["carry"],
            "rolldown": res["rolldown"],
            "price":    res["price"],
            "total":    res["total"],
            "yield":    y,
        })

    if not rows:
        return _empty_fig(f"No yield data for {tenor} — connect Bloomberg")

    rows.sort(key=lambda r: r["total"], reverse=True)
    labels   = [r["label"]    for r in rows]
    carries  = [r["carry"]    for r in rows]
    rolls    = [r["rolldown"] for r in rows]
    prices   = [r["price"]    for r in rows]
    totals   = [r["total"]    for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Carry", y=labels, x=carries, orientation="h",
        marker_color=GREEN,
        hovertemplate="<b>%{y}</b><br>Carry: %{x:+.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Roll-down", y=labels, x=rolls, orientation="h",
        marker_color=TEAL,
        hovertemplate="<b>%{y}</b><br>Roll-down: %{x:+.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Price Return", y=labels, x=prices, orientation="h",
        marker_color=[GREEN if p >= 0 else RED for p in prices],
        hovertemplate="<b>%{y}</b><br>Price Return: %{x:+.2f}%<extra></extra>",
    ))

    # Annotate total return on each bar
    for i, (lbl, tot) in enumerate(zip(labels, totals)):
        fig.add_annotation(
            x=tot, y=lbl,
            text=f"  {tot:+.2f}%",
            showarrow=False, xanchor="left",
            font=dict(size=9, color=GREEN if tot >= 0 else RED,
                      family=FONT_FAMILY),
        )

    fig.add_vline(x=0, line_dash="dot", line_color=BORDER_LT, line_width=1)
    fig.update_layout(
        barmode="relative",
        title=(f"Cross-Country Return — {tenor}  ({horizon_months}M)  "
               f"Par {parallel_bps:+.0f} / Spd {spread_bps:+.0f} bps<br>"
               f"<sup>Sorted by total return. Carry (green) · Roll-down (teal) · "
               f"Price (green/red)</sup>"),
        xaxis_title="Return (%)",
        yaxis=dict(title="", autorange="reversed",
                   tickfont=dict(size=10, family=FONT_FAMILY)),
        height=max(280, len(rows) * 40 + 80),
        legend=dict(orientation="h", y=-0.15, x=0.0,
                    font=dict(size=9, family=FONT_FAMILY)),
    )
    return _dark(fig)


def chart_yield_spread_heatmap(data: Dict, countries_sel: List[str] = None) -> go.Figure:

    """
    Country × country grid heatmap of current 10Y yield spreads (bps).
    Cell colour = z-score of that spread vs its ~10Y history.
    Red = spread negative / historically tight; Green = spread positive / historically wide.
    """
    y10 = data["yields"]["10Y"]
    _filter = countries_sel if countries_sel else COUNTRIES
    countries = [c for c in _filter if c in y10 and y10[c] is not None]
    # Historical 10Y yields for z-score (~10 years = 2520 business days)
    hist_df = get_hist_df("10Y", days=2520)
    z_matrix, text_matrix, hover_matrix = [], [], []
    for ca in countries:          # row = base country
        z_row, t_row, h_row = [], [], []
        for cb in countries:      # col = quote country
            if ca == cb:
                z_row.append(None)
                t_row.append("—")
                h_row.append(f"<b>{FLAGS.get(ca,'')} {ca}</b>")
            else:
                spread_pct = y10[ca] - y10[cb]
                spread_bps = round(spread_pct * 100, 0)
                # Compute 10Y z-score from historical spread
                zscore = None
                if ca in hist_df.columns and cb in hist_df.columns:
                    hist_spread = (hist_df[ca] - hist_df[cb]).dropna()
                    if len(hist_spread) >= 20:
                        mu    = hist_spread.mean()
                        sigma = hist_spread.std()
                        zscore = round((spread_pct - mu) / sigma, 2) if sigma > 0 else 0.0
                # zscore stays None if insufficient history — cell renders blank in heatmap
                z_row.append(zscore)
                t_row.append(f"{spread_bps:+.0f}")
                z_str = f"{zscore:+.2f}σ" if zscore is not None else "N/A (no history)"
                h_row.append(
                    f"<b>{FLAGS.get(ca,'')} {ca} − {FLAGS.get(cb,'')} {cb}</b><br>"
                    f"Spread: {spread_bps:+.0f} bps<br>"
                    f"10Y Z-Score: {z_str}<br>"
                    + (f"{'Wide vs history ↑' if zscore > 1 else ('Tight/negative vs history ↓' if zscore < -1 else 'Near historical avg')}"
                       if zscore is not None else "Connect Bloomberg for z-score history")
                )
        z_matrix.append(z_row)
        text_matrix.append(t_row)
        hover_matrix.append(h_row)
    xlabels = [f"{FLAGS.get(c,'')} {c}" for c in countries]
    ylabels = [f"{FLAGS.get(c,'')} {c}" for c in countries]
    colorscale = [
        [0.00, "#8b0000"],   # dark red   (z ≤ −3, spread very tight/negative)
        [0.50, "#1E2535"],   # neutral    (z = 0)
        [1.00, "#1a7c1a"],   # dark green (z ≥ +3, spread historically wide)
    ]
    fig = go.Figure(go.Heatmap(
        z=z_matrix,
        x=xlabels,
        y=ylabels,
        customdata=hover_matrix,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale=colorscale,
        zmid=0,
        zmin=-3,
        zmax=3,
        colorbar=dict(
            title=dict(text="10Y<br>Z-Score", font=dict(family=FONT_FAMILY, size=10)),
            tickfont=dict(family=FONT_FAMILY, size=10),
            tickvals=[-3, -2, -1, 0, 1, 2, 3],
            ticktext=["-3σ", "-2σ", "-1σ", "0", "+1σ", "+2σ", "+3σ"],
        ),
        zsmooth=False,
        xgap=2,
        ygap=2,
    ))
    _add_cell_annotations(fig, z_matrix, xlabels, ylabels, text_matrix, font_size=10,
                          force_show=True)
    fig.update_layout(
        title="10Y Yield Spread Matrix  (bps, colour = 10Y z-score)<br>"
              "<sup>Row minus column. "
              "Green = spread wide vs 10Y history  |  Red = spread tight or negative vs 10Y history</sup>",
        xaxis=dict(title="Quote Country (−)", side="top", tickangle=-30),
        yaxis=dict(title="Base Country (+)", autorange="reversed"),
        height=500,
    )
    return _dark(fig)


def chart_zscore_spread_heatmap(data: Dict, countries_sel: List[str] = None,
                                days: int = 1260) -> go.Figure:
    """
    Country × country heatmap showing the z-score of the current 10Y yield spread
    relative to the chosen lookback period (1Y–30Y). Both cell text and colour
    reflect the z-score so the user can see the magnitude directly.
    """
    y10 = data["yields"]["10Y"]
    _filter = countries_sel if countries_sel else COUNTRIES
    countries = [c for c in _filter if c in y10 and y10[c] is not None]
    yr_label = {252: "1Y", 504: "2Y", 756: "3Y", 1260: "5Y",
                2520: "10Y", 3780: "15Y", 5040: "20Y", 7560: "30Y"}.get(days, f"{days}d")
    hist_df = get_hist_df("10Y", days=days)
    z_matrix, text_matrix, hover_matrix = [], [], []
    for ca in countries:
        z_row, t_row, h_row = [], [], []
        for cb in countries:
            if ca == cb:
                z_row.append(None)
                t_row.append("—")
                h_row.append(f"<b>{FLAGS.get(ca,'')} {ca}</b>")
            else:
                spread_pct = y10[ca] - y10[cb]
                spread_bps = round(spread_pct * 100, 0)
                zscore = None
                if not hist_df.empty and ca in hist_df.columns and cb in hist_df.columns:
                    hist_spread = (hist_df[ca] - hist_df[cb]).dropna()
                    if len(hist_spread) >= 20:
                        mu    = hist_spread.mean()
                        sigma = hist_spread.std()
                        zscore = round((spread_pct - mu) / sigma, 2) if sigma > 0 else 0.0
                z_row.append(zscore)
                z_str = f"{zscore:+.2f}σ" if zscore is not None else "N/A"
                t_row.append(z_str)
                dir_label = ""
                if zscore is not None:
                    dir_label = ("Wide vs history ↑" if zscore > 1
                                 else ("Tight/negative vs history ↓" if zscore < -1
                                       else "Near historical avg"))
                h_row.append(
                    f"<b>{FLAGS.get(ca,'')} {ca} − {FLAGS.get(cb,'')} {cb}</b><br>"
                    f"Spread: {spread_bps:+.0f} bps<br>"
                    f"{yr_label} Z-Score: {z_str}"
                    + (f"<br>{dir_label}" if dir_label else "")
                )
        z_matrix.append(z_row)
        text_matrix.append(t_row)
        hover_matrix.append(h_row)
    xlabels = [f"{FLAGS.get(c,'')} {c}" for c in countries]
    ylabels = [f"{FLAGS.get(c,'')} {c}" for c in countries]
    colorscale = [
        [0.00, "#8b0000"],
        [0.50, "#1E2535"],
        [1.00, "#1a7c1a"],
    ]
    fig = go.Figure(go.Heatmap(
        z=z_matrix, x=xlabels, y=ylabels,
        customdata=hover_matrix,
        hovertemplate="%{customdata}<extra></extra>",
        colorscale=colorscale,
        zmid=0, zmin=-3, zmax=3,
        colorbar=dict(
            title=dict(text=f"{yr_label}<br>Z-Score", font=dict(family=FONT_FAMILY, size=10)),
            tickfont=dict(family=FONT_FAMILY, size=10),
            tickvals=[-3, -2, -1, 0, 1, 2, 3],
            ticktext=["-3σ", "-2σ", "-1σ", "0", "+1σ", "+2σ", "+3σ"],
        ),
        zsmooth=False, xgap=2, ygap=2,
    ))
    _add_cell_annotations(fig, z_matrix, xlabels, ylabels, text_matrix,
                          font_size=9, force_show=True)
    fig.update_layout(
        title=(f"10Y Spread Z-Score Matrix  ({yr_label} lookback)<br>"
               f"<sup>Row minus column vs {yr_label} history.  "
               f"Green = historically wide  |  Red = historically tight/negative</sup>"),
        xaxis=dict(title="Quote Country (−)", side="top", tickangle=-30),
        yaxis=dict(title="Base Country (+)", autorange="reversed"),
        height=max(350, len(countries) * 44 + 120),
    )
    return _dark(fig)


# ==========================================================================
#  IDEAS TABLE BUILDER
# ==========================================================================

CONV_BADGE = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}
OL_BADGE   = {"BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➡️"}


# ==========================================================================
#  FORWARD RATE MONITOR — derived from par sovereign yield curves
# ==========================================================================


def compute_implied_forwards(data: Dict) -> Dict:
    """
    Bootstrap implied forward rates from par sovereign yield curves.
    Annual compounding: f(m,n) = ((1+rₙ)ⁿ / (1+rₘ)ᵐ)^(1/(n-m)) − 1
    Yields are in percent; output is also in percent.
    Returns: {country: {"2s5s": val, "5s10s": val, "10s30s": val}}
    """
    y   = data.get("yields", {})
    r2  = y.get("2Y",  {})
    r5  = y.get("5Y",  {})
    r10 = y.get("10Y", {})
    r30 = y.get("30Y", {})
    result = {}
    for c in COUNTRIES:
        entry = {}
        # 2s5s: implied 3Y rate, 2Y forward
        try:
            if c in r2 and c in r5 and r2[c] is not None and r5[c] is not None:
                entry["2s5s"] = round(
                    (((1 + r5[c] / 100) ** 5 / (1 + r2[c] / 100) ** 2) ** (1 / 3) - 1) * 100, 3
                )
        except Exception:
            pass
        # 5s10s: implied 5Y rate, 5Y forward — the "5Y5Y" that central banks watch
        try:
            if c in r5 and c in r10 and r5[c] is not None and r10[c] is not None:
                entry["5s10s"] = round(
                    (((1 + r10[c] / 100) ** 10 / (1 + r5[c] / 100) ** 5) ** (1 / 5) - 1) * 100, 3
                )
        except Exception:
            pass
        # 10s30s: implied 20Y rate, 10Y forward — ultra-long fiscal/inflation signal
        try:
            if c in r10 and c in r30 and r10[c] is not None and r30[c] is not None:
                entry["10s30s"] = round(
                    (((1 + r30[c] / 100) ** 30 / (1 + r10[c] / 100) ** 10) ** (1 / 20) - 1) * 100, 3
                )
        except Exception:
            pass
        if entry:
            result[c] = entry
    return result


def chart_fwd_bar(data: Dict, fwd_key: str = "5s10s") -> go.Figure:
    """Bar chart of selected implied forward rate, cross-country."""
    fwds = compute_implied_forwards(data)
    label_map = {
        "2s5s":   "3Y Rate, 2Y Fwd",
        "5s10s":  "5Y5Y (5s10s Fwd)",
        "10s30s": "20Y Rate, 10Y Fwd",
    }
    cs = [c for c in COUNTRIES if c in fwds and fwd_key in fwds[c]]
    vs = [fwds[c][fwd_key] for c in cs]
    if not vs:
        return _empty_fig("No forward rate data — connect Bloomberg")
    fig = go.Figure(go.Bar(
        x=[f"{FLAGS.get(c, '')} {c}" for c in cs],
        y=vs,
        marker_color=[CCOLORS.get(c, TEXT_MUT) for c in cs],
        text=[f"{v:.2f}%" for v in vs],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>" + label_map.get(fwd_key, fwd_key) + ": %{y:.3f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=BORDER_LT)
    fig.update_layout(
        title=f"Implied {label_map.get(fwd_key, fwd_key)}{_ind_tag(data)}",
        yaxis_title="Yield (%)",
    )
    return _dark(fig)


def chart_fwd_curve(data: Dict, countries_sel: List[str] = None) -> go.Figure:
    """
    Spot yield curves (solid lines) plus implied forward rates (diamond markers)
    for each selected country. Diamonds sit at the forward's notional midpoint.
    """
    sel  = countries_sel or COUNTRIES
    fwds = compute_implied_forwards(data)
    y    = data.get("yields", {})
    fig  = go.Figure()
    spot_tenors = [("2Y", 2), ("5Y", 5), ("10Y", 10), ("30Y", 30)]
    # Forward midpoints: 2s5s centred at 3.5Y, 5s10s at 7.5Y, 10s30s at 20Y
    fwd_defs = [
        ("2s5s",   3.5, "3Y, 2Y Fwd"),
        ("5s10s",  7.5, "5Y5Y"),
        ("10s30s", 20,  "20Y, 10Y Fwd"),
    ]
    for c in sel:
        color = CCOLORS.get(c, TEXT_MUT)
        flag  = FLAGS.get(c, "")
        # Spot curve
        xs, ys = [], []
        for t, x in spot_tenors:
            v = y.get(t, {}).get(c)
            if v is not None:
                xs.append(x)
                ys.append(v)
        if xs:
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines+markers",
                name=f"{flag} {c}",
                line=dict(color=color, width=2),
                marker=dict(size=6, symbol="circle"),
                legendgroup=c,
                showlegend=True,
                hovertemplate=f"<b>{c} Spot</b><br>%{{x}}Y: %{{y:.3f}}%<extra></extra>",
            ))
        # Implied forward diamonds
        fc = fwds.get(c, {})
        fwx, fwy, fwt = [], [], []
        for k, mx, lbl in fwd_defs:
            v = fc.get(k)
            if v is not None:
                fwx.append(mx)
                fwy.append(v)
                fwt.append(lbl)
        if fwx:
            fig.add_trace(go.Scatter(
                x=fwx, y=fwy, mode="markers",
                name=f"{flag} {c} Fwd",
                marker=dict(color=color, size=11, symbol="diamond",
                            line=dict(color="white", width=1.2)),
                legendgroup=c,
                showlegend=False,
                text=fwt,
                hovertemplate=f"<b>{c}</b><br>%{{text}}: %{{y:.3f}}%<extra></extra>",
            ))
    fig.update_layout(
        title=f"Spot Yield Curves + Implied Forward Rates  (◆ = Fwd){_ind_tag(data)}",
        xaxis=dict(
            title="Tenor / Fwd Midpoint (Yrs)",
            tickvals=[2, 3.5, 5, 7.5, 10, 20, 30],
            ticktext=["2Y", "3.5Y", "5Y", "7.5Y", "10Y", "20Y", "30Y"],
        ),
        yaxis_title="Yield / Fwd Rate (%)",
        hovermode="closest",
    )
    return _dark(fig)


def chart_fwd_premium(data: Dict) -> go.Figure:
    """
    5Y5Y forward rate minus current 10Y spot yield, per country.
    Positive = market prices terminal rate above current 10Y (bear steepener embedded).
    Negative = terminal rate priced below 10Y (dovish long-run pricing — duration bullish).
    """
    fwds = compute_implied_forwards(data)
    y10  = data.get("yields", {}).get("10Y", {})
    cs, vs = [], []
    for c in COUNTRIES:
        f55 = fwds.get(c, {}).get("5s10s")
        s10 = y10.get(c)
        if f55 is not None and s10 is not None:
            cs.append(c)
            vs.append(round(f55 - s10, 3))
    if not vs:
        return _empty_fig("No forward rate data — connect Bloomberg")
    colors = [RED if v > 0.05 else (GREEN if v < -0.05 else YELLOW) for v in vs]
    fig = go.Figure(go.Bar(
        x=[f"{FLAGS.get(c, '')} {c}" for c in cs],
        y=vs,
        marker_color=colors,
        text=[f"{v:+.2f}%" for v in vs],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>5Y5Y − 10Y Spot: %{y:+.3f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER_LT)
    fig.update_layout(
        title=f"5Y5Y Fwd Premium over 10Y Spot{_ind_tag(data)}",
        yaxis_title="Forward − Spot (%)",
    )
    return _dark(fig)


# ==========================================================================
#  CB POLICY PATH CHARTS — OIS-implied rate paths
# ==========================================================================


def chart_policy_path(data: Dict, cbs_sel: List[str] = None) -> go.Figure:
    """
    Market-implied policy rate path per central bank.
    Month 0 = current policy rate; subsequent points = OIS at 3/6/12/18/24M.
    """
    sel    = cbs_sel or list(OIS_PATH_TICKERS.keys())
    ois    = data.get("ois_path", {})
    policy = data.get("macro", {}).get("POLICY_RATE", {})
    x_vals = [0, 3, 6, 12, 18, 24]
    x_labs = ["Now", "3M", "6M", "12M", "18M", "24M"]
    fig = go.Figure()
    for cb in sel:
        color   = OIS_CB_COLORS.get(cb, TEXT_MUT)
        flag    = OIS_CB_FLAGS.get(cb, "")
        pol_key = OIS_CB_POLICY_MAP.get(cb, cb)
        cur     = policy.get(pol_key)
        ois_cb  = ois.get(cb, {})
        ys = [cur if cur is not None else np.nan]
        for t in ["3M", "6M", "12M", "18M", "24M"]:
            v = ois_cb.get(t)
            ys.append(v if v is not None else np.nan)
        if all(np.isnan(v) if isinstance(v, float) else v is None for v in ys):
            continue
        fig.add_trace(go.Scatter(
            x=x_vals, y=ys,
            mode="lines+markers",
            name=f"{flag} {cb}",
            line=dict(color=color, width=2.5),
            marker=dict(size=8),
            connectgaps=True,
            hovertemplate=f"<b>{flag} {cb}</b><br>%{{x}}M: %{{y:.3f}}%<extra></extra>",
        ))
    fig.update_layout(
        title=f"Market-Implied Policy Rate Path (OIS){_ind_tag(data)}",
        xaxis=dict(title="Months Forward", tickvals=x_vals, ticktext=x_labs),
        yaxis_title="Rate (%)",
        hovermode="x unified",
    )
    return _dark(fig)


def chart_implied_cuts(data: Dict) -> go.Figure:
    """
    Bar: (12M OIS − current policy rate) × 100, in basis points.
    Green = cuts priced, Red = hikes priced, Yellow = flat.
    """
    ois    = data.get("ois_path", {})
    policy = data.get("macro", {}).get("POLICY_RATE", {})
    cbs, vals = [], []
    for cb in OIS_PATH_TICKERS:
        pol_key = OIS_CB_POLICY_MAP.get(cb, cb)
        cur     = policy.get(pol_key)
        ois_12m = ois.get(cb, {}).get("12M")
        if cur is not None and ois_12m is not None:
            cbs.append(cb)
            vals.append(round((ois_12m - cur) * 100, 1))
    if not vals:
        return _empty_fig("No OIS data — connect Bloomberg and verify tickers")
    colors = [RED if v > 5 else (GREEN if v < -5 else YELLOW) for v in vals]
    fig = go.Figure(go.Bar(
        x=[f"{OIS_CB_FLAGS.get(cb, '')} {cb}" for cb in cbs],
        y=vals,
        marker_color=colors,
        text=[f"{v:+.0f} bps" for v in vals],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>12M implied change: %{y:+.1f} bps<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=BORDER_LT)
    fig.update_layout(
        title=f"12M OIS-Implied Rate Change{_ind_tag(data)}",
        yaxis_title="Basis Points (vs Current Policy Rate)",
    )
    return _dark(fig)


def chart_policy_path_heatmap(data: Dict) -> go.Figure:
    """
    Heatmap: rows = CBs, cols = Now / 3M / 6M / 12M / 18M / 24M.
    Rate levels with implied change in bps vs current policy rate.
    """
    ois    = data.get("ois_path", {})
    policy = data.get("macro", {}).get("POLICY_RATE", {})
    cbs        = list(OIS_PATH_TICKERS.keys())
    col_labels = ["Now", "3M", "6M", "12M", "18M", "24M"]
    z, text = [], []
    for cb in cbs:
        pol_key = OIS_CB_POLICY_MAP.get(cb, cb)
        cur     = policy.get(pol_key)
        ois_cb  = ois.get(cb, {})
        row_z, row_t = [], []
        vals = [cur] + [ois_cb.get(t) for t in ["3M", "6M", "12M", "18M", "24M"]]
        for i, v in enumerate(vals):
            if v is None:
                row_z.append(None)
                row_t.append("N/A")
            else:
                row_z.append(round(v, 3))
                if i == 0 or cur is None:
                    row_t.append(f"{v:.2f}%")
                else:
                    delta = (v - cur) * 100
                    row_t.append(f"{v:.2f}%\n({delta:+.0f}bps)")
        z.append(row_z)
        text.append(row_t)
    y_labels = [f"{OIS_CB_FLAGS.get(cb, '')} {cb}" for cb in cbs]
    if all(all(v is None for v in row) for row in z):
        return _empty_fig("No OIS path data — connect Bloomberg and verify tickers")
    fig = go.Figure(go.Heatmap(
        z=z, x=col_labels, y=y_labels,
        colorscale=[[0, "#7C3AED"], [0.25, "#3B82F6"], [0.5, "#14B8A6"],
                    [0.75, "#EAB308"], [1, "#EF4444"]],
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=10, family=FONT_FAMILY),
        hovertemplate="<b>%{y}</b> · %{x}: %{z:.3f}%<extra></extra>",
        showscale=True,
        colorbar=dict(title=dict(text="Rate (%)", font=dict(size=10, family=FONT_FAMILY))),
    ))
    fig.update_layout(
        title=f"OIS Rate Path Matrix{_ind_tag(data)}",
        xaxis=dict(side="top", title=""),
    )
    return _dark(fig)


def build_ideas_summary_table(ideas: List[Dict]) -> html.Div:

    if not ideas:
        return html.Div()
    rows = []
    for idea in ideas:
        conv  = idea.get("conviction", "")
        direc = idea.get("direction", "")
        rows.append({
            "#":         idea.get("rank", "—"),
            "Idea":      idea.get("idea_name", "—"),
            "Country":   f"{FLAGS.get(idea.get('country',''), '')} {idea.get('country', '—')}",
            "Tenor":     idea.get("tenor", "—"),
            "Direction": direc,
            "Conviction": f"{CONV_BADGE.get(conv, '')} {conv}",
            "Outlook":   f"{OL_BADGE.get(idea.get('outlook',''), '')} {idea.get('outlook','')}",
            "Entry":     idea.get("entry_yield", "—"),
            "Target":    idea.get("take_profit_yield", "—"),
            "Stop":      idea.get("stop_loss_yield", "—"),
            "JPY Pickup (bps)": idea.get("hedged_pickup_bps", "—"),
            "Horizon":   idea.get("time_horizon", "—"),
        })
    return dash_table.DataTable(
        id="ideas-summary-dt",
        data=rows,
        columns=[{"name": c, "id": c} for c in rows[0].keys()],
        style_table={"overflowX": "auto", "backgroundColor": BG_DEEP,
                     "border": f"1px solid {BORDER}", "borderRadius": "6px"},
        style_cell={
            "backgroundColor": BG_DEEP, "color": TEXT,
            "border": f"1px solid {BORDER}",
            "fontFamily": FONT_FAMILY, "fontSize": "12px",
            "textAlign": "left", "padding": "8px 10px",
            "whiteSpace": "nowrap",
        },
        style_header={
            "backgroundColor": BG_CARD2, "color": ACCENT,
            "fontWeight": "bold", "border": f"1px solid {BORDER_LT}",
            "fontFamily": FONT_FAMILY, "fontSize": "11px",
            "textAlign": "center", "padding": "8px 10px",
        },
        style_cell_conditional=[
            {"if": {"column_id": "#"},              "width": "40px",  "textAlign": "center"},
            {"if": {"column_id": "Tenor"},          "width": "60px",  "textAlign": "center"},
            {"if": {"column_id": "Entry"},          "width": "70px",  "textAlign": "center"},
            {"if": {"column_id": "Target"},         "width": "70px",  "textAlign": "center"},
            {"if": {"column_id": "Stop"},           "width": "70px",  "textAlign": "center"},
            {"if": {"column_id": "JPY Pickup (bps)"},"width": "100px","textAlign": "center"},
            {"if": {"column_id": "Horizon"},        "width": "80px",  "textAlign": "center"},
        ],
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#0A0D14"},
            {"if": {"filter_query": '{Direction} contains "LONG"'},  "color": GREEN},
            {"if": {"filter_query": '{Direction} contains "SHORT"'}, "color": RED},
            {"if": {"filter_query": '{Conviction} contains "HIGH"'},
             "backgroundColor": "#0F2018", "borderLeft": f"3px solid {GREEN}"},
        ],
        sort_action="native",
    )


def build_ideas_datatable(ideas: List[Dict]) -> html.Div:

    if not ideas:
        return html.P("No ideas loaded yet.",
                      style={"color": TEXT_MUT, "padding": "30px", "textAlign": "center"})
    rows = []
    for idea in ideas:
        rows.append({
            "Rank":       idea.get("rank", "—"),
            "Idea":       idea.get("idea_name", "—"),
            "Country":    f"{FLAGS.get(idea.get('country',''), '')} {idea.get('country', '—')}",
            "Tenor":      idea.get("tenor", "—"),
            "Direction":  idea.get("direction", "—"),
            "Conv.":      f"{CONV_BADGE.get(idea.get('conviction',''), '')} {idea.get('conviction','')}",
            "Rationale":  idea.get("rationale", "—"),
            "Entry":      idea.get("entry_yield", "—"),
            "Stop Loss":  idea.get("stop_loss_yield", "—"),
            "Tgt Profit": idea.get("take_profit_yield", "—"),
            "JPY Pickup": idea.get("hedged_pickup_bps", "—"),
            "Horizon":    idea.get("time_horizon", "—"),
            "Key Risk":   idea.get("key_risks", "—"),
            "Cut Loss If": idea.get("stop_loss_triggers", "—"),
            "Take Profit If": idea.get("take_profit_triggers", "—"),
            "Outlook":    f"{OL_BADGE.get(idea.get('outlook',''), '')} {idea.get('outlook','')}",
        })
    # Column width config: commentary cols get more room
    COMMENTARY_COLS = {"Rationale", "Key Risk", "Cut Loss If", "Take Profit If"}
    NARROW_COLS     = {"Rank", "Tenor", "Conv.", "Outlook", "Horizon"}
    MEDIUM_COLS     = {"Idea", "Country", "Direction", "Entry", "Stop Loss", "Tgt Profit", "JPY Pickup"}
    col_widths = {}
    for c in rows[0].keys():
        if c in NARROW_COLS:
            col_widths[c] = {"minWidth": "70px",  "width": "80px",  "maxWidth": "100px"}
        elif c in MEDIUM_COLS:
            col_widths[c] = {"minWidth": "110px", "width": "130px", "maxWidth": "160px"}
        elif c in COMMENTARY_COLS:
            col_widths[c] = {"minWidth": "260px", "width": "300px", "maxWidth": "380px"}
        else:
            col_widths[c] = {"minWidth": "100px", "width": "120px", "maxWidth": "180px"}
    return dash_table.DataTable(
        id="ideas-dt",
        data=rows,
        columns=[{"name": c, "id": c, "presentation": "markdown"
                  if c in COMMENTARY_COLS else "input"}
                 for c in rows[0].keys()],
        style_table={"overflowX": "auto", "backgroundColor": BG_DEEP,
                     "border": f"1px solid {BORDER}", "borderRadius": "6px"},
        style_cell={
            "backgroundColor": BG_DEEP, "color": TEXT,
            "border": f"1px solid {BORDER}",
            "fontFamily": FONT_FAMILY, "fontSize": "13px",
            "textAlign": "left", "padding": "10px 12px",
            "whiteSpace": "normal", "height": "auto",
        },
        style_header={
            "backgroundColor": BG_CARD2, "color": ACCENT,
            "fontWeight": "bold", "border": f"1px solid {BORDER_LT}",
            "fontFamily": FONT_FAMILY, "fontSize": "12px",
            "textAlign": "center", "padding": "10px 12px",
            "whiteSpace": "normal",
        },
        style_cell_conditional=[
            {**{"if": {"column_id": c}}, **widths}
            for c, widths in col_widths.items()
        ],
        style_data_conditional=[
            {"if": {"row_index": "odd"},    "backgroundColor": "#0A0D14"},
            {"if": {"filter_query": '{Direction} contains "LONG"'},  "color": GREEN},
            {"if": {"filter_query": '{Direction} contains "SHORT"'}, "color": RED},
            {"if": {"filter_query": '{Outlook} contains "BULLISH"'}, "color": GREEN},
            {"if": {"filter_query": '{Outlook} contains "BEARISH"'}, "color": RED},
            {"if": {"filter_query": '{Conv.} contains "HIGH"'},
             "backgroundColor": "#0F2018", "borderLeft": f"3px solid {GREEN}"},
        ],
        tooltip_data=[{c: {"value": str(r.get(c, "")), "type": "text"} for c in r} for r in rows],
        tooltip_duration=None,
        page_size=8,
        sort_action="native",
        filter_action="native",
    )

# ==========================================================================
#  TICKER COVERAGE SUMMARY
# ==========================================================================


def print_data_coverage_summary(data: Dict) -> None:
    """
    After get_data(), print a grouped table of every ticker that returned no
    value. Compares each ticker definition dict against the populated data dict.
    Skips entirely when Bloomberg is not connected (nothing useful to report).
    """
    if not bbg.ok:
        return

    # Each entry: (category_label, description, bbg_ticker)
    missing: List[tuple] = []

    # ── Sovereign yields ──────────────────────────────────────────────────
    for tenor, tmap in YIELD_TICKERS.items():
        for country, tkr in tmap.items():
            if data.get("yields", {}).get(tenor, {}).get(country) is None:
                missing.append((f"Yields {tenor}", country, tkr))

    # ── Macro indicators ─────────────────────────────────────────────────
    for indicator, tmap in MACRO_TICKERS.items():
        for country, tkr in tmap.items():
            if data.get("macro", {}).get(indicator, {}).get(country) is None:
                missing.append((f"Macro {indicator}", country, tkr))

    # ── FX rates ──────────────────────────────────────────────────────────
    for pair, tkr in FX_TICKERS.items():
        if data.get("fx", {}).get(pair) is None:
            missing.append(("FX", pair, tkr))

    # ── JPY hedge costs (one entry per foreign 3M rate) ──────────────────
    for country, tkr in JPY_HEDGE_COST_TICKERS.items():
        if data.get("hedge_costs", {}).get(country) is None:
            missing.append(("JPY Hedge Cost", country, tkr))

    # ── SGD hedge costs ───────────────────────────────────────────────────
    for country, tkr in SGD_HEDGE_COST_TICKERS.items():
        if data.get("sgd_hedge_costs", {}).get(country) is None:
            missing.append(("SGD Hedge Cost", country, tkr))

    # ── Real yields (TIPS / linkers) ──────────────────────────────────────
    for tenor, tmap in REAL_YIELD_TICKERS.items():
        for country, tkr in tmap.items():
            if data.get("real_yields", {}).get(tenor, {}).get(country) is None:
                missing.append((f"Real Yield {tenor}", country, tkr))

    # ── Inflation swaps ───────────────────────────────────────────────────
    for tenor, tmap in INFL_SWAP_TICKERS.items():
        for region, tkr in tmap.items():
            if data.get("infl_swaps", {}).get(tenor, {}).get(region) is None:
                missing.append((f"Infl Swap {tenor}", region, tkr))

    # ── Fiscal balance % GDP ──────────────────────────────────────────────
    for country, tkr in FISCAL_GDP_TICKERS.items():
        if data.get("fiscal_gdp", {}).get(country) is None:
            missing.append(("Fiscal / GDP", country, tkr))

    # ── Government debt % GDP ─────────────────────────────────────────────
    for country, tkr in DEBT_GDP_TICKERS.items():
        if data.get("debt_gdp", {}).get(country) is None:
            missing.append(("Debt / GDP", country, tkr))

    # ── OIS policy path ───────────────────────────────────────────────────
    for cb, tenor_map in OIS_PATH_TICKERS.items():
        for tenor, tkr in tenor_map.items():
            if data.get("ois_path", {}).get(cb, {}).get(tenor) is None:
                missing.append((f"OIS Path {cb}", tenor, tkr))

    # ── Print results ─────────────────────────────────────────────────────
    sep = "=" * 72
    print(f"\n{sep}")
    if not missing:
        print("  ✅  All tickers returned data successfully.")
        print(sep)
        return

    print(f"  ⚠️   TICKER FETCH ERRORS — {len(missing)} ticker(s) returned no data")
    print(sep)
    col_w = (22, 28, 30)
    header = (
        f"  {'Category':<{col_w[0]}} {'Key':<{col_w[1]}} {'BBG Ticker':<{col_w[2]}}"
    )
    print(header)
    print(f"  {'-' * col_w[0]} {'-' * col_w[1]} {'-' * col_w[2]}")
    last_cat = None
    for cat, key, tkr in sorted(missing, key=lambda x: x[0]):
        # Blank line between category groups for readability
        if last_cat is not None and cat != last_cat:
            print()
        print(f"  {cat:<{col_w[0]}} {key:<{col_w[1]}} {tkr:<{col_w[2]}}")
        last_cat = cat
    print(sep + "\n")


# ==========================================================================
#  APP LAYOUT
# ==========================================================================

INITIAL_DATA    = get_data()
print_data_coverage_summary(INITIAL_DATA)
MACRO_HISTORY   = fetch_macro_history_bbg(lookback_years=50)
INITIAL_ZSCORES = compute_zscores(INITIAL_DATA, MACRO_HISTORY)

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.SLATE,
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&display=swap",
    ],
    title="FI Dashboard | Global Multi Asset",
    suppress_callback_exceptions=True,
)


def kpi_card(label: str, value: str, sub: str = "",

             color: str = ACCENT, border_color: str = BORDER) -> html.Div:
    return html.Div(
        style={
            "backgroundColor": BG_CARD,
            "border": f"1px solid {border_color}",
            "borderTop": f"3px solid {color}",
            "borderRadius": "4px",
            "padding": "10px 14px",
        },
        children=[
            html.Div(label, style={"color": TEXT_MUT, "fontSize": "9px",
                                    "letterSpacing": "0.12em", "textTransform": "uppercase",
                                    "fontFamily": FONT_FAMILY}),
            html.Div(value, style={"color": color, "fontSize": "20px",
                                    "fontWeight": "600", "marginTop": "2px",
                                    "fontFamily": FONT_FAMILY}),
            html.Div(sub, style={"color": TEXT_MUT, "fontSize": "9px",
                                  "marginTop": "2px", "fontFamily": FONT_FAMILY}),
        ],
    )


def build_kpi_row(data: Dict) -> dbc.Row:

    y10  = data["yields"].get("10Y", {})
    m    = data["macro"]
    jgb     = y10.get("Japan")
    italy   = y10.get("Italy")
    germany = y10.get("Germany")
    us      = y10.get("US")
    uk      = y10.get("UK")
    boj_rate = m.get("POLICY_RATE", {}).get("Japan")
    ecb_rate = m.get("POLICY_RATE", {}).get("ECB")
    btp_bund = round((italy - germany) * 100, 0) if (italy is not None and germany is not None) else None
    us_jgb   = round((us - jgb) * 100, 0) if (us is not None and jgb is not None) else None
    usdjpy   = data["fx"].get("USDJPY")
    us_hy    = data["hedged_10y"].get("US")
    us_sl    = data["slopes"].get("US")
    rate_cycle_jp = data["rate_cycle"].get("Japan", "")
    return dbc.Row([
        dbc.Col(kpi_card("🇯🇵 JGB 10Y",   f"{_fmt(jgb, '.2f')}%",
                          f"BOJ: {_fmt(boj_rate, '.2f')}%  {rate_cycle_jp}",
                          color=TEAL), width=2),
        dbc.Col(kpi_card("🇺🇸 UST 10Y",   f"{_fmt(us, '.2f')}%",
                          f"2s10s: {_fmt(us_sl, '+.2f')}%  |  Hedged: {_fmt(us_hy, '.2f')}%",
                          color=CCOLORS["US"]), width=2),
        dbc.Col(kpi_card("🇩🇪 Bund 10Y",  f"{_fmt(germany, '.2f')}%",
                          f"ECB: {_fmt(ecb_rate, '.2f')}%"), width=2),
        dbc.Col(kpi_card("🇬🇧 Gilt 10Y",  f"{_fmt(uk, '.2f')}%",
                          f"2s10s: {_fmt(data['slopes'].get('UK'), '+.2f')}%"), width=2),
        dbc.Col(kpi_card("BTP-Bund Spread", f"{_fmt(btp_bund, '.0f')} bps",
                          "Italy–Germany 10Y", color=YELLOW,
                          border_color=YELLOW if (btp_bund is not None and btp_bund > 150) else BORDER), width=2),
        dbc.Col(kpi_card("USDJPY",          f"{_fmt(usdjpy, '.1f')}",
                          f"US-JP 10Y: {_fmt(us_jgb, '+.0f')} bps",
                          color=CCOLORS["Japan"]), width=2),
    ], className="g-2 mb-3")

# ── Shared controls ───────────────────────────────────────────────────────

def country_checklist(id_prefix: str) -> dbc.Checklist:

    return dbc.Checklist(
        id=f"{id_prefix}-countries",
        options=[{"label": f"{FLAGS.get(c,'')} {c}", "value": c} for c in COUNTRIES],
        value=COUNTRIES, inline=True,
        inputClassName="me-1",
        labelStyle={"marginRight": "10px", "fontSize": "11px",
                    "color": TEXT, "fontFamily": FONT_FAMILY},
    )


def tenor_group(id_prefix: str, default: str = "10Y") -> dbc.ButtonGroup:

    tenors = ["2Y", "5Y", "10Y", "30Y"]
    return dbc.ButtonGroup([
        dbc.Button(t,
                   id=f"{id_prefix}-{t.lower()}",
                   n_clicks=1 if t == default else 0,
                   color="primary" if t == default else "outline-primary",
                   size="sm", className="px-3")
        for t in tenors
    ])


def hist_group(id_prefix: str) -> dbc.ButtonGroup:

    return dbc.ButtonGroup([
        dbc.Button("1Y", id=f"{id_prefix}-hist-1y", n_clicks=0,
                   color="outline-secondary", size="sm", className="px-3"),
        dbc.Button("2Y", id=f"{id_prefix}-hist-2y", n_clicks=1,
                   color="secondary",         size="sm", className="px-3"),
        dbc.Button("5Y", id=f"{id_prefix}-hist-5y", n_clicks=0,
                   color="outline-secondary", size="sm", className="px-3"),
    ])

# ─ style helpers ─────────────────────────────────────────────────────────
CARD_STYLE  = {"backgroundColor": BG_CARD, "border": f"1px solid {BORDER}",
               "borderRadius": "6px", "marginBottom": "8px"}
GRAPH_CFG   = {"displayModeBar": False}
SEC_TITLE   = lambda t, s="": html.Div([
    html.H6(t, style={"color": ACCENT, "fontFamily": FONT_FAMILY, "marginBottom": "2px",
                       "fontWeight": "600", "fontSize": "12px", "letterSpacing": "0.05em"}),
    html.P(s,  style={"color": TEXT_MUT, "fontSize": "10px", "marginBottom": "8px",
                       "fontFamily": FONT_FAMILY}) if s else html.Span(),
])


def _safe_ideas(data: Dict) -> List[Dict]:

    """Wrap generate_ideas_from_data so a Bloomberg failure returns an empty list."""
    try:
        return generate_ideas_from_data(data)
    except Exception as e:
        print(f"  ⚠️  generate_ideas_from_data failed: {e}")
        return []


def _safe_spread_panel(data: Dict):

    """Wrap _spread_summary_panel; return a plain N/A div on failure."""
    try:
        return _spread_summary_panel(data)
    except Exception as e:
        print(f"  ⚠️  _spread_summary_panel failed: {e}")
        return html.Div("Spread data unavailable (N/A)",
                        style={"color": TEXT_MUT, "fontFamily": FONT_FAMILY,
                               "padding": "12px", "fontSize": "12px"})

# ==========================================================================
#  MACRO SURPRISE + MULTI-SIGNAL SCORECARD
# ==========================================================================

# CB inflation targets (%)
CB_INFLATION_TARGETS = {
    "US": 2.0, "UK": 2.0, "Germany": 2.0, "France": 2.0, "Italy": 2.0,
    "Japan": 2.0, "Australia": 2.5, "Canada": 2.0, "Singapore": 2.0,
}

# Country → OIS CB key (None = no OIS data)
_COUNTRY_TO_CB = {
    "US": "US", "UK": "UK", "Australia": "Australia",
    "Japan": "Japan", "Canada": "Canada",
    "Germany": "ECB", "France": "ECB", "Italy": "ECB",
    "Singapore": None,
}


def _score_label(s: int) -> str:
    """Convert integer score to ▲▼ label string."""
    if s >= 2:   return f"+{s} ▲▲"
    if s == 1:   return f"+{s} ▲"
    if s == 0:   return " 0 —"
    if s == -1:  return f"{s} ▼"
    return f"{s} ▼▼"


def _score_color(s) -> str:
    if not isinstance(s, (int, float)):
        return TEXT_MUT
    if s >= 2:   return GREEN
    if s == 1:   return "#86EFAC"
    if s == 0:   return TEXT_MUT
    if s == -1:  return "#FCA5A5"
    return RED


def compute_macro_surprise(data: Dict) -> Dict:
    """
    Per-country macro surprise scores for bond investors:
      CPI vs CB target  → negative deviation = dovish = bullish bonds (+2 to -2)
      PMI vs 50         → contraction = cuts expected = bullish bonds (+2 to -2)
    Returns {country: {cpi, target, cpi_dev, cpi_score, pmi, pmi_score, macro_score}}
    """
    results = {}
    macro = data["macro"]
    for country in COUNTRIES:
        cpi    = _get_cpi(macro, country)
        pmi    = macro.get("PMI_MFG", {}).get(country)
        target = CB_INFLATION_TARGETS.get(country, 2.0)
        cpi_dev, cpi_score = None, 0
        if cpi is not None:
            cpi_dev = round(cpi - target, 2)
            if cpi_dev < -0.5:   cpi_score = +2
            elif cpi_dev < 0.0:  cpi_score = +1
            elif cpi_dev < 0.5:  cpi_score =  0
            elif cpi_dev < 1.5:  cpi_score = -1
            else:                cpi_score = -2
        pmi_score = 0
        if pmi is not None:
            if pmi < 47:         pmi_score = +2
            elif pmi < 50:       pmi_score = +1
            elif pmi <= 50.5:    pmi_score =  0
            elif pmi < 52:       pmi_score = -1
            else:                pmi_score = -2
        results[country] = {
            "cpi": cpi, "target": target, "cpi_dev": cpi_dev,
            "cpi_score": cpi_score,
            "pmi": pmi, "pmi_score": pmi_score,
            "macro_score": cpi_score + pmi_score,
        }
    return results


def compute_multi_signal_scorecard(data: Dict, hedge_base: str = "unhedged") -> List[Dict]:
    """
    Five-signal conviction scorecard per country (each signal –2 to +2):
      1. CPI surprise  — CPI vs CB target
      2. PMI signal    — PMI vs 50
      3. Yield z-score — 10Y yield cheap/rich vs 5Y history
      4. Policy path   — OIS-implied 12M rate change
      5. Carry rank    — 10Y carry+roll vs peers, adjusted for hedge_base
    Total range: –10 to +10
    """
    macro_surp = compute_macro_surprise(data)
    macro      = data["macro"]
    ois_path   = data.get("ois_path", {})
    y10        = data["yields"].get("10Y", {})

    # ── Signal 3: yield z-score vs 5Y history ─────────────────────────────
    hist_df = get_hist_df("10Y", days=1260)
    yield_z = {}
    for c in COUNTRIES:
        yld = y10.get(c)
        if yld is None or hist_df.empty or c not in hist_df.columns:
            yield_z[c] = None; continue
        h = hist_df[c].dropna()
        if len(h) < 20:
            yield_z[c] = None; continue
        mu, sigma = h.mean(), h.std()
        yield_z[c] = round((yld - mu) / sigma, 2) if sigma > 0 else 0.0

    # ── Signal 4: OIS policy path — implied 12M rate change (bps) ─────────
    policy_delta = {}
    for c in COUNTRIES:
        cb = _COUNTRY_TO_CB.get(c)
        if cb is None:
            policy_delta[c] = None; continue
        ois_12m = ois_path.get(cb, {}).get("12M")
        rate    = _get_rate(macro, c)
        if ois_12m is None or rate is None:
            policy_delta[c] = None; continue
        policy_delta[c] = round((ois_12m - rate) * 100, 1)

    # ── Signal 5: carry rank quintiles (hedge-adjusted) ───────────────────
    carry_rows = compute_carry_rolldown(data, hedge_base)
    carry_10y  = {r["Country"]: r["_total_sort"]
                  for r in carry_rows if r["Tenor"] == "10Y"
                  and isinstance(r["_total_sort"], (int, float))}
    sorted_carry = sorted(carry_10y.items(), key=lambda x: x[1], reverse=True)
    n = len(sorted_carry)
    carry_rank = {c: i for i, (c, _) in enumerate(sorted_carry)}  # 0 = best

    def _carry_score(c):
        if c not in carry_rank or n == 0:
            return 0
        r = carry_rank[c]
        if r < n * 0.2:    return +2
        if r < n * 0.4:    return +1
        if r < n * 0.6:    return  0
        if r < n * 0.8:    return -1
        return -2

    rows = []
    for country in COUNTRIES:
        ms  = macro_surp.get(country, {})
        cpi_sc  = ms.get("cpi_score", 0)
        pmi_sc  = ms.get("pmi_score", 0)
        yz      = yield_z.get(country)
        ps      = policy_delta.get(country)
        carry_v = carry_10y.get(country)

        # Yield z-score → score
        yz_score = 0
        if yz is not None:
            if yz > 1.5:     yz_score = +2
            elif yz > 0.5:   yz_score = +1
            elif yz > -0.5:  yz_score =  0
            elif yz > -1.5:  yz_score = -1
            else:            yz_score = -2

        # Policy path → score (negative delta = cuts = bullish)
        ps_score = 0
        if ps is not None:
            if ps < -50:    ps_score = +2
            elif ps < -10:  ps_score = +1
            elif ps < 10:   ps_score =  0
            elif ps < 25:   ps_score = -1
            else:           ps_score = -2

        carry_sc = _carry_score(country)
        total    = cpi_sc + pmi_sc + yz_score + ps_score + carry_sc

        rows.append({
            "country":         country,
            "flag":            FLAGS.get(country, ""),
            "cpi":             ms.get("cpi"),
            "cpi_dev":         ms.get("cpi_dev"),
            "cpi_score":       cpi_sc,
            "pmi":             ms.get("pmi"),
            "pmi_score":       pmi_sc,
            "yield_z":         yz,
            "yz_score":        yz_score,
            "policy_delta":    ps,
            "ps_score":        ps_score,
            "carry_1y":        round(carry_v, 0) if carry_v is not None else None,
            "carry_score":     carry_sc,
            "total":           total,
        })

    rows.sort(key=lambda r: r["total"], reverse=True)
    return rows


def _conviction_badge(total: int) -> str:
    if total >= 6:   return "STRONG BUY"
    if total >= 3:   return "BUY"
    if total >= 1:   return "MILD BUY"
    if total == 0:   return "NEUTRAL"
    if total >= -2:  return "MILD SELL"
    if total >= -5:  return "SELL"
    return "STRONG SELL"


def _conviction_color(total: int) -> str:
    if total >= 3:   return GREEN
    if total >= 1:   return "#86EFAC"
    if total == 0:   return TEXT_MUT
    if total >= -2:  return "#FCA5A5"
    return RED


def build_macro_surprise_panel(data: Dict) -> html.Div:
    """
    Table: country × (CPI, target, deviation, CPI score, PMI, PMI score, macro score).
    Color-coded by score direction.
    """
    ms = compute_macro_surprise(data)
    rows = []
    for c in COUNTRIES:
        d = ms.get(c, {})
        cpi_dev = d.get("cpi_dev")
        cpi_sc  = d.get("cpi_score", 0)
        pmi_sc  = d.get("pmi_score", 0)
        mac_sc  = d.get("macro_score", 0)
        rows.append({
            "Country":     f"{FLAGS.get(c,'')} {c}",
            "CPI (%)":     f"{d['cpi']:.1f}" if d.get("cpi") is not None else "N/A",
            "Target (%)":  f"{d['target']:.1f}",
            "CPI Dev (pp)": f"{cpi_dev:+.2f}" if cpi_dev is not None else "N/A",
            "CPI Signal":  _score_label(cpi_sc),
            "PMI":         f"{d['pmi']:.1f}" if d.get("pmi") is not None else "N/A",
            "PMI Signal":  _score_label(pmi_sc),
            "Macro Score": f"{mac_sc:+d}",
            "_cpi_sc":  cpi_sc,
            "_pmi_sc":  pmi_sc,
            "_mac_sc":  mac_sc,
        })
    rows.sort(key=lambda r: r["_mac_sc"], reverse=True)

    DISP = ["Country", "CPI (%)", "Target (%)", "CPI Dev (pp)",
            "CPI Signal", "PMI", "PMI Signal", "Macro Score"]
    style_cond = []
    for i, r in enumerate(rows):
        for col, sc_key in [("CPI Signal", "_cpi_sc"),
                             ("PMI Signal", "_pmi_sc"),
                             ("Macro Score", "_mac_sc")]:
            clr = _score_color(r[sc_key])
            style_cond.append({"if": {"row_index": i, "column_id": col},
                                "color": clr, "fontWeight": "600"})

    return dash_table.DataTable(
        data=[{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
        columns=[{"name": c, "id": c} for c in DISP],
        style_table={"overflowX": "auto", "backgroundColor": BG_DEEP,
                     "border": f"1px solid {BORDER}", "borderRadius": "6px"},
        style_cell={"backgroundColor": BG_DEEP, "color": TEXT,
                    "border": f"1px solid {BORDER}",
                    "fontFamily": FONT_FAMILY, "fontSize": "12px",
                    "textAlign": "center", "padding": "8px 10px"},
        style_header={"backgroundColor": BG_CARD2, "color": ACCENT,
                      "fontWeight": "bold", "border": f"1px solid {BORDER_LT}",
                      "fontFamily": FONT_FAMILY, "fontSize": "11px",
                      "textAlign": "center", "padding": "8px 10px"},
        style_data_conditional=style_cond,
        page_size=len(rows),
    )


def build_scorecard_panel(data: Dict, hedge_base: str = "unhedged") -> html.Div:
    """
    Left: signal-breakdown table (one row per country, sorted by total).
    Right: horizontal bar chart ranked by total conviction score.
    """
    sc_rows = compute_multi_signal_scorecard(data, hedge_base)
    if not sc_rows:
        return html.P("No data.", style={"color": TEXT_MUT})

    DISP_COLS = ["Country", "CPI Sig", "PMI Sig",
                 "Yield Z Sig", "Path Sig", "Carry Sig", "Total", "View"]
    tbl_data, style_cond = [], []
    for i, r in enumerate(sc_rows):
        total = r["total"]
        badge = _conviction_badge(total)
        tbl_data.append({
            "Country":     f"{r['flag']} {r['country']}",
            "CPI Sig":     _score_label(r["cpi_score"]),
            "PMI Sig":     _score_label(r["pmi_score"]),
            "Yield Z Sig": (_score_label(r["yz_score"])
                            + (f"  ({r['yield_z']:+.2f}σ)" if r["yield_z"] is not None else "")),
            "Path Sig":    (_score_label(r["ps_score"])
                            + (f"  ({r['policy_delta']:+.0f}bps)" if r["policy_delta"] is not None else "")),
            "Carry Sig":   (_score_label(r["carry_score"])
                            + (f"  ({r['carry_1y']:+.0f}bps)" if r["carry_1y"] is not None else "")),
            "Total":       f"{total:+d}",
            "View":        badge,
        })
        tc = _conviction_color(total)
        style_cond += [
            {"if": {"row_index": i, "column_id": "Total"}, "color": tc, "fontWeight": "700"},
            {"if": {"row_index": i, "column_id": "View"},  "color": tc, "fontWeight": "600"},
        ]
        for col, sc_key in [("CPI Sig", "cpi_score"), ("PMI Sig", "pmi_score"),
                             ("Yield Z Sig", "yz_score"), ("Path Sig", "ps_score"),
                             ("Carry Sig", "carry_score")]:
            style_cond.append({"if": {"row_index": i, "column_id": col},
                                "color": _score_color(r[sc_key])})

    table = dash_table.DataTable(
        data=tbl_data,
        columns=[{"name": c, "id": c} for c in DISP_COLS],
        style_table={"overflowX": "auto", "backgroundColor": BG_DEEP,
                     "border": f"1px solid {BORDER}", "borderRadius": "6px"},
        style_cell={"backgroundColor": BG_DEEP, "color": TEXT,
                    "border": f"1px solid {BORDER}",
                    "fontFamily": FONT_FAMILY, "fontSize": "12px",
                    "textAlign": "center", "padding": "8px 10px"},
        style_header={"backgroundColor": BG_CARD2, "color": ACCENT,
                      "fontWeight": "bold", "border": f"1px solid {BORDER_LT}",
                      "fontFamily": FONT_FAMILY, "fontSize": "11px",
                      "textAlign": "center", "padding": "8px 10px"},
        style_data_conditional=style_cond,
        page_size=len(tbl_data),
    )

    # ── Conviction bar chart ───────────────────────────────────────────────
    labels = [f"{r['flag']} {r['country']}" for r in sc_rows]
    totals = [r["total"] for r in sc_rows]
    colors = [_conviction_color(t) for t in totals]
    fig = go.Figure(go.Bar(
        y=labels, x=totals,
        orientation="h",
        marker_color=colors,
        text=[f"{t:+d}  {_conviction_badge(t)}" for t in totals],
        textposition="outside",
        textfont=dict(size=10, family=FONT_FAMILY, color=TEXT),
        hovertemplate="<b>%{y}</b><br>Score: %{x:+d}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color=BORDER_LT, line_width=1)
    fig.update_layout(
        title="Conviction Ranking (–10 to +10)",
        xaxis=dict(range=[-11, 14], zeroline=False,
                   tickfont=dict(size=9, family=FONT_FAMILY)),
        yaxis=dict(autorange="reversed",
                   tickfont=dict(size=11, family=FONT_FAMILY)),
        height=320, margin=dict(l=20, r=120, t=40, b=20),
    )

    return html.Div([
        dbc.Row([
            dbc.Col(table, width=8),
            dbc.Col(dcc.Graph(figure=_dark(fig), config=GRAPH_CFG), width=4),
        ]),
    ])


# ==========================================================================
#  CARRY / ROLL-DOWN TABLE
# ==========================================================================

# Approximate par-bond modified durations for screening purposes
_CARRY_DUR = {"2Y": 1.9, "5Y": 4.4, "10Y": 8.2, "30Y": 18.5}


def compute_carry_rolldown(data: Dict, hedge_base: str = "unhedged") -> List[Dict]:
    """
    For each country × tenor compute:
      • Carry (bps)        = yield × 100  (unhedged)
                             or (yield + hedge_cost) × 100  (JPY / SGD hedged)
      • Roll-down Δy (bps) = yield drop as bond ages 1Y along the curve
                             (roll-down is yield-curve arithmetic — unaffected by hedging)
      • Roll Return (bps)  = approx_duration × roll_Δy_in_pct × 100
      • Total 1Y (bps)     = Carry + Roll Return

    hedge_base: "unhedged" | "jpy" | "sgd"
    """
    # Hedge cost dicts: country → cost in same % units as yields (can be negative)
    # The base-currency country has a hedge cost of 0 (no FX hedge needed for domestic bonds)
    if hedge_base == "jpy":
        hcosts   = data.get("hedge_costs", {})
        zero_hc  = {"Japan"}        # JPY investor in JGBs: hedge cost = 0
    elif hedge_base == "sgd":
        hcosts   = data.get("sgd_hedge_costs", {})
        zero_hc  = {"Singapore"}    # SGD investor in SGS: hedge cost = 0
    else:
        hcosts   = {}
        zero_hc  = set()

    rows = []
    tenors = ["2Y", "5Y", "10Y", "30Y"]
    for country in COUNTRIES:

        y = {}
        for t in tenors:
            val = data["yields"].get(t, {}).get(country)
            y[t] = float(val) if val is not None else None

        if all(v is None for v in y.values()):
            continue

        ynum = {2: y["2Y"], 5: y["5Y"], 10: y["10Y"], 30: y["30Y"]}

        def interp(n_lo, n_hi, n_target):
            lo, hi = ynum.get(n_lo), ynum.get(n_hi)
            if lo is None or hi is None:
                return None
            return lo + (n_target - n_lo) / (n_hi - n_lo) * (hi - lo)

        y_aged = {
            "2Y":  (y["2Y"] - (y["5Y"] - y["2Y"]) / 3.0
                    if y["2Y"] is not None and y["5Y"] is not None else None),
            "5Y":  interp(2,  5,   4),
            "10Y": interp(5,  10,  9),
            "30Y": interp(10, 30, 29),
        }

        # Per-country hedge cost (same for all tenors — it's a 3M FX hedge)
        # Base-currency country (e.g. Japan in JPY mode) has zero hedge cost by definition
        if country in zero_hc:
            hc_pct = 0.0
        else:
            hc_pct = hcosts.get(country)      # None when unhedged or BBG unavailable
        hc_bps = round(hc_pct * 100, 1) if hc_pct is not None else None

        for tenor in tenors:
            yld = y[tenor]
            if yld is None:
                continue
            dur = _CARRY_DUR[tenor]

            # Carry: apply hedge cost if available, otherwise fall back to gross
            if hc_pct is not None:
                carry_bps = round((yld + hc_pct) * 100, 1)
            else:
                carry_bps = round(yld * 100, 1)

            aged = y_aged[tenor]
            if aged is not None:
                roll_dy_pct  = yld - aged
                roll_dy_bps  = round(roll_dy_pct * 100, 1)
                roll_ret_bps = round(dur * roll_dy_pct * 100, 1)
            else:
                roll_dy_bps = roll_ret_bps = None

            total_bps = (round(carry_bps + roll_ret_bps, 1)
                         if roll_ret_bps is not None else None)

            row = {
                "Flag":           FLAGS.get(country, ""),
                "Country":        country,
                "Tenor":          tenor,
                "Yield (%)":      round(yld, 3),
                "Carry (bps)":    carry_bps,
                "Roll Δy (bps)":  roll_dy_bps  if roll_dy_bps  is not None else "N/A",
                "Roll Ret (bps)": roll_ret_bps if roll_ret_bps is not None else "N/A",
                "Total 1Y (bps)": total_bps    if total_bps    is not None else "N/A",
                "_total_sort":    total_bps    if total_bps    is not None else -9999,
            }
            if hedge_base != "unhedged":
                row["Hedge Cost (bps)"] = hc_bps if hc_bps is not None else "N/A"
            rows.append(row)

    rows.sort(key=lambda r: r["_total_sort"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["Rank"] = i
    return rows


def build_carry_charts_panel(data: Dict, hedge_base: str = "unhedged") -> html.Div:
    """
    Returns the two carry/roll-down bar charts:
      • Grouped by Country (tenor = series)
      • Grouped by Tenor (sorted descending within each group)
    """
    rows = compute_carry_rolldown(data, hedge_base)
    if not rows:
        return html.P("No yield data — connect Bloomberg.",
                      style={"color": TEXT_MUT, "fontFamily": FONT_FAMILY,
                             "padding": "20px", "textAlign": "center"})

    _hlabel = {"jpy": " — JPY Hedged", "sgd": " — SGD Hedged"}.get(hedge_base, "")

    # ── Chart 1: grouped by country (tenor = series) ─────────────────────
    tenor_order = ["2Y", "5Y", "10Y", "30Y"]
    fig1 = go.Figure()
    bar_colors = {"2Y": "#60A5FA", "5Y": "#34D399", "10Y": "#FBBF24", "30Y": "#F87171"}
    for tenor in tenor_order:
        tenor_rows = [r for r in rows if r["Tenor"] == tenor
                      and isinstance(r["_total_sort"], (int, float))]
        tenor_rows_sorted = sorted(tenor_rows, key=lambda r: r["_total_sort"], reverse=True)
        fig1.add_trace(go.Bar(
            name=tenor,
            x=[f"{r['Flag']} {r['Country']}" for r in tenor_rows_sorted],
            y=[r["_total_sort"] for r in tenor_rows_sorted],
            marker_color=bar_colors[tenor],
            text=[f"{r['_total_sort']:.0f}" for r in tenor_rows_sorted],
            textposition="outside",
            textfont=dict(size=9, family=FONT_FAMILY),
        ))
    fig1.update_layout(
        title=f"Grouped by Country{_hlabel}",
        barmode="group", yaxis_title="bps",
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=9,
                    family=FONT_FAMILY)),
        height=300, margin=dict(t=50, b=40),
    )

    # ── Chart 2: tenor groups, sorted descending within each group ───────
    # Insert GAP_WIDTH empty slots between tenor groups so they visually
    # separate without needing separator lines.
    GAP_WIDTH = 2
    x_idx, y_vals2, bar_clrs2, tick_txt, bar_txt2, hover_txt2 = [], [], [], [], [], []
    shapes, annotations2 = [], []
    cursor = 0
    for i, tenor in enumerate(tenor_order):
        tenor_rows = [r for r in rows if r["Tenor"] == tenor
                      and isinstance(r["_total_sort"], (int, float))]
        sorted_grp = sorted(tenor_rows, key=lambda r: r["_total_sort"], reverse=True)
        n = len(sorted_grp)
        # Tenor label centred over the group
        annotations2.append(dict(
            x=cursor + (n - 1) / 2, y=1.03,
            xref="x", yref="paper",
            text=f"<b>{tenor}</b>",
            showarrow=False,
            font=dict(size=11, color=ACCENT, family=FONT_FAMILY),
        ))
        for r in sorted_grp:
            x_idx.append(cursor)
            y_vals2.append(r["_total_sort"])
            bar_clrs2.append(CCOLORS.get(r["Country"], TEXT_MUT))
            tick_txt.append(f"{r['Flag']} {r['Country']}")
            bar_txt2.append(f"{r['_total_sort']:.0f}")
            hover_txt2.append(
                f"<b>{r['Flag']} {r['Country']} {r['Tenor']}</b><br>"
                f"Total 1Y: {r['_total_sort']:.0f} bps<extra></extra>"
            )
            cursor += 1
        # Advance cursor by GAP_WIDTH before next group (skip last)
        if i < len(tenor_order) - 1:
            cursor += GAP_WIDTH

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=x_idx, y=y_vals2,
        marker_color=bar_clrs2,
        text=bar_txt2, textposition="outside",
        textfont=dict(size=9, family=FONT_FAMILY),
        showlegend=False,
        hovertemplate=hover_txt2,
    ))
    # Dummy traces for country legend
    for country in COUNTRIES:
        if any(r["Country"] == country for r in rows):
            fig2.add_trace(go.Bar(
                x=[None], y=[None],
                name=f"{FLAGS.get(country,'')} {country}",
                marker_color=CCOLORS.get(country, TEXT_MUT),
                showlegend=True,
            ))

    fig2.update_layout(
        title=f"Grouped by Tenor{_hlabel}  (sorted descending within each group)",
        yaxis_title="bps",
        xaxis=dict(
            tickmode="array", tickvals=x_idx, ticktext=tick_txt,
            tickangle=-35, tickfont=dict(size=9, family=FONT_FAMILY),
            range=[-0.5, cursor - GAP_WIDTH - 0.5],
        ),
        annotations=annotations2,
        legend=dict(orientation="h", y=1.08, x=0,
                    font=dict(size=9, family=FONT_FAMILY)),
        height=300, margin=dict(t=50, b=40),
        barmode="relative",
    )

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_dark(fig1), config=GRAPH_CFG), width=6),
            dbc.Col(dcc.Graph(figure=_dark(fig2), config=GRAPH_CFG), width=6),
        ]),
    ])


def build_carry_rolldown_panel(data: Dict, hedge_base: str = "unhedged") -> html.Div:
    """Returns the ranked carry/roll-down DataTable (no charts)."""
    rows = compute_carry_rolldown(data, hedge_base)
    if not rows:
        return html.P("No yield data — connect Bloomberg.",
                      style={"color": TEXT_MUT, "fontFamily": FONT_FAMILY,
                             "padding": "20px", "textAlign": "center"})

    base_cols = ["Rank", "Country", "Tenor", "Yield (%)"]
    if hedge_base != "unhedged":
        base_cols.append("Hedge Cost (bps)")
    base_cols += ["Carry (bps)", "Roll Δy (bps)", "Roll Ret (bps)", "Total 1Y (bps)"]
    display_cols = base_cols
    tbl_rows = [{c: (f"{r['Flag']} {r['Country']}" if c == "Country" else r.get(c, "N/A"))
                 for c in display_cols}
                for r in rows]

    total_vals = [r["_total_sort"] for r in rows]
    v_max = max(total_vals) if total_vals else 1
    v_min = min(total_vals) if total_vals else 0

    def _cell_color(val):
        if not isinstance(val, (int, float)):
            return {}
        rng = max(v_max - v_min, 1)
        norm = (val - v_min) / rng
        if norm >= 0.6:
            return {"backgroundColor": "rgba(34,197,94,0.18)", "color": GREEN}
        if norm <= 0.25:
            return {"backgroundColor": "rgba(239,68,68,0.15)", "color": RED}
        return {}

    style_data_cond = []
    for i, r in enumerate(rows):
        clr = _cell_color(r["_total_sort"])
        if clr:
            style_data_cond.append({
                "if": {"row_index": i, "column_id": "Total 1Y (bps)"},
                **clr,
            })
        roll = r.get("Roll Δy (bps)")
        if isinstance(roll, (int, float)):
            roll_clr = ({"backgroundColor": "rgba(34,197,94,0.10)", "color": GREEN}
                        if roll >= 0
                        else {"backgroundColor": "rgba(239,68,68,0.10)", "color": RED})
            style_data_cond.append({
                "if": {"row_index": i, "column_id": "Roll Δy (bps)"},
                **roll_clr,
            })

    table = dash_table.DataTable(
        data=tbl_rows,
        columns=[{"name": c, "id": c} for c in display_cols],
        sort_action="native",
        style_table={"overflowX": "auto", "backgroundColor": BG_DEEP,
                     "border": f"1px solid {BORDER}", "borderRadius": "6px"},
        style_cell={
            "backgroundColor": BG_DEEP, "color": TEXT,
            "border": f"1px solid {BORDER}",
            "fontFamily": FONT_FAMILY, "fontSize": "12px",
            "textAlign": "center", "padding": "8px 10px",
        },
        style_header={
            "backgroundColor": BG_CARD2, "color": ACCENT,
            "fontWeight": "bold", "border": f"1px solid {BORDER_LT}",
            "fontFamily": FONT_FAMILY, "fontSize": "11px",
            "textAlign": "center", "padding": "8px 10px",
        },
        style_data_conditional=style_data_cond,
        page_size=len(tbl_rows),
    )

    return html.Div(dbc.Row([dbc.Col(table, width=12)]))


# ==========================================================================
#  TAB LAYOUTS
# ==========================================================================

# ── Tab 1: Investment Ideas ───────────────────────────────────────────────
tab_ideas = dbc.Tab(label="💡 Ideas", tab_id="t-ideas", children=[
    html.Div(className="p-3", children=[

        # ── Hedge Perspective Toggle ──────────────────────────────────────
        dbc.Row([
            dbc.Col(
                html.Div([
                    html.Span("Hedge Perspective:",
                              style={"color": TEXT_MUT, "fontSize": "11px",
                                     "fontFamily": FONT_FAMILY, "marginRight": "10px",
                                     "verticalAlign": "middle"}),
                    dbc.RadioItems(
                        id="ideas-hedge-toggle",
                        options=[
                            {"label": "Unhedged", "value": "unhedged"},
                            {"label": "JPY Hedged", "value": "jpy"},
                            {"label": "SGD Hedged", "value": "sgd"},
                        ],
                        value="unhedged",
                        inline=True,
                        style={"fontFamily": FONT_FAMILY, "fontSize": "11px",
                               "display": "inline-block"},
                        inputStyle={"marginRight": "4px"},
                        labelStyle={"marginRight": "16px", "color": TEXT},
                    ),
                ], style={"display": "flex", "alignItems": "center",
                          "backgroundColor": BG_CARD,
                          "border": f"1px solid {BORDER}",
                          "borderRadius": "6px", "padding": "8px 14px"}),
                width="auto",
            ),
        ], className="mb-3"),

        # ── 1. Multi-Signal Conviction Scorecard ──────────────────────────
        SEC_TITLE("Multi-Signal Conviction Scorecard",
                  "5-signal composite score (–10 to +10) per country: CPI surprise, PMI surprise, "
                  "yield z-score vs 5Y history, OIS-implied policy path, carry rank (hedge-adjusted). "
                  "Positive = bullish bond (buy); Negative = bearish bond (sell)."),
        html.Div(id="scorecard-container",
                 children=build_scorecard_panel(INITIAL_DATA)),
        html.Hr(style={"borderColor": BORDER, "margin": "20px 0"}),

        # ── 2. Carry + Roll-Down Charts ───────────────────────────────────
        SEC_TITLE("1Y Carry + Roll-Down by Country & Tenor",
                  "Grouped by Country (left) and by Tenor (right). "
                  "Bars sorted descending within each tenor group. Values in bps."),
        html.Div(id="carry-charts-container",
                 children=build_carry_charts_panel(INITIAL_DATA)),
        html.Hr(style={"borderColor": BORDER, "margin": "20px 0"}),

        # ── 3. Investment Idea Screener ───────────────────────────────────
        dbc.Row([
            dbc.Col(SEC_TITLE(
                "Investment Idea Screener",
                "Rule-based screener: ranks DM sovereign ideas by hedged pickup vs JGB, rate cycle, real rate, macro momentum & curve slope",
            ), width=10),
            dbc.Col(dbc.Badge(
                "Auto-updates on Refresh", color="success",
                style={"fontFamily": FONT_FAMILY, "fontSize": "10px", "padding": "6px 10px"},
            ), width=2, className="text-end", style={"paddingTop": "10px"}),
        ], className="mb-3", align="center"),
        html.Div(id="ideas-summary-container",
                 children=build_ideas_summary_table(_safe_ideas(INITIAL_DATA))),
        html.Hr(style={"borderColor": BORDER, "margin": "16px 0"}),
        SEC_TITLE("Full Screener Detail",
                  "Detailed rationale, triggers and risk factors for each idea"),
        html.Div(id="ideas-container",
                 children=build_ideas_datatable(_safe_ideas(INITIAL_DATA))),
        html.Hr(style={"borderColor": BORDER, "margin": "20px 0"}),

        # ── 4. Scoring Methodology + Hedged Yield charts ──────────────────
        SEC_TITLE("Scoring Methodology",
                  "Each idea is scored across 6 factors — higher absolute score = higher conviction"),
        dbc.Row([
            dbc.Col(html.Div(style={**CARD_STYLE, "padding": "12px"}, children=[
                html.Table([
                    html.Thead(html.Tr([
                        html.Th("Factor", style={"color": ACCENT, "fontFamily": FONT_FAMILY, "padding": "4px 8px", "fontSize": "11px"}),
                        html.Th("Bullish Signal",  style={"color": GREEN, "fontFamily": FONT_FAMILY, "padding": "4px 8px", "fontSize": "11px"}),
                        html.Th("Bearish Signal",  style={"color": RED,   "fontFamily": FONT_FAMILY, "padding": "4px 8px", "fontSize": "11px"}),
                    ])),
                    html.Tbody([
                        html.Tr([html.Td(f, style={"padding":"3px 8px","fontSize":"10px","fontFamily":FONT_FAMILY}),
                                 html.Td(b, style={"padding":"3px 8px","fontSize":"10px","color":GREEN,"fontFamily":FONT_FAMILY}),
                                 html.Td(br,style={"padding":"3px 8px","fontSize":"10px","color":RED, "fontFamily":FONT_FAMILY})])
                        for f, b, br in [
                            ("Hedged Pickup vs JGB", "> +80 bps (+3 pts)", "< 0 bps (−2 pts)"),
                            ("Rate Cycle",   "Cutting (+ 2 pts)",     "Hiking (−2 pts)"),
                            ("Real Rate",    "> +1.5% (+2 pts)",      "< 0% (−1 pt)"),
                            ("Growth/PMI",   "GDP < 1%, PMI < 49",    "PMI > 52 (−1 pt)"),
                            ("Fiscal",       "—",                     "Debt/GDP > 120% or deficit < −5% (−1 pt)"),
                            ("Curve Slope",  "Steep > 30 bps (+1 pt)","Inverted < −10 bps (−1 pt)"),
                            ("Credit",       "AAA (+1 pt)",           "BBB (−1 pt)"),
                        ]
                    ]),
                ], style={"width":"100%","borderCollapse":"collapse"})
            ]), width=6),
            dbc.Col([
                dcc.Graph(id="hy-bar",   figure=_safe_chart(chart_hedged_yield, INITIAL_DATA),
                          config=GRAPH_CFG, style={"height": "280px"}),
            ], width=6),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id="hg-table", figure=_safe_chart(chart_hedge_table, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "260px"}), width=12),
        ], className="mt-2"),
        html.Hr(style={"borderColor": BORDER, "margin": "20px 0"}),

        # ── 5. Carry & Roll-Down Table ────────────────────────────────────
        SEC_TITLE("Carry & Roll-Down Table",
                  "1Y total return = carry (income) + roll-down (price gain as bond ages along the curve). "
                  "Roll Δy = expected yield drop in 1Y via interpolation. Green = high return, Red = low/negative."),
        html.Div(id="carry-table-container",
                 children=build_carry_rolldown_panel(INITIAL_DATA)),
        html.Hr(style={"borderColor": BORDER, "margin": "20px 0"}),

        # ── 6. Macro Surprise Score ───────────────────────────────────────
        SEC_TITLE("Macro Surprise Score",
                  "CPI deviation from central bank target (±2 pts) + PMI vs 50 (±2 pts). "
                  "Positive = inflation above target or growth expansionary (bearish bonds); "
                  "Negative = below target or contraction (bullish bonds)."),
        html.Div(id="macro-surprise-container",
                 children=build_macro_surprise_panel(INITIAL_DATA)),
    ])
])

# ── Tab 2: Yields & Curves ────────────────────────────────────────────────
tab_yields = dbc.Tab(label="📈 Yields", tab_id="t-yields", children=[
    html.Div(className="p-3", children=[
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_hedged_yield_heatmap, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "380px"}), width=6),
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_hedged_yield_heatmap_sgd, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "380px"}), width=6),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col([
                html.Label("Tenor:", style={"color": TEXT_MUT, "fontSize": "11px",
                                             "fontFamily": FONT_FAMILY, "marginRight": "8px"}),
                tenor_group("yld"),
                html.Span("  "),
                hist_group("yld"),
            ], width=8),
            dbc.Col(country_checklist("yld"), width=4),
        ], className="mb-3", align="center"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="yld-bar",   figure=_safe_chart(chart_yield_bar, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "280px"}), width=6),
            dbc.Col(dcc.Graph(id="yld-slope", figure=_safe_chart(chart_slope_bar, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "280px"}), width=6),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id="yld-curve", figure=_safe_chart(chart_yield_curve, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "340px"}), width=6),
            dbc.Col(dcc.Graph(id="yld-hist",  figure=_safe_chart(chart_hist_yields),
                              config=GRAPH_CFG, style={"height": "340px"}), width=6),
        ], className="mt-2"),
    ])
])
# ── Tab 3: Macro Dashboard ────────────────────────────────────────────────

tab_macro = dbc.Tab(label="🌍 Macro", tab_id="t-macro", children=[
    html.Div(className="p-3", children=[

        # ── Row 1: Heatmap (left, w=6)  +  Interactive TS Explorer (right, w=6) ──
        dbc.Row([
            # ── LEFT: macro heatmap with country filter ────────────────────
            dbc.Col(
                html.Div(style={**CARD_STYLE, "padding": "10px"}, children=[
                    SEC_TITLE("Macro Heatmap", "Z-score vs 10Y history · select countries to filter"),
                    dcc.Checklist(
                        id="macro-heatmap-countries",
                        options=[
                            {"label": html.Span(
                                f"{FLAGS.get(c,'')} {c}",
                                style={"color": CCOLORS.get(c, TEXT), "fontSize": "11px",
                                       "fontFamily": FONT_FAMILY, "marginRight": "8px"},
                            ), "value": c}
                            for c in COUNTRIES
                        ],
                        value=COUNTRIES,
                        inline=True,
                        inputStyle={"marginRight": "3px", "cursor": "pointer"},
                        style={"marginBottom": "8px"},
                    ),
                    dcc.Graph(
                        id="macro-heatmap-graph",
                        figure=_safe_chart(chart_macro_heatmap, INITIAL_DATA, INITIAL_ZSCORES),
                        config=GRAPH_CFG,
                        style={"height": "460px"},
                    ),
                ]),
                width=6,
            ),

            # ── RIGHT: interactive macro time series explorer ─────────────
            dbc.Col(
                html.Div(style={**CARD_STYLE, "padding": "10px"}, children=[
                    SEC_TITLE(
                        "Macro Time Series Explorer",
                        "Multi-select countries & indicators · date range · normalise · dual axis",
                    ),

                    # ── Controls Row 1: Country + Indicator checkboxes ────────
                    dbc.Row([
                        dbc.Col([
                            html.Label("Countries", style={
                                "color": TEXT_MUT, "fontSize": "10px",
                                "fontFamily": FONT_FAMILY, "marginBottom": "4px",
                            }),
                            dcc.Checklist(
                                id="macro-ts-countries",
                                options=MACRO_TS_COUNTRY_OPTIONS,
                                value=["US", "Japan", "UK"],
                                inline=True,
                                inputStyle={"marginRight": "3px", "cursor": "pointer"},
                                labelStyle={
                                    "fontSize": "10px", "fontFamily": FONT_FAMILY,
                                    "color": TEXT, "marginRight": "8px",
                                },
                            ),
                        ], width=12),
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Indicators", style={
                                "color": TEXT_MUT, "fontSize": "10px",
                                "fontFamily": FONT_FAMILY, "marginBottom": "4px",
                            }),
                            dcc.Checklist(
                                id="macro-ts-indicators",
                                options=MACRO_TS_INDICATOR_OPTIONS,
                                value=["CPI_YOY"],
                                inline=True,
                                inputStyle={"marginRight": "3px", "cursor": "pointer"},
                                labelStyle={
                                    "fontSize": "10px", "fontFamily": FONT_FAMILY,
                                    "color": TEXT, "marginRight": "8px",
                                },
                            ),
                        ], width=12),
                    ], className="mb-2"),

                    # ── Controls Row 2: Quick period tabs ────────────────────
                    dbc.Row([
                        dbc.Col([
                            html.Label("Period", style={
                                "color": TEXT_MUT, "fontSize": "10px",
                                "fontFamily": FONT_FAMILY, "marginBottom": "2px",
                            }),
                            dbc.ButtonGroup([
                                dbc.Button(
                                    lbl, id=f"macro-ts-period-{lbl.lower()}",
                                    n_clicks=0, size="sm",
                                    color="primary" if lbl == "5Y" else "secondary",
                                    style={"fontFamily": FONT_FAMILY, "fontSize": "10px",
                                           "padding": "3px 8px"},
                                )
                                for lbl in ["MTD", "YTD", "1Y", "3Y", "5Y", "10Y", "30Y", "MAX"]
                            ], size="sm"),
                        ], width=12),
                    ], className="mb-2"),

                    # ── Controls Row 3: Start / End dates + Checkboxes ───────
                    dbc.Row([
                        dbc.Col([
                            html.Label("Start", style={
                                "color": TEXT_MUT, "fontSize": "10px",
                                "fontFamily": FONT_FAMILY, "marginBottom": "2px",
                            }),
                            dbc.Input(
                                id="macro-ts-start-date",
                                type="date",
                                value=(datetime.today() - timedelta(days=365 * 5)).strftime("%Y-%m-%d"),
                                size="sm",
                                style={
                                    "backgroundColor": BG_DEEP, "color": TEXT,
                                    "border": f"1px solid {BORDER}",
                                    "borderRadius": "4px", "fontSize": "11px",
                                    "fontFamily": FONT_FAMILY,
                                    "padding": "4px 8px", "height": "30px",
                                },
                            ),
                        ], width=3),
                        dbc.Col([
                            html.Label("End", style={
                                "color": TEXT_MUT, "fontSize": "10px",
                                "fontFamily": FONT_FAMILY, "marginBottom": "2px",
                            }),
                            dbc.Input(
                                id="macro-ts-end-date",
                                type="date",
                                value=datetime.today().strftime("%Y-%m-%d"),
                                size="sm",
                                style={
                                    "backgroundColor": BG_DEEP, "color": TEXT,
                                    "border": f"1px solid {BORDER}",
                                    "borderRadius": "4px", "fontSize": "11px",
                                    "fontFamily": FONT_FAMILY,
                                    "padding": "4px 8px", "height": "30px",
                                },
                            ),
                        ], width=3),
                        dbc.Col([
                            dcc.Checklist(
                                id="macro-ts-normalise",
                                options=[{"label": " Normalise (100)", "value": "norm"}],
                                value=[],
                                style={"marginTop": "16px"},
                                labelStyle={
                                    "color": TEXT, "fontSize": "10px",
                                    "fontFamily": FONT_FAMILY,
                                },
                                inputStyle={"marginRight": "4px"},
                            ),
                        ], width=3),
                        dbc.Col([
                            dcc.Checklist(
                                id="macro-ts-dual-axis",
                                options=[{"label": " Dual Y-Axis", "value": "dual"}],
                                value=[],
                                style={"marginTop": "16px"},
                                labelStyle={
                                    "color": TEXT, "fontSize": "10px",
                                    "fontFamily": FONT_FAMILY,
                                },
                                inputStyle={"marginRight": "4px"},
                            ),
                        ], width=3),
                    ], className="mb-2", align="end"),

                    # ── The interactive time series chart ─────────────────────
                    dcc.Graph(
                        id="macro-ts-chart",
                        config=GRAPH_CFG,
                        style={"height": "370px"},
                    ),
                ]),
                width=6,
            ),
        ]),

        # ── Row 2: Macro Panels (full width) ─────────────────────────────
        dbc.Row([
            dbc.Col(dcc.Graph(
                figure=_safe_chart(chart_macro_panels, INITIAL_DATA),
                config=GRAPH_CFG, style={"height": "520px"},
            ), width=12),
        ], className="mt-2"),

        # ── Row 3: Current Account + Fiscal Balance ──────────────────────
        dbc.Row([
            dbc.Col(dcc.Graph(
                figure=_safe_chart(chart_current_account, INITIAL_DATA),
                config=GRAPH_CFG, style={"height": "300px"},
            ), width=6),
            dbc.Col(dcc.Graph(
                figure=_safe_chart(chart_fiscal_balance, INITIAL_DATA),
                config=GRAPH_CFG, style={"height": "300px"},
            ), width=6),
        ], className="mt-2"),

        # ── Row 4: Policy vs Inflation + Fiscal Sustainability ───────────
        dbc.Row([
            dbc.Col(dcc.Graph(
                figure=_safe_chart(chart_policy_vs_inflation, INITIAL_DATA),
                config=GRAPH_CFG, style={"height": "360px"},
            ), width=6),
            dbc.Col(dcc.Graph(
                figure=_safe_chart(chart_fiscal_sustainability, INITIAL_DATA),
                config=GRAPH_CFG, style={"height": "360px"},
            ), width=6),
        ], className="mt-2"),
    ])
])

# ── Tab 4: FX & Hedging ───────────────────────────────────────────────────
tab_fx = dbc.Tab(label="💱 FX / Hedging", tab_id="t-fx", children=[
    html.Div(className="p-3", children=[
        dbc.Alert(
            "⚠️  Cross-currency basis tickers all require Bloomberg terminal verification. "
            "See Ticker Reference tab. Values shown are indicative.",
            color="warning", dismissable=True,
            style={"fontSize": "11px", "fontFamily": FONT_FAMILY}
        ),
        # ── XCcy basis (JPY + SGD) — top row ─────────────────────────────
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_xccy_basis, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "300px"}), width=6),
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_xccy_basis_sgd, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "300px"}), width=6),
        ]),
        # ── Hedged yield bar + tables ─────────────────────────────────────
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_hedged_yield, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "300px"}), width=12),
        ], className="mt-2"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_hedge_table, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "290px"}), width=7),
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_fx_bar, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "290px"}), width=5),
        ], className="mt-2"),
    ])
])

# ── Tab 5: Spread Analysis ────────────────────────────────────────────────

def _spread_summary_panel(data: Dict) -> html.Div:

    """
    Full-width spread summary card with three columns:
      1. Key Pairs — curated watch-list spreads
      2. Top 3 Largest — widest abs spreads across all pairs
      3. Top 3 Biggest 1M Change — largest abs move over past ~22 business days
    """
    y10 = data["yields"]["10Y"]
    countries = [c for c in COUNTRIES if c in y10 and y10[c] is not None]
    # ── All pairwise spreads ──────────────────────────────────────────────
    all_pairs = []
    for i, ca in enumerate(countries):
        for cb in countries[i + 1:]:
            bps = round((y10[ca] - y10[cb]) * 100, 0)
            all_pairs.append((
                f"{FLAGS.get(ca,'')} {ca} − {FLAGS.get(cb,'')} {cb}",
                bps, ca, cb,
            ))
    # ── 1-month change (~22 business days) ───────────────────────────────
    hist_df = get_hist_df("10Y", days=22)
    pair_changes = []
    for label, curr_bps, ca, cb in all_pairs:
        if ca in hist_df.columns and cb in hist_df.columns:
            past_bps = round((hist_df[ca].iloc[0] - hist_df[cb].iloc[0]) * 100, 0)
            chg = round(curr_bps - past_bps, 0)
            pair_changes.append((label, curr_bps, chg))
    top3_abs = sorted(all_pairs,   key=lambda x: abs(x[1]), reverse=True)[:5]
    top3_chg = sorted(pair_changes, key=lambda x: abs(x[2]), reverse=True)[:5]
    # ── Z-scores (2-year lookback) ────────────────────────────────────────
    hist_z_df = get_hist_df("10Y", days=504)
    zscore_pairs = []
    for label, curr_bps, ca, cb in all_pairs:
        if ca in hist_z_df.columns and cb in hist_z_df.columns:
            spread_series = (hist_z_df[ca] - hist_z_df[cb]) * 100
            mu  = float(spread_series.mean())
            std = float(spread_series.std())
            if std > 0:
                z = (curr_bps - mu) / std
                zscore_pairs.append((label, curr_bps, z))
    top5_z = sorted(zscore_pairs, key=lambda x: abs(x[2]), reverse=True)[:5]
    # ── Shared cell styles ────────────────────────────────────────────────
    TD  = {"padding": "5px 8px", "fontSize": "11px", "fontFamily": FONT_FAMILY}
    TDM = {**TD, "color": TEXT_MUT, "fontSize": "10px"}
    TH  = {"padding": "5px 8px", "fontSize": "10px", "fontFamily": FONT_FAMILY,
           "color": ACCENT, "letterSpacing": "0.08em", "textTransform": "uppercase",
           "borderBottom": f"1px solid {BORDER_LT}"}
    def mini_table(header_cells, body_rows):
        return html.Table([
            html.Thead(html.Tr([html.Th(h, style=TH) for h in header_cells])),
            html.Tbody(body_rows),
        ], style={"width": "100%", "borderCollapse": "collapse"})
    # ── Section 1: Key Pairs ──────────────────────────────────────────────
    key_pairs = [
        ("BTP–Bund 10Y",   "Italy",     "Germany",   "Sovereign risk premium"),
        ("UST–JGB 10Y",    "US",        "Japan",      "USD/JPY carry driver"),
        ("Gilt–Bund 10Y",  "UK",        "Germany",    "UK fiscal premium"),
        ("AGB–UST 10Y",    "Australia", "US",         "AUD pickup"),
        ("Canada–UST 10Y", "Canada",    "US",         "CA growth discount"),
        ("SG–JGB 10Y",     "Singapore", "Japan",      "SGS vs JGB"),
    ]
    key_rows = []
    for label, ca, cb, note in key_pairs:
        _va = y10.get(ca);  _vb = y10.get(cb)
        if _va is None or _vb is None:
            bps_str = "N/A"
            col = TEXT_MUT
        else:
            bps = round((_va - _vb) * 100, 0)
            bps_str = f"{bps:+.0f} bps"
            col = GREEN if bps >= 0 else RED
        key_rows.append(html.Tr([
            html.Td(label,    style=TD),
            html.Td(bps_str,  style={**TD, "color": col, "fontWeight": "600"}),
            html.Td(note,     style=TDM),
        ]))
    col1 = mini_table(["Pair", "Spread", "Note"], key_rows)
    # ── Section 2: Top 3 Largest ──────────────────────────────────────────
    abs_rows = []
    for rank, (label, bps, ca, cb) in enumerate(top3_abs, 1):
        col = GREEN if bps >= 0 else RED
        abs_rows.append(html.Tr([
            html.Td(f"#{rank}",             style={**TDM, "color": TEXT_MUT}),
            html.Td(label,                  style=TD),
            html.Td(f"{bps:+.0f} bps",     style={**TD, "color": col, "fontWeight": "600"}),
        ]))
    col2 = mini_table(["#", "Pair", "Spread"], abs_rows)
    # ── Section 3: Top 3 Biggest 1M Change ───────────────────────────────
    chg_rows = []
    for rank, (label, curr_bps, chg) in enumerate(top3_chg, 1):
        chg_col = GREEN if chg >= 0 else RED
        arrow   = "▲" if chg >= 0 else "▼"
        chg_rows.append(html.Tr([
            html.Td(f"#{rank}",                      style={**TDM, "color": TEXT_MUT}),
            html.Td(label,                           style=TD),
            html.Td(f"{curr_bps:+.0f} bps",         style={**TD, "color": TEXT_MUT}),
            html.Td(f"{arrow} {abs(chg):.0f} bps",  style={**TD, "color": chg_col, "fontWeight": "600"}),
        ]))
    col3 = mini_table(["#", "Pair", "Current", "1M Chg"], chg_rows)
    # ── Section 4: Top 5 Z-Score Spreads ──────────────────────────────────
    zscore_rows = []
    for rank, (label, bps, z) in enumerate(top5_z, 1):
        z_col = (RED if z >= 2 else ORANGE if z >= 1 else
                 RED if z <= -2 else ORANGE if z <= -1 else GREEN)
        arrow = "▲" if z >= 0 else "▼"
        zscore_rows.append(html.Tr([
            html.Td(f"#{rank}",             style={**TDM, "color": TEXT_MUT}),
            html.Td(label,                  style=TD),
            html.Td(f"{bps:+.0f} bps",     style={**TD, "color": TEXT_MUT}),
            html.Td(f"{arrow} {z:.1f}σ",   style={**TD, "color": z_col, "fontWeight": "600"}),
        ]))
    col4 = mini_table(["#", "Pair", "Spread", "Z-Score"], zscore_rows)
    # ── Assemble card ─────────────────────────────────────────────────────
    def section(title, subtitle, content):
        return html.Div([
            html.Div(title,    style={"color": ACCENT, "fontSize": "11px", "fontWeight": "600",
                                      "fontFamily": FONT_FAMILY, "marginBottom": "2px",
                                      "letterSpacing": "0.05em"}),
            html.Div(subtitle, style={"color": TEXT_MUT, "fontSize": "9px",
                                      "fontFamily": FONT_FAMILY, "marginBottom": "8px"}),
            content,
        ], style={"padding": "0 12px", "borderLeft": f"2px solid {BORDER_LT}"})
    return html.Div(
        style={**CARD_STYLE, "padding": "14px 4px"},
        children=[
            html.Div("Key Spread Summary",
                     style={"color": ACCENT, "fontSize": "12px", "fontWeight": "600",
                             "fontFamily": FONT_FAMILY, "marginBottom": "12px",
                             "paddingLeft": "12px"}),
            dbc.Row([
                dbc.Col(section("Key Pairs",
                                "Curated watch-list  |  10Y yield spread",
                                col1), width=4),
                dbc.Col(section("Top 5 Largest Spreads",
                                "Widest absolute spread across all country pairs",
                                col2), width=2),
                dbc.Col(section("Top 5 Biggest 1M Change",
                                "Largest absolute move over past ~1 month",
                                col3), width=3),
                dbc.Col(section("Top 5 Extreme Z-Scores",
                                "Most stretched vs 2Y history  |  10Y spread",
                                col4), width=3),
            ], className="g-0"),
        ],
    )

_SPREAD_TENORS  = ["2Y", "5Y", "10Y", "30Y"]
_SPREAD_PERIODS = [("1Y", 252), ("2Y", 504), ("3Y", 756), ("5Y", 1260),
                   ("10Y", 2520), ("15Y", 3780), ("20Y", 5040), ("30Y", 7560)]
_SPRD_HEATMAP_DEFAULT = COUNTRIES
_SPRD_BASE_DEFAULT    = "US"
_SPRD_OTHER_DEFAULT   = "Germany"

def _inline_radio(cid: str, default: str) -> dbc.RadioItems:
    """Compact single-select country radio buttons."""
    return dbc.RadioItems(
        id=cid,
        options=[{"label": f"{FLAGS.get(c,'')} {c}", "value": c} for c in COUNTRIES],
        value=default,
        inline=True,
        style={"fontSize": "11px", "fontFamily": FONT_FAMILY, "color": TEXT_MUT},
        inputStyle={"marginRight": "3px"},
        labelStyle={"marginRight": "10px"},
    )

_BTN_SM = {"fontFamily": FONT_FAMILY, "fontSize": "11px"}

tab_spreads = dbc.Tab(label="📊 Spreads", tab_id="t-spreads", children=[
    html.Div(className="p-3", children=[
        dbc.Row([
            dbc.Col(_safe_spread_panel(INITIAL_DATA), width=12),
        ]),
        # ── Heatmap + Comparison side by side ──────────────────────────────
        dbc.Row([
            # Left: 10Y spread heatmap
            dbc.Col([
                dbc.Row([
                    dbc.Col(
                        html.Span("10Y Spread Matrix (bps, colour = 10Y z-score)",
                                  style={"color": TEXT_MUT, "fontSize": "10px",
                                         "fontFamily": FONT_FAMILY}),
                        width="auto",
                    ),
                    dbc.Col(
                        dbc.ButtonGroup([
                            dbc.Button("All",  id="sprd-heatmap-all",  n_clicks=0,
                                       size="sm", color="secondary", style=_BTN_SM),
                            dbc.Button("None", id="sprd-heatmap-none", n_clicks=0,
                                       size="sm", color="secondary", style=_BTN_SM),
                        ]),
                        width="auto",
                    ),
                ], align="center", justify="between", className="mb-1"),
                dbc.Checklist(
                    id="sprd-heatmap-countries",
                    options=[{"label": f"{FLAGS.get(c,'')} {c}", "value": c}
                             for c in COUNTRIES],
                    value=_SPRD_HEATMAP_DEFAULT,
                    inline=True,
                    style={"fontSize": "11px", "fontFamily": FONT_FAMILY,
                           "color": TEXT_MUT, "marginBottom": "6px"},
                    inputStyle={"marginRight": "3px"},
                    labelStyle={"marginRight": "10px"},
                ),
                dcc.Graph(id="sprd-heatmap-graph",
                          figure=_safe_chart(chart_yield_spread_heatmap, INITIAL_DATA),
                          config=GRAPH_CFG, style={"height": "500px"}),
            ], width=6),
            # Right: base vs compare yield comparison (fill + annotations)
            dbc.Col([
                html.Span("Historical Yield Comparison",
                          style={"color": TEXT_MUT, "fontSize": "10px",
                                 "fontFamily": FONT_FAMILY, "marginBottom": "4px",
                                 "display": "block"}),
                dbc.Row([
                    dbc.Col([
                        html.Label("Base", style={"color": TEXT_MUT, "fontSize": "10px",
                                                   "fontFamily": FONT_FAMILY,
                                                   "marginBottom": "2px"}),
                        _inline_radio("sprd-base-country", _SPRD_BASE_DEFAULT),
                    ], width=12, className="mb-1"),
                ]),
                dbc.Row([
                    dbc.Col([
                        html.Label("Compare vs", style={"color": TEXT_MUT, "fontSize": "10px",
                                                         "fontFamily": FONT_FAMILY,
                                                         "marginBottom": "2px"}),
                        _inline_radio("sprd-other-country", _SPRD_OTHER_DEFAULT),
                    ], width=12, className="mb-2"),
                ]),
                dbc.Row([
                    dbc.Col([
                        html.Label("Tenor", style={"color": TEXT_MUT, "fontSize": "10px",
                                                    "fontFamily": FONT_FAMILY,
                                                    "marginBottom": "3px"}),
                        dbc.ButtonGroup([
                            dbc.Button(t, id=f"sprd-t-{t.lower()}", n_clicks=0,
                                       size="sm",
                                       color="primary" if t == "10Y" else "secondary",
                                       style=_BTN_SM)
                            for t in _SPREAD_TENORS
                        ]),
                    ], width="auto"),
                    dbc.Col([
                        html.Label("Period", style={"color": TEXT_MUT, "fontSize": "10px",
                                                     "fontFamily": FONT_FAMILY,
                                                     "marginBottom": "3px"}),
                        dbc.ButtonGroup([
                            dbc.Button(lbl, id=f"sprd-p-{lbl.lower()}", n_clicks=0,
                                       size="sm",
                                       color="primary" if lbl == "5Y" else "secondary",
                                       style=_BTN_SM)
                            for lbl, _ in _SPREAD_PERIODS
                        ]),
                    ], width="auto"),
                ], align="end", className="mb-2"),
                dcc.Graph(id="sprd-compare-chart",
                          config=GRAPH_CFG, style={"height": "420px"}),
            ], width=6),
        ], className="mt-2"),
        # ── Z-Score heatmap (period-toggleable) ────────────────────────────
        dbc.Row([
            dbc.Col([
                dbc.Row([
                    dbc.Col(
                        html.Span("Z-Score Spread Matrix  (lookback period controls z-score window)",
                                  style={"color": TEXT_MUT, "fontSize": "10px",
                                         "fontFamily": FONT_FAMILY}),
                        width="auto",
                    ),
                    dbc.Col(
                        dbc.ButtonGroup([
                            dbc.Button(lbl, id=f"sprd-z-p-{lbl.lower()}", n_clicks=0,
                                       size="sm",
                                       color="primary" if lbl == "5Y" else "secondary",
                                       style=_BTN_SM)
                            for lbl, _ in _SPREAD_PERIODS
                        ]),
                        width="auto",
                    ),
                ], align="center", justify="between", className="mb-1"),
                dcc.Graph(id="sprd-zscore-graph",
                          figure=_safe_chart(chart_zscore_spread_heatmap, INITIAL_DATA),
                          config=GRAPH_CFG),
            ], width=12),
        ], className="mt-3"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_spread_vs_jgb, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "310px"}), width=6),
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_breakeven, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "310px"}), width=6),
        ], className="mt-2"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_slope_bar, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "300px"}), width=12),
        ], className="mt-2"),
    ])
])

# ── Tab 6: Breakeven ─────────────────────────────────────────────────────
tab_breakeven = dbc.Tab(label="📉 Breakeven", tab_id="t-breakeven", children=[
    html.Div(className="p-3", children=[
        dbc.Alert(
            "⚠️  5Y breakeven tickers (USGGBE05, UKGGBE05, DEGGBE05, JNGBE05) require Bloomberg terminal verification.",
            color="warning", dismissable=True,
            style={"fontSize": "11px", "fontFamily": FONT_FAMILY}
        ),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_breakeven_curve, INITIAL_DATA),
                              config=GRAPH_CFG), width=12),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=_safe_chart(chart_breakeven_spread, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "320px"}), width=12),
        ]),
    ])
])

# ── Tab: TIPS / Real Yields ───────────────────────────────────────────────
_SIM_HORIZON_OPTIONS = [
    {"label": "1M",  "value": 1},
    {"label": "3M",  "value": 3},
    {"label": "6M",  "value": 6},
    {"label": "9M",  "value": 9},
    {"label": "12M", "value": 12},
]
_SIM_PATH_OPTIONS = [
    {"label": "Linear",       "value": "linear"},
    {"label": "Front-loaded", "value": "front"},
    {"label": "Back-loaded",  "value": "back"},
]

_BOND_SIM_HORIZON_OPTIONS = [
    {"label": "1M",  "value": 1},
    {"label": "3M",  "value": 3},
    {"label": "6M",  "value": 6},
    {"label": "1Y",  "value": 12},
    {"label": "2Y",  "value": 24},
    {"label": "3Y",  "value": 36},
]
_BOND_TENOR_OPTIONS = [
    {"label": "2Y",  "value": "2Y"},
    {"label": "5Y",  "value": "5Y"},
    {"label": "10Y", "value": "10Y"},
    {"label": "30Y", "value": "30Y"},
]
_BOND_TENOR_MATURITY  = {"2Y": 2.0, "5Y": 5.0, "10Y": 10.0, "30Y": 30.0}
_BOND_SIM_PATH_OPTIONS = [
    {"label": "Linear",       "value": "linear"},
    {"label": "Front-loaded", "value": "front"},
    {"label": "Back-loaded",  "value": "back"},
]

tab_tips = dbc.Tab(label="🏛️ TIPS / Real", tab_id="t-tips", children=[
    html.Div(className="p-3", children=[

        dbc.Alert([
            html.Strong("TIPS / Linker Dashboard | "),
            "Real yields: US TIPS ✅  UK linkers, German ILBs, JGBi & others ⚠️ need BBG verification. "
            "Inflation swaps: US ✅  EUR & UK ⚠️ verify tickers. "
            "No fallback data — all fields show N/A when Bloomberg is offline.",
        ], color="warning", dismissable=True,
           style={"fontSize": "11px", "fontFamily": FONT_FAMILY}),

        # ── Section 1: Real Yield + Carry Snapshot ──────────────────────
        dbc.Row([
            dbc.Col(SEC_TITLE(
                "Real Yield Snapshot — TIPS / Linkers with 3M Carry + Rolldown",
                "10Y real yields per country. Right panel = estimated 3M carry + rolldown (bps). "
                "Diamond = shadow real rate (Policy Rate − CPI). Below zero = financial repression.",
            ), width=12),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="tips-carry-chart",
                              figure=_safe_chart(chart_real_yield_carry, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "360px"}), width=12),
        ], className="mb-3"),

        html.Hr(style={"borderColor": BORDER, "margin": "8px 0"}),

        # ── Section 2: Real Rate Regime Panel ───────────────────────────
        dbc.Row([
            dbc.Col(SEC_TITLE(
                "Real Rate Regime Panel",
                "Current 10Y real yield vs long-run ±1σ band (2015–2025). "
                "Diamond = current level. Blue band = ±1σ range. Dotted line = long-run mean. "
                "Above band = historically high real rates; below = historically repressed.",
            ), width=12),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="tips-regime-chart",
                              figure=_safe_chart(chart_real_rate_regime, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "330px"}), width=12),
        ], className="mb-3"),

        html.Hr(style={"borderColor": BORDER, "margin": "8px 0"}),

        # ── Section 3: Enhanced TIPS Table ──────────────────────────────
        dbc.Row([
            dbc.Col(SEC_TITLE(
                "TIPS vs Nominal — Enhanced Comparison Table",
                "Real yield z-score: >+1σ = historically rich (amber). "
                "BE Rich/Cheap z: +ve = BEs pricing above history (inflation insurance expensive). "
                "Carry+Roll = estimated 3M carry and rolldown in bps. "
                "Green = positive real return. Red = financial repression.",
            ), width=12),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="tips-table-chart",
                              figure=_safe_chart(chart_tips_table_enhanced, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "270px"}), width=12),
        ], className="mb-3"),

        html.Hr(style={"borderColor": BORDER, "margin": "8px 0"}),

        # ── Section 4: Cross-Market RV Matrix ───────────────────────────
        dbc.Row([
            dbc.Col(SEC_TITLE(
                "Cross-Market TIPS RV Matrix",
                "z-scores vs ~10Y history. "
                "Real Yield z: +ve = yield above historical mean (cheap in price, attractive entry). "
                "BE Rich/Cheap z: -ve = BEs below history (inflation under-priced). "
                "Carry+Roll: estimated 3M carry + rolldown in bps.",
            ), width=12),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="tips-rv-matrix",
                              figure=_safe_chart(chart_tips_rv_matrix, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "280px"}), width=12),
        ], className="mb-3"),

        html.Hr(style={"borderColor": BORDER, "margin": "8px 0"}),

        # ── Section 5: Inflation Swap Curves ────────────────────────────
        dbc.Row([
            dbc.Col(SEC_TITLE(
                "Inflation Swap Curves — Forward Market Expectations",
                "Zero-coupon swap rates at 1Y → 2Y → 5Y → 10Y. "
                "Star = explicit 5Y5Y forward (key CB anchor). "
                "Inversion warning shown when 1Y > 10Y. "
                "Yellow dashed = current CPI. Dotted = 2% CB target.",
            ), width=12),
        ], className="mb-1"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="tips-swap-chart",
                              figure=_safe_chart(chart_infl_swap_enhanced, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "410px"}), width=12),
        ], className="mb-3"),

        html.Hr(style={"borderColor": BORDER, "margin": "8px 0"}),

        # ── Section 6: Growth Proxy + Seasonality Row ───────────────────
        dbc.Row([
            dbc.Col([
                dbc.Row([dbc.Col(SEC_TITLE(
                    "Real Yield vs ISM Manufacturing",
                    "US 10Y real yield vs ISM PMI (trailing 24M). "
                    "Deviations from OLS fit = monetary policy mis-pricing vs growth cycle. "
                    "Requires BBG history; N/A when offline.",
                ), width=12)], className="mb-1"),
                dcc.Graph(id="tips-pmi-chart",
                          figure=_safe_chart(chart_real_yield_vs_pmi, INITIAL_DATA, MACRO_HISTORY),
                          config=GRAPH_CFG, style={"height": "340px"}),
            ], width=6),
            dbc.Col([
                dbc.Row([dbc.Col(SEC_TITLE(
                    "US Breakeven Seasonality",
                    "Average monthly change in US 10Y BE (bps) over 5Y of history. "
                    "Error bars = ±1σ. Vertical line = current month. "
                    "Requires BBG history; N/A when offline.",
                ), width=12)], className="mb-1"),
                dcc.Graph(id="tips-seasonal-chart",
                          figure=_safe_chart(chart_be_seasonality, INITIAL_DATA),
                          config=GRAPH_CFG, style={"height": "340px"}),
            ], width=6),
        ], className="mb-3"),

        html.Hr(style={"borderColor": BORDER, "margin": "12px 0"}),

        # ── Section 7: Scenario Simulation Widget ───────────────────────
        dbc.Row([
            dbc.Col(html.Div([
                html.Span("📐  Scenario Simulator — TIPS Total Return",
                          style={"color": TEAL, "fontWeight": "600",
                                 "fontSize": "13px", "fontFamily": FONT_FAMILY}),
                html.Span("  |  Model breakeven & rate changes → decompose P&L over up to 12 months",
                          style={"color": TEXT_MUT, "fontSize": "10px", "fontFamily": FONT_FAMILY}),
            ]), width=12),
        ], className="mb-2"),

        dbc.Row([
            # ── Left: Input panel ──────────────────────────────────────
            dbc.Col([
                html.Div(style={
                    "backgroundColor": BG_CARD2, "border": f"1px solid {BORDER}",
                    "borderLeft": f"3px solid {TEAL}", "borderRadius": "6px",
                    "padding": "14px 16px",
                }, children=[
                    # Instrument
                    html.Label("Instrument", style={"color": TEXT_MUT, "fontSize": "10px",
                                                     "fontFamily": FONT_FAMILY,
                                                     "textTransform": "uppercase",
                                                     "letterSpacing": "0.1em"}),
                    dcc.Dropdown(
                        id="tips-sim-instrument",
                        options=[{"label": k, "value": k} for k in SIM_INSTRUMENTS],
                        value="US TIPS 10Y",
                        clearable=False,
                        style={"backgroundColor": BG_DEEP, "color": TEXT,
                               "fontSize": "11px", "fontFamily": FONT_FAMILY,
                               "marginBottom": "12px"},
                    ),
                    # Current real yield (auto-filled)
                    html.Label("Current Real Yield (%)", style={"color": TEXT_MUT, "fontSize": "10px",
                                                                  "fontFamily": FONT_FAMILY}),
                    dcc.Input(id="tips-sim-ry-start", type="number", debounce=True,
                              step=0.01, min=-5.0, max=10.0,
                              style={"width": "100%", "backgroundColor": BG_DEEP,
                                     "color": TEXT, "border": f"1px solid {BORDER}",
                                     "borderRadius": "4px", "padding": "5px 8px",
                                     "fontSize": "11px", "fontFamily": FONT_FAMILY,
                                     "marginBottom": "10px"}),
                    # Real yield target slider
                    html.Label("Target Real Yield (%)", style={"color": TEXT_MUT, "fontSize": "10px",
                                                                 "fontFamily": FONT_FAMILY}),
                    dcc.Slider(id="tips-sim-ry-end", min=-2.0, max=6.0, step=0.05,
                               value=2.0, marks={i: f"{i}%" for i in range(-2, 7)},
                               tooltip={"placement": "bottom", "always_visible": False}),
                    html.Div(style={"marginBottom": "10px"}),
                    # Current breakeven
                    html.Label("Current Breakeven (%)", style={"color": TEXT_MUT, "fontSize": "10px",
                                                                  "fontFamily": FONT_FAMILY}),
                    dcc.Input(id="tips-sim-be-start", type="number", debounce=True,
                              step=0.01, min=-1.0, max=10.0,
                              style={"width": "100%", "backgroundColor": BG_DEEP,
                                     "color": TEXT, "border": f"1px solid {BORDER}",
                                     "borderRadius": "4px", "padding": "5px 8px",
                                     "fontSize": "11px", "fontFamily": FONT_FAMILY,
                                     "marginBottom": "10px"}),
                    # Breakeven target slider
                    html.Label("Target Breakeven (%)", style={"color": TEXT_MUT, "fontSize": "10px",
                                                                "fontFamily": FONT_FAMILY}),
                    dcc.Slider(id="tips-sim-be-end", min=-1.0, max=6.0, step=0.05,
                               value=2.35, marks={i: f"{i}%" for i in range(-1, 7)},
                               tooltip={"placement": "bottom", "always_visible": False}),
                    html.Div(style={"marginBottom": "10px"}),
                    # Policy rate change
                    html.Label("Policy Rate Change (bps, scenario context)",
                               style={"color": TEXT_MUT, "fontSize": "10px",
                                      "fontFamily": FONT_FAMILY}),
                    dcc.Slider(id="tips-sim-policy-delta", min=-300, max=300, step=25,
                               value=0,
                               marks={v: f"{v:+d}" for v in [-300,-200,-100,0,100,200,300]},
                               tooltip={"placement": "bottom", "always_visible": False}),
                    html.Div(style={"marginBottom": "12px"}),
                    # Time horizon
                    html.Label("Time Horizon", style={"color": TEXT_MUT, "fontSize": "10px",
                                                       "fontFamily": FONT_FAMILY,
                                                       "textTransform": "uppercase",
                                                       "letterSpacing": "0.1em"}),
                    dbc.RadioItems(
                        id="tips-sim-horizon", options=_SIM_HORIZON_OPTIONS, value=6,
                        inline=True,
                        inputStyle={"marginRight": "4px"},
                        labelStyle={"marginRight": "10px", "color": TEXT,
                                    "fontSize": "11px", "fontFamily": FONT_FAMILY},
                    ),
                    html.Div(style={"marginBottom": "10px"}),
                    # Path shape
                    html.Label("Rate Path Shape", style={"color": TEXT_MUT, "fontSize": "10px",
                                                          "fontFamily": FONT_FAMILY,
                                                          "textTransform": "uppercase",
                                                          "letterSpacing": "0.1em"}),
                    dbc.RadioItems(
                        id="tips-sim-path", options=_SIM_PATH_OPTIONS, value="linear",
                        inline=True,
                        inputStyle={"marginRight": "4px"},
                        labelStyle={"marginRight": "10px", "color": TEXT,
                                    "fontSize": "11px", "fontFamily": FONT_FAMILY},
                    ),
                    html.Div(style={"marginBottom": "14px"}),
                    # Reset button
                    dbc.Button("↺ Reset to Market", id="tips-sim-reset", size="sm",
                               color="secondary", outline=True,
                               style={"fontFamily": FONT_FAMILY, "fontSize": "11px",
                                      "width": "100%"}),
                ]),
            ], width=3),

            # ── Right: Output panel ────────────────────────────────────
            dbc.Col([
                dbc.Row([
                    dbc.Col(dcc.Graph(id="tips-sim-decomp",
                                     config=GRAPH_CFG, style={"height": "270px"}), width=7),
                    dbc.Col(dcc.Graph(id="tips-sim-summary",
                                     config=GRAPH_CFG, style={"height": "270px"}), width=5),
                ], className="mb-2"),
                dbc.Row([
                    dbc.Col(dcc.Graph(id="tips-sim-path-chart",
                                     config=GRAPH_CFG, style={"height": "360px"}), width=6),
                    dbc.Col(dcc.Graph(id="tips-sim-heatmap",
                                     config=GRAPH_CFG, style={"height": "360px"}), width=6),
                ]),
            ], width=9),
        ], className="mb-3"),

    ])
])

# ── Tab 7: Bond Return Simulator ─────────────────────────────────────────
tab_bond = dbc.Tab(label="📐 Bond Returns", tab_id="t-bond", children=[
    html.Div(className="p-3", children=[

        dbc.Row([
            dbc.Col(html.Div([
                html.Span("📐  Sovereign Bond Return Simulator",
                          style={"color": ACCENT2, "fontWeight": "600",
                                 "fontSize": "13px", "fontFamily": FONT_FAMILY}),
                html.Span("  |  Decompose carry · roll-down · price return for any country & tenor",
                          style={"color": TEXT_MUT, "fontSize": "10px",
                                 "fontFamily": FONT_FAMILY}),
            ]), width=12),
        ], className="mb-2"),

        dbc.Row([
            # ── Left: Input panel ──────────────────────────────────────
            dbc.Col([
                html.Div(style={
                    "backgroundColor": BG_CARD2, "border": f"1px solid {BORDER}",
                    "borderLeft": f"3px solid {ACCENT2}", "borderRadius": "6px",
                    "padding": "14px 16px",
                }, children=[
                    # Country
                    html.Label("Country", style={"color": TEXT_MUT, "fontSize": "10px",
                                                  "fontFamily": FONT_FAMILY,
                                                  "textTransform": "uppercase",
                                                  "letterSpacing": "0.1em"}),
                    dcc.Dropdown(
                        id="bond-sim-country",
                        options=[{"label": f"{FLAGS.get(c,'')} {c}", "value": c}
                                 for c in COUNTRIES],
                        value="US",
                        clearable=False,
                        style={"backgroundColor": BG_DEEP, "color": TEXT,
                               "fontSize": "11px", "fontFamily": FONT_FAMILY,
                               "marginBottom": "10px"},
                    ),
                    # Tenor
                    html.Label("Tenor", style={"color": TEXT_MUT, "fontSize": "10px",
                                               "fontFamily": FONT_FAMILY,
                                               "textTransform": "uppercase",
                                               "letterSpacing": "0.1em"}),
                    dbc.RadioItems(
                        id="bond-sim-tenor", options=_BOND_TENOR_OPTIONS, value="10Y",
                        inline=True,
                        inputStyle={"marginRight": "4px"},
                        labelStyle={"marginRight": "10px", "color": TEXT,
                                    "fontSize": "11px", "fontFamily": FONT_FAMILY},
                    ),
                    html.Div(style={"marginBottom": "10px"}),
                    # Starting yield (auto-filled, editable)
                    html.Label("Starting Yield (%)", style={"color": TEXT_MUT, "fontSize": "10px",
                                                             "fontFamily": FONT_FAMILY}),
                    dcc.Input(id="bond-sim-yield-start", type="number", debounce=True,
                              step=0.01, min=0.0, max=20.0,
                              style={"width": "100%", "backgroundColor": BG_DEEP,
                                     "color": TEXT, "border": f"1px solid {BORDER}",
                                     "borderRadius": "4px", "padding": "5px 8px",
                                     "fontSize": "11px", "fontFamily": FONT_FAMILY,
                                     "marginBottom": "8px"}),
                    # Coupon override (auto-filled to yield, editable)
                    html.Label("Coupon Override (%, blank = at-par)",
                               style={"color": TEXT_MUT, "fontSize": "10px",
                                      "fontFamily": FONT_FAMILY}),
                    dcc.Input(id="bond-sim-coupon", type="number", debounce=True,
                              step=0.01, min=0.0, max=20.0, placeholder="same as yield",
                              style={"width": "100%", "backgroundColor": BG_DEEP,
                                     "color": TEXT, "border": f"1px solid {BORDER}",
                                     "borderRadius": "4px", "padding": "5px 8px",
                                     "fontSize": "11px", "fontFamily": FONT_FAMILY,
                                     "marginBottom": "12px"}),
                    html.Hr(style={"borderColor": BORDER, "margin": "6px 0 10px 0"}),
                    # Parallel shift slider
                    html.Label("Parallel Shift (bps)",
                               style={"color": TEXT_MUT, "fontSize": "10px",
                                      "fontFamily": FONT_FAMILY}),
                    dcc.Slider(id="bond-sim-parallel", min=-300, max=300, step=25,
                               value=0,
                               marks={v: f"{v:+d}" for v in [-300,-150,0,150,300]},
                               tooltip={"placement": "bottom", "always_visible": False}),
                    html.Div(style={"marginBottom": "10px"}),
                    # Spread change slider
                    html.Label("Spread Change (bps)",
                               style={"color": TEXT_MUT, "fontSize": "10px",
                                      "fontFamily": FONT_FAMILY}),
                    dcc.Slider(id="bond-sim-spread", min=-200, max=200, step=25,
                               value=0,
                               marks={v: f"{v:+d}" for v in [-200,-100,0,100,200]},
                               tooltip={"placement": "bottom", "always_visible": False}),
                    html.Div(style={"marginBottom": "10px"}),
                    # Policy rate change slider (contextual)
                    html.Label("Policy Rate Δ (bps, scenario context)",
                               style={"color": TEXT_MUT, "fontSize": "10px",
                                      "fontFamily": FONT_FAMILY}),
                    dcc.Slider(id="bond-sim-policy", min=-300, max=300, step=25,
                               value=0,
                               marks={v: f"{v:+d}" for v in [-300,-150,0,150,300]},
                               tooltip={"placement": "bottom", "always_visible": False}),
                    html.Div(style={"marginBottom": "12px"}),
                    html.Hr(style={"borderColor": BORDER, "margin": "6px 0 10px 0"}),
                    # Holding period
                    html.Label("Holding Period", style={"color": TEXT_MUT, "fontSize": "10px",
                                                         "fontFamily": FONT_FAMILY,
                                                         "textTransform": "uppercase",
                                                         "letterSpacing": "0.1em"}),
                    dbc.RadioItems(
                        id="bond-sim-horizon", options=_BOND_SIM_HORIZON_OPTIONS, value=12,
                        inline=True,
                        inputStyle={"marginRight": "4px"},
                        labelStyle={"marginRight": "8px", "color": TEXT,
                                    "fontSize": "11px", "fontFamily": FONT_FAMILY},
                    ),
                    html.Div(style={"marginBottom": "10px"}),
                    # Path shape (for cumulative return path chart)
                    html.Label("Yield Path Shape", style={"color": TEXT_MUT, "fontSize": "10px",
                                                           "fontFamily": FONT_FAMILY,
                                                           "textTransform": "uppercase",
                                                           "letterSpacing": "0.1em"}),
                    dbc.RadioItems(
                        id="bond-sim-path-shape", options=_BOND_SIM_PATH_OPTIONS, value="linear",
                        inline=True,
                        inputStyle={"marginRight": "4px"},
                        labelStyle={"marginRight": "8px", "color": TEXT,
                                    "fontSize": "11px", "fontFamily": FONT_FAMILY},
                    ),
                    html.Div(style={"marginBottom": "14px"}),
                    # Reset
                    dbc.Button("↺ Reset to Market", id="bond-sim-reset", size="sm",
                               color="secondary", outline=True,
                               style={"fontFamily": FONT_FAMILY, "fontSize": "11px",
                                      "width": "100%"}),
                ]),
            ], width=3),

            # ── Right: Output panel ────────────────────────────────────
            dbc.Col([
                dbc.Row([
                    dbc.Col(dcc.Graph(id="bond-sim-waterfall",
                                     config=GRAPH_CFG, style={"height": "330px"}), width=7),
                    dbc.Col(dcc.Graph(id="bond-sim-summary",
                                     config=GRAPH_CFG, style={"height": "330px"}), width=5),
                ], className="mb-2"),
                dbc.Row([
                    dbc.Col(dcc.Graph(id="bond-sim-path",
                                     config=GRAPH_CFG, style={"height": "390px"}), width=6),
                    dbc.Col(dcc.Graph(id="bond-sim-heatmap",
                                     config=GRAPH_CFG, style={"height": "390px"}), width=6),
                ], className="mb-2"),
                dbc.Row([
                    dbc.Col(dcc.Graph(id="bond-sim-country-bar",
                                     config=GRAPH_CFG, style={"height": "400px"}), width=12),
                ]),
            ], width=9),
        ], className="mb-3"),

    ])
])

# ── Tab: Forward Rate Monitor ─────────────────────────────────────────────
_OIS_CB_CHECKLIST_OPTIONS = [
    {"label": f"{OIS_CB_FLAGS.get(cb, '')} {cb}", "value": cb}
    for cb in OIS_PATH_TICKERS.keys()
]

tab_fwd = dbc.Tab(label="⏩ Fwd Rates", tab_id="t-fwd", children=[
    html.Div(className="p-3", children=[
        dbc.Row([
            dbc.Col(SEC_TITLE(
                "Implied Forward Rate Monitor",
                "Bootstrapped from par sovereign yield curves · ◆ = implied forward · solid = spot curve",
            ), width=12),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col([
                html.Label("Segment:", style={"color": TEXT_MUT, "fontSize": "11px",
                                              "fontFamily": FONT_FAMILY, "marginRight": "8px"}),
                dbc.RadioItems(
                    id="fwd-segment",
                    options=[
                        {"label": "2s5s  —  3Y, 2Y Fwd",   "value": "2s5s"},
                        {"label": "5s10s —  5Y5Y",          "value": "5s10s"},
                        {"label": "10s30s — 20Y, 10Y Fwd",  "value": "10s30s"},
                    ],
                    value="5s10s",
                    inline=True,
                    inputStyle={"marginRight": "4px"},
                    labelStyle={"marginRight": "18px", "color": TEXT, "fontSize": "11px",
                                "fontFamily": FONT_FAMILY},
                ),
            ], width=8),
            dbc.Col(country_checklist("fwd"), width=4),
        ], className="mb-3", align="center"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="fwd-curve",
                              figure=_safe_chart(chart_fwd_curve, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "400px"}), width=8),
            dbc.Col(dcc.Graph(id="fwd-premium",
                              figure=_safe_chart(chart_fwd_premium, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "400px"}), width=4),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="fwd-bar",
                              figure=_safe_chart(chart_fwd_bar, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "300px"}), width=12),
        ]),
        html.Hr(style={"borderColor": BORDER, "margin": "14px 0"}),
        dbc.Row([
            dbc.Col(html.Div(style={**CARD_STYLE, "padding": "12px"}, children=[
                SEC_TITLE("Forward Rate Methodology",
                          "Annual compounding bootstrap from par sovereign yields"),
                html.Table([
                    html.Thead(html.Tr([
                        html.Th(h, style={"color": ACCENT, "fontFamily": FONT_FAMILY,
                                          "padding": "4px 10px", "fontSize": "11px"})
                        for h in ["Label", "Tenors Used", "Formula", "Market Interpretation"]
                    ])),
                    html.Tbody([
                        html.Tr([
                            html.Td(lbl, style={"padding":"3px 10px","fontSize":"10px",
                                                "fontFamily":FONT_FAMILY,"color":TEXT}),
                            html.Td(tnr, style={"padding":"3px 10px","fontSize":"10px",
                                                "fontFamily":FONT_FAMILY,"color":TEXT_MUT}),
                            html.Td(fml, style={"padding":"3px 10px","fontSize":"10px",
                                                "fontFamily":FONT_FAMILY,"color":TEXT_MUT}),
                            html.Td(ins, style={"padding":"3px 10px","fontSize":"10px",
                                                "fontFamily":FONT_FAMILY,"color":TEXT_MUT}),
                        ])
                        for lbl, tnr, fml, ins in [
                            ("2s5s (3Y, 2Y Fwd)",    "2Y & 5Y spot",
                             "[(1+r₅)⁵/(1+r₂)²]^(1/3)−1",
                             "Near-term expectations — front-end cut/hike pricing"),
                            ("5s10s (5Y5Y)",          "5Y & 10Y spot",
                             "[(1+r₁₀)¹⁰/(1+r₅)⁵]^(1/5)−1",
                             "Neutral rate anchor — key Fed/ECB long-run gauge"),
                            ("10s30s (20Y, 10Y Fwd)", "10Y & 30Y spot",
                             "[(1+r₃₀)³⁰/(1+r₁₀)¹⁰]^(1/20)−1",
                             "Ultra-long premium — fiscal sustainability signal"),
                        ]
                    ]),
                ], style={"width":"100%","borderCollapse":"collapse"}),
            ]), width=12),
        ], className="mt-2"),
    ])
])

# ── Tab: CB Policy Path ────────────────────────────────────────────────────
tab_cb_path = dbc.Tab(label="🏦 CB Path", tab_id="t-cb-path", children=[
    html.Div(className="p-3", children=[
        dbc.Row([
            dbc.Col(SEC_TITLE(
                "Central Bank Policy Rate Path",
                "OIS-implied rate path vs current policy rates · negative 12M delta = cuts priced",
            ), width=9),
            dbc.Col(dbc.Alert(
                "⚠️ All OIS tickers require terminal verification",
                color="warning", dismissable=True,
                style={"fontSize": "10px", "fontFamily": FONT_FAMILY, "padding": "5px 10px"},
            ), width=3),
        ], className="mb-2", align="center"),
        dbc.Row([
            dbc.Col([
                html.Label("Central Banks:", style={"color": TEXT_MUT, "fontSize": "11px",
                                                     "fontFamily": FONT_FAMILY, "marginRight": "8px"}),
                dbc.Checklist(
                    id="cb-path-sel",
                    options=_OIS_CB_CHECKLIST_OPTIONS,
                    value=list(OIS_PATH_TICKERS.keys()),
                    inline=True,
                    inputStyle={"marginRight": "3px"},
                    labelStyle={"marginRight": "14px", "fontSize": "11px",
                                "color": TEXT, "fontFamily": FONT_FAMILY},
                ),
            ], width=12),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="cb-path-chart",
                              figure=_safe_chart(chart_policy_path, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "370px"}), width=7),
            dbc.Col(dcc.Graph(id="cb-cuts-chart",
                              figure=_safe_chart(chart_implied_cuts, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "370px"}), width=5),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="cb-path-heatmap",
                              figure=_safe_chart(chart_policy_path_heatmap, INITIAL_DATA),
                              config=GRAPH_CFG, style={"height": "340px"}), width=12),
        ]),
        html.Hr(style={"borderColor": BORDER, "margin": "14px 0"}),
        dbc.Row([
            dbc.Col(html.Div(style={**CARD_STYLE, "padding": "12px"}, children=[
                SEC_TITLE("OIS Ticker Reference",
                          "Overnight indexed swap rates · all marked ⚠️ need terminal verification"),
                dash_table.DataTable(
                    data=[
                        {
                            "CB":         f"{OIS_CB_FLAGS.get(cb,'')} {cb}",
                            "Underlying": OIS_CB_UNDERLYING.get(cb, ""),
                            "3M":         tm.get("3M", ""),
                            "6M":         tm.get("6M", ""),
                            "12M":        tm.get("12M", ""),
                            "18M":        tm.get("18M", ""),
                            "24M":        tm.get("24M", ""),
                        }
                        for cb, tm in OIS_PATH_TICKERS.items()
                    ],
                    columns=[{"name": c, "id": c}
                             for c in ["CB", "Underlying", "3M", "6M", "12M", "18M", "24M"]],
                    style_table={"overflowX": "auto", "backgroundColor": BG_DEEP},
                    style_cell={"backgroundColor": BG_DEEP, "color": TEXT,
                                "border": f"1px solid {BORDER}", "fontSize": "10px",
                                "fontFamily": FONT_FAMILY, "padding": "5px 8px",
                                "textAlign": "left"},
                    style_header={"backgroundColor": BG_CARD2, "color": ACCENT,
                                  "fontWeight": "600", "fontSize": "10px",
                                  "fontFamily": FONT_FAMILY},
                ),
            ]), width=12),
        ], className="mt-2"),
    ])
])

# ── Tab 8: Ticker Reference ───────────────────────────────────────────────
# _XCCY_JPY_PAIR_MAP and _XCCY_SGD_PAIR_MAP are defined near the data layer
# (after SGD_3M_RATE_TICKER) and reused here for the ticker reference table.

_TBL_CELL  = {"backgroundColor": BG_DEEP, "color": TEXT, "border": f"1px solid {BORDER}",
               "padding": "5px 8px", "fontSize": "11px", "fontFamily": FONT_FAMILY}
_TBL_HDR   = {"backgroundColor": BG_CARD2, "color": ACCENT, "fontWeight": "bold",
               "border": f"1px solid {BORDER_LT}", "fontFamily": FONT_FAMILY}
_TBL_STYLE = {"overflowX": "auto", "backgroundColor": BG_DEEP}
_VERIFY_COND = [{"if": {"filter_query": '{Status} contains "Verify"'}, "color": YELLOW}]

tab_tickers = dbc.Tab(label="🔧 Tickers", tab_id="t-tickers", children=[
    html.Div(className="p-3", children=[
        dbc.Alert([
            html.Strong("Bloomberg Ticker Reference | "),
            "Tickers marked ⚠️ need terminal verification. "
            "Use BBG functions: DES <ticker> → to verify, SRCH → to find alternatives.",
        ], color="info", style={"fontSize": "11px", "fontFamily": FONT_FAMILY}),

        # ── Row 1: Sovereign Yields | Macro ──────────────────────────────
        dbc.Row([
            dbc.Col([
                html.H6("Sovereign Yield Tickers",
                        style={"color": ACCENT, "fontFamily": FONT_FAMILY, "fontSize": "12px"}),
                dash_table.DataTable(
                    data=[{"Tenor": t, "Country": c, "BBG Ticker": tkr, "Status": "✅"}
                           for t, tm in YIELD_TICKERS.items()
                           for c, tkr in tm.items()],
                    columns=[{"name": col, "id": col} for col in ["Tenor", "Country", "BBG Ticker", "Status"]],
                    style_table=_TBL_STYLE, style_cell=_TBL_CELL, style_header=_TBL_HDR,
                    style_data_conditional=_VERIFY_COND,
                    page_size=12,
                )
            ], width=6),
            dbc.Col([
                html.H6("Macro Tickers (CPI, PMI, Policy Rate, Breakeven)",
                        style={"color": ACCENT, "fontFamily": FONT_FAMILY, "fontSize": "12px"}),
                dash_table.DataTable(
                    data=[{"Category": cat, "Country": c, "BBG Ticker": tkr}
                           for cat, tm in MACRO_TICKERS.items()
                           for c, tkr in tm.items()],
                    columns=[{"name": col, "id": col} for col in ["Category", "Country", "BBG Ticker"]],
                    style_table=_TBL_STYLE, style_cell=_TBL_CELL, style_header=_TBL_HDR,
                    page_size=12,
                )
            ], width=6),
        ]),

        # ── Row 2: FX | XCcy Basis (actual tickers) ──────────────────────
        dbc.Row([
            dbc.Col([
                html.H6("FX vs JPY Tickers",
                        style={"color": ACCENT, "fontFamily": FONT_FAMILY, "fontSize": "12px"}),
                dash_table.DataTable(
                    data=[{"Pair": p, "BBG Ticker": t, "Status": "✅"}
                           for p, t in FX_TICKERS.items()],
                    columns=[{"name": c, "id": c} for c in ["Pair", "BBG Ticker", "Status"]],
                    style_table=_TBL_STYLE, style_cell=_TBL_CELL, style_header=_TBL_HDR,
                    style_data_conditional=_VERIFY_COND,
                )
            ], width=3),
            dbc.Col([
                html.H6("XCcy Basis vs JPY — actual tickers queried",
                        style={"color": ACCENT, "fontFamily": FONT_FAMILY, "fontSize": "12px"}),
                html.P("Basis = JPYI3M Curncy minus foreign 3M rate (computed in Python)",
                       style={"color": TEXT_MUT, "fontSize": "10px", "fontFamily": FONT_FAMILY,
                              "marginBottom": "4px"}),
                dash_table.DataTable(
                    data=(
                        [{"Pair": p, "Foreign 3M Ticker": t, "JPY Rate": JPY_3M_RATE_TICKER,
                          "Status": "✅"}
                          for p, t in _XCCY_JPY_PAIR_MAP.items()]
                    ),
                    columns=[{"name": c, "id": c}
                              for c in ["Pair", "Foreign 3M Ticker", "JPY Rate", "Status"]],
                    style_table=_TBL_STYLE, style_cell=_TBL_CELL, style_header=_TBL_HDR,
                    style_data_conditional=_VERIFY_COND,
                )
            ], width=5),
            dbc.Col([
                html.H6("XCcy Basis vs SGD — actual tickers queried",
                        style={"color": ACCENT, "fontFamily": FONT_FAMILY, "fontSize": "12px"}),
                html.P("Basis = SGDI3M Curncy minus foreign 3M rate (computed in Python)",
                       style={"color": TEXT_MUT, "fontSize": "10px", "fontFamily": FONT_FAMILY,
                              "marginBottom": "4px"}),
                dash_table.DataTable(
                    data=(
                        [{"Pair": p, "Foreign 3M Ticker": t, "SGD Rate": SGD_3M_RATE_TICKER,
                          "Status": "✅"}
                          for p, t in _XCCY_SGD_PAIR_MAP.items()]
                    ),
                    columns=[{"name": c, "id": c}
                              for c in ["Pair", "Foreign 3M Ticker", "SGD Rate", "Status"]],
                    style_table=_TBL_STYLE, style_cell=_TBL_CELL, style_header=_TBL_HDR,
                    style_data_conditional=_VERIFY_COND,
                )
            ], width=4),
        ], className="mt-3"),

        # ── Row 3: JPY Hedge Cost | SGD Hedge Cost ────────────────────────
        dbc.Row([
            dbc.Col([
                html.H6("JPY Hedge Cost Tickers",
                        style={"color": ACCENT, "fontFamily": FONT_FAMILY, "fontSize": "12px"}),
                html.P(f"JPY 3M base rate: {JPY_3M_RATE_TICKER}  |  Hedge cost = JPY 3M − foreign 3M",
                       style={"color": TEXT_MUT, "fontSize": "10px", "fontFamily": FONT_FAMILY,
                              "marginBottom": "4px"}),
                dash_table.DataTable(
                    data=(
                        [{"Country": c, "Foreign 3M Ticker": tkr, "Status": "✅"}
                          for c, tkr in JPY_HEDGE_COST_TICKERS.items()] +
                        [{"Country": "Japan (base)", "Foreign 3M Ticker": JPY_3M_RATE_TICKER,
                          "Status": "✅"}]
                    ),
                    columns=[{"name": c, "id": c} for c in ["Country", "Foreign 3M Ticker", "Status"]],
                    style_table=_TBL_STYLE, style_cell=_TBL_CELL, style_header=_TBL_HDR,
                    style_data_conditional=_VERIFY_COND,
                )
            ], width=6),
            dbc.Col([
                html.H6("SGD Hedge Cost Tickers",
                        style={"color": ACCENT, "fontFamily": FONT_FAMILY, "fontSize": "12px"}),
                html.P(f"SGD 3M base rate: {SGD_3M_RATE_TICKER}  |  Hedge cost = SGD 3M − foreign 3M",
                       style={"color": TEXT_MUT, "fontSize": "10px", "fontFamily": FONT_FAMILY,
                              "marginBottom": "4px"}),
                dash_table.DataTable(
                    data=(
                        [{"Country": c, "Foreign 3M Ticker": tkr, "Status": "✅"}
                          for c, tkr in SGD_HEDGE_COST_TICKERS.items()] +
                        [{"Country": "Singapore (base)", "Foreign 3M Ticker": SGD_3M_RATE_TICKER,
                          "Status": "✅"}]
                    ),
                    columns=[{"name": c, "id": c} for c in ["Country", "Foreign 3M Ticker", "Status"]],
                    style_table=_TBL_STYLE, style_cell=_TBL_CELL, style_header=_TBL_HDR,
                    style_data_conditional=_VERIFY_COND,
                )
            ], width=6),
        ], className="mt-3"),

        # ── Row 4: Real Yields | Inflation Swaps ─────────────────────────
        dbc.Row([
            dbc.Col([
                html.H6("Real Yield Tickers (TIPS / ILBs)",
                        style={"color": ACCENT, "fontFamily": FONT_FAMILY, "fontSize": "12px"}),
                dash_table.DataTable(
                    data=[{"Tenor": t, "Country": c, "BBG Ticker": tkr,
                           "Status": "✅" if c == "US" else "⚠️ Verify"}
                           for t, tm in REAL_YIELD_TICKERS.items()
                           for c, tkr in tm.items()],
                    columns=[{"name": c, "id": c} for c in ["Tenor", "Country", "BBG Ticker", "Status"]],
                    style_table=_TBL_STYLE, style_cell=_TBL_CELL, style_header=_TBL_HDR,
                    style_data_conditional=_VERIFY_COND,
                )
            ], width=6),
            dbc.Col([
                html.H6("Inflation Swap Tickers (Zero-Coupon)",
                        style={"color": ACCENT, "fontFamily": FONT_FAMILY, "fontSize": "12px"}),
                dash_table.DataTable(
                    data=[{"Tenor": t, "Region": r, "BBG Ticker": tkr,
                           "Status": "✅" if r == "US" else "⚠️ Verify"}
                           for t, rm in INFL_SWAP_TICKERS.items()
                           for r, tkr in rm.items()],
                    columns=[{"name": c, "id": c} for c in ["Tenor", "Region", "BBG Ticker", "Status"]],
                    style_table=_TBL_STYLE, style_cell=_TBL_CELL, style_header=_TBL_HDR,
                    style_data_conditional=_VERIFY_COND,
                    page_size=10,
                )
            ], width=6),
        ], className="mt-3"),

        # ── Row 5: OIS Policy Path ────────────────────────────────────────
        dbc.Row([
            dbc.Col([
                html.H6("OIS Policy Path Tickers  ⚠️ All require terminal verification",
                        style={"color": YELLOW, "fontFamily": FONT_FAMILY, "fontSize": "12px"}),
                dash_table.DataTable(
                    data=[{"CB": cb, "Tenor": tenor, "BBG Ticker": tkr, "Status": "⚠️ Verify"}
                           for cb, tm in OIS_PATH_TICKERS.items()
                           for tenor, tkr in tm.items()],
                    columns=[{"name": c, "id": c} for c in ["CB", "Tenor", "BBG Ticker", "Status"]],
                    style_table=_TBL_STYLE, style_cell=_TBL_CELL, style_header=_TBL_HDR,
                    style_data_conditional=_VERIFY_COND,
                    page_size=12,
                )
            ], width=6),
            dbc.Col([
                html.H6("Fiscal Balance & Debt-to-GDP Tickers  ⚠️ All require terminal verification",
                        style={"color": YELLOW, "fontFamily": FONT_FAMILY, "fontSize": "12px"}),
                dash_table.DataTable(
                    data=(
                        [{"Category": "Fiscal Balance (% GDP)", "Country": c, "BBG Ticker": tkr,
                          "Status": "⚠️ Verify"}
                          for c, tkr in FISCAL_GDP_TICKERS.items()] +
                        [{"Category": "Govt Debt (% GDP)", "Country": c, "BBG Ticker": tkr,
                          "Status": "⚠️ Verify"}
                          for c, tkr in DEBT_GDP_TICKERS.items()]
                    ),
                    columns=[{"name": c, "id": c}
                              for c in ["Category", "Country", "BBG Ticker", "Status"]],
                    style_table=_TBL_STYLE, style_cell=_TBL_CELL, style_header=_TBL_HDR,
                    style_data_conditional=_VERIFY_COND,
                    page_size=12,
                )
            ], width=6),
        ], className="mt-3"),
    ])
])

# ── Full App Layout ───────────────────────────────────────────────────────
app.layout = html.Div(
    style={"backgroundColor": BG_DEEP, "minHeight": "100vh", "fontFamily": FONT_FAMILY},
    children=[
        # Header
        html.Div(
            style={"backgroundColor": BG_CARD, "borderBottom": f"2px solid {ACCENT}",
                   "padding": "10px 20px", "marginBottom": "12px"},
            children=[dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Span("GLOBAL FIXED INCOME DASHBOARD",
                                  style={"color": TEXT, "fontWeight": "700", "fontSize": "15px",
                                         "letterSpacing": "0.12em", "fontFamily": FONT_FAMILY}),
                        html.Span("  |  JPY Denominated  |  DM Sovereign Focus",
                                  style={"color": TEXT_MUT, "fontSize": "11px"}),
                    ]),
                    html.Div(
                        f"{INITIAL_DATA['source']}  |  Loaded: {INITIAL_DATA['timestamp']}",
                        style={"color": TEXT_MUT, "fontSize": "10px", "marginTop": "2px",
                               "fontFamily": FONT_FAMILY}),
                ], width=10),
                dbc.Col([
                    dbc.Badge("BBG Live" if bbg.ok else "Indicative",
                              color="success" if bbg.ok else "warning",
                              style={"fontFamily": FONT_FAMILY, "fontSize": "11px",
                                     "padding": "6px 10px"}),
                ], width=2, className="text-end", style={"paddingTop": "6px"}),
            ], align="center")]
        ),
        # KPI Row
        html.Div(build_kpi_row(INITIAL_DATA), style={"padding": "0 20px"}),
        # Tabs
        html.Div(style={"padding": "0 20px"}, children=[
            dbc.Tabs(
                id="main-tabs", active_tab="t-ideas",
                children=[tab_ideas, tab_yields, tab_macro, tab_fx, tab_spreads, tab_breakeven, tab_tips, tab_bond, tab_fwd, tab_cb_path, tab_tickers],
                style={"marginTop": "12px", "fontFamily": FONT_FAMILY},
            )
        ]),
        # Store — pre-loaded once at startup, never re-fetched
        dcc.Store(id="store-data", data=INITIAL_DATA),
        # Per-session UI state stores (thread-safe alternative to mutable function attrs)
        dcc.Store(id="store-yield-state",  data={"tenor": "10Y", "days": 504}),
        dcc.Store(id="store-spread-state", data={"tenor": "10Y", "days": 1260}),
        dcc.Store(id="store-zscore-state", data={"days": 1260}),
        html.Div(
            style={"padding": "18px 20px", "borderTop": f"1px solid {BORDER}",
                   "marginTop": "30px", "color": TEXT_MUT, "fontSize": "10px",
                   "textAlign": "center", "fontFamily": FONT_FAMILY},
            children=[
                "Global Multi Asset  |  JPY-Denominated Fixed Income Dashboard  |  ",
                "For internal research use only — not investment advice  |  ",
                "⚠️ Verify tickers marked in the Tickers tab before live use"
            ]
        ),
    ]
)

# ==========================================================================
#  CALLBACKS
# ==========================================================================


@app.callback(
    Output("ideas-container",         "children"),
    Output("ideas-summary-container", "children"),
    Input("store-data",               "data"),
)

def update_ideas(stored_data):

    ideas = _safe_ideas(stored_data or INITIAL_DATA)
    return build_ideas_datatable(ideas), build_ideas_summary_table(ideas)


@app.callback(
    Output("scorecard-container",      "children"),
    Output("carry-charts-container",   "children"),
    Output("carry-table-container",    "children"),
    Output("macro-surprise-container", "children"),
    Input("store-data",                "data"),
    Input("ideas-hedge-toggle",        "value"),
)
def update_ideas_hedge(stored_data, hedge_base):
    data = stored_data or INITIAL_DATA
    hb   = hedge_base or "unhedged"
    return (
        build_scorecard_panel(data, hb),
        build_carry_charts_panel(data, hb),
        build_carry_rolldown_panel(data, hb),
        build_macro_surprise_panel(data),
    )


@app.callback(
    Output("yld-bar",           "figure"),
    Output("yld-curve",         "figure"),
    Output("yld-hist",          "figure"),
    Output("store-yield-state", "data"),
    Input("yld-2y",      "n_clicks"),
    Input("yld-5y",      "n_clicks"),
    Input("yld-10y",     "n_clicks"),
    Input("yld-30y",     "n_clicks"),
    Input("yld-hist-1y", "n_clicks"),
    Input("yld-hist-2y", "n_clicks"),
    Input("yld-hist-5y", "n_clicks"),
    Input("yld-countries", "value"),
    State("store-data",        "data"),
    State("store-yield-state", "data"),
)
def update_yield_tab(n2, n5, n10, n30, h1y, h2y, h5y, countries, stored, yld_state):
    data      = stored or INITIAL_DATA
    yld_state = yld_state or {"tenor": "10Y", "days": 504}
    tid       = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""
    tenor_map = {"yld-2y": "2Y", "yld-5y": "5Y", "yld-10y": "10Y", "yld-30y": "30Y"}
    days_map  = {"yld-hist-1y": 252, "yld-hist-2y": 504, "yld-hist-5y": 1260}
    tenor = tenor_map.get(tid, yld_state["tenor"])
    days  = days_map.get(tid, yld_state["days"])
    sel   = countries or COUNTRIES
    return (
        chart_yield_bar(data, tenor),
        chart_yield_curve(data, sel),
        chart_hist_yields(tenor, days, sel),
        {"tenor": tenor, "days": days},
    )


@app.callback(
    Output("sprd-compare-chart",  "figure"),
    Output("store-spread-state",  "data"),
    Input("sprd-base-country",  "value"),
    Input("sprd-other-country", "value"),
    Input("sprd-t-2y",    "n_clicks"),
    Input("sprd-t-5y",    "n_clicks"),
    Input("sprd-t-10y",   "n_clicks"),
    Input("sprd-t-30y",   "n_clicks"),
    Input("sprd-p-1y",    "n_clicks"),
    Input("sprd-p-2y",    "n_clicks"),
    Input("sprd-p-3y",    "n_clicks"),
    Input("sprd-p-5y",    "n_clicks"),
    Input("sprd-p-10y",   "n_clicks"),
    Input("sprd-p-15y",   "n_clicks"),
    Input("sprd-p-20y",   "n_clicks"),
    Input("sprd-p-30y",   "n_clicks"),
    State("store-spread-state", "data"),
)
def update_spread_compare(base, other,
                          _t2, _t5, _t10, _t30,
                          _p1, _p2, _p3, _p5, _p10, _p15, _p20, _p30,
                          sprd_state):
    sprd_state = sprd_state or {"tenor": "10Y", "days": 1260}
    tenor_map  = {"sprd-t-2y": "2Y", "sprd-t-5y": "5Y",
                  "sprd-t-10y": "10Y", "sprd-t-30y": "30Y"}
    period_map = {"sprd-p-1y": 252, "sprd-p-2y": 504, "sprd-p-3y": 756,
                  "sprd-p-5y": 1260, "sprd-p-10y": 2520, "sprd-p-15y": 3780,
                  "sprd-p-20y": 5040, "sprd-p-30y": 7560}
    tid   = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""
    tenor = tenor_map.get(tid, sprd_state["tenor"])
    days  = period_map.get(tid, sprd_state["days"])
    return (
        chart_yield_comparison(base or _SPRD_BASE_DEFAULT, other or _SPRD_OTHER_DEFAULT,
                               tenor, days),
        {"tenor": tenor, "days": days},
    )


@app.callback(
    Output("sprd-heatmap-countries", "value"),
    Input("sprd-heatmap-all",  "n_clicks"),
    Input("sprd-heatmap-none", "n_clicks"),
    prevent_initial_call=True,
)
def update_sprd_heatmap_all_none(_all, _none):
    tid = (ctx.triggered[0]["prop_id"].split(".")[0]
           if ctx.triggered else "")
    return COUNTRIES if tid == "sprd-heatmap-all" else []


@app.callback(
    Output("sprd-heatmap-graph", "figure"),
    Input("sprd-heatmap-countries", "value"),
    State("store-data", "data"),
    prevent_initial_call=True,
)
def update_sprd_heatmap(countries_sel, stored):
    data = stored or INITIAL_DATA
    sel  = countries_sel or COUNTRIES
    return _safe_chart(chart_yield_spread_heatmap, data, sel)


@app.callback(
    Output("sprd-zscore-graph",   "figure"),
    Output("store-zscore-state",  "data"),
    Input("sprd-heatmap-countries", "value"),
    Input("sprd-z-p-1y",   "n_clicks"),
    Input("sprd-z-p-2y",   "n_clicks"),
    Input("sprd-z-p-3y",   "n_clicks"),
    Input("sprd-z-p-5y",   "n_clicks"),
    Input("sprd-z-p-10y",  "n_clicks"),
    Input("sprd-z-p-15y",  "n_clicks"),
    Input("sprd-z-p-20y",  "n_clicks"),
    Input("sprd-z-p-30y",  "n_clicks"),
    State("store-data",        "data"),
    State("store-zscore-state", "data"),
    prevent_initial_call=True,
)
def update_sprd_zscore(countries_sel,
                       _p1, _p2, _p3, _p5, _p10, _p15, _p20, _p30,
                       stored, zscore_state):
    zscore_state = zscore_state or {"days": 1260}
    period_map   = {"sprd-z-p-1y": 252, "sprd-z-p-2y": 504, "sprd-z-p-3y": 756,
                    "sprd-z-p-5y": 1260, "sprd-z-p-10y": 2520, "sprd-z-p-15y": 3780,
                    "sprd-z-p-20y": 5040, "sprd-z-p-30y": 7560}
    tid  = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""
    days = period_map.get(tid, zscore_state["days"])
    data = stored or INITIAL_DATA
    sel  = countries_sel or COUNTRIES
    return (
        _safe_chart(chart_zscore_spread_heatmap, data, sel, days),
        {"days": days},
    )

# ==========================================================================
# MACRO TIME SERIES EXPLORER — PERIOD BUTTON + CHART CALLBACKS
# ==========================================================================

_MACRO_TS_PERIODS = ["MTD", "YTD", "1Y", "3Y", "5Y", "10Y", "30Y", "MAX"]

@app.callback(
    Output("macro-ts-start-date", "value"),
    Output("macro-ts-end-date",   "value"),
    [Input(f"macro-ts-period-{p.lower()}", "n_clicks") for p in _MACRO_TS_PERIODS],
    prevent_initial_call=True,
)
def update_macro_ts_period(*n_clicks):
    """
    When a period button is clicked, auto-set start and end dates.
    """
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
    # Extract period label from id like "macro-ts-period-5y" → "5Y"
    period = btn_id.replace("macro-ts-period-", "").upper()

    today = datetime.today()
    end_date = today.strftime("%Y-%m-%d")

    if period == "MTD":
        start = today.replace(day=1)
    elif period == "YTD":
        start = today.replace(month=1, day=1)
    elif period == "1Y":
        start = today - timedelta(days=365)
    elif period == "3Y":
        start = today - timedelta(days=365 * 3)
    elif period == "5Y":
        start = today - timedelta(days=365 * 5)
    elif period == "10Y":
        start = today - timedelta(days=365 * 10)
    elif period == "30Y":
        start = today - timedelta(days=365 * 30)
    elif period == "MAX":
        start = datetime(1970, 1, 1)
    else:
        start = today - timedelta(days=365 * 5)

    return start.strftime("%Y-%m-%d"), end_date


@app.callback(
    [Output(f"macro-ts-period-{p.lower()}", "color") for p in _MACRO_TS_PERIODS],
    [Input(f"macro-ts-period-{p.lower()}", "n_clicks") for p in _MACRO_TS_PERIODS],
)
def highlight_macro_ts_period(*n_clicks):
    """
    Highlight the active period button (primary), dim the rest (secondary).
    """
    if not ctx.triggered or all(n == 0 for n in n_clicks):
        # Default: 5Y is active
        return ["primary" if p == "5Y" else "secondary" for p in _MACRO_TS_PERIODS]

    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
    return [
        "primary" if f"macro-ts-period-{p.lower()}" == btn_id else "secondary"
        for p in _MACRO_TS_PERIODS
    ]


@app.callback(
    Output("macro-heatmap-graph", "figure"),
    Input("macro-heatmap-countries", "value"),
    Input("store-data", "data"),
)
def update_macro_heatmap(selected_countries, stored_data):
    """Re-render macro heatmap filtered to the ticked countries."""
    data = stored_data or INITIAL_DATA
    countries = selected_countries or COUNTRIES
    return _safe_chart(chart_macro_heatmap, data, INITIAL_ZSCORES, countries)


@app.callback(
    Output("macro-ts-chart", "figure"),
    Input("macro-ts-countries",   "value"),
    Input("macro-ts-indicators",  "value"),
    Input("macro-ts-start-date",  "value"),
    Input("macro-ts-end-date",    "value"),
    Input("macro-ts-normalise",   "value"),
    Input("macro-ts-dual-axis",   "value"),
)
def update_macro_ts_chart(countries, indicators, start_date, end_date,
                          normalise_val, dual_val):
    """
    Interactive macro time series chart beside the macro heatmap.
    - Multi-select countries & indicators (from MACRO_TICKERS)
    - Start / End date range filtering
    - Normalise checkbox  → rebases every series to 100 at its first value
    - Dual Y-Axis checkbox → first indicator on left axis, remaining on right
    Data source: MACRO_HISTORY (pre-loaded at startup), fallback to live BBG bdh.
    """
    if not countries or not indicators:
        return _empty_fig("Select at least one country and one indicator")

    do_norm = "norm" in (normalise_val or [])
    do_dual = "dual" in (dual_val or []) and len(indicators) >= 2

    # ── Parse date boundaries ─────────────────────────────────────────────
    try:
        dt_start = pd.Timestamp(start_date)
    except Exception:
        dt_start = pd.Timestamp.today() - pd.DateOffset(years=5)
    try:
        dt_end = pd.Timestamp(end_date)
    except Exception:
        dt_end = pd.Timestamp.today()

    # ── Build figure (with secondary_y when dual mode) ────────────────────
    if do_dual:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    DASH_STYLES = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]
    trace_count = 0

    for ind_idx, indicator in enumerate(indicators):
        tmap = MACRO_TICKERS.get(indicator, {})
        if not tmap:
            continue

        use_secondary = do_dual and ind_idx >= 1
        dash_style = DASH_STYLES[ind_idx % len(DASH_STYLES)]

        for country in countries:
            ticker = tmap.get(country)
            if not ticker:
                continue

            # ── 1) Try pre-loaded MACRO_HISTORY ───────────────────────────
            series = None
            if MACRO_HISTORY and indicator in MACRO_HISTORY:
                series = MACRO_HISTORY[indicator].get(country)

            # ── 2) Fallback: live Bloomberg bdh pull ──────────────────────
            if series is None and bbg.ok:
                try:
                    end_str   = dt_end.strftime("%Y%m%d")
                    start_str = dt_start.strftime("%Y%m%d")
                    df_bbg = bbg.bdh([ticker], "PX_LAST", start_str, end_str)
                    if not df_bbg.empty:
                        col = (ticker if ticker in df_bbg.columns
                               else (df_bbg.columns[0]
                                     if len(df_bbg.columns) == 1 else None))
                        if col is not None:
                            series = df_bbg[col].dropna()
                except Exception:
                    pass

            if series is None or (hasattr(series, '__len__') and len(series) == 0):
                continue

            # ── Ensure pandas Series, filter date range ───────────────────
            s = series.copy()
            s.index = pd.to_datetime(s.index)
            s = s.sort_index()
            s = s.loc[(s.index >= dt_start) & (s.index <= dt_end)].dropna()
            if len(s) == 0:
                continue

            # ── Normalise to 100 at first observation in range ────────────
            if do_norm:
                v0 = s.iloc[0]
                if v0 != 0:
                    s = s / v0 * 100.0
                else:
                    s = s - v0 + 100.0

            # ── Build trace ───────────────────────────────────────────────
            color     = CCOLORS.get(country, ACCENT)
            flag      = _MACRO_TS_FLAGS.get(country, "")
            ind_label = _MACRO_TS_DISPLAY.get(indicator, indicator)
            label     = f"{flag} {country} — {ind_label}"

            trace = go.Scatter(
                x=s.index,
                y=s.values,
                mode="lines",
                name=label,
                line=dict(color=color, width=2, dash=dash_style),
                hovertemplate=(
                    f"{label}<br>"
                    "%{x|%Y-%m-%d}: %{y:.2f}<extra></extra>"
                ),
            )

            if do_dual:
                fig.add_trace(trace, secondary_y=use_secondary)
            else:
                fig.add_trace(trace)

            trace_count += 1

    # ── Empty-state guard ─────────────────────────────────────────────────
    if trace_count == 0:
        return _empty_fig(
            "No historical data for selection.\n"
            "Connect Bloomberg or check MACRO_TICKERS."
        )

    # ── Axis labels ───────────────────────────────────────────────────────
    if do_dual:
        lbl_left  = _MACRO_TS_DISPLAY.get(indicators[0], indicators[0])
        lbl_right = _MACRO_TS_DISPLAY.get(indicators[1], indicators[1])
        if do_norm:
            lbl_left  += " (norm)"
            lbl_right += " (norm)"
        fig.update_yaxes(
            title_text=lbl_left,  secondary_y=False,
            gridcolor=BORDER, zerolinecolor=BORDER,
            title_font=dict(size=10, family=FONT_FAMILY, color=TEXT),
            tickfont=dict(size=9, family=FONT_FAMILY, color=TEXT_MUT),
        )
        fig.update_yaxes(
            title_text=lbl_right, secondary_y=True,
            gridcolor=BORDER, zerolinecolor=BORDER,
            title_font=dict(size=10, family=FONT_FAMILY, color=TEXT),
            tickfont=dict(size=9, family=FONT_FAMILY, color=TEXT_MUT),
        )
    else:
        y_title = ("Normalised (100 = start)" if do_norm
                   else _MACRO_TS_DISPLAY.get(indicators[0], indicators[0]))
        fig.update_yaxes(title_text=y_title)

    # ── Layout polish ─────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text="Macro Time Series Explorer",
            font=dict(size=12, color=TEXT, family=FONT_FAMILY),
        ),
        xaxis_title="",
        legend=dict(
            orientation="h", y=-0.28, x=0.0,
            font=dict(size=8, color=TEXT, family=FONT_FAMILY),
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
        margin=dict(l=50, r=50, t=36, b=70),
    )

    return _dark(fig)
# ==========================================================================
#  TIPS SIMULATION CALLBACKS
# ==========================================================================


@app.callback(
    Output("tips-sim-ry-start", "value"),
    Output("tips-sim-be-start", "value"),
    Output("tips-sim-ry-end",   "value"),
    Output("tips-sim-be-end",   "value"),
    Input("tips-sim-instrument", "value"),
    Input("tips-sim-reset",      "n_clicks"),
    State("store-data",          "data"),
    prevent_initial_call=False,
)
def populate_sim_inputs(instrument, _reset, stored):
    """Auto-populate simulator inputs from live/stored market data when instrument changes."""
    data    = stored or INITIAL_DATA
    inst    = SIM_INSTRUMENTS.get(instrument or "US TIPS 10Y", SIM_INSTRUMENTS["US TIPS 10Y"])
    country = inst["country"]

    ry_live = data.get("real_yields", {}).get("10Y", {}).get(country)
    be_live = data["macro"].get("BREAKEVEN_10Y", {}).get(country)

    # Use live data if available; otherwise use IND_HIST_STATS long-run mean as default
    ry_stats = IND_HIST_STATS.get("REAL_YIELD_10Y", {})
    be_stats = IND_HIST_STATS.get("BREAKEVEN_10Y",  {})

    ry_default = ry_live if ry_live is not None else (ry_stats[country][0] if country in ry_stats else 2.0)
    be_default = be_live if be_live is not None else (be_stats[country][0] if country in be_stats else 2.35)

    return (
        round(ry_default, 2),
        round(be_default, 2),
        round(ry_default, 2),   # target defaults to current (no-change)
        round(be_default, 2),
    )


@app.callback(
    Output("tips-sim-decomp",      "figure"),
    Output("tips-sim-heatmap",     "figure"),
    Output("tips-sim-path-chart",  "figure"),
    Output("tips-sim-summary",     "figure"),
    Input("tips-sim-instrument",   "value"),
    Input("tips-sim-ry-start",     "value"),
    Input("tips-sim-ry-end",       "value"),
    Input("tips-sim-be-start",     "value"),
    Input("tips-sim-be-end",       "value"),
    Input("tips-sim-horizon",      "value"),
    Input("tips-sim-path",         "value"),
    State("store-data",            "data"),
    prevent_initial_call=False,
)
def update_sim_outputs(instrument, ry_start, ry_end, be_start, be_end,
                       horizon, path, stored):
    """Compute TIPS total return scenario and render all output charts."""
    data = stored or INITIAL_DATA

    # --- Resolve inputs with safe defaults ---
    inst    = SIM_INSTRUMENTS.get(instrument or "US TIPS 10Y", SIM_INSTRUMENTS["US TIPS 10Y"])
    country = inst["country"]
    maturity = inst["maturity"]
    coupon   = inst["coupon"]

    ry_stats = IND_HIST_STATS.get("REAL_YIELD_10Y", {})
    be_stats = IND_HIST_STATS.get("BREAKEVEN_10Y",  {})

    def _safe_val(v, fallback):
        return v if (v is not None and not (isinstance(v, float) and np.isnan(v))) else fallback

    ry_live = data.get("real_yields", {}).get("10Y", {}).get(country)
    be_live = data["macro"].get("BREAKEVEN_10Y", {}).get(country)
    ry_def  = ry_live if ry_live is not None else (ry_stats[country][0] if country in ry_stats else 2.0)
    be_def  = be_live if be_live is not None else (be_stats[country][0] if country in be_stats else 2.35)

    ry_s = _safe_val(ry_start, ry_def)
    ry_e = _safe_val(ry_end,   ry_def)
    be_s = _safe_val(be_start, be_def)
    be_e = _safe_val(be_end,   be_def)
    hm   = int(_safe_val(horizon, 6))
    ps   = path or "linear"

    # Rolldown estimate: (ry10 − ry5) / 5 × horizon_years × 100 bps
    ry5_live  = data.get("real_yields", {}).get("5Y", {}).get(country)
    if ry5_live is not None and ry_s is not None:
        rolldown_bps = round((ry_s - ry5_live) / 5.0 * (hm / 12.0) * 100, 1)
    else:
        rolldown_bps = 0.0

    # --- TIPS scenario ---
    tips_res = compute_tips_scenario(
        ry_s, ry_e, be_s, be_e, hm, coupon, maturity, rolldown_bps
    )
    # --- Nominal scenario: same maturity/coupon, yield = ry + be ---
    nom_coupon = coupon + be_s   # approx nominal coupon = real coupon + starting BE
    nom_res    = compute_nominal_scenario(
        ry_s + be_s, ry_e + be_e, hm, nom_coupon, maturity
    )

    fig_decomp  = _safe_chart(chart_tips_sim_decomp, tips_res, nom_res, hm)
    fig_heatmap = _safe_chart(chart_tips_sim_heatmap, ry_s, be_s, hm, coupon, maturity)
    fig_path    = _safe_chart(chart_tips_sim_path,
                              ry_s, ry_e, be_s, be_e, hm, coupon, maturity, ps, rolldown_bps)
    fig_summary = _safe_chart(_build_sim_summary, tips_res, nom_res, hm,
                               ry_s, ry_e, be_s, be_e)

    return fig_decomp, fig_heatmap, fig_path, fig_summary


# ==========================================================================
#  BOND RETURN SIMULATOR CALLBACKS
# ==========================================================================

@app.callback(
    Output("bond-sim-yield-start", "value"),
    Output("bond-sim-coupon",      "value"),
    Input("bond-sim-country",      "value"),
    Input("bond-sim-tenor",        "value"),
    Input("bond-sim-reset",        "n_clicks"),
    State("store-data",            "data"),
    prevent_initial_call=False,
)
def populate_bond_sim_inputs(country, tenor, _reset, stored):
    """Auto-fill starting yield and coupon from live market data when country/tenor changes."""
    data = stored or INITIAL_DATA
    c    = country or "US"
    t    = tenor   or "10Y"
    y    = data.get("yields", {}).get(t, {}).get(c)
    val  = round(y, 3) if y is not None else None
    return val, val   # yield-start, coupon both default to live yield


@app.callback(
    Output("bond-sim-waterfall",   "figure"),
    Output("bond-sim-heatmap",     "figure"),
    Output("bond-sim-summary",     "figure"),
    Output("bond-sim-path",        "figure"),
    Output("bond-sim-country-bar", "figure"),
    Input("bond-sim-country",      "value"),
    Input("bond-sim-tenor",        "value"),
    Input("bond-sim-horizon",      "value"),
    Input("bond-sim-parallel",     "value"),
    Input("bond-sim-spread",       "value"),
    Input("bond-sim-policy",       "value"),
    Input("bond-sim-yield-start",  "value"),
    Input("bond-sim-coupon",       "value"),
    Input("bond-sim-path-shape",   "value"),
    Input("bond-sim-reset",        "n_clicks"),
    State("store-data",            "data"),
    prevent_initial_call=False,
)
def update_bond_sim_outputs(country, tenor, horizon, parallel_bps, spread_bps,
                             policy_bps, yield_start, coupon_input, path_shape,
                             _reset, stored):
    """Compute sovereign bond return decomposition and render all output charts."""
    data = stored or INITIAL_DATA

    def _sv(v, default):
        return v if (v is not None and not (isinstance(v, float) and np.isnan(v))) else default

    c   = country or "US"
    t   = tenor   or "10Y"
    hm  = int(_sv(horizon,       12))
    par = float(_sv(parallel_bps, 0))
    spd = float(_sv(spread_bps,   0))
    pol = float(_sv(policy_bps,   0))
    ps  = path_shape or "linear"

    # Resolve starting yield
    y_live = data.get("yields", {}).get(t, {}).get(c)
    y_s    = float(_sv(yield_start, y_live if y_live is not None else 4.0))

    # Coupon: use override if provided, else at-par (= yield_start)
    coupon_pct = float(_sv(coupon_input, y_s))

    maturity  = _BOND_TENOR_MATURITY.get(t, 10.0)
    delta_bps = par + spd   # pol is scenario context only — not a yield shock
    roll_bps  = _bond_roll_bps(data, c, t, hm)

    result = compute_bond_scenario(
        yield_start=y_s,
        delta_yield_bps=delta_bps,
        horizon_months=hm,
        coupon_pct=coupon_pct,
        maturity_years=maturity,
        rolldown_bps=roll_bps,
    )

    no_data_msg = f"No yield data for {c} {t} — connect Bloomberg"
    if y_live is None:
        return (_empty_fig(no_data_msg),) * 5

    waterfall   = _safe_chart(chart_bond_sim_waterfall, result, hm, c, t)
    heatmap     = _safe_chart(chart_bond_sim_heatmap, y_s, roll_bps,
                               result["carry"], hm, maturity)
    summary     = _safe_chart(_build_bond_sim_summary, result, hm,
                               y_s, par, spd, pol, c, t)
    path_chart  = _safe_chart(chart_bond_sim_path, y_s, delta_bps, hm,
                               coupon_pct, maturity, roll_bps, ps)
    # Pass coupon override to country bar only if user explicitly set one
    coupon_ovr  = float(coupon_input) if coupon_input is not None else None
    country_bar = _safe_chart(chart_bond_sim_country_bar, data, t, hm,
                               par + spd, 0.0, coupon_ovr)

    return waterfall, heatmap, summary, path_chart, country_bar


# ==========================================================================
#  FORWARD RATE MONITOR CALLBACKS
# ==========================================================================


@app.callback(
    Output("fwd-bar",     "figure"),
    Output("fwd-curve",   "figure"),
    Output("fwd-premium", "figure"),
    Input("fwd-segment",  "value"),
    Input("fwd-countries","value"),
    State("store-data",   "data"),
)
def update_fwd_tab(fwd_seg, countries, stored):
    data = stored or INITIAL_DATA
    seg  = fwd_seg   or "5s10s"
    sel  = countries or COUNTRIES
    return (
        _safe_chart(chart_fwd_bar,     data, seg),
        _safe_chart(chart_fwd_curve,   data, sel),
        _safe_chart(chart_fwd_premium, data),
    )


# ==========================================================================
#  CB POLICY PATH CALLBACKS
# ==========================================================================


@app.callback(
    Output("cb-path-chart",   "figure"),
    Output("cb-cuts-chart",   "figure"),
    Output("cb-path-heatmap", "figure"),
    Input("cb-path-sel",      "value"),
    State("store-data",       "data"),
)
def update_cb_path(cbs_sel, stored):
    data = stored or INITIAL_DATA
    sel  = cbs_sel or list(OIS_PATH_TICKERS.keys())
    return (
        _safe_chart(chart_policy_path,         data, sel),
        _safe_chart(chart_implied_cuts,         data),
        _safe_chart(chart_policy_path_heatmap, data),
    )


# ==========================================================================
#  ENTRY POINT
# ==========================================================================

if __name__ == "__main__":

    sep = "=" * 65
    print(sep)
    print("  GLOBAL FIXED INCOME DASHBOARD | JPY Denominated | DM Sovereigns")
    print(sep)
    print(f"  Bloomberg  : {'✅  Connected (live data)' if bbg.ok else '⚠️   Not connected — all market data N/A (no indicative fallback)'}")
    print()
    print("  🌐  Dashboard → http://localhost:8050")
    print(sep)
    app.run(debug=True, host="127.0.0.1", port=8050)
