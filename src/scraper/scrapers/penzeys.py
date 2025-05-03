
from typing import List, Dict, Set
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .utils import polite_get, classify_tokens, parse_weight_token, UNIT_TO_G

BASE="https://www.penzeys.com"

def scrape(limit:int=3, delay:float=2.0)->List[Dict]:
    letters=[chr(c) for c in range(ord('A'), ord('Z')+1)]
    product_urls: Set[str]=set()
    rows=[]
    for letter in letters:
        if len(product_urls)>=limit:
            break
        idx_url=f"{BASE}/shop/spices/?letter={letter}"
        try:
            html=polite_get(idx_url, delay).text
        except Exception:
            continue
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.select('a[href*="/shop/spices/"]'):   # NEW selector
            link = urljoin(BASE, a['href'])
            if link not in product_urls:
                product_urls.add(link)
                rows.extend(parse_product(link, delay))
                if len(product_urls)>=limit:
                    break
    return rows

def parse_product(url:str, delay:float)->List[Dict]:
    html=polite_get(url, delay).text
    soup=BeautifulSoup(html, 'html.parser')
    name_tag=soup.find('h1')
    name=name_tag.get_text(strip=True) if name_tag else "Unknown"
    rows=[]
    # Penzeys lists sizes in select#size-select or divs
    options = soup.select('select#size option, div.product-variant, div#variant-select option')
    if not options:
        options=soup.select('div.product-variant')
    if not options:
        price_tag = soup.select_one('span#price, span.price, div.price')
        price=float(price_tag.get_text(strip=True).replace('$','')) if price_tag else None
        rows.append(dict(
            vendor='penzeys',
            name=name,
            form=None,
            size_label=None,
            net_weight_g=None,
            price_usd=price,
            in_stock=True,
            url=url
        ))
        return rows

    for opt in options:
        text=opt.get_text(" ", strip=True)
        price_match=re.search(r'\$([0-9\.]+)', text)
        price=float(price_match.group(1)) if price_match else None
        tokens=[t.strip() for t in re.split(r" / |, ", text) if t.strip()]
        form,label,wt_title=classify_tokens(tokens)
        grams=wt_title
        rows.append(dict(
            vendor='penzeys',
            name=name,
            form=form,
            size_label=label,
            net_weight_g=grams,
            price_usd=price,
            in_stock=True,
            url=url
        ))
    return rows
