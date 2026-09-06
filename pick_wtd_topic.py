#!/usr/bin/env python3
"""
pick_wtd_topic.py — pick a fresh unused topic from the WTD 500+ pool.
Usage:
  python pick_wtd_topic.py            # print next unused topic (random, theme-weighted finance)
  python pick_wtd_topic.py --mark      # pick + mark used (call BEFORE generating the video)
  python pick_wtd_topic.py --reset     # mark all unused again (never auto-run)
  python pick_wtd_topic.py --stats     # show used/unused counts by theme
"""
import json, os, random, sys

POOL = "/root/ShortGPT/wtd_topic_pool.json"

def load():
    d = json.load(open(POOL))
    return d["topics"]

def save(topics):
    d = json.load(open(POOL))
    d["topics"] = topics
    json.dump(d, open(POOL, "w"), indent=1)

def main():
    topics = load()
    if "--stats" in sys.argv:
        used = sum(1 for t in topics if t["used"])
        by = {}
        for t in topics:
            by.setdefault(t["theme"], [0,0])
            by[t["theme"]][1] += 1
            if t["used"]: by[t["theme"]][0] += 1
        print(f"TOTAL {len(topics)} | used {used} | fresh {len(topics)-used}")
        for th,(u,c) in sorted(by.items()):
            print(f"  {th:9s} used {u}/{c}")
        return

    fresh = [t for t in topics if not t["used"]]
    if not fresh:
        print("POOL EXHAUSTED — run --reset to reuse (or add topics).")
        sys.exit(2)

    # finance-weighted pick: 60% chance to choose from finance if any remain
    fin = [t for t in fresh if t["theme"] == "finance"]
    if fin and random.random() < 0.60:
        pick = random.choice(fin)
    else:
        pick = random.choice(fresh)

    if "--mark" in sys.argv:
        for t in topics:
            if t["A"] == pick["A"] and t["B"] == pick["B"]:
                t["used"] = True
        save(topics)

    print(f"{pick['A']} vs {pick['B']}\t[{pick['theme']}]")

if __name__ == "__main__":
    main()