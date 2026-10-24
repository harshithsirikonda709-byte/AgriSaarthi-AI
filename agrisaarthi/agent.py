"""
AgriSaarthi AI - Fetch.ai Autonomous Decision Agent.
Supports:
  1. Direct uAgent-to-uAgent structured communication via FarmerProfileRequest model.
  2. Official Agent Chat Protocol (ACP v0.3.0) via chat_protocol_spec for ASI:One & Agentverse.
  3. Seamless local mode, Agentverse Inspector, and Mailbox registration.
"""

import os
import asyncio
from typing import Optional
from dotenv import load_dotenv

from uagents import Agent, Context

from agrisaarthi.models import (
    FarmerProfileRequest,
    RecommendationResponse,
)
from agrisaarthi.engine import AgriSaarthiEngine
from agrisaarthi.chat_protocol import create_chat_protocol

# Load environment configuration
load_dotenv()

AGENT_NAME = os.getenv("AGRI_AGENT_NAME", "agrisaarthi_crop_advisor")
AGENT_SEED = os.getenv("AGRI_AGENT_SEED", "agrisaarthi_secure_seed_fetchathon_2026")
AGENT_PORT = int(os.getenv("AGRI_AGENT_PORT", "8000"))
AGENT_ENDPOINT = os.getenv("AGRI_AGENT_ENDPOINT", f"http://127.0.0.1:{AGENT_PORT}/submit")
# uagents 0.26.1: `mailbox` is a bool. The Agentverse side is set up via the
# Local Agent Inspector (Connect -> Mailbox); no mailbox key is needed in code.
ENABLE_MAILBOX = os.getenv("ENABLE_AGENTVERSE_MAILBOX", "true").lower() == "true"
PUBLISH_MANIFEST = os.getenv("PUBLISH_AGENT_MANIFEST", "true").lower() == "true"


def create_agent(
    name: str = AGENT_NAME,
    seed: str = AGENT_SEED,
    port: int = AGENT_PORT,
    endpoint: Optional[str] = AGENT_ENDPOINT,
    enable_mailbox: bool = ENABLE_MAILBOX,
    publish_manifest: bool = PUBLISH_MANIFEST,
) -> Agent:
    """Factory to instantiate the AgriSaarthi uAgent with custom or environment config."""
    mailbox_arg = bool(enable_mailbox)

    # Ensure an active event loop exists for Python 3.12 without deprecation warnings
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    agent_kwargs = {
        "name": name,
        "seed": seed,
        "port": port,
        "loop": loop,
        "network": os.getenv("AGENT_NETWORK", "testnet"),
        "description": (
            "Autonomous climate-smart crop advisory and agricultural decision support "
            "agent for Indian farmers based on location, soil, water, season, and budget."
        ),
    }

    # An explicit endpoint overrides mailbox in the SDK, so only set one.
    if mailbox_arg:
        agent_kwargs["mailbox"] = True
    elif endpoint:
        agent_kwargs["endpoint"] = [endpoint]

    agri_agent = Agent(**agent_kwargs)

    # Safely load UTF-8 README for Agentverse profile (avoids uAgents SDK cp1252 default on Windows)
    readme_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "README.md")
    if os.path.exists(readme_file):
        try:
            with open(readme_file, "r", encoding="utf-8") as f:
                agri_agent._readme = f.read()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Protocol 1: Native Structured Agent-to-Agent Communication
    # -------------------------------------------------------------------------
    @agri_agent.on_message(model=FarmerProfileRequest)
    async def handle_farmer_profile_request(
        ctx: Context, sender: str, msg: FarmerProfileRequest
    ):
        ctx.logger.info(f"Received FarmerProfileRequest from agent: {sender}")
        ctx.logger.info(
            f"   Details: State={msg.state}, Season={msg.season.value}, "
            f"Soil={msg.soil_type.value}, Water={msg.water_availability.value}, "
            f"Land={msg.land_size_acres}ac, Budget=INR {msg.budget_inr:,.0f}"
        )

        # Run multi-step recommendation engine
        response: RecommendationResponse = AgriSaarthiEngine.execute(msg)

        ctx.logger.info(
            f"Sending RecommendationResponse back to {sender}. "
            f"Status: {response.workflow_status}, Primary Recs: {len(response.primary_recommendations)}"
        )

        await ctx.send(sender, response)

    # -------------------------------------------------------------------------
    # Protocol 2: Official Agent Chat Protocol (ACP v0.3.0) for ASI:One
    # -------------------------------------------------------------------------
    chat_proto = create_chat_protocol(engine_cls=AgriSaarthiEngine)
    agri_agent.include(chat_proto, publish_manifest=publish_manifest)

    # -------------------------------------------------------------------------
    # Lifecycle: Startup
    # -------------------------------------------------------------------------
    @agri_agent.on_event("startup")
    async def handle_startup(ctx: Context):
        ctx.logger.info("=" * 60)
        ctx.logger.info(f"[AgriSaarthi] AI Agent '{ctx.agent.name}' is Online!")
        ctx.logger.info(f"Agent Address : {ctx.agent.address}")
        ctx.logger.info(f"Wallet Address: {agri_agent.wallet.address()}")
        ctx.logger.info("Protocols     : AgentChatProtocol:0.3.0 (ACP) + FarmerProfileRequest")
        if mailbox_arg:
            ctx.logger.info("Agentverse Mailbox mode is ACTIVE.")
        else:
            ctx.logger.info(f"Local Endpoint: {endpoint}")
        ctx.logger.info("=" * 60)

    return agri_agent


# Default agent instance
agent = create_agent()

if __name__ == "__main__":
    print(f"Starting AgriSaarthi agent '{agent.name}'...")
    agent.run()
