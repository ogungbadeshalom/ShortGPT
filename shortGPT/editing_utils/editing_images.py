from shortGPT.api_utils.image_api import getBingImages
from tqdm import tqdm
import random
import math
import re
import os
import time
import requests

# Per-process run id + seen-URL registry -> fixes image REUSE across renders.
_RUN_ID = int(time.time())
_SEEN_URLS = set()


def searchPexelsImages(query, top=5, api_key=None, download_dir="_pexels_imgs"):
    """Search Pexels photos by query; DOWNLOAD results locally (avoids CDN 403)."""
    key = api_key or os.getenv("PEXELS_API_KEY")
    os.makedirs(download_dir, exist_ok=True)
    if not key:
        return None
    UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": top},
            headers={"Authorization": key, "User-Agent": UA},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        out = []
        import urllib.request as _urllib_request
        for i, p in enumerate(data.get("photos", [])):
            url = p["src"]["large"]
            local = os.path.join(download_dir, f"{_RUN_ID}_{abs(hash(query))}_{i}.jpg")
            try:
                # urllib + Referer header reliably downloads Pexels CDN from datacenter
                req = _urllib_request.Request(url, headers={"User-Agent": UA,
                                                           "Referer": "https://www.bing.com/"})
                with _urllib_request.urlopen(req, timeout=20) as resp:
                    content = resp.read()
                with open(local, "wb") as f:
                    f.write(content)
                out.append({"url": local, "width": p["width"], "height": p["height"]})
            except Exception as e:
                print(f"      [pexels image {i} download failed: {e}]")
        return out if out else None
    except Exception as e:
        print(f"      [pexels image search failed for '{query}': {e}]")
        return None


def searchWebImages(query, top=6, download_dir="_web_imgs", retries=3):
    """Fetch REAL web images (game art/screenshots) via Bing, download locally.
    Returns list of {url(local file), width, height}."""
    os.makedirs(download_dir, exist_ok=True)
    UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    try:
        bing = getBingImages(query, retries=retries) or []
        out = []
        for i, img in enumerate(bing):
            url = img.get("url")
            if not url:
                continue
            # skip obvious placeholder/icon URLs
            if any(x in url.lower() for x in ['svg', 'logo', 'icon', 'spacer', 'blank',
                                              'data:', 'transparent', 'placeholder']):
                continue
            ext = url.lower().rsplit('.', 1)[-1] if '.' in url else 'jpg'
            if ext not in ('jpg', 'jpeg', 'png', 'webp'):
                ext = 'jpg'
            local = os.path.join(download_dir, f"{_RUN_ID}_{abs(hash(query))}_{i}.{ext}")
            # DEDUP: skip URLs we've already fetched this run (fixes reuse)
            if url in _SEEN_URLS:
                continue
            # Try up to 2 times per URL; add Referer header (many hosts 403
            # direct hotlink downloads from datacenter IPs without it).
            got = False
            for attempt in range(2):
                try:
                    ir = requests.get(
                        url, headers={"User-Agent": UA,
                                      "Referer": "https://www.bing.com/",
                                      "Accept": "image/webp,image/*,*/*;q=0.8"},
                        timeout=20)
                    ir.raise_for_status()
                    if len(ir.content) < 4000:
                        break  # too small = placeholder, try next attempt's candidate
                    with open(local, "wb") as f:
                        f.write(ir.content)
                    _SEEN_URLS.add(url)
                    out.append({"url": local,
                                "width": img.get("width", 720),
                                "height": img.get("height", 720)})
                    got = True
                    break
                except Exception:
                    continue
        return out if out else None
    except Exception as e:
        print(f"      [web image search failed for '{query}': {e}]")
        return None


def getImageUrlsTimed(imageTextPairs):
    return [(pair[0], searchImageUrlsFromQuery(pair[1])) for pair in tqdm(imageTextPairs, desc='Search engine queries for images...')]


def searchWikimediaImages(query, top=4, download_dir="_wiki_imgs"):
    """Fetch REAL, factual images from Wikimedia Commons. Keyless, free, and
    WORKS from this datacenter box (verified live). Best for history/mythology/
    finance/factual narration — real named artifacts/photos vs generic stock.

    Returns list of dicts: {url (full), thumb (480px), title, desc, lic}.
    Filters to YouTube-safe licenses (PD/CC0/CC BY/CC BY-SA)."""
    import urllib.request as _u, urllib.parse, json, os, re
    os.makedirs(download_dir, exist_ok=True)
    safe = re.sub(r'\s*(image|photo|picture|pic)\b.*$', '', query).strip()
    safe = re.sub(r'\s+at\s+\d+.*$', '', safe).strip()  # not needed; keep simple
    api = ("https://commons.wikimedia.org/w/api.php?action=query"
           "&generator=search&gsrnamespace=6&gsrlimit=" + str(top) +
           "&gsrsearch=" + urllib.parse.quote(safe) +
           "&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=480&format=json")
    req = _u.Request(api, headers={"User-Agent": "shorts-pipeline/1.0"})
    try:
        with _u.urlopen(req, timeout=25) as resp:
            d = json.loads(resp.read().decode())
    except Exception as e:
        print(f"      [wikimedia search failed for '{query}': {e}]")
        return []
    ok_l = ("PublicDomain", "CC0", "CC BY", "CC BY-SA")
    out = []
    for p in d.get("query", {}).get("pages", {}).values():
        ii = p.get("imageinfo", [{}])[0]
        if not ii:
            continue
        lic = (ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "") or "")
        lic = lic.replace("Public domain", "PublicDomain")
        if any(k in lic for k in ok_l):
            out.append({"url": ii.get("url"), "thumb": ii.get("thumburl"),
                        "title": p.get("title"), "desc": ii.get("descriptionurl"),
                        "lic": lic})
    return out[:top]


def searchImageUrlsFromQuery(query, top=3, expected_dim=[720, 720], retries=3):
    # HARD-FILTER: narrow backup on top of the (already people-banning) prompt.
    # Only block terms that would NEVER legitimately appear in a game-object
    # query. 'model'/'face'/'hands' are deliberately NOT blocked — "pig model",
    # "creeper face", "hand holding controller" are valid GAME images.
    _FORBIDDEN = ['nude', 'nsfw', 'sexy', 'porn', 'hot woman', 'hot man',
                  'bikini', 'underwear', 'girlfriend', 'onlyfans']
    low = query.lower()
    if any(f in low for f in _FORBIDDEN):
        # REJECT entirely: an unsafe query must NOT produce an image.
        # The scene will just show the gameplay background instead of a wrong pic.
        print(f"      [image gate] REJECTED unsafe query: {query!r}")
        return None

    # PREFER Pexels (verified, search-matched images served by an official API —
    # reliable from this datacenter box). Web/Bing scraping is flaky and is only
    # a fallback. Strip the trailing " image"/"photo" noise for Pexels matching.
    pexels_query = re.sub(r'\s*(image|photo|picture|pic)$', '', query.strip()).strip()
    images = searchPexelsImages(pexels_query, top=top)
    if not images:
        # Broaden: for game queries, fall back to just the theme keyword(s)
        # (e.g. "minecraft pig model image" -> "minecraft") so Pexels finds something.
        broad = re.sub(r'\s*(pig model|model|cave|character|world|building|creeper|game).*$', '', pexels_query, flags=re.I).strip()
        if broad and broad != pexels_query:
            images = searchPexelsImages(broad, top=top)
    if not images:
        images = searchWebImages(query, top=top, retries=retries)
    if not images:
        try:
            import time; time.sleep(1.0)
        except Exception:
            pass
        images = searchWebImages(query, top=top, retries=retries)
    if images:
        distances = list(map(lambda x: math.dist([x['width'], x['height']], expected_dim), images[0:top]))
        best = min(range(len(distances)), key=lambda i: distances[i])
        candidates = [i for i in range(len(distances)) if distances[i] <= distances[best] * 1.3]
        pick = random.choice(candidates)
        return images[pick]['url']
    return None