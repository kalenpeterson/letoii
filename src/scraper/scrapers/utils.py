
import time, random, re, requests
from typing import Dict, List, Optional
from bs4 import BeautifulSoup, FeatureNotFound

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

WEIGHT_RE = re.compile(
    r"(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>oz|ounce|ounces|lb\.?|lbs\.?|pound|kg|kilogram|g|gram)s?", re.I
)
UNIT_TO_G = {
    "g":1,"gram":1,"grams":1,
    "kg":1000,"kilogram":1000,
    "oz":28.3495,"ounce":28.3495,"ounces":28.3495,
    "lb":453.592,"lb.":453.592,"lbs":453.592,"lbs.":453.592,"pound":453.592
}

FORM_KEYWORDS = {"ground","whole","powder","cracked","granulated","seed","leaf","flakes","coarse","fine"}

def polite_get(url:str, delay:float=2.0):
    time.sleep(delay+random.random())
    r=requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r

def parse_weight_token(token:str)->Optional[float]:
    m=WEIGHT_RE.search(token)
    if not m:
        return None
    val=float(m.group('val'))
    unit=m.group('unit').lower().rstrip('.')
    return round(val*UNIT_TO_G.get(unit,1),3)

def classify_tokens(tokens:List[str]):
    form=size_label=None
    weight=None
    for t in tokens:
        if weight is None:
            weight=parse_weight_token(t)
            if weight:
                continue
        if form is None and t.lower() in FORM_KEYWORDS:
            form=t.title()
            continue
        if size_label is None:
            size_label=t.title()
    return form,size_label,weight

def make_soup(html:str):
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, 'lxml')
    except (FeatureNotFound, Exception):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, 'html.parser')
