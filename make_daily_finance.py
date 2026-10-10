#!/usr/bin/env python3
"""
make_daily_finance.py — generate one 30s "Just The Difference" finance Short.
Picks a fresh topic from the pool, has DeepSeek write the "This is A / This is B /
What's the difference?" beats, fetches 2 Pexels concept photos, renders the video,
and writes output metadata (video path + title) for the uploader.

Usage:
  make_daily_finance.py                     # generate next video (marks topic used)
  make_daily_finance.py --topic "Bank:Create Arbitrary"   # force a specific pair
  make_daily_finance.py --dry                # pick topic + write plan, don't render
"""
import os, sys, json, subprocess, urllib.request, urllib.parse, io, datetime, time
sys.path.insert(0, '/root/ShortGPT')
os.chdir('/root/ShortGPT')

import yaml
cfg = yaml.safe_load(open('/root/.hermes/config.yaml'))
LLM_KEY = cfg['model']['api_key']
LLM_BASE = "https://freeinference.org/v1/chat/completions"
LLM_MODEL = os.environ.get("WTD_LLM", "deepseek-v4-flash")

POOL = "/root/ShortGPT/wtd_topic_pool.json"
WORKDIR = "/root/ShortGPT"
FRAME_DIR = "/root/wtd_frames_daily"
TMP = os.path.join(FRAME_DIR, "tmp")
os.makedirs(FRAME_DIR, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

VOICE = "en-US-AndrewMultilingualNeural"

def pexels_key():
    for line in open('/root/AutoShorts-AI/.env'):
        if line.strip().startswith("PEXELS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("no Pexels key in AutoShorts-AI/.env")

def pick_topic(mark=True):
    d = json.load(open(POOL))
    fresh = [t for t in d["topics"] if not t["used"]]
    if not fresh:
        raise RuntimeError("pool exhausted")
    # finance is the only theme now; pick random
    pick = fresh[(int(datetime.datetime.now().timestamp()) + hash(str(datetime.datetime.now().minute))) % len(fresh)]
    if mark:
        for t in d["topics"]:
            if t["A"]==pick["A"] and t["B"]==pick["B"]:
                t["used"]=True
        json.dump(d, open(POOL,'w'), indent=1)
    return pick

def llm(prompt):
    body = json.dumps({"model": LLM_MODEL, "messages":[{"role":"user","content":prompt}],
                       "max_tokens": 1200, "temperature": 0.8}).encode()
    req = urllib.request.Request(LLM_BASE, data=body, headers={
        "Authorization": f"Bearer {LLM_KEY}", "Content-Type":"application/json",
        "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/124"})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"].strip()

def gen_beats(a, b):
    """Ask DeepSeek for the exact beat flow. Returns list of (pose, show, narration)."""
    # doing narration strings directly
    prompt = f"""Write the English voiceover narration for a 30-second YouTube Short that compares "{a}" vs "{b}".
The structure MUST be exactly 7 spoken lines:
1. "This is {a}."  (short, 4-6 words)
2. "This is {b}."  (short)
3. "What's the difference?"
4-6. THREE clear lines explaining the KEY difference in plain spoken English, each 9-14 words, no jargon.
7. One closing practical line (8-12 words) ending with a clear takeaway.

Rules: spoken-language, punchy, second person, zero jargon, explain so a teenager understands, accurate and educational (definitional, NOT personalized investment advice). NO markdown, NO numbering. Output ONLY the 7 narration lines, one per line. Total between 85-105 words so it lands near 30 seconds. Do not use bullets."""
    txt = llm(prompt)
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    return lines

def gen_meta(a, b):
    """Generate a full explanation description + SEO tags for the short via LLM."""
    prompt = f"""Write YouTube metadata for a finance explainer short comparing "{a}" vs "{b}".

DESCRIPTION (60-90 words): a full, clear explanation of the difference anyone can
read. Start with the one-sentence difference, then 2-3 supporting sentences.
Plain, useful, no hype. Do NOT mention "subscribe".

TAGS: exactly 12-15 comma-separated YouTube tags. Include the two terms, "vs",
personal finance, investing, money, financial literacy, plus related searchable
topics. All lowercase.

Output EXACTLY this format, nothing else:
DESCRIPTION:
<the description>
TAGS:
<comma separated tags>
"""
    txt = llm(prompt)
    desc = ""
    tags = []
    if "DESCRIPTION:" in txt and "TAGS:" in txt:
        head, tail = txt.split("TAGS:", 1)
        desc = head.split("DESCRIPTION:", 1)[1].strip().strip('"')
        tags = [t.strip() for t in tail.split(",") if t.strip()]
    if not desc:
        desc = f"{a} and {b} are easy to mix up. This short explains the real difference clearly."
    if not tags:
        tags = [a.lower(), b.lower(), "personal finance", "investing", "money",
                "financial literacy", "finance explained", "shorts"]
    return desc, tags

def fetch_pexels(query, out_path, exclude_id=None):
    key = pexels_key()
    u = "https://api.pexels.com/v1/search?query=" + urllib.parse.quote(query) + "&per_page=5"
    req = urllib.request.Request(u, headers={"Authorization":key,"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read())
    for ph in d.get("photos", []):
        pid = str(ph.get("id"))
        if exclude_id and pid == str(exclude_id):
            continue  # never reuse the other side's exact photo
        url = ph["src"]["large"]
        try:
            ir = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) Chrome/124","Referer":"https://www.pexels.com/"})
            data = urllib.request.urlopen(ir, timeout=40).read()
            if len(data) < 3000: continue
            from PIL import Image
            im = Image.open(io.BytesIO(data)).convert("RGB")
            im.thumbnail((440, 440))
            im.save(out_path)
            return out_path, pid
        except Exception as e:
            continue
    return None, None

def dur(f):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=noprint_wrappers=1:nokey=1", f],capture_output=True,text=True)
    try: return float(r.stdout.strip())
    except: return 3.0

def gen_voice_safe(vm, text, audio, attempts=4):
    """Retry TTS until the file is real audio. EdgeTTSVoiceModule.generate_voice
    swallows the underlying exception (run_in_executor result is never awaited),
    so a 403'd clip leaves a 0-byte mp3 and 'succeeds' — then ffmpeg dies on it.
    edge-tts 403s are burst-flaky: single clips pass, 1-3 clips in a rapid burst
    fail. Backoff + retry clears it; a 0-byte file never passes this gate."""
    for i in range(attempts):
        try:
            vm.generate_voice(text, audio)
        except Exception as e:
            print(f"  [tts retry {i+1}/{attempts}] {str(e)[:120]}", flush=True)
        if os.path.exists(audio) and os.path.getsize(audio) > 1000 and dur(audio) > 0.5:
            return
        time.sleep(5 + 7*i)   # 5s, 12s, 19s — burst window passes
    raise SystemExit(f"TTS failed after {attempts} attempts: {audio}")

def chunks(text, size=3):
    w = text.split(); return [" ".join(w[i:i+size]) for i in range(0,len(w),size)]

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("CMD FAILED:", " ".join(cmd)[:160]); print(r.stderr[-800:]); sys.exit(1)
    return r

def main():
    from wtd_compositor import render_beat, register_concept, render_cta
    sys.argv = sys.argv if hasattr(sys.argv,'__iter__') else sys.argv

    # dry-run topic only
    if "--topic" in sys.argv:
        i = sys.argv.index("--topic")
        a, b = sys.argv[i+1].split(" vs ")
        topic = {"A":a,"B":b}
    else:
        topic = pick_topic(mark="--dry" not in sys.argv)

    a, b = topic["A"], topic["B"]
    print(f"📋 TOPIC: {a} vs {b}\n", flush=True)

    if "--dry" in sys.argv:
        script = gen_beats(a, b)
        print("SCRIPT:")
        for ln in script: print("  ", ln)
        sys.exit(0)

    # 1) script
    beats = gen_beats(a, b)
    if len(beats) < 5:
        print("WARN: shallow script, padding"); beats += ["That's the difference.","Follow for daily money clarity."]
    while len(beats) < 5:
        beats.append("That's the difference.")
    beats = beats[:7]

    # 2) concept photos (fallback: leave blank -> compositor shows no photo)
    KA, KB = str(a).lower().replace(" ","").replace("/","-"), str(b).lower().replace(" ","").replace("/","-")
    imgA = os.path.join(FRAME_DIR, f"{KA}.png")
    imgB = os.path.join(FRAME_DIR, f"{KB}.png")
    okA, pidA = fetch_pexels(f"{a} finance", imgA)
    # fetch B excluding A's photo ID so the two comparison sides are ALWAYS different
    okB, pidB = fetch_pexels(f"{b} finance", imgB, exclude_id=pidA)
    print(f"📷 image A({a}): {'OK' if okA else 'NONE'} (id {pidA})  image B({b}): {'OK' if okB else 'NONE'} (id {pidB})", flush=True)
    if okA: register_concept(KA, imgA)
    if okB: register_concept(KB, imgB)

    # 2a) SEO description + tags (full explanation + search-rich tags)
    seo_desc, seo_tags = gen_meta(a, b)

    # 3) build beats: first 3 = locked flow w/ proper poses, rest explanation
    BEATS = []
    # This is A (left, show left) | This is B (left->right, both) | What's the difference (ask,both)
    labelA = a.upper()
    labelB = b.upper()

    # 2b) thumbnail frame: the "What's the difference?" card (both concepts + ask
    #     stickman + question) — this IS the channel's signature thumbnail. Rendered
    #     now so it's guaranteed complete, written to _latest_wtd.json for upload.
    thumb_path = os.path.join(FRAME_DIR, "_thumb.png")
    render_beat(thumb_path, labelA, KA, labelB, KB, "", "ask", "both",
                caption="What's the difference?")
    if len(beats) >= 3:
        BEATS.append((labelA, KA, labelB, KB, "left", "left", beats[0]))
        BEATS.append((labelA, KA, labelB, KB, "right", "both", beats[1]))
        BEATS.append((labelA, KA, labelB, KB, "ask", "both", beats[2]))
        for extra in beats[3:]:
            BEATS.append((labelA, KA, labelB, KB, "ask", "both", extra))
    else:
        raise RuntimeError("script too short")

    from shortGPT.audio.edge_voice_module import EdgeTTSVoiceModule
    vm = EdgeTTSVoiceModule(VOICE)

    chunk_frames, beat_audio = [], []
    t = 0.0; fi = 0
    for bi, (L,LI,R,RI,pose,show,nar) in enumerate(BEATS):
        audio = os.path.join(FRAME_DIR, f"beat{bi:02d}.mp3")
        gen_voice_safe(vm, nar, audio)
        d = dur(audio)
        cs = chunks(nar); nw = sum(len(c.split()) for c in cs)
        for c in cs:
            share = d*(len(c.split())/nw)
            fr = os.path.join(FRAME_DIR, f"f{fi:03d}.png")
            render_beat(fr, L, LI, R, RI, "", pose, show, caption=c)
            chunk_frames.append((fr, share)); fi += 1
        beat_audio.append((audio, d, t)); t += d
    print(f"\n>>> narration: {t:.1f}s", flush=True)

    # 3b) CTA end-card: voice + static frame appended as final beat
    cta_text = "Follow for more money clarity. See you tomorrow."
    cta_audio = os.path.join(FRAME_DIR, "cta.mp3")
    gen_voice_safe(vm, cta_text, cta_audio)
    dcta = dur(cta_audio)
    cta_chunks = chunks(cta_text)
    cta_nw = sum(len(c.split()) for c in cta_chunks)
    for c in cta_chunks:
        share = dcta*(len(c.split())/cta_nw)
        fr = os.path.join(FRAME_DIR, f"f{fi:03d}_cta.png")
        render_cta(fr, main="Follow for more money clarity.", sub="@justthediff", caption=c)
        chunk_frames.append((fr, share)); fi += 1
    beat_audio.append((cta_audio, dcta, t)); t += dcta
    print(f"cta: {dcta:.2f}s | {cta_text}", flush=True)

    # 3c) static full-CTA hold frame at the very END (so video never ends on a
    #     mid-word fragment): full message + handle held ~1.2s after the voice.
    hold = 1.2
    fr = os.path.join(FRAME_DIR, f"f{fi:03d}_ctahold.png")
    render_cta(fr, main="Follow for more money clarity. See you tomorrow.", sub="@justthediff")
    chunk_frames.append((fr, hold)); fi += 1
    t += hold
    print(f">>> total with cta: {t:.1f}s", flush=True)

    # frames -> silent
    concat = os.path.join(TMP, "frames.txt")
    with open(concat, "w") as f:
        for i,(fr,share) in enumerate(chunk_frames):
            seg = os.path.join(TMP, f"seg{i:03d}.mp4")
            run(["ffmpeg","-y","-loglevel","error","-loop","1","-framerate","30",
                 "-t", f"{share:.3f}","-i",fr,
                 "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-t",f"{share:.3f}",seg])
            f.write(f"file '{seg}'\n")
    silent = os.path.join(TMP,"silent.mp4")
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",concat,"-c","copy",silent])

    # audio
    parts=[]
    for i,(audio,d,start) in enumerate(beat_audio):
        p=os.path.join(TMP,f"a{i:02d}.wav")
        run(["ffmpeg","-y","-loglevel","error","-i",audio,"-ar","44100","-ac","2",p]); parts.append(p)
    alist=os.path.join(TMP,"audio.txt")
    open(alist,"w").write("".join(f"file '{p}'\n" for p in parts))
    track=os.path.join(TMP,"track.wav")
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",alist,"-ar","44100","-ac","2",track])
    # pad the track with trailing silence (the CTA hold frame) so -shortest
    # doesn't chop the final static card
    track_padded=os.path.join(TMP,"track_padded.wav")
    run(["ffmpeg","-y","-loglevel","error","-i",track,"-af",f"apad=pad_dur={hold}",
         "-ar","44100","-ac","2",track_padded])
    track=track_padded

    out = os.path.join(WORKDIR, f"wtd_{a.replace(' ','').replace('/','-')}_{b.replace(' ','').replace('/','-')}.mp4")
    run(["ffmpeg","-y","-loglevel","error","-i",silent,"-i",track,"-c:v","copy","-c:a","aac","-shortest",out])
    dur_out = dur(out)
    print(f"✅ DONE -> {out} ({dur_out:.1f}s)", flush=True)

    json.dump({"topic":"{a} vs {b}".format(a=a,b=b),"file":out,
               "title":f"The Difference Between: {a} vs {b} #shorts",
               "thumbnail": thumb_path if os.path.exists(thumb_path) else "",
               "description": seo_desc, "tags": seo_tags,
               "duration":dur_out},
              open(os.path.join(WORKDIR,"_latest_wtd.json"),"w"), indent=1)
    print(json.dumps({"file":out,"title":f"The Difference Between: {a} vs {b}","thumbnail":thumb_path,"duration":dur_out}))

if __name__ == "__main__":
    main()