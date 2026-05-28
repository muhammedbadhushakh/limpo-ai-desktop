"""
PortableAI - USB Portable Multi-Model AI Chat App
Auto-retries on rate limits. Never exposes API keys in errors.
"""

import os, json, time, requests, threading, webbrowser
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from pathlib import Path

app = Flask(__name__)

BASE_DIR    = Path(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = BASE_DIR / "models_config.json"

DEFAULT_CONFIG = {
    "models": [
        {"id": "gpt-4o",                  "name": "GPT-4o",            "provider": "openai",    "api_key": "", "enabled": True},
        {"id": "gemini-2.0-flash",        "name": "Gemini 2.0 Flash",  "provider": "gemini",    "api_key": "", "enabled": True},
        {"id": "claude-sonnet-4-20250514","name": "Claude Sonnet 4",   "provider": "anthropic", "api_key": "", "enabled": True},
        {"id": "llama3.2",                "name": "Llama 3.2 (Local)", "provider": "ollama",    "api_key": "", "enabled": True},
    ]
}

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def safe_error(e):
    """Return error message with API keys stripped out."""
    msg = str(e)
    # Remove anything that looks like an API key from URLs/messages
    import re
    msg = re.sub(r'key=[A-Za-z0-9_\-]{10,}', 'key=***', msg)
    msg = re.sub(r'sk-[A-Za-z0-9_\-]{10,}', 'sk-***', msg)
    msg = re.sub(r'AIza[A-Za-z0-9_\-]{10,}', 'AIza***', msg)
    msg = re.sub(r'sk-ant-[A-Za-z0-9_\-]{10,}', 'sk-ant-***', msg)
    # Shorten the URL part
    msg = re.sub(r'for url: https?://\S+', 'for url: [hidden]', msg)
    return msg

# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/models", methods=["GET"])
def get_models():
    return jsonify(load_config())

@app.route("/api/models", methods=["POST"])
def save_models():
    save_config(request.json)
    return jsonify({"ok": True})

@app.route("/api/ollama/list", methods=["GET"])
def list_ollama_models():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        names = [m["name"] for m in r.json().get("models", [])]
        return jsonify({"models": names})
    except:
        return jsonify({"models": [], "error": "Ollama not running"})

@app.route("/api/chat", methods=["POST"])
def chat():
    data      = request.json
    model_id  = data.get("model_id")
    messages  = data.get("messages", [])
    cfg       = load_config()

    model_cfg = next((m for m in cfg["models"] if m["id"] == model_id), None)
    if not model_cfg:
        return jsonify({"error": "Model not found"}), 404

    provider = model_cfg["provider"]
    api_key  = model_cfg.get("api_key", "")

    def generate():
        try:
            if provider == "openai":
                yield from with_retry(stream_openai, api_key, model_id, messages)
            elif provider == "gemini":
                yield from with_retry(stream_gemini, api_key, model_id, messages)
            elif provider == "anthropic":
                yield from with_retry(stream_anthropic, api_key, model_id, messages)
            elif provider == "ollama":
                yield from stream_ollama(model_id, messages)
            else:
                yield f"data: {json.dumps({'error': 'Unknown provider'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': safe_error(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


# ── Auto-retry wrapper ────────────────────────────────────────────────────────

def with_retry(fn, *args, max_retries=3):
    """
    Calls fn(*args). If a 429 rate-limit is hit, waits and retries up to
    max_retries times, yielding a friendly status message each time.
    """
    for attempt in range(max_retries + 1):
        try:
            yield from fn(*args)
            return
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                if attempt < max_retries:
                    wait = 15 * (attempt + 1)   # 15s, 30s, 45s
                    msg = f"⏳ Rate limited by API. Retrying in {wait} seconds... (attempt {attempt+1}/{max_retries})"
                    yield f"data: {json.dumps({'token': msg})}\n\n"
                    time.sleep(wait)
                else:
                    yield f"data: {json.dumps({'error': '❌ Rate limit hit too many times. Please wait 1 minute and try again.'})}\n\n"
                    return
            else:
                raise   # re-raise non-429 errors


# ── Provider streaming helpers ────────────────────────────────────────────────

def stream_openai(api_key, model_id, messages):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model_id, "messages": messages, "stream": True}
    with requests.post("https://api.openai.com/v1/chat/completions",
                       headers=headers, json=payload, stream=True, timeout=60) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line and line.startswith(b"data: "):
                raw = line[6:]
                if raw == b"[DONE]": break
                chunk = json.loads(raw)
                token = chunk["choices"][0]["delta"].get("content", "")
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"

def stream_gemini(api_key, model_id, messages):
    parts = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        parts.append({"role": role, "parts": [{"text": m["content"]}]})
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model_id}:streamGenerateContent?alt=sse&key={api_key}")
    with requests.post(url, json={"contents": parts}, stream=True, timeout=60) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line and line.startswith(b"data: "):
                raw = line[6:]
                if raw == b"[DONE]": break
                try:
                    chunk = json.loads(raw)
                    token = chunk["candidates"][0]["content"]["parts"][0]["text"]
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
                except: pass

def stream_anthropic(api_key, model_id, messages):
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    payload = {"model": model_id, "max_tokens": 2048, "messages": messages, "stream": True}
    with requests.post("https://api.anthropic.com/v1/messages",
                       headers=headers, json=payload, stream=True, timeout=60) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line and line.startswith(b"data: "):
                chunk = json.loads(line[6:])
                if chunk.get("type") == "content_block_delta":
                    token = chunk.get("delta", {}).get("text", "")
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"

def stream_ollama(model_id, messages):
    payload = {"model": model_id, "messages": messages, "stream": True}
    with requests.post("http://localhost:11434/api/chat",
                       json=payload, stream=True, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"
                if chunk.get("done"): break


# ── Launch ────────────────────────────────────────────────────────────────────

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:7891")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=7891, debug=False)