#!/usr/bin/env python3
"""
make_wtd_single.py — single-comparison WTD Short (custom topic).
Reuses locked v8 template + auto-fit/wrap text (compositor v6).
"""
import os, sys, subprocess
sys.path.insert(0, '/root/ShortGPT')
os.chdir('/root/ShortGPT')

from wtd_compositor import render_beat

# ===== CONFIG: swap these for each video =====
OUT = "/root/ShortGPT/wtd_finance_single.mp4"
BEATS = [  # (left_label, left_img, right_label, right_img, pose, show, narration)
    ("INDEX FUND","indexfund","ETF","etf", "left","left","This is an index fund."),
    ("INDEX FUND","indexfund","ETF","etf", "right","both","This is an ETF."),
    ("INDEX FUND","indexfund","ETF","etf", "ask","both","What's the difference?"),
    ("INDEX FUND","indexfund","ETF","etf", "left","both","An index fund fills once a day, at the market close."),
    ("INDEX FUND","indexfund","ETF","etf", "right","both","An ETF trades all day, in seconds, at live prices."),
    ("INDEX FUND","indexfund","ETF","etf", "ask","both","Same market, same basket, but the trading is different."),
    ("INDEX FUND","indexfund","ETF","etf", "ask","both","So index funds are simpler, set once a day, hands off."),
    ("INDEX FUND","indexfund","ETF","etf", "ask","both","ETFs give flexibility, and often lower fees."),
    ("INDEX FUND","indexfund","ETF","etf", "ask","both","One trades daily, one trades all day. That's it."),
]
# =============================================

from shortGPT.audio.edge_voice_module import EdgeTTSVoiceModule
VOICE = "en-US-AndrewMultilingualNeural"
vm = EdgeTTSVoiceModule(VOICE)

FRAME_DIR = "/root/wtd_frames_sg"
TMP = os.path.join(FRAME_DIR, "tmp")
os.makedirs(FRAME_DIR, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

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
    for bi, (l, li, r, ri, pose, show, nar) in enumerate(BEATS):
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
        print(f"beat{bi}: {d:.2f}s | {nar[:40]}", flush=True)
    total = t
    print(f"\n>>> total narration: {total:.1f}s", flush=True)

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

    run(["ffmpeg","-y","-loglevel","error","-i",silent,"-i",track,"-c:v","copy","-c:a","aac","-shortest",OUT])
    print(f"done -> {OUT} ({dur(OUT):.1f}s)", flush=True)

if __name__ == "__main__":
    main()