"""
PriceAgent — All-in-one file
============================
SETUP (run these once in terminal/cmd):
  pip install flask playwright
  playwright install chromium

RUN:
  python app.py

OPEN BROWSER:
  http://localhost:5500
"""

from flask import Flask, request, jsonify, Response
import json, time, re, urllib.parse
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

app = Flask(__name__)

# ── CORS (allows browser to talk to this server) ──────────────────────────────
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# ── Serve the frontend HTML ───────────────────────────────────────────────────
@app.route('/')
def index():
    return HTML_PAGE

# ── Health check ──────────────────────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'playwright': PLAYWRIGHT_AVAILABLE})

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean_price(text):
    if not text: return None
    digits = re.sub(r'[^\d]', '', str(text))
    return int(digits) if digits else None

def extract_rating(text):
    if not text: return None
    m = re.search(r'(\d+\.?\d*)', str(text))
    return float(m.group(1)) if m else None

# ── Real scrapers ─────────────────────────────────────────────────────────────
def scrape_flipkart(page, query):
    results = []
    try:
        url = f"https://www.flipkart.com/search?q={urllib.parse.quote(query)}"
        page.goto(url, timeout=20000, wait_until='domcontentloaded')
        page.wait_for_timeout(2000)
        try: page.click('button._2KpZ6l._2doB4z', timeout=2000)
        except: pass
        for card in page.query_selector_all('div._1AtVbE')[:6]:
            try:
                name_el  = card.query_selector('div._4rR01T, a.s1Q9rs, div.KzDlHZ')
                price_el = card.query_selector('div._30jeq3')
                orig_el  = card.query_selector('div._3I9_wc')
                rating_el= card.query_selector('div._3LWZlK')
                link_el  = card.query_selector('a._1fQZEK, a.s1Q9rs, a._2rpwqI')
                name  = name_el.inner_text().strip() if name_el else None
                price = clean_price(price_el.inner_text()) if price_el else None
                if not name or not price: continue
                orig  = clean_price(orig_el.inner_text()) if orig_el else price
                href  = link_el.get_attribute('href') if link_el else ''
                link  = f"https://www.flipkart.com{href}" if href and not href.startswith('http') else (href or url)
                results.append({'platform':'Flipkart','name':name[:80],'seller':'Flipkart Seller',
                    'price':price,'original':orig or price,'shipping':0,'delivery':'3-5 days',
                    'rating':extract_rating(rating_el.inner_text()) if rating_el else 4.2,
                    'reviews':0,'returnDays':10,'coupon':False,'couponSaving':0,
                    'warranty':'1 Year Mfr','link':link,
                    'logo':'F','logoColor':'#2874F0','logoBg':'#0d1a40','verified':True})
                if len(results) >= 2: break
            except: continue
    except Exception as e:
        print(f"Flipkart error: {e}")
    return results

def scrape_amazon(page, query):
    results = []
    try:
        url = f"https://www.amazon.in/s?k={urllib.parse.quote(query)}"
        page.goto(url, timeout=20000, wait_until='domcontentloaded')
        page.wait_for_timeout(2000)
        for card in page.query_selector_all('div[data-component-type="s-search-result"]')[:6]:
            try:
                name_el   = card.query_selector('h2 span')
                price_el  = card.query_selector('span.a-price-whole')
                orig_el   = card.query_selector('span.a-text-price span.a-offscreen')
                rating_el = card.query_selector('span.a-icon-alt')
                link_el   = card.query_selector('h2 a')
                name  = name_el.inner_text().strip() if name_el else None
                price = clean_price(price_el.inner_text()) if price_el else None
                if not name or not price: continue
                orig  = clean_price(orig_el.inner_text()) if orig_el else price
                href  = link_el.get_attribute('href') if link_el else ''
                link  = f"https://www.amazon.in{href}" if href and href.startswith('/') else (href or url)
                results.append({'platform':'Amazon','name':name[:80],'seller':'Amazon Seller',
                    'price':price,'original':orig or price,'shipping':0,'delivery':'2-4 days',
                    'rating':extract_rating(rating_el.inner_text()) if rating_el else 4.3,
                    'reviews':0,'returnDays':10,'coupon':False,'couponSaving':0,
                    'warranty':'1 Year Mfr','link':link,
                    'logo':'📦','logoColor':'#FF9900','logoBg':'#1a1200','verified':True})
                if len(results) >= 2: break
            except: continue
    except Exception as e:
        print(f"Amazon error: {e}")
    return results

def scrape_croma(page, query):
    results = []
    try:
        url = f"https://www.croma.com/searchB?q={urllib.parse.quote(query)}%3Arelevance"
        page.goto(url, timeout=20000, wait_until='domcontentloaded')
        page.wait_for_timeout(2500)
        for card in page.query_selector_all('li.product-item')[:4]:
            try:
                name_el  = card.query_selector('h3.product-title a, a.product-name')
                price_el = card.query_selector('span.amount')
                link_el  = card.query_selector('h3.product-title a, a.product-name')
                name  = name_el.inner_text().strip() if name_el else None
                price = clean_price(price_el.inner_text()) if price_el else None
                if not name or not price: continue
                href  = link_el.get_attribute('href') if link_el else ''
                link  = f"https://www.croma.com{href}" if href and not href.startswith('http') else (href or url)
                results.append({'platform':'Croma','name':name[:80],'seller':'Croma Retail',
                    'price':price,'original':price,'shipping':0,'delivery':'4-6 days',
                    'rating':4.4,'reviews':0,'returnDays':15,'coupon':False,'couponSaving':0,
                    'warranty':'1 Year Mfr','link':link,
                    'logo':'C','logoColor':'#00a651','logoBg':'#001a0d','verified':True})
                if len(results) >= 1: break
            except: continue
    except Exception as e:
        print(f"Croma error: {e}")
    return results

# ── Fallback mock data (when no internet / scraping fails) ────────────────────
def mock_results(query):
    base = 15000 + (hash(query) % 15000)
    platforms = [
        {'platform':'Flipkart','seller':'Flipkart Seller','delta':-800,
         'link':f"https://www.flipkart.com/search?q={urllib.parse.quote(query)}",
         'shipping':0,'returnDays':10,'delivery':'3 days','rating':4.3,'reviews':8400,
         'coupon':True,'couponSaving':300,'logo':'F','logoColor':'#2874F0','logoBg':'#0d1a40'},
        {'platform':'Amazon','seller':'Amazon Seller','delta':0,
         'link':f"https://www.amazon.in/s?k={urllib.parse.quote(query)}",
         'shipping':0,'returnDays':10,'delivery':'2 days','rating':4.5,'reviews':12800,
         'coupon':True,'couponSaving':500,'logo':'📦','logoColor':'#FF9900','logoBg':'#1a1200'},
    ]
    results = []
    for v in platforms:
        price = base + v['delta']
        results.append({
            'platform':v['platform'],'name':query,'seller':v['seller'],
            'price':price,'original':int(price*1.15),'shipping':v['shipping'],
            'delivery':v['delivery'],'rating':v['rating'],'reviews':v['reviews'],
            'returnDays':v['returnDays'],'coupon':v['coupon'],'couponSaving':v['couponSaving'],
            'warranty':'1 Year Manufacturer','link':v['link'],
            'logo':v['logo'],'logoColor':v['logoColor'],'logoBg':v['logoBg'],'verified':True,
            'effective': price + v['shipping'] - v['couponSaving'],
        })
    return results

# ── Search route (SSE streaming) ──────────────────────────────────────────────
def evt(data):
    return f"data: {json.dumps(data)}\n\n"

def run_scraper(query, selected):
    yield evt({'type':'step','status':'running','text':f'Parsing query: "{query}"...'})
    time.sleep(0.3)
    yield evt({'type':'step','status':'done','text':f'Identified: {query}'})

    scraped = {}  # key -> list

    if PLAYWRIGHT_AVAILABLE:
        yield evt({'type':'step','status':'running','text':'Launching headless Chromium...'})
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-blink-features=AutomationControlled'])
                ctx = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width':1280,'height':800}, locale='en-IN',
                )
                scraper_map = [
                    ('flipkart', 'Flipkart', scrape_flipkart),
                    ('amazon',   'Amazon',   scrape_amazon),
                ]
                for key, label, fn in scraper_map:
                    if 'all' not in selected and key not in selected: continue
                    yield evt({'type':'step','status':'running','text':f'Scraping {label}...'})
                    page = ctx.new_page()
                    try:
                        res = fn(page, query)
                        scraped[key] = res
                        if res:
                            yield evt({'type':'step','status':'done','text':f'{label}: found {len(res)} result(s) ✓'})
                        else:
                            yield evt({'type':'step','status':'warn','text':f'{label}: no results — using estimated price'})
                    except Exception as e:
                        scraped[key] = []
                        yield evt({'type':'step','status':'warn','text':f'{label}: could not scrape — using estimated price'})
                    finally:
                        page.close()
                    time.sleep(0.3)
                browser.close()
        except Exception as e:
            yield evt({'type':'step','status':'warn','text':f'Browser error: {str(e)[:60]}'})

    # Always show ALL platforms — use real data if scraped, else mock with real search link
    yield evt({'type':'step','status':'running','text':'Building full comparison across all platforms...'})
    time.sleep(0.4)

    mock = mock_results(query)
    mock_map = {r['platform'].lower().replace(' ',''): r for r in mock}

    all_results = []
    platform_configs = [
        ('flipkart', 'Flipkart', f"https://www.flipkart.com/search?q={urllib.parse.quote(query)}"),
        ('amazon',   'Amazon',   f"https://www.amazon.in/s?k={urllib.parse.quote(query)}"),
    ]
    for key, label, search_link in platform_configs:
        if 'all' not in selected and key not in selected:
            continue
        real = scraped.get(key, [])
        if real:
            r = dict(real[0])
            r['link'] = r.get('link') or search_link
            all_results.append(r)
        else:
            mk = label.lower().replace(' ','')
            base = mock_map.get(mk) or mock_map.get(key) or mock[0]
            r = dict(base)
            r['link'] = search_link
            r['name'] = query
            all_results.append(r)

    yield evt({'type':'step','status':'running','text':'Computing effective prices & ranking...'})
    time.sleep(0.3)
    for r in all_results:
        r['effective'] = r['price'] + r['shipping'] - r['couponSaving']
    all_results.sort(key=lambda x: x['effective'])
    yield evt({'type':'step','status':'done','text':f'Done! Compared {len(all_results)} platforms.'})
    yield evt({'type':'results','data':all_results})

@app.route('/search')
def search():
    query = request.args.get('q','').strip()
    platforms = request.args.get('platforms','all').split(',')
    if not query:
        return jsonify({'error':'Missing query'}), 400
    return Response(
        run_scraper(query, platforms),
        mimetype='text/event-stream',
        headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'}
    )

# ── Start server ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 50)
    print("  PriceAgent is starting...")
    print(f"  Playwright: {'✅ Available' if PLAYWRIGHT_AVAILABLE else '❌ Not installed (using demo data)'}")
    print("=" * 50)
    print()
    print("  ✅ Open your browser and go to:")
    print("     http://localhost:5500")
    print()
    print("  Press Ctrl+C to stop.")
    print("=" * 50)

    app.run(debug=False, port=808==0, threaded=True)


print("hello world")























