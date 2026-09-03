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
    Get image queries for the short, TIMED AND CONTENT-MATCHED TO REAL SPEECH.

    captions: [((start,end), text), ...] — REAL spoken times from whisper.

    Approach (fixes image/audio desync + content mismatch):
    1. Group captions into ~n REAL spoken segments (by actual time windows).
    2. For each segment, send the LLM the ACTUAL TEXT spoken in that window and
       ask it to return ONE image query for THAT line.
    3. Time each image to the real start of ITS segment.

    This guarantees the image query is written from the actual narration that
    plays while that image is on screen — no more guessed timestamps drifting
    away from the words.
    """
    if not captions:
        return []

    # Sort captions by real start time
    captions = sorted(captions, key=lambda c: c[0][0])
    end_audio = captions[-1][0][1]

    n = min(n, len(captions))   # cannot have more images than spoken caption groups

    # --- Group captions into n consecutive real-time segments ---
    total = len(captions)
    boundaries = []
    for i in range(n):
        b = int(round(i * total / n))
        boundaries.append(b)
    boundaries.append(total)

    segments = []  # [(seg_start_seconds, "text of that spoken segment")]
    for i in range(n):
        lb, ub = boundaries[i], boundaries[i + 1]
        seg_caps = captions[lb:ub]
        if not seg_caps:
            continue
        start = seg_caps[0][0][0]
        text = " ".join(t.strip() for _, t in seg_caps)
        segments.append((round(start, 2), text))

    # --- Ask the LLM for a query per REAL segment ---
    chat, _ = gpt_utils.load_local_yaml_prompt('prompt_templates/editing_generate_images.yaml')
    numbered = "\n".join(
        f"Segment {i+1} (at {st}s): \"{text}\"" for i, (st, text) in enumerate(segments))
    # pass each segment's real text so the model writes a query for THAT line
    prompt = chat.replace('<<CAPTIONS TIMED>>', numbered).replace("<<NUMBER>>", f"{len(segments)}")

    try:
        import json
        res = gpt_utils.llm_completion(chat_prompt=prompt)
        # locate JSON object in the response
        start = res.find('{')
        end = res.rfind('}') + 1
        if start == -1 or end == 0:
            return []
        data = json.loads(res[start:end])
        queries = data.get("image_queries", [])
    except Exception as e:
        print(f"[image timing] LLM parse failed: {e}")
        return []

    # --- Map each returned query to the REAL segment time (index-aligned) ---
    pairs = []
    for i, item in enumerate(queries):
        if i >= len(segments):
            break
        start = float(segments[i][0])
        query = str(item.get("query", "")).strip()
        if not query:
            continue
        # show this image from its segment start until just before the next
        if i < len(segments) - 1:
            end = min(start + maxTime, segments[i + 1][0])
        else:
            end = min(start + maxTime, end_audio)
        if end <= start:
            end = start + 1.0
        pairs.append(((start, end), query + " image"))
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