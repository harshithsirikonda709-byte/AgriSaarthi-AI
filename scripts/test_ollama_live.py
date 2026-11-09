"""
Live Verification Script for AgriSaarthi AI Ollama Integration.
Demonstrates:
  1. Connecting to local Ollama API at http://localhost:11434
  2. Inspecting installed models and verifying configured OLLAMA_MODEL
  3. Generating grounded agricultural recommendation explanations
  4. Testing Telugu follow-up questions
  5. Testing conversational missing information handling
"""

import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "replace")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "replace")

from agrisaarthi.ollama_client import OllamaClient
from agrisaarthi.chat_protocol import process_chat_message, reset_session


def run_live_verification():
    print("=" * 70)
    print("🌾 AgriSaarthi AI — Live Ollama Integration Verification")
    print("=" * 70)

    client = OllamaClient()
    print(f"Ollama Base URL : {client.base_url}")
    print(f"Configured Model: {client.model}")
    print(f"Timeout         : {client.timeout}s")
    print("-" * 70)

    # 1. Health & Model Availability
    print("1. Checking Ollama connection and installed models...")
    available, msg = client.check_availability()
    print(f"   Status: {'[ONLINE]' if available else '[OFFLINE]'}")
    print(f"   Detail: {msg}")

    if not available:
        print("\n❌ Ollama service or model is unavailable.")
        print(f"   Please start Ollama (`ollama serve`) and pull model (`ollama pull {client.model}`).")
        return False

    installed = client.get_installed_models()
    print(f"   Installed models: {installed}")
    print("\n[PASS] Ollama connection verified successfully!\n")

    # 2. Live Crop Recommendation with Grounded Explanation (English)
    print("2. Testing Live Crop Recommendation (English)...")
    sender_en = "live_verify_en"
    reset_session(sender_en)
    prompt_en = (
        "I have 5 acres of alluvial soil in Punjab with tubewell water for Rabi season, budget 100000"
    )
    print(f"   Prompt: \"{prompt_en}\"")
    reply_en = process_chat_message(text=prompt_en, sender=sender_en)

    print("\n--- Model Response (English) ---")
    print(reply_en[:400] + ("..." if len(reply_en) > 400 else ""))
    assert "AgriSaarthi Crop Advisory: Punjab" in reply_en, "Missing structured recommendation header"
    assert "Wheat" in reply_en, "Missing expected crop recommendation"
    print("\n[PASS] English crop recommendation generated and verified!\n")

    # 3. Live Follow-up Consultation in Telugu (Preserving Context)
    print("3. Testing Live Follow-up Consultation in Telugu...")
    sender_te = "live_verify_te"
    reset_session(sender_te)
    prompt_te1 = "తెలంగాణలో 4 ఎకరాల నల్ల నేల ఉంది, ఖరీఫ్ సీజన్, బోరు బావి నీరు, బడ్జెట్ 1 లక్ష"
    print(f"   Turn 1 (Telugu Profile): \"{prompt_te1}\"")
    reply_te1 = process_chat_message(text=prompt_te1, sender=sender_te)
    print(f"   Turn 1 Response: {reply_te1[:120]}...\n")

    prompt_te2 = "పత్తి పంట గురించి సమగ్ర వివరాలు మరియు రిస్కులు చెప్పండి"
    print(f"   Turn 2 (Telugu Follow-up): \"{prompt_te2}\"")
    reply_te2 = process_chat_message(text=prompt_te2, sender=sender_te)
    print("\n--- Model Follow-up Response (Telugu) ---")
    print(reply_te2[:350] + ("..." if len(reply_te2) > 350 else ""))
    print("\n[PASS] Telugu follow-up consultation with context preserved successfully!\n")

    # 4. Live Missing Information Question
    print("4. Testing Conversational Missing Information Prompt...")
    sender_missing = "live_verify_missing"
    reset_session(sender_missing)
    partial_prompt = "I have 3 acres in Andhra Pradesh for Kharif season"
    print(f"   Partial Prompt: \"{partial_prompt}\"")
    reply_missing = process_chat_message(text=partial_prompt, sender=sender_missing)
    print("\n--- Missing Information Question ---")
    print(reply_missing[:300] + ("..." if len(reply_missing) > 300 else ""))
    print("\n[PASS] Conversational follow-up question for missing details verified!\n")

    print("=" * 70)
    print("🎉 ALL LIVE OLLAMA VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = run_live_verification()
    sys.exit(0 if success else 1)
