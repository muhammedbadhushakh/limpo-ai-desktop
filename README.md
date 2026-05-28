# ⚡ PortableAI — USB Portable Multi-Model AI Chat

Run ChatGPT, Gemini, Claude, and local Ollama models from a USB drive.
No installation needed on the target PC.

---

## 📁 Files
```
PortableAI/
├── PortableAI.exe        ← Double-click to launch
├── models_config.json    ← Your API keys & model list (auto-created)
├── _internal/            ← App files (don't delete)
└── README.txt
```

---

## 🚀 How to Run
1. Plug in your USB drive
2. Double-click **PortableAI.exe**
3. Your browser opens automatically at http://127.0.0.1:7891

---

## 🧩 Adding Models (first-time setup)
1. Click **Models** in the sidebar
2. Enter your API keys for the models you want
3. Click **Save Changes**

### Where to get API keys:
| Provider | URL |
|----------|-----|
| OpenAI (ChatGPT) | https://platform.openai.com/api-keys |
| Google Gemini    | https://aistudio.google.com/app/apikey |
| Anthropic Claude | https://console.anthropic.com/settings/keys |
| Ollama (free/offline) | Install from https://ollama.com |

---

## 🦙 Using Ollama (100% Offline)
1. Install Ollama on the PC: https://ollama.com/download
2. Pull a model (only once per PC):
   ```
   ollama pull llama3.2
   ```
3. Open PortableAI → Models → your local models appear automatically!

---

## ➕ Adding Custom Models
In Models page → click **+ Add Model**
- Fill in display name, model ID, provider, and API key
- Works with any OpenAI-compatible API

---

## 🔒 Privacy
- API keys are stored only in `models_config.json` on your USB
- Nothing is sent anywhere except the AI provider you choose
- Close the app window to stop the server

---

## 🛠 Build from Source
```bash
pip install flask requests pyinstaller
python build_exe.py
```
"# limpo-ai-desktop" 
