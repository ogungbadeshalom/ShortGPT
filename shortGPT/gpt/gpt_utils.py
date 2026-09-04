import json
import os
import re
from time import sleep, time

import openai
import tiktoken
import yaml

from shortGPT.config.api_db import ApiKeyManager


def num_tokens_from_messages(texts, model="gpt-4o-mini"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-4o-mini":  # note: future models may deviate from this
        if isinstance(texts, str):
            texts = [texts]
        score = 0
        for text in texts:
            score += 4 + len(encoding.encode(text))
        return score
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.
        See https://github.com/openai/openai-python/blob/main/chatml.md for information""")


def extract_biggest_json(string):
    json_regex = r"\{(?:[^{}]|(?R))*\}"
    json_objects = re.findall(json_regex, string)
    if json_objects:
        return max(json_objects, key=len)
    return None


def get_first_number(string):
    pattern = r'\b(0|[1-9]|10)\b'
    match = re.search(pattern, string)
    if match:
        return int(match.group())
    else:
        return None


def load_yaml_file(file_path: str) -> dict:
    """Reads and returns the contents of a YAML file as dictionary"""
    return yaml.safe_load(open_file(file_path))


def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    return json_data

from pathlib import Path

def load_local_yaml_prompt(file_path):
    _here = Path(__file__).parent
    _absolute_path = (_here / '..' / file_path).resolve()
    json_template = load_yaml_file(str(_absolute_path))
    return json_template['chat_prompt'], json_template['system_prompt']


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()
from openai import OpenAI

def llm_completion(chat_prompt="", system="", temp=0.7, max_tokens=2000, remove_nl=True, conversation=None):
    openai_key= ApiKeyManager.get_api_key("OPENAI_API_KEY")
    gemini_key = ApiKeyManager.get_api_key("GEMINI_API_KEY")
    import requests as _req
    llm_base = os.environ.get("LLM_BASE_URL", "").strip().rstrip("/")
    llm_model = os.environ.get("LLM_MODEL", "deepseek-v4-flash").strip()
    llm_key = os.environ.get("LLM_API_KEY", "").strip()
    if not llm_base or not llm_key:
        # fall back to original OpenAI/Gemini clients
        if gemini_key:
            llm_base = "https://generativelanguage.googleapis.com/v1beta/openai"
            llm_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite-preview-02-05")
            llm_key = gemini_key
        elif openai_key:
            llm_base = "https://api.openai.com/v1"
            llm_model = "gpt-4o-mini"
            llm_key = openai_key
        else:
            raise Exception("No OpenAI/Gemini/base credentials found for LLM request")
    max_retry = 5
    retry = 0
    error = ""
    for i in range(max_retry):
        try:
            if conversation:
                messages = conversation
            else:
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": chat_prompt}
                ]
            resp = _req.post(
                f"{llm_base}/chat/completions",
                headers={"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"},
                json={"model": llm_model, "messages": messages, "max_tokens": max_tokens, "temperature": temp},
                timeout=120,
            )
            resp_json = resp.json()
            _msg = resp_json["choices"][0]["message"]
            text = (_msg.get("content") or "").strip()
            if not text:
                _rc = (_msg.get("reasoning_content") or _msg.get("reasoning") or "").strip()
                if _rc:
                    # Retry with a larger budget + disable_thinking so we get an
                    # actual 'content', not the chain-of-thought.
                    try:
                        _retry = _req.post(
                            f"{llm_base}/chat/completions",
                            headers={"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"},
                            json={"model": llm_model, "messages": messages,
                                  "max_tokens": max_tokens * 3, "temperature": temp,
                                  "chat_template_kwargs": {"disable_thinking": True}},
                            timeout=120,
                        )
                        _rj = _retry.json()
                        text = (_rj["choices"][0]["message"].get("content") or "").strip()
                    except Exception:
                        pass
                if not text and _rc:
                    text = _rc[-800:]  # last resort: short usable tail
            if remove_nl:
                text = re.sub('\\s+', ' ', text)
            filename = '%s_llm_completion.txt' % time()
            if not os.path.exists('.logs/gpt_logs'):
                os.makedirs('.logs/gpt_logs')
            with open('.logs/gpt_logs/%s' % filename, 'w', encoding='utf-8') as outfile:
                outfile.write(f"System prompt: ===\n{system}\n===\n"+f"Chat prompt: ===\n{chat_prompt}\n===\n" + f'RESPONSE:\n====\n{text}\n===\n')
            return text
        except Exception as oops:
            retry += 1
            rb = resp if 'resp' in locals() else None
            rj = 'none'
            try:
                rj = (rb.text if rb is not None else 'none')[:300]
            except Exception:
                rj = 'none'
            print('Error communicating with LLM:', oops, rj)
            error = str(oops)
            sleep(1)
    raise Exception(f"Error communicating with LLM Endpoint Completion errored more than error: {error}")