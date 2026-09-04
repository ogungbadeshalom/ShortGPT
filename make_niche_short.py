#!/usr/bin/env python3
"""
Auto-produce a themed faceless Short using the ShortGPT engine.
Generic pipeline (niche-agnostic); defaults to gaming/Minecraft for now.

Usage:
  python make_niche_short.py [--niche gaming] [--topic "Minecraft creeper story"]

Config per niche: background query (Pexels), a topic prompt, and output path.
The script generation + rendering is delegated to render_niche.py (glm-5.2),
so this adds a title/topic selector on top.
"""
import argparse, os, subprocess, sys, time, json, random

BASE = "/root/ShortGPT"
os.chdir(BASE)

# Pexels-authoritative bgs per niche (verified Minecraft for gaming)
NICHE_BG = {
    "gaming": ["minecraft", "minecraft gameplay", "minecraft world"],
    "mystery": ["dark forest fog", "abandoned ruins mist", "old castle ruins"],
    "mythology": ["ancient greek temple", "roman statue marble", "ancient ruins columns"],
    "tech": ["futuristic technology", "server room", "computer chip"],
    "food": ["cooking kitchen food", "chef preparing dish", "fresh ingredients"],
}

# Curated gaming facts topics (real, teachable) to auto-pick from
GAMING_TOPICS = [
    "Minecraft surprising facts: the Creeper was a failed pig model and how it became iconic",
    "Minecraft surprising facts: the game was almost called Cave Game and its original creator story",
    "Gaming surprising facts: how the first cheat code was an accident and the legend it created",
    "Minecraft surprising secrets: the hidden world type that was never finished",
]

def pick_topic(niche):
    if niche == "gaming":
        return random.choice(GAMING_TOPICS)
    # generic fallback: just use the niche theme
    return f"Surprising facts about {niche} that most people don't know"

def run(niche, topic):
    """Render one short for the niche via render_niche.py, overriding the facts."""
    # We patch the facts into the CONF at runtime by calling a small wrapper.
    # Simplest: write a temporary runner that sets FACTS_TYPE for render_niche.
    # render_niche.py reads niche from argv and its CONF facts; to keep it clean,
    # we build background via render_niche then render with FACTS_TYPE override.
    env = dict(os.environ)
    env["PEXELS_API_KEY"] = _pexels_key()
    # Use render_niche to do bg + render; but it has its own facts per niche.
    # For a topic override, call run_sample directly after building an appropriate bg.
    print(f"[pipeline] niche={niche} topic={topic}")
    # Build themed background via render_niche's bg builder (importable)
    sys.path.insert(0, BASE)
    import render_niche as rn
    rn.NICHE = niche
    c = rn.CONF[niche]
    rn.build_bg(c["bg"])
    # clean image caches for fresh verified images
    for d in ("_web_imgs", "_pexels_imgs"):
        subprocess.run(["python3", "-c",
            f"import shutil; shutil.rmtree('{d}', ignore_errors=True)"])
    # Run the engine with a topic override
    env["FACTS_TYPE"] = topic
    r = subprocess.run(["/root/AutoShorts-AI/.venv/bin/python", "run_sample.py"],
                       env=env, cwd=BASE, timeout=1200)
    if r.returncode != 0:
        print(f"[pipeline] RENDER FAILED rc={r.returncode}")
        return None
    out = c["out"]
    subprocess.run(["cp", "sample_output.mp4", out], cwd=BASE)
    # cleanup big bg temp
    for f in ("/tmp/niche_bg_raw.mp4",):
        if os.path.exists(f):
            try: os.remove(f)
            except: pass
    print(f"[pipeline] SAVED {out}")
    return out

def _pexels_key():
    for line in open(f"{BASE}/../AutoShorts-AI/.env"):
        line = line.strip()
        if line.startswith("PEXELS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--niche", default="gaming", choices=list(NICHE_BG.keys()))
    ap.add_argument("--topic", default=None, help="override the facts topic")
    args = ap.parse_args()
    topic = args.topic or pick_topic(args.niche)
    out = run(args.niche, topic)
    if out:
        print(f"RESULT:{out}")

if __name__ == "__main__":
    main()