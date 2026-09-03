from shortGPT.api_utils.image_api import getBingImages
from tqdm import tqdm
import random
import math
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
            params={"query": query, "per_page": top, "orientation": "portrait"},
            headers={"Authorization": key, "User-Agent": UA},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        out = []
        for i, p in enumerate(data.get("photos", [])):
            url = p["src"]["large"]
            local = os.path.join(download_dir, f"{_RUN_ID}_{abs(hash(query))}_{i}.jpg")
            try:
                ir = requests.get(url, headers={"User-Agent": UA}, timeout=20)
                ir.raise_for_status()
                with open(local, "wb") as f:
                    f.write(ir.content)
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
            if any(x in url.lower() for x in ['svg', 'logo', 'icon', 'spacer', 'blank']):
                continue
            ext = url.lower().rsplit('.', 1)[-1] if '.' in url else 'jpg'
            if ext not in ('jpg', 'jpeg', 'png', 'webp'):
                ext = 'jpg'
            local = os.path.join(download_dir, f"{_RUN_ID}_{abs(hash(query))}_{i}.{ext}")
            try:
                # DEDUP: skip URLs we've already fetched this run (fixes reuse)
                if url in _SEEN_URLS:
                    continue
                ir = requests.get(url, headers={"User-Agent": UA}, timeout=20)
                ir.raise_for_status()
                if len(ir.content) < 3000:
                    continue  # too small = placeholder
                with open(local, "wb") as f:
                    f.write(ir.content)
                _SEEN_URLS.add(url)
                out.append({"url": local,
                            "width": img.get("width", 720),
                            "height": img.get("height", 720)})
            except Exception as e:
                continue
        return out if out else None
    except Exception as e:
        print(f"      [web image search failed for '{query}': {e}]")
        return None


def getImageUrlsTimed(imageTextPairs):
    return [(pair[0], searchImageUrlsFromQuery(pair[1])) for pair in tqdm(imageTextPairs, desc='Search engine queries for images...')]


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

    # Prefer REAL web images (actual game art/screenshots) over stock Pexels.
    images = searchWebImages(query, top=top, retries=retries)
    if not images:
        return None  # if web search gives nothing usable, DON'T substitute a random stock image
    if images:
        distances = list(map(lambda x: math.dist([x['width'], x['height']], expected_dim), images[0:top]))
        best = min(range(len(distances)), key=lambda i: distances[i])
        candidates = [i for i in range(len(distances)) if distances[i] <= distances[best] * 1.3]
        pick = random.choice(candidates)
        return images[pick]['url']
    return None