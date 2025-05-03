#!/usr/bin/env python3
"""
worldspice_pure_spices.py
=========================

Variant‑level scraper for the “Pure Spices” collection on WorldSpice.

Columns
-------
name | form | size_label | net_weight_g | price_usd | in_stock | url
"""
import argparse
import random
import re
import time
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup, FeatureNotFound

# ───────────────────────── Constants ─────────────────────────
BASE_URL   = "https://worldspice.com"
COLLECTION = f"{BASE_URL}/collections/pure-spices"
HEADERS    = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

FORM_KEYWORDS = {
    "ground", "whole", "cracked", "powder", "granulated",
    "seed", "leaf", "flakes", "coarse", "fine",
}

SIZE_ORDER = [
    "Tiny", "Extra Small", "Small", "Medium", "Large", "Extra Large",
    "XL", "XXL", "Bulk", "1 lb.", "2 lb.", "3 lb.", "4 lb."
]

WEIGHT_RE_INLINE = re.compile(
    r"(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>oz|ounce|ounces|lb\.?|lbs\.?|pound|kg|kilogram|g|gram)s?",
    flags=re.I,
)
WEIGHT_RE_HTML = re.compile(r"\(([0-9]+)\s*g\)")

UNIT_TO_G = {
    "g": 1, "gram": 1, "grams": 1,
    "kg": 1000, "kilogram": 1000,
    "oz": 28.3495, "ounce": 28.3495, "ounces": 28.3495,
    "lb": 453.592, "lb.": 453.592, "lbs": 453.592,
    "lbs.": 453.592, "pound": 453.592,
}

# ───────────────────────── Utilities ─────────────────────────
def polite_get(url: str, min_delay: float) -> requests.Response:
    time.sleep(min_delay + random.random())   # ≤1 s jitter
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r

def make_soup(html: str):
    try:
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser")

def find_product_links(html: str) -> Set[str]:
    anchors = make_soup(html).select('a[href^="/products/"]')
    return {urljoin(BASE_URL, a["href"].split("?", 1)[0]) for a in anchors}

# ───────────────────────── Weight helpers ─────────────────────────
def weight_from_variant_json(v: Dict) -> Optional[float]:
    """Tier‑1 & Tier‑2: pull grams or weight+unit from Shopify JSON."""
    grams = v.get("grams", 0)
    if grams:
        return float(grams)

    wt, unit = v.get("weight"), (v.get("weight_unit") or "").lower()
    if wt and unit in UNIT_TO_G:
        return round(wt * UNIT_TO_G[unit], 3)
    return None

def weight_from_token(token: str) -> Optional[float]:
    """Parse '1 lb', '2.5oz', etc. in variant title."""
    m = WEIGHT_RE_INLINE.search(token)
    if not m:
        return None
    val = float(m.group("val"))
    unit = m.group("unit").lower().rstrip(".")
    return round(val * UNIT_TO_G[unit], 3)

def weights_from_html(html: str) -> List[float]:
    """Tier‑3: extract all '(74g)' etc. lines from product page."""
    return sorted({float(g) for g in WEIGHT_RE_HTML.findall(html)})

# ───────────────────────── Token classifier ─────────────────────────
def classify_tokens(tokens: List[str]):
    """
    Return (form, size_label, weight_from_title).
    """
    form = size_label = None
    weight_inline = None

    for tok in tokens:
        if weight_inline is None:
            weight_inline = weight_from_token(tok)
            if weight_inline:
                continue
        if form is None and tok.lower() in FORM_KEYWORDS:
            form = tok.title()
            continue
        if size_label is None and tok:
            size_label = tok.title()
    return form, size_label, weight_inline

# ───────────────────────── Variant parser ─────────────────────────
def parse_product_variants(product_url: str, min_delay: float) -> List[Dict]:
    """
    Build rows for every variant, filling net_weight_g with the best available
    data (JSON → inline title → Net‑Weight lines from HTML).
    """
    # 1) JSON for basic variant data
    vjson = polite_get(product_url.rstrip("/") + ".js", min_delay).json()
    name = vjson["title"]
    variants = vjson["variants"]

    # 2) HTML once, to harvest Net‑Weight lines
    html = polite_get(product_url, min_delay).text
    grams_list = weights_from_html(html)

    # Build a mapping size_label -> grams (Small→first, Medium→second, …)
    label_to_weight = {}
    if grams_list:
        # collect size labels in order of appearance among variants
        seen_labels = []
        for v in variants:
            tokens = [t.strip() for t in re.split(r" / |, ", v["title"]) if t.strip()]
            _, lbl, _ = classify_tokens(tokens)
            if lbl and lbl not in seen_labels:
                seen_labels.append(lbl)

        for lbl, g in zip(seen_labels, grams_list):
            label_to_weight[lbl] = g

    rows: List[Dict] = []
    for v in variants:
        tokens = [t.strip() for t in re.split(r" / |, ", v["title"]) if t.strip()]
        form, size_label, weight_inline = classify_tokens(tokens)

        # choose best weight source
        net_g = (
            weight_from_variant_json(v) or
            weight_inline or
            label_to_weight.get(size_label)
        )

        rows.append(
            dict(
                name          = name,
                form          = form,
                size_label    = size_label,
                net_weight_g  = net_g,
                price_usd     = v["price"] / 100,
                in_stock      = v["available"],
                url           = product_url,
            )
        )
    return rows

# ───────────────────────── Crawl loop ─────────────────────────
def crawl_collection(min_delay: float, limit: int) -> List[Dict]:
    seen: Set[str] = set()
    out: List[Dict] = []
    page = 1
    while len(seen) < limit:
        html = polite_get(f"{COLLECTION}?page={page}", min_delay).text
        urls = find_product_links(html) - seen
        if not urls:
            break
        for u in urls:
            if len(seen) >= limit:
                break
            out.extend(parse_product_variants(u, min_delay))
            seen.add(u)
        page += 1
    return out

# ───────────────────────── Main ─────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",   default="worldspice_pure_spices.csv")
    ap.add_argument("--delay", type=float, default=2.0,
                    help="minimum seconds between requests")
    ap.add_argument("--limit", type=int, default=3,
                    help="maximum number of *products* to scrape")
    args = ap.parse_args()

    data = crawl_collection(args.delay, args.limit)
    df = pd.DataFrame(data)
    df.to_csv(args.out, index=False)

    print(f"✓ Scraped {len(df)} variant rows "
          f"from {len(set(r['url'] for r in data))} products.")
    print(f"  Saved → {args.out}\n")
    print(df.head(min(12, len(df))).to_markdown(index=False))
