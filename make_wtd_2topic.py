#!/usr/bin/env python3
"""
make_wtd_2topic.py — 2-comparison WTD Short (45s+ retention format).
Structure: HOOK -> [X alone, Y both, ask, explain-payoff] x2 (two topics)
         -> quick recap + soft CTA. Target 45-60s.
Reuses locked v8 template (render_beat + edge TTS two-pass assembly).
"""
import os, sys, subprocess
sys.path.insert(0, '/root/ShortGPT')
os.chdir('/root/ShortGPT')

from wtd_compositor import render_beat

OUT = "/root/ShortGPT/wtd_2topic_finance.mp4"
FRAME_DIR = "/root/wtd_frames_2t"
TMP = os.path.join(FRAME_DIR, "tmp")
os.makedirs(FRAME_DIR, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

# beat = (left_label, left_img, right_label, right_img, pose, show, narration)
# show: 'left' = first image alone; 'both' = pair shown together
TOPIC1 = [  # Index Fund vs ETF
    ("INDEX FUND","indexfund","ETF","etf", "left","left","An index fund tracks a whole market, like the whole S&P 500 in one basket."),
    ("INDEX FUND","indexfund","ETF","etf", "right","both","An ETF is a fund you trade like a stock, any moment the market's open."),
    ("INDEX FUND","indexfund","ETF","etf", "ask","both","So what's the difference?"),
    ("INDEX FUND","indexfund","ETF","etf", "left","both","Index funds buy and sell once a day, through your mutual fund company."),
    ("INDEX FUND","indexfund","ETF","etf", "right","both","ETFs trade all day long, with live prices, just like a stock."),
    ("INDEX FUND","indexfund","ETF","etf", "ask","both","Index fund, set once daily. ETF, trades all day. Both track the market."),
]
TOPIC2 = [  # Simple vs Compound Interest
    ("SIMPLE","simple","COMPOUND","compound", "left","left","Simple interest only grows on the money you first put in."),
    ("SIMPLE","simple","COMPOUND","compound", "right","both","Compound interest grows on your money, plus the interest you already earned."),
    ("SIMPLE","simple","COMPOUND","compound", "ask","both","So what's the real difference?"),
    ("SIMPLE","simple","COMPOUND","compound", "left","both","Simple interest pays you the same amount every single year."),
    ("SIMPLE","simple","COMPOUND","compound", "right","both","Compound interest grows every year, because your interest earns interest too."),
    ("SIMPLE","simple","COMPOUND","compound", "ask","both","Simple, a flat reward. Compound, a snowball. That's the difference."),
]
ALL = [("HOOK", None, []) ]  # placeholder not used
BEATS = []
for label_prefix, t in [("A", TOPIC1), ("B", TOPIC2)]:
    for b in t:
        BEATS.append((label_prefix, b))

from shortGPT.audio.edge_voice_module import EdgeTTSVoiceModule
VOICE = "en-US-AndrewMultilingualNeural"
vm = EdgeTTSVoiceModule(VOICE)

def dur(f):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=noprint_wrappers=1:nokey=1", f],
                       capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except: return 3.0

def chunks(text, size=3):
    words = text.split()
    return [" ".join(words[i:i+size]) for i in range(0, len(words), size)]

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("CMD FAILED:", " ".join(cmd)[:200]); print(r.stderr[-1200:]); sys.exit(1)
    return r

def main():
    chunk_frames, beat_audio = [], []
    t = 0.0; fi = 0
    for bi, (g, (l, li, r, ri, pose, show, nar)) in enumerate(BEATS):
        if g == "R" and bi > 0: pass
        audio = os.path.join(FRAME_DIR, f"beat{bi:02d}.mp3")
        vm.generate_voice(nar, audio)
        d = dur(audio)
        cs = chunks(nar); n_words = sum(len(c.split()) for c in cs)
        for c in cs:
            share = d * (len(c.split())/n_words)
            frame = os.path.join(FRAME_DIR, f"f{fi:03d}.png")
            render_beat(frame, l, li, r, ri, "", pose, show, caption=c)
            chunk_frames.append((frame, share)); fi += 1
        beat_audio.append((audio, d, t)); t += d
        print(f"({'hook' if g=='R' and bi==0 else g}) beat{bi}: {d:.2f}s | {nar[:40]}", flush=True)
    total = t
    print(f"\n>>> total narration: {total:.1f}s", flush=True)

    # PASS 1: frames -> silent video
    concat_file = os.path.join(TMP, "frames.txt")
    with open(concat_file, "w") as f:
        for i,(frame,share) in enumerate(chunk_frames):
            seg = os.path.join(TMP, f"seg{i:03d}.mp4")
            run(["ffmpeg","-y","-loglevel","error","-loop","1","-framerate","30",
                 "-t", f"{share:.3f}","-i",frame,
                 "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
                 "-t", f"{share:.3f}", seg])
            f.write(f"file '{seg}'\n")
    silent = os.path.join(TMP, "silent.mp4")
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",concat_file,"-c","copy",silent])
    print(f"silent video: {dur(silent):.2f}s", flush=True)

    # PASS 2: audio (beats back-to-back)
    parts=[]
    for i,(audio,d,start) in enumerate(beat_audio):
        part=os.path.join(TMP,f"a{i:02d}.wav")
        run(["ffmpeg","-y","-loglevel","error","-i",audio,"-ar","44100","-ac","2",part])
        parts.append(part)
    listf=os.path.join(TMP,"audio.txt")
    with open(listf,"w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    track=os.path.join(TMP,"track.wav")
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",listf,"-ar","44100","-ac","2",track])
    print(f"audio track: {dur(track):.2f}s", flush=True)

    # PASS 3: mux
    run(["ffmpeg","-y","-loglevel","error","-i",silent,"-i",track,"-c:v","copy","-c:a","aac","-shortest",OUT])
    print(f"done -> {OUT} ({dur(OUT):.1f}s)", flush=True)

if __name__ == "__main__":
    main()