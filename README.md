# 🌾 AgriSaarthi AI (Fetch-A-Thon 3.0)

**AgriSaarthi AI** is a decentralized autonomous agricultural decision agent built with the **Fetch.ai uAgents Framework**. It assists Indian farmers in selecting optimal, climate-smart, and financially viable crops based on their location, soil type, water availability, planting season, and investment budget.

---

## 🚀 Key Features

- **Fetch.ai uAgent Core**: Powered by `uagents>=0.26.0`, running on tested Python 3.12 with unique cryptographic agent identity and wallet addressing.
- **Bilingual Conversational Interface (Telugu & English)**:
  - Supports Telugu script (`తెలుగు`), English, and mixed Telenglish sentences.
  - Automatically detects preferred language and responds in the same language by default.
  - Understands ordinary farmer sentences, local units (ఎకరాలు/acres, లక్షలు/lakhs, వేలు/thousands), and district-level mapping (Warangal -> Telangana, Guntur -> Andhra Pradesh).
  - Preserves session context across multi-turn follow-ups without re-requesting farm parameters.
  - Allows on-the-fly language switching (`Reply in English` / `తెలుగులో సమాధానం చెప్పండి`).
- **Voice-Ready Farmer Web Interface**:
  - Browser-native speech-to-text (Web Speech API `te-IN` and `en-IN`) with microphone pulse animations.
  - Text-to-speech audio playback with Listen, Replay, and Stop controls.
  - Zero paid APIs or external dependencies required.
- **Dual Communication Protocols**:
  1. **Native Structured Protocol**: `FarmerProfileRequest` & `RecommendationResponse` models for uAgent-to-uAgent decentralized orchestration.
  2. **Agent Chat Protocol (ACP v0.3.0)**: Compliant with official Fetch.ai `chat_protocol_spec` for **ASI:One** and Agentverse mailbox.
- **Multi-Step Agronomic Pipeline**:
  - **Step 1: Input Validation**: Checks land size bounds, detects unrealistic budgets, and screens for high-risk soil-water mismatches.
  - **Step 2: Crop Suitability Scoring**: Evaluates season affinity, soil compatibility, water requirement stress levels, and state-level agro-climatic bonuses.
  - **Step 3: Economic Feasibility & Profitability Analysis**: Projects total cultivation costs using CACP/ICAR benchmarks, checks budget headroom, and estimates net profit margins based on official MSP 2024–2025 benchmarks.
  - **Step 4: Decision Synthesis & Advisory**: Separates top primary recommendations from diversification hedges, providing step-by-step reasoning and transparent limitations.
- **Verified Reference Dataset**: 11 authentic Indian crops spanning Kharif, Rabi, and Zaid seasons (Paddy, Wheat, Cotton, Mustard, Chickpea, Bajra, Soybean, Groundnut, Maize, Moong, Sugarcane) with documented agronomic requirements.
- **Honest Data & Live Feeds Policy**: Explicitly discloses that zero live external APIs are called, no live weather or daily APMC spot auction prices are scraped, and all profit figures are baseline agronomic estimates.

---

## 📂 Project Structure

```
AgriSaarthi/
├── agrisaarthi/
│   ├── __init__.py           # Package marker and version
│   ├── models.py             # Validated uagents.Model schemas (Pydantic)
│   ├── engine.py             # 4-step crop recommendation engine
│   ├── agent.py              # Autonomous Fetch.ai uAgent with ACP & Mailbox
│   ├── chat_protocol.py      # Bilingual ACP v0.3.0 protocol & multi-intent router
│   └── data/
│       ├── __init__.py       # Data package init
│       └── crops.py          # Documented Indian crop reference database
├── web/
│   └── index.html            # Farmer voice web interface (STT/TTS in Telugu & English)
├── scripts/
│   ├── demo_query.py         # Multi-scenario verification and demo runner
│   └── run_farmer_ui.py      # Zero-dependency local web server for farmer UI
├── tests/
│   ├── __init__.py
│   ├── test_models.py        # Schema validation unit tests
│   ├── test_engine.py        # Agronomic scoring & budget logic unit tests
│   ├── test_agent.py         # Agent initialization & mailbox tests
│   ├── test_chat_protocol.py # Bilingual ACP, Telenglish & multi-turn tests
│   └── test_ui_server.py     # Web UI server tests
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules (protects .env and private keys)
├── requirements.txt          # Python dependencies
└── README.md                 # Setup, run, and Agentverse instructions
```

---

## 🛠️ Windows Setup and Run Instructions

### Prerequisites
- **Python Version**: **Python 3.10 to 3.13** (Python 3.12 recommended; Python 3.14+ is not yet supported by the uAgents asyncio event loop).
- Verify Python 3.12 is installed:
  ```powershell
  py -3.12 --version
  ```

### 1. Create and Activate Virtual Environment
Open PowerShell inside `AgriSaarthi`:
```powershell
# Create Python 3.12 virtual environment
py -3.12 -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell complains about execution policy, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### 2. Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
*(The defaults are pre-configured to run locally out-of-the-box without requiring third-party API keys).*

---

## 🧪 Running Unit Tests

Run the full automated test suite (13 tests verifying schemas, engine logic, and agent initialization):
```powershell
pytest -v
```

All tests run locally and deterministically without network dependencies.

---

## 🖥️ Running the Interactive Demo

To test real-world scenarios across Punjab (Rabi Wheat/Mustard), Rajasthan (Arid Kharif Bajra/Moong), and Maharashtra (Black Soil Cotton/Soybean):
```powershell
python scripts/demo_query.py
```

Sample output:
```
🌾 SCENARIO: Punjab Rabi Sowing (Low Risk, Alluvial Soil)
📍 Location : Punjab (Sangrur)
📐 Land Size: 5.0 Acres
🌱 Season   : RABI | Soil: Alluvial
💧 Water    : Moderate | Risk: Low
💰 Budget   : ₹110,000 (₹22,000/acre)
----------------------------------------------------------------------
Status: SUCCESS

🏆 Top Primary Recommendations:
  1. Wheat [गेहूँ (Wheat)] - Suitability: 100.0/100
     • Category      : Cereal
     • Est. Cost/Acre: ₹18,000 (Total: ₹90,000)
     • Est. Net Profit: ₹28,075/acre
     • Water Fit     : Optimal | Soil Fit: Optimal
     • Budget Status : Within Budget
  2. Mustard / Rapeseed [सरसों (Mustard)] - Suitability: 100.0/100
     • Category      : Oilseed
     • Est. Cost/Acre: ₹13,000 (Total: ₹65,000)
     • Est. Net Profit: ₹34,600/acre
```

---

## 🤖 Running the Autonomous Fetch.ai Agent

Start the agent locally:
```powershell
python -m agrisaarthi.agent
```

On startup, the agent will display:
```
============================================================
🌾 AgriSaarthi AI Agent 'agrisaarthi_crop_advisor' is Online!
📍 Agent Address : agent1qgquxx39728pek3e8a6w60l0wll4hqljkuf0z24u0r2nekzcjcqtxw3lakd
👛 Wallet Address: fetch19q6txap73w68r84sqhj9mh5j78knkz4uxfrk8e
🌐 Local Endpoint: http://127.0.0.1:8000/submit
============================================================
```

---

## 🌐 Agentverse & ASI:One Connection (uagents 0.26.1)

> [!IMPORTANT]
> A local endpoint like `http://127.0.0.1:8000/submit` cannot be reached by Agentverse or ASI:One.
> The Local Agent Inspector is a debugging UI. It can only make the agent reachable by switching it to **Mailbox** mode.

### What the installed SDK does (verified from source)
- `Agent(mailbox=True)` registers the Agentverse mailbox endpoint. In 0.26.1 `mailbox` is a **bool**; there is no mailbox key.
- On startup the agent logs: `Agent inspector available at https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A<port>&address=<agent address>`.
- If Almanac **contract** registration fails with `InsufficientFundsError`, the SDK skips it and keeps running. Almanac **API** registration is a separate step that doesn't need funds.

### Steps
1. In your local `.env`, set `ENABLE_AGENTVERSE_MAILBOX=true`.
2. Restart: `python -m agrisaarthi.agent`.
3. Open the printed Inspector URL in a browser where you're logged in to Agentverse.
4. Click **Connect** → **Mailbox** and finish the prompts.
5. Check that the agent appears under your Agentverse agents. Also check that the terminal shows no `Agent mailbox not found` warnings.
6. On the agent's Agentverse page, add a name, description and README so ASI:One can match it.
7. Test from ASI:One (see "Verifying ASI:One reachability" below).

### Verifying ASI:One reachability
A response in ASI:One counts as verified only if your local terminal shows all three of these log lines:
- `Received ChatMessage from <sender> (msg_id=...)`
- `Sent ChatAcknowledgement for msg_id=...`
- `Dispatched ChatMessage response to <sender>`

If ASI:One answers but these lines never appear, the answer came from ASI:One's own model, not from AgriSaarthi.

### ACP implementation
`agrisaarthi/chat_protocol.py` builds `Protocol(spec=chat_protocol_spec)` from `uagents_core.contrib.protocols.chat` (`AgentChatProtocol:0.3.0`). It handles `ChatMessage` and `ChatAcknowledgement` and acknowledges every message. It handles start-session and end-session content, and runs JSON or natural-language queries through the recommendation engine. It is included with `publish_manifest=True`.

---

## 🌐 Running the Farmer Voice Demo Web Interface

To experience the live voice-enabled bilingual interface:
```powershell
python scripts/run_farmer_ui.py
```
Open **http://127.0.0.1:8080** in Google Chrome or Microsoft Edge:
1. Click the **🎙️ Microphone button** to speak in Telugu (`te-IN`) or English (`en-IN`).
2. Alternatively, click any of the **Quick Suggestion Chips** (e.g. Telangana 4 acres black soil).
3. Listen to the generated response using the **🔊 వినండి (Listen)** / **⏹️ ఆపు (Stop)** buttons.
4. Switch language on-the-fly (`తెలుగు` / `English` button or type *"Reply in English"*).

---

## 📊 Status Summary

| Component | Status | Details |
|---|---|---|
| **Bilingual NLP (Telugu, English, Telenglish)** | ✅ Verified | Understands scripts, dialects, local units (ఎకరాలు, లక్షలు, వేలు), districts |
| **Voice Interface (STT & TTS)** | ✅ Verified | Web Speech API (`te-IN`, `en-IN`), replay & stop controls, typed fallback |
| **Recommendation Engine & Dataset** | ✅ Verified | 11 authentic ICAR/CACP crops, 4-step agronomic pipeline, zero invented APIs |
| **ACP (`AgentChatProtocol:0.3.0`)** | ✅ Verified | Full Fetch.ai spec compliance, multi-turn context preservation, session store |
| **Automated Unit Tests** | ✅ Verified | **41/41 passing tests** covering Telugu, English, mixed queries, UI server |
| **Secrets & Safety** | ✅ Verified | `.env` and `private_keys.json` excluded in `.gitignore`, no secret leaks |
| **Agentverse Mailbox** | ✅ Verified | Polling active on Testnet (`https://agentverse.ai/v2/agents/mailbox/submit`) |
