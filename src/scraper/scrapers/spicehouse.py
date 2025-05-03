
from typing import List, Dict
import re
from urllib.parse import urljoin
from .utils import polite_get, classify_tokens, parse_weight_token, UNIT_TO_G

BASE="https://www.thespicehouse.com"
COLLECTION="https://www.thespicehouse.com/collections/all"

def scrape(limit:int=3, delay:float=2.0)->List[Dict]:
    from bs4 import BeautifulSoup
    seen=set()
    rows=[]
    page=1
    while len(seen)<limit:
        html=polite_get(f"{COLLECTION}?page={page}", delay).text
        soup=BeautifulSoup(html, 'html.parser')
        links={urljoin(BASE,a['href'].split('?',1)[0]) for a in soup.select('a[href^="/products/"]')}
        new=links-seen
        if not new:
            break
        for url in sorted(new):
            if len(seen)>=limit:
                break
            rows.extend(parse_product(url, delay))
            seen.add(url)
        page+=1
    return rows

def parse_product(url:str, delay:float)->List[Dict]:
    data=polite_get(url.rstrip('/')+'.js', delay).json()
    name=data['title']
    rows=[]
    for v in data['variants']:
        tokens=[t.strip() for t in re.split(r" / |, ", v['title']) if t.strip()]
        form,label,wt_title=classify_tokens(tokens)
        grams=v.get('grams') or 0
        if grams==0:
            weight=v.get('weight')
            unit=v.get('weight_unit','').lower()
            if weight and unit in UNIT_TO_G:
                grams=round(weight*UNIT_TO_G[unit],3)
            else:
                grams=wt_title
        rows.append(dict(
            vendor="spicehouse",
            name=name,
            form=form,
            size_label=label,
            net_weight_g=grams,
            price_usd=v['price']/100,
            in_stock=v['available'],
            url=url
        ))
    return rows
