import os, sys, time, yaml, shutil
os.chdir('/root/ShortGPT')
sys.path.insert(0, '/root/ShortGPT')

# --- env ---
if os.path.exists('/root/AutoShorts-AI/.env'):
    for line in open('/root/AutoShorts-AI/.env'):
        line=line.strip()
        if line and not line.startswith('#') and '=' in line:
            k,v=line.split('=',1)
            if k in ('PEXELS_API_KEY','GEMINI_API_KEY','GEMINI_MODEL'):
                os.environ.setdefault(k,v)
cfg=yaml.safe_load(open('/root/.hermes/config.yaml'))
m=cfg.get('model',{})
os.environ['LLM_BASE_URL']=m.get('base_url','https://freeinference.org/v1').rstrip('/')
os.environ['LLM_MODEL']='deepseek-v4-flash'  # stable for script gen (glm-5.2 returns empty content intermittently)
os.environ['LLM_API_KEY']=m.get('api_key','')

from shortGPT.config.asset_db import AssetDatabase, AssetType
from shortGPT.config.languages import Language
from shortGPT.audio.edge_voice_module import EdgeTTSVoiceModule
from shortGPT.engine.facts_short_engine import FactsShortEngine

# register local assets (idempotent)
AssetDatabase.add_local_asset("Gameplay Footage", AssetType.BACKGROUND_VIDEO, "public/background_video.mp4")
AssetDatabase.add_local_asset("Chill Synth", AssetType.BACKGROUND_MUSIC, "public/background_music.mp3")
# Subscribe animation: the repo registers a remote YouTube URL which (a) breaks
# get_asset_link and (b) is YouTube (blocked on this datacenter box). Use the
# bundled local file instead so the render can finish.
try:
    AssetDatabase.remove_asset("subscribe animation")
except Exception:
    pass
AssetDatabase.add_local_asset("subscribe animation", AssetType.VIDEO, "public/subscribe-animation.mp4")
print("assets: bg dur =", AssetDatabase.get_asset_duration("Gameplay Footage"))
print("bg link =", AssetDatabase.get_asset_link("Gameplay Footage"))
print("music link =", AssetDatabase.get_asset_link("Chill Synth"))
print("subscribe link =", AssetDatabase.get_asset_link("subscribe animation"))

voice = EdgeTTSVoiceModule("en-US-AndrewMultilingualNeural")
engine = FactsShortEngine(
    voiceModule=voice,
    facts_type=os.environ.get("FACTS_TYPE", "Video game facts"),
    background_video_name="Gameplay Footage",
    background_music_name="Chill Synth",
    num_images=6,
    watermark="FactsDaily",
    language=Language.ENGLISH,
)

def logger(msg):
    print("LOG:", msg, flush=True)
engine.set_logger(logger)

t0=time.time()
print("=== START MAKECONTENT ===", flush=True)
try:
    for step, msg in engine.makeContent():
        print(f"STEP {step}: {msg}", flush=True)
except Exception as e:
    import traceback
    print("ENGINE FAILED at step:", flush=True)
    traceback.print_exc()
    sys.exit(1)
print(f"=== DONE in {time.time()-t0:.1f}s ===", flush=True)

final = engine.get_video_output_path()
print("final video path:", final, flush=True)
if final and os.path.exists(final):
    shutil.copy(final, "/root/ShortGPT/sample_output.mp4")
    print("Copied to /root/ShortGPT/sample_output.mp4, size",
          round(os.path.getsize('/root/ShortGPT/sample_output.mp4')/1e6,1), "MB", flush=True)
else:
    print("NO OUTPUT FILE", flush=True)
    sys.exit(2)