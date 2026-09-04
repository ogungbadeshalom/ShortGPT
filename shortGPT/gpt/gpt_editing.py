from shortGPT.gpt import gpt_utils
import json


def extractJsonFromString(text):
    start = text.find('{')
    end = text.rfind('}') + 1
    if start == -1 or end == 0:
        raise Exception("Error: No JSON object found in response")
    json_str = text[start:end]
    return json.loads(json_str)


def getImageQueryPairs(captions, n=15, maxTime=2):
    """
    Get image queries for the short, TIMED TO THE EXACT SPOKEN LINE that
    mentions the subject — NOT to a coarse segment group.

    captions: [((start,end), text), ...] — REAL spoken times from whisper.

    Why this fixes image/audio desync:
    OLD: captions were bucketed evenly by *count*, one image per bucket shown at
         the bucket START. If the bucket was 0-4s but "phone call" is spoken at
         3s, the phone image appears at 0s — BEFORE the narration says it.
    NEW: pass every caption line with its REAL timestamps to the LLM; it returns
         each image query with the index of the line whose subject it depicts,
         and we anchor the image to THAT line's own start time.
    """
    if not captions:
        return []

    captions = sorted(captions, key=lambda c: c[0][0])
    end_audio = captions[-1][0][1]
    n = min(n, len(captions))

    # --- Send each spoken line with its real time so the model can anchor ---
    numbered = "\n".join(
        f'Line {i}: [{cap[0][0]:.2f}-{cap[0][1]:.2f}] "{cap[1].strip()}"'
        for i, cap in enumerate(captions))
    chat, _ = gpt_utils.load_local_yaml_prompt('prompt_templates/editing_generate_images.yaml')
    prompt = (chat.replace('<<CAPTIONS TIMED>>', numbered)
                  .replace("<<NUMBER>>", f"{n}"))

    try:
        res = gpt_utils.llm_completion(chat_prompt=prompt)
        start = res.find('{')
        end = res.rfind('}') + 1
        if start == -1 or end == 0:
            return []
        data = json.loads(res[start:end])
        items = data.get("image_queries", [])
    except Exception as e:
        print(f"[image timing] LLM parse failed: {e}")
        return []

    # --- Anchor each image to the exact line index it depicts ---
    pairs = []
    for item in items:
        q = str(item.get("query", "")).strip()
        if not q:
            continue
        start_t = None
        if "line" in item:
            li = int(item["line"])
            if 0 <= li < len(captions):
                start_t = captions[li][0][0]
        elif "timestamp" in item:
            ts = float(item["timestamp"])
            best = captions[-1] if captions else None
            for c in captions:
                if c[0][0] > ts:
                    break
                best = c
            start_t = best[0][0] if best else captions[0][0][0]
        if start_t is None:
            continue
        end_t = min(start_t + maxTime, end_audio)
        if end_t - start_t < 0.8:
            end_t = min(start_t + 0.8, end_audio)
        if end_t <= start_t:
            saved = pairs[-1][0][1] if pairs else 0.0
            end_t = min(max(start_t + 0.8, saved + 0.1), end_audio)
        pairs.append(((round(start_t, 2), round(end_t, 2)), q + " image"))
    pairs.sort(key=lambda p: p[0][0])
    return pairs


def getVideoSearchQueriesTimed(captions_timed):
    """
    Generate timed video search queries based on caption timings.
    Returns list of [time_range, search_queries] pairs.
    """
    err = ""

    for _ in range(4):
        try:
            # Get total video duration from last caption
            end_time = captions_timed[-1][0][1]

            # Load and prepare prompt
            chat, system = gpt_utils.load_local_yaml_prompt('prompt_templates/editing_generate_videos.yaml')
            prompt = chat.replace("<<TIMED_CAPTIONS>>", f"{captions_timed}")

            # Get response and parse JSON
            res = gpt_utils.llm_completion(chat_prompt=prompt, system=system)
            data = extractJsonFromString(res)

            # Convert to expected format
            formatted_queries = []
            for segment in data["video_segments"]:
                time_range = segment["time_range"]
                queries = segment["queries"]

                # Validate time range
                if not (0 <= time_range[0] < time_range[1] <= end_time):
                    continue

                # Ensure exactly 3 queries
                while len(queries) < 3:
                    queries.append(queries[-1])
                queries = queries[:3]

                formatted_queries.append([time_range, queries])

            # Verify coverage
            if not formatted_queries:
                raise ValueError("Generated segments don't cover full video duration")

            return formatted_queries
        except Exception as e:
            err = str(e)
            print(f"Error generating video search queries {err}")
    raise Exception(f"Failed to generate video search queries {err}")