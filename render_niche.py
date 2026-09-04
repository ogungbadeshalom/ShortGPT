#!/usr/bin/env python3
"""Render a sample Short for a given niche, with a themed Pexels background.
Usage: python render_niche.py <niche_key>
niche keys: mystery, mythology, tech, food, gaming
Outputs to /root/ShortGPT/niche_<key>.mp4"""
import os, sys, subprocess, json, time, requests

NICHE = sys.argv[1]
os.chdir('/root/ShortGPT')

# \u2014 niche config: bg query + facts type + output name
CONF = {
    "mystery": {
        "bg": "dark forest fog ruins",
        "facts": "Hidden histories and unsolved mysteries: the story of a place that vanished and the truth historians argue about",
        "out": "niche_mystery.mp4",
    },
    "mythology": {
        "bg": ["ancient greek temple", "roman statue marble", "ancient ruins columns", "greek mythology statue"],
        "facts": "Mythology revealed: the surprising true story behind a famous myth and the secret meaning hidden in it",
        "out": "niche_mythology.mp4",
    },
    "tech": {
        "bg": ["futuristic technology", "artificial intelligence", "server room", "computer chip"],
        "facts": "AI and technology revealed: the surprising hidden truth about artificial intelligence most people don't know",
        "out": "niche_tech.mp4",
    },
    "food": {
        "bg": ["cooking kitchen food", "chef preparing dish", "fresh ingredients", "restaurant kitchen"],
        "facts": "Food secrets revealed: the surprising chemistry behind a famous dish and why it tastes so good",
        "out": "niche_food.mp4",
    },
    "gaming": {
        "bg": ["minecraft", "minecraft gameplay", "minecraft world"],
        "youtube_bg": "https://www.youtube.com/shorts/DYxFa_ZFj_c",  # user's Minecraft gameplay (fresh cookies clear the bot-block)
        "facts": "Minecraft surprising facts: the Creeper was a failed pig model and how it became iconic, plus why the game's original name was Cave Game",
        "out": "niche_gaming.mp4",
    },
    "finance": {
        "bg": ["money finance coins", "stock market graph", "budget calculator", "piggy bank saving"],
        "youtube_bg": "https://www.youtube.com/shorts/DYxFa_ZFj_c",  # SAME background as former video (user's gameplay)
        "facts": "Money and personal finance facts: surprising truths about saving, credit cards, and how money really works that most people don't know (financial literacy, not investment advice)",
        "out": "niche_finance.mp4",
    },
}

def pexels_bg(query):
    """Fetch a themed portrait background from Pexels (>=720x1280, >=20s). query may be str or list."""
    if isinstance(query, str):
        queries = [query]
    else:
        queries = query
    key = os.getenv("PEXELS_API_KEY")
    h = {"Authorization": key, "User-Agent": "Mozilla/5.0"}
    last_err = None
    for q in queries:
        try:
            r = requests.get("https://api.pexels.com/videos/search",
                             headers=h, params={"query": q, "orientation": "portrait",
                                                "per_page": 30}, timeout=60)
            r.raise_for_status()
            for v in r.json().get("videos", []):
                if v["width"] >= 720 and v["height"] >= 1280 and v["duration"] >= 20:
                    best = None
                    for f in v.get("video_files", []):
                        if f.get("width") and f.get("height") and f["width"] >= 720 and f["height"] >= 1280:
                            if best is None or (f["width"]*f["height"]) > (best["width"]*best["height"]):
                                best = f
                    if best:
                        return best["link"]
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"no portrait bg for {query}: {last_err}")

def _use_pexels(query):
    """Download a themed Pexels portrait background to /tmp/niche_bg_raw.mp4."""
    url = pexels_bg(query)
    rr = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=120)
    rr.raise_for_status()
    with open("/tmp/niche_bg_raw.mp4", "wb") as f:
        for chunk in rr.iter_content(1 << 20):
            f.write(chunk)

def build_bg(query, youtube_bg=None):
    os.makedirs("public", exist_ok=True)
    if youtube_bg:
        # Try the user's YouTube video first (fresh cookies usually clear the block).
        print("BG from YouTube:", youtube_bg)
        _dl = subprocess.run(["/root/AutoShorts-AI/.venv/bin/yt-dlp", "--cookies", "/root/shortgpt_cookies.txt",
                              "-f", "bv*[height<=1080]+ba/b[height<=1080]", "-o", "/tmp/niche_bg_raw.%(ext)s",
                              youtube_bg], capture_output=True, text=True, timeout=240)
        import glob
        cands = glob.glob("/tmp/niche_bg_raw.*")
        ok = _dl.returncode == 0 and cands and os.path.getsize(cands[0]) > 50000
        if not ok:
            # YouTube blocked / failed -> SOFT FAIL to the themed Pexels background.
            print(f"BG from YouTube failed (rc={_dl.returncode}) -> falling back to Pexels: {query}")
            for c in cands:
                try: os.remove(c)
                except: pass
            _use_pexels(query)
            return
        raw = cands[0]
        subprocess.run(["cp", raw, "/tmp/niche_bg_raw.mp4"], check=True)
    else:
        _use_pexels(query)
    # probe duration
    pr = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-i", "/tmp/niche_bg_raw.mp4"],
                        capture_output=True, text=True)
    dur = float(json.loads(pr.stdout)["format"]["duration"])
    loops = int(176 / max(dur, 0.001)) + 1
    with open("/tmp/niche_loops.txt", "w") as f:
        for _ in range(loops):
            f.write("file '/tmp/niche_bg_raw.mp4'\n")
    # re-encode vertical loop (cover-fit to 1080x1920); generous timeout on this 2-core box
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", "/tmp/niche_loops.txt", "-vf",
                    "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "public/background_video.mp4"], check=True, timeout=600)
    print("BG READY", query)

def main():
    c = CONF[NICHE]
    build_bg(c["bg"], youtube_bg=c.get("youtube_bg"))
    # clean image cache for fresh themed images
    subprocess.run(["python3", "-c",
        "import shutil; shutil.rmtree('_web_imgs', ignore_errors=True); shutil.rmtree('_pexels_imgs', ignore_errors=True)"])
    env = dict(os.environ)
    env["FACTS_TYPE"] = c["facts"]
    r = subprocess.run(["/root/AutoShorts-AI/.venv/bin/python", "run_sample.py"],
                       env=env, timeout=900)
    if r.returncode != 0:
        print(f"RENDER FAILED niche={NICHE} rc={r.returncode}")
        sys.exit(1)
    shutil_ok = subprocess.run(["cp", "sample_output.mp4", c["out"]]).returncode
    print("SAVED", c["out"])
    # clean disk: remove big bg raw + rendered copies
    for f in ["/tmp/niche_bg_raw.mp4", "public/bg_loop_long.mp4", "public/bg_loop_copy.mp4"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

if __name__ == "__main__":
    main()