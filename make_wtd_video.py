#!/usr/bin/env python3
"""
make_wtd_video.py (v7b) — WTD Short with synced word captions.
Two-pass assembly (robust):
  1) frames -> silent video via concat (each chunk frame shown its share)
  2) beat audios -> full track (each padded with silence to its timeline slot)
  3) mux
"""
import os, sys, subprocess
sys.path.insert(0, '/root/ShortGPT')
os.chdir('/root/ShortGPT')

from wtd_compositor import render_beat, W, H

OUT = "/root/ShortGPT/wtd_debit_credit.mp4"
FRAME_DIR = "/root/wtd_frames_dc"
TMP = "/root/wtd_frames8/tmp"
os.makedirs(FRAME_DIR, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

BEATS = [
    ("DEBIT","debit","CREDIT","credit", "", "left", "left",
     "This is a debit card."),
    ("DEBIT","debit","CREDIT","credit", "", "right", "both",
     "This is a credit card."),
    ("DEBIT","debit","CREDIT","credit", "", "ask", "both",
     "What's the difference?"),
    ("DEBIT","debit","CREDIT","credit", "", "left", "both",
     "A debit card spends your own money, straight from your bank account."),
    ("DEBIT","debit","CREDIT","credit", "", "right", "both",
     "A credit card borrows the bank's money, and you pay it back later."),
    ("DEBIT","debit","CREDIT","credit", "", "ask", "both",
     "So, debit is your cash. Credit is a loan."),
    ("DEBIT","debit","CREDIT","credit", "", "ask", "both",
     "That's the difference."),
]

from shortGPT.audio.edge_voice_module import EdgeTTSVoiceModule
VOICE = "en-US-AndrewMultilingualNeural"

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
        print("CMD FAILED:", " ".join(cmd)[:200])
        print(r.stderr[-1200:])
        sys.exit(1)
    return r

def main():
    vm = EdgeTTSVoiceModule(VOICE)
    # 1) build chunk frames + beat audio, compute timeline
    chunk_frames = []   # (frame, share)
    beat_audio = []     # (audio, beat_dur, start_time)
    t = 0.0
    fi = 0
    for b, (l, li, r, ri, q, pose, show, nar) in enumerate(BEATS):
        audio = os.path.join(FRAME_DIR, f"beat{b:02d}.mp3")
        vm.generate_voice(nar, audio)
        d = dur(audio)
        cs = chunks(nar)
        n_words = sum(len(c.split()) for c in cs)
        for c in cs:
            share = d * (len(c.split())/n_words)
            frame = os.path.join(FRAME_DIR, f"f{fi:03d}.png")
            render_beat(frame, l, li, r, ri, q, pose, show, caption=c)
            chunk_frames.append((frame, share))
            fi += 1
        beat_audio.append((audio, d, t))
        t += d
        print(f"beat{b}: {d:.2f}s, {len(cs)} chunks | {nar[:40]}", flush=True)
    total = t

    # 2) PASS 1: frames -> silent video
    concat_file = os.path.join(TMP, "frames.txt")
    with open(concat_file, "w") as f:
        for i, (frame, share) in enumerate(chunk_frames):
            seg = os.path.join(TMP, f"seg{i:03d}.mp4")
            run(["ffmpeg","-y","-loglevel","error","-loop","1","-framerate","30",
                 "-t", f"{share:.3f}","-i",frame,
                 "-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
                 "-t", f"{share:.3f}", seg])
            f.write(f"file '{seg}'\n")
    silent = os.path.join(TMP, "silent.mp4")
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0",
         "-i", concat_file, "-c","copy", silent])
    print(f"silent video: {dur(silent):.2f}s (target {total:.2f})", flush=True)

    # 3) PASS 2: audio timeline (pad each beat to its slot, concat)
    parts = []
    for i, (audio, d, start) in enumerate(beat_audio):
        part = os.path.join(TMP, f"a{i:02d}.wav")
        gap = start - (sum(x[1] for x in beat_audio[:i]) if i==0 else 0)
        # build with adelay-style: silence before = start - cumulative_dur
        cum = sum(x[1] for x in beat_audio[:i])
        pre = max(0.0, start - cum)  # should be 0 (beats are back-to-back)
        if pre > 0.001:
            run(["ffmpeg","-y","-loglevel","error","-i",audio,
                 "-af",f"adelay={int(pre*1000)}|{int(pre*1000)}",
                 "-ar","44100","-ac","2", part])
        else:
            run(["ffmpeg","-y","-loglevel","error","-i",audio,
                 "-ar","44100","-ac","2", part])
        parts.append(part)
    listf = os.path.join(TMP, "audio.txt")
    with open(listf,"w") as f:
        for p in parts: f.write(f"file '{p}'\n")
    track = os.path.join(TMP, "track.wav")
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0",
         "-i", listf, "-ar","44100","-ac","2", track])
    print(f"audio track: {dur(track):.2f}s", flush=True)

    # 4) PASS 3: mux
    run(["ffmpeg","-y","-loglevel","error","-i",silent,"-i",track,
         "-c:v","copy","-c:a","aac","-shortest", OUT])
    print(f"done -> {OUT} ({dur(OUT):.1f}s)", flush=True)

if __name__ == "__main__":
    main()