"""
Tests for Fetch.ai AgriSaarthi uAgent initialization, startup lifecycle, and message protocols.
"""

import asyncio
from agrisaarthi.agent import create_agent
from agrisaarthi.models import (
    FarmerProfileRequest,
    Season,
    SoilType,
    WaterAvailability,
    RiskTolerance,
)
from agrisaarthi.engine import AgriSaarthiEngine


def test_agent_initialization():
    """Agent should initialize with valid address, wallet, and name."""
    test_agent = create_agent(
        name="test_agrisaarthi",
        seed="test_agrisaarthi_seed_phrase_secure_123",
        port=8011,
        endpoint="http://127.0.0.1:8011/submit",
        enable_mailbox=False,
    )

    assert test_agent.name == "test_agrisaarthi"
    assert test_agent.address.startswith("agent1")
    assert test_agent.wallet.address().startswith("fetch1")


def test_agent_startup_lifecycle():
    """Verify handle_startup event executes cleanly without context attribute errors."""
    test_agent = create_agent(
        name="test_startup_agent",
        seed="test_startup_seed_secure_987",
        port=8022,
        endpoint="http://127.0.0.1:8022/submit",
        enable_mailbox=False,
    )

    # Execute all registered startup handlers via agent's run_startup_tasks
    asyncio.run(test_agent.run_startup_tasks())

    assert test_agent.name == "test_startup_agent"
    assert test_agent.address.startswith("agent1")


def test_agent_mailbox_mode_uses_agentverse_mailbox_endpoint():
    """enable_mailbox=True must register the SDK's Agentverse mailbox endpoint."""
    test_agent = create_agent(
        name="test_mailbox_agent",
        seed="test_mailbox_seed_456",
        port=8033,
        endpoint="http://127.0.0.1:8033/submit",
        enable_mailbox=True,
        publish_manifest=False,
    )
    urls = [ep.url for ep in test_agent._endpoints]
    assert urls == [test_agent.agentverse.mailbox_endpoint]
    assert test_agent.mailbox_client is not None


def test_agent_local_mode_uses_local_endpoint():
    """enable_mailbox=False keeps the local endpoint and no mailbox client."""
    test_agent = create_agent(
        name="test_local_agent",
        seed="test_local_seed_789",
        port=8034,
        endpoint="http://127.0.0.1:8034/submit",
        enable_mailbox=False,
        publish_manifest=False,
    )
    urls = [ep.url for ep in test_agent._endpoints]
    assert urls == ["http://127.0.0.1:8034/submit"]
    assert test_agent.mailbox_client is None


def test_agent_engine_integration_e2e():
    """Simulate end-to-end message flow through the recommendation engine."""
    request = FarmerProfileRequest(
        farmer_id="e2e_farmer_test",
        state="Karnataka",
        district="Dharwad",
        land_size_acres=4.0,
        soil_type=SoilType.RED,
        water_availability=WaterAvailability.MODERATE,
        season=Season.KHARIF,
        budget_inr=70000.0,
        risk_tolerance=RiskTolerance.MODERATE,
    )

    response = AgriSaarthiEngine.execute(request)

    assert response.workflow_status == "SUCCESS"
    assert response.farmer_id == "e2e_farmer_test"
    assert len(response.primary_recommendations) > 0
    assert response.budget_summary["land_size_acres"] == 4.0

    # Ensure model serialization to dict and JSON works for uAgent transport
    data_dict = response.dict()
    assert "primary_recommendations" in data_dict
    assert "step_by_step_reasoning" in data_dict
    assert "limitations_and_advisory" in data_dict
