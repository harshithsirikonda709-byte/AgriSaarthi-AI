"""
Ollama API Client and Agricultural Assistant Integration for AgriSaarthi AI.
Provides lightweight, zero-external-dependency communication with a local Ollama instance.
Supports:
  - Configurable endpoint (OLLAMA_BASE_URL, default http://localhost:11434)
  - Configurable model (OLLAMA_MODEL, default qwen2.5:0.5b)
  - Configurable timeout (OLLAMA_TIMEOUT, default 15.0s)
  - Clear error detection for offline Ollama or uninstalled models
  - Strict grounding in AgriSaarthi recommendation engine outputs
  - Telugu and English prompt templates and responses
"""

import os
import json
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List, Tuple

from dotenv import load_dotenv

from agrisaarthi.models import FarmerProfileRequest, RecommendationResponse

# Load environment configuration
load_dotenv()

logger = logging.getLogger("agrisaarthi.ollama")

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:0.5b"
DEFAULT_OLLAMA_TIMEOUT = 30.0
DEFAULT_OLLAMA_MAX_TOKENS = 256


# =============================================================================
# Custom Exception Hierarchy
# =============================================================================

class OllamaError(Exception):
    """Base exception for all Ollama client errors."""
    pass


class OllamaConnectionError(OllamaError):
    """Raised when Ollama cannot be reached or the request times out."""
    pass


class OllamaModelNotFoundError(OllamaError):
    """Raised when the specified model is not installed/downloaded in Ollama."""
    pass


class OllamaResponseError(OllamaError):
    """Raised when Ollama returns an unexpected HTTP status or payload."""
    pass


# =============================================================================
# Ollama Client Implementation
# =============================================================================

class OllamaClient:
    """
    Lightweight, reusable client for interacting with the local Ollama API.
    Uses standard library urllib to avoid extra external dependencies.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (
            base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        ).rstrip("/")
        self.model = (
            model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        ).strip()
        try:
            self.timeout = float(
                timeout or os.getenv("OLLAMA_TIMEOUT", str(DEFAULT_OLLAMA_TIMEOUT))
            )
        except (ValueError, TypeError):
            self.timeout = DEFAULT_OLLAMA_TIMEOUT
        try:
            self.max_tokens = int(
                os.getenv("OLLAMA_MAX_TOKENS", str(DEFAULT_OLLAMA_MAX_TOKENS))
            )
        except (ValueError, TypeError):
            self.max_tokens = DEFAULT_OLLAMA_MAX_TOKENS

    def get_installed_models(self) -> List[str]:
        """
        Query /api/tags to retrieve the list of installed model names.
        Raises OllamaConnectionError if Ollama is unreachable.
        """
        url = f"{self.base_url}/api/tags"
        req = urllib.request.Request(
            url,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                names: List[str] = []
                for m in models:
                    name = m.get("name", "")
                    if name:
                        names.append(name)
                        if name.endswith(":latest"):
                            names.append(name[:-7])
                return names
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", str(e))
            raise OllamaConnectionError(
                f"Ollama is unreachable at {self.base_url} ({reason}). "
                "Please verify Ollama is running (`ollama serve`)."
            ) from e
        except Exception as e:
            raise OllamaConnectionError(
                f"Failed to connect to Ollama at {self.base_url}: {e}"
            ) from e

    def check_availability(self) -> Tuple[bool, str]:
        """
        Check if Ollama service is reachable and the configured model is installed.
        Returns:
            (is_available: bool, status_description: str)
        """
        try:
            installed = self.get_installed_models()
        except OllamaConnectionError as e:
            return False, str(e)

        target = self.model
        target_base = target.split(":")[0]
        is_installed = any(
            target == m or target_base == m.split(":")[0] or m.startswith(target)
            for m in installed
        )

        if not is_installed:
            return False, (
                f"Ollama model '{self.model}' is not installed. "
                f"Available models: {installed or 'none'}. "
                f"To install, run: `ollama pull {self.model}`"
            )

        return True, f"Ollama is online with model '{self.model}'."

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        system: Optional[str] = None,
    ) -> str:
        """
        Send a conversation to Ollama /api/chat endpoint with streaming disabled.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": str}
            temperature: Sampling temperature (default 0.2 for consistency)
            system: Optional system prompt to prepend

        Returns:
            Assistant's response text.

        Raises:
            OllamaConnectionError, OllamaModelNotFoundError, OllamaResponseError
        """
        payload_messages = list(messages)
        if system and not any(m.get("role") == "system" for m in payload_messages):
            payload_messages.insert(0, {"role": "system", "content": system})

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": self.max_tokens,
            },
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/api/chat"
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")
                if status != 200:
                    raise OllamaResponseError(f"Ollama returned HTTP status {status}: {body}")
                result = json.loads(body)
                content = result.get("message", {}).get("content", "")
                return content.strip()
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            if e.code == 404:
                raise OllamaModelNotFoundError(
                    f"Model '{self.model}' not found in Ollama (HTTP 404). "
                    f"Please install it using: `ollama pull {self.model}`"
                ) from e
            raise OllamaResponseError(
                f"Ollama HTTP {e.code} error: {e.reason}. Details: {error_body}"
            ) from e
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", str(e))
            raise OllamaConnectionError(
                f"Ollama connection error at {self.base_url}: {reason}. "
                "Ensure Ollama is running (`ollama serve`)."
            ) from e
        except TimeoutError as e:
            raise OllamaConnectionError(
                f"Ollama request timed out after {self.timeout}s at {self.base_url}."
            ) from e
        except Exception as e:
            if "timed out" in str(e).lower():
                raise OllamaConnectionError(
                    f"Ollama request timed out after {self.timeout}s at {self.base_url}."
                ) from e
            raise OllamaResponseError(f"Unexpected Ollama communication error: {e}") from e


# =============================================================================
# Agricultural Assistant Prompts & Workflows
# =============================================================================

def build_system_prompt(lang: str = "en") -> str:
    """
    Constructs the core system prompt enforcing strict agricultural rules:
      - Identifying farmer problem before prescribing treatment
      - Maximum three targeted follow-up questions for missing details
      - Distinguishing verified retrieved reference evidence from general knowledge
      - Never hallucinating chemical pesticide dosages, prices, schemes, or sources
      - Transparently stating uncertainty and recommending KVK/expert physical inspection
      - Telugu and English language instruction
    """
    lang_instruction = (
        "Respond in fluent, respectful, and simple Telugu (తెలుగు) easily understood by rural farmers. Avoid overly complex jargon."
        if lang == "te"
        else "Respond in clear, accessible, farmer-friendly English. Avoid academic jargon."
    )

    return f"""You are AgriSaarthi AI, a responsible, trustworthy agricultural decision assistant for Indian farmers.

CORE OPERATIONAL RULES:
1. IDENTIFY THE PROBLEM FIRST: Before suggesting any treatment or action, understand the farmer's specific crop, symptom, and field conditions. Never prescribe treatments or jump to conclusions from vague descriptions.
2. MAXIMUM THREE TARGETED QUESTIONS: When essential diagnostic details are missing, ask at most THREE focused, highly relevant follow-up questions (e.g. crop growth stage/age, location of symptom on older vs younger leaves, recent water/soil conditions).
3. ABSOLUTE ZERO HALLUCINATION: NEVER invent agricultural facts, unverified government schemes, chemical pesticide or fungicide dosages, prices, or citations. Do not claim that weather, soil conditions, or crop diseases have been verified unless verified data is provided in context.
4. DISTINGUISH RETRIEVED EVIDENCE FROM GENERAL KNOWLEDGE: When verified official reference evidence (from ICAR, IIRR, CICR, IIWBR, IIHR, or State Agricultural Universities) is provided in context, explicitly attribute it and explain what evidence supports each possible cause. Clearly state when advice is general agronomic guidance vs. verified reference knowledge.
5. EXPLAIN UNCERTAINTY & MANDATE EXPERT INSPECTION: Never diagnose a disease with 100% certainty based on visible symptoms alone. Symptoms like yellowing or curling can stem from overlapping factors (nutrient deficiencies, fungal pathogens, root pests, or abiotic stress). State uncertainty transparently and advise the farmer to bring a physical sample to their nearest Krishi Vigyan Kendra (KVK) or Village Agriculture Officer (VAO).
6. RECOMMEND ONLY SAFE, NON-TOXIC INITIAL ACTIONS: Suggest safe cultural practices (e.g. improving drainage, using sticky traps, removing diseased debris) and warn against indiscriminate chemical spraying without laboratory or expert confirmation.
7. LANGUAGE & TONE: {lang_instruction} Use clean markdown formatting with bullet points.
"""


def explain_crop_recommendation_with_ollama(
    profile: FarmerProfileRequest,
    response: RecommendationResponse,
    client: Optional[OllamaClient] = None,
    lang: str = "en",
    user_query: str = "",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Uses the local Ollama LLM to generate an explanation of the crop recommendations
    produced by AgriSaarthiEngine, strictly grounded in the structured engine outputs.

    Returns:
        Tuple[Optional[str], Optional[str]]: (model_output, error_notice)
        If model call succeeds: (text, None)
        If model call fails: (None, error_message)
    """
    llm = client or OllamaClient()

    # Build concise context block from verified engine data
    recs_summary: List[str] = []
    for idx, crop in enumerate(response.primary_recommendations, 1):
        recs_summary.append(
            f"Crop {idx}: {crop.crop_name} ({crop.hindi_name})\n"
            f"  - Suitability Score: {crop.suitability_score}/100\n"
            f"  - Category: {crop.category}\n"
            f"  - Soil Compatibility: {crop.soil_compatibility}\n"
            f"  - Water Compatibility: {crop.water_compatibility}\n"
            f"  - Estimated Cost: INR {crop.estimated_cost_per_acre_inr:,.0f}/acre (Total: INR {crop.total_estimated_cost_inr:,.0f})\n"
            f"  - Expected Yield: {crop.expected_yield_range_quintals_per_acre[0]} - {crop.expected_yield_range_quintals_per_acre[1]} quintals/acre\n"
            f"  - Estimated Net Profit: INR {crop.estimated_net_profit_per_acre_inr:,.0f}/acre\n"
            f"  - Key Strengths: {', '.join(crop.key_strengths)}\n"
            f"  - Risk Factors: {', '.join(crop.risk_factors)}"
        )

    alt_summary: List[str] = []
    for alt in response.alternative_recommendations:
        alt_summary.append(
            f"- {alt.crop_name} (Score: {alt.suitability_score}/100, Cost/ac: INR {alt.estimated_cost_per_acre_inr:,.0f})"
        )

    context_prompt = (
        f"VERIFIED ENGINE OUTPUT FOR FARMER:\n"
        f"Farm Holding: {profile.land_size_acres:.1f} acres in {profile.state} (District: {profile.district or 'N/A'})\n"
        f"Season: {profile.season.value.upper()}\n"
        f"Soil: {profile.soil_type.value.title()}\n"
        f"Water: {profile.water_availability.value.title()}\n"
        f"Budget: INR {profile.budget_inr:,.0f} (INR {profile.budget_inr / profile.land_size_acres:,.0f}/acre)\n"
        f"Status: {response.workflow_status}\n\n"
        f"PRIMARY RECOMMENDED CROPS:\n"
        f"{chr(10).join(recs_summary) if recs_summary else 'No viable crops found within constraints.'}\n\n"
        f"ALTERNATIVE / DIVERSIFICATION CROPS:\n"
        f"{chr(10).join(alt_summary) if alt_summary else 'None'}\n\n"
        f"ENGINE REASONING STEPS:\n"
        f"{chr(10).join(f'- {s}' for s in response.step_by_step_reasoning)}\n\n"
        f"ADVISORY LIMITATIONS:\n"
        f"{chr(10).join(f'- {l}' for l in response.limitations_and_advisory)}\n\n"
        f"TASK:\n"
        f"Present these recommendations to the farmer in a warm, helpful manner in "
        f"{'Telugu (తెలుగు)' if lang == 'te' else 'English'}. "
        f"Explain why each crop is suited to their soil and season, highlight the key benefits and risks, "
        f"and mention advisory limitations (such as Soil Health Card testing and consulting local KVK). "
        f"Do NOT invent new numbers or unverified live prices."
    )

    try:
        explanation = llm.chat(
            messages=[{"role": "user", "content": context_prompt}],
            system=build_system_prompt(lang=lang),
        )
        return explanation, None
    except Exception as e:
        logger.warning(f"Ollama explanation failed: {e}")
        return None, str(e)


def answer_follow_up_with_ollama(
    query: str,
    profile: Optional[FarmerProfileRequest],
    response: Optional[RecommendationResponse],
    client: Optional[OllamaClient] = None,
    lang: str = "en",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Answers farmer follow-up questions using Ollama grounded in previous recommendations.
    """
    llm = client or OllamaClient()

    context_lines = []
    if profile and response:
        context_lines.append(
            f"FARM CONTEXT: {profile.land_size_acres:.1f} acres in {profile.state}, "
            f"Season: {profile.season.value}, Soil: {profile.soil_type.value}, Water: {profile.water_availability.value}, "
            f"Budget: INR {profile.budget_inr:,.0f}."
        )
        crops_info = [
            f"{c.crop_name} (Score: {c.suitability_score}/100, Est Cost: INR {c.estimated_cost_per_acre_inr:,.0f}/ac, "
            f"Est Profit: INR {c.estimated_net_profit_per_acre_inr:,.0f}/ac, Strengths: {'; '.join(c.key_strengths)}, "
            f"Risks: {'; '.join(c.risk_factors)})"
            for c in response.primary_recommendations
        ]
        context_lines.append(f"RECOMMENDED CROPS: {chr(10).join(crops_info)}")
    else:
        context_lines.append("FARM CONTEXT: No previous recommendation profile registered in this session.")

    prompt = (
        f"{chr(10).join(context_lines)}\n\n"
        f"FARMER'S FOLLOW-UP QUESTION:\n\"{query}\"\n\n"
        f"TASK:\n"
        f"Answer the farmer's question in {'Telugu (తెలుగు)' if lang == 'te' else 'English'}. "
        f"If the question asks about why a crop was chosen, risks, costs, or profits, use the exact data above. "
        f"If the question involves crop diseases or fertilizer recommendations, do not guess chemical dosages; "
        f"advise testing soil and seeking local KVK/extension assistance. "
        f"If no farm context exists, guide the farmer to provide their land, state, soil, water, season, and budget."
    )

    try:
        reply = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system=build_system_prompt(lang=lang),
        )
        return reply, None
    except Exception as e:
        logger.warning(f"Ollama follow-up failed: {e}")
        return None, str(e)


def ask_missing_info_with_ollama(
    missing_fields: List[str],
    user_message: str,
    client: Optional[OllamaClient] = None,
    lang: str = "en",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Generates polite, targeted follow-up questions asking the farmer for missing farm details.
    """
    llm = client or OllamaClient()

    prompt = (
        f"The farmer sent the following message:\n\"{user_message}\"\n\n"
        f"To calculate optimal crop recommendations, AgriSaarthi requires these missing parameters:\n"
        f"{', '.join(missing_fields)}\n\n"
        f"TASK:\n"
        f"In a polite, encouraging, farmer-friendly tone in "
        f"{'Telugu (తెలుగు)' if lang == 'te' else 'English'}, "
        f"acknowledge what they shared and ask clear follow-up questions to collect the missing details. "
        f"Provide brief examples for the missing fields."
    )

    try:
        reply = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system=build_system_prompt(lang=lang),
        )
        return reply, None
    except Exception as e:
        logger.warning(f"Ollama missing info question failed: {e}")
        return None, str(e)


def explain_crop_problem_follow_up_with_ollama(
    crop: str,
    symptom: str,
    questions: List[str],
    client: Optional[OllamaClient] = None,
    lang: str = "en",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Formulates a polite response acknowledging the crop symptom and asking
    at most three relevant follow-up questions before prescribing treatment.
    """
    llm = client or OllamaClient()

    questions_formatted = "\n".join(f"{idx}. {q}" for idx, q in enumerate(questions[:3], 1))
    prompt = (
        f"FARMER OBSERVATION: The farmer reports that in their {crop}, {symptom}.\n\n"
        f"DIAGNOSTIC TARGET QUESTIONS TO ASK (MAX 3):\n"
        f"{questions_formatted}\n\n"
        f"TASK:\n"
        f"In {'Telugu (తెలుగు)' if lang == 'te' else 'English'}, "
        f"politely acknowledge their concern, explain that this symptom can stem from multiple possible causes, "
        f"and ask these exact 3 questions clearly so we can narrow down the issue safely. "
        f"Do NOT diagnose a disease with certainty yet. Do NOT prescribe any chemical pesticides."
    )

    try:
        reply = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system=build_system_prompt(lang=lang),
        )
        return reply, None
    except Exception as e:
        logger.warning(f"Ollama crop problem follow-up question failed: {e}")
        return None, str(e)


def diagnose_crop_problem_with_ollama(
    crop: str,
    symptom: str,
    farmer_answers: str,
    possible_causes: List[Dict[str, str]],
    safe_actions: List[str],
    source_name: str,
    source_reference: str,
    client: Optional[OllamaClient] = None,
    lang: str = "en",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Synthesizes a structured crop diagnostic advisory based on retrieved official reference evidence
    and the farmer's answers to the follow-up questions.
    """
    llm = client or OllamaClient()

    causes_text = []
    for c in possible_causes:
        causes_text.append(
            f"- Cause: {c.get('name_en', '')} ({c.get('name_te', '')})\n"
            f"  Evidence: {c.get('evidence_en', '')}\n"
            f"  Key distinguishing clues: {c.get('clues_en', '')}"
        )

    causes_formatted = "\n".join(causes_text)
    actions_formatted = "\n".join(f"- {a}" for a in safe_actions)

    prompt = (
        f"RETRIEVED OFFICIAL AGRICULTURAL REFERENCE:\n"
        f"Source: {source_name} ({source_reference})\n"
        f"Crop: {crop} | Symptom: {symptom}\n\n"
        f"POSSIBLE VERIFIED CAUSES & EVIDENCE:\n"
        f"{causes_formatted}\n\n"
        f"SAFE NEXT STEPS (CULTURAL / NON-TOXIC):\n"
        f"{actions_formatted}\n\n"
        f"FARMER'S REPORTED ANSWERS & CONDITIONS:\n"
        f"\"{farmer_answers}\"\n\n"
        f"TASK:\n"
        f"In {'Telugu (తెలుగు)' if lang == 'te' else 'English'}:\n"
        f"1. Summarize the possible causes based on the official reference evidence.\n"
        f"2. Explain what evidence supports each possibility given the farmer's answers (e.g. leaf position, crop age, water stagnation).\n"
        f"3. Suggest safe next steps (cultural practices, drainage, observation).\n"
        f"4. State clearly what additional inspection or expert examination is needed.\n"
        f"5. Emphasize UNCERTAINTY: state that a definitive diagnosis cannot be made from visible symptoms alone, and strongly recommend taking a physical sample to the local Krishi Vigyan Kendra (KVK) or Village Agriculture Officer (VAO).\n"
        f"6. DO NOT invent chemical pesticide dosages or claim diseases have been verified."
    )

    try:
        reply = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system=build_system_prompt(lang=lang),
        )
        return reply, None
    except Exception as e:
        logger.warning(f"Ollama crop diagnosis synthesis failed: {e}")
        return None, str(e)
