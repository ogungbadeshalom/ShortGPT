#!/usr/bin/env python3
"""Render a "What's the difference?" Short using WTDShortEngine + the 3 stickman frames.

Usage:
  python make_wtd_short.py
"""
import os, sys, time, yaml, shutil, json
os.chdir('/root/ShortGPT')
sys.path.insert(0, '/root/ShortGPT')

# --- env (only the keys run_sample needs) ---
if os.path.exists('/root/AutoShorts-AI/.env'):
    for line in open('/root/AutoShorts-AI/.env'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            if k in ('PEXELS_API_KEY', 'GEMINI_API_KEY', 'GEMINI_MODEL'):
                os.environ.setdefault(k, v)

from shortGPT.config.asset_db import AssetDatabase, AssetType
from shortGPT.config.languages import Language
from shortGPT.audio.edge_voice_module import EdgeTTSVoiceModule
from shortGPT.engine.wtd_short_engine import WTDShortEngine

# Register the same local assets the default pipeline uses (idempotent).
AssetDatabase.add_local_asset("Gameplay Footage", AssetType.BACKGROUND_VIDEO, "public/background_video.mp4")
AssetDatabase.add_local_asset("Chill Synth", AssetType.BACKGROUND_MUSIC, "public/background_music.mp3")
AssetDatabase.add_local_asset("subscribe animation", AssetType.VIDEO, "public/subscribe-animation.mp4")

# ============================================================
# THE 3 STICKMAN FRAME ASSETS (verbatim - do not replace)
# ============================================================
F1 = "/root/panels/panel_1.png"  # points upper-left
F2 = "/root/panels/panel_2.png"  # points upper-right
F3 = "/root/panels/panel_3.png"  # puzzled "?"

# ============================================================
# SSD vs HDD PLAN  (win = frame, kw = on-screen text, text = narration)
# ============================================================
PLAN = [
    {"frame": F1, "keyword": "SSD vs HDD", "text":
        "SSD and HDD. Same job. Completely different machines."},
    {"frame": F1, "keyword": "SSD", "text":
        "An SSD stores your data with flash memory. No moving parts at all."},
    {"frame": F2, "keyword": "HDD", "text":
        "An HDD stores data on spinning magnetic disks."},
    {"frame": F3, "keyword": "???", "text":
        "So what's actually different?"},
    {"frame": F3, "keyword": "SSD = FAST", "text":
        "The SSD has no moving parts, so it's faster and quieter."},
    {"frame": F3, "keyword": "HDD = CHEAP", "text":
        "The HDD physically spins, so it's slower but cheaper per gigabyte."},
    {"frame": F1, "keyword": "SPEED vs COST", "text":
        "So basically, SSD equals speed. HDD equals cheaper storage."},
    {"frame": F3, "keyword": "THAT'S THE DIFFERENCE", "text":
        "That's the difference."},
]

voice = EdgeTTSVoiceModule("en-US-AndrewMultilingualNeural")
engine = WTDShortEngine(
    voiceModule=voice,
    wtd_plan=PLAN,
    background_video_name="Gameplay Footage",
    background_music_name="Chill Synth",
    watermark="FactsDaily",
    language=Language.ENGLISH,
)

def logger(msg):
    print("LOG:", msg, flush=True)
engine.set_logger(logger)

t0 = time.time()
print("=== START WTD MAKECONTENT ===", flush=True)
try:
    for step, msg in engine.makeContent():
        print(f"STEP {step}: {msg}", flush=True)
except Exception as e:
    import traceback
    print("WTD ENGINE FAILED:", flush=True)
    traceback.print_exc()
    sys.exit(1)
print(f"=== DONE in {time.time()-t0:.1f}s ===", flush=True)

final = engine.get_video_output_path()
print("final video path:", final, flush=True)
if final and os.path.exists(final):
    shutil.copy(final, "/root/ShortGPT/wtd_output.mp4")
    print("Copied to /root/ShortGPT/wtd_output.mp4, size",
          round(os.path.getsize('/root/ShortGPT/wtd_output.mp4')/1e6, 1), "MB", flush=True)
else:
    print("NO OUTPUT FILE", flush=True)
    sys.exit(2)