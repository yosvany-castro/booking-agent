"""Tests for the dating agent router graph."""

import pytest
from langchain_core.messages import HumanMessage
from langgraph.graph.state import Command

from app.core.langgraph.dating_agent import DatingAgentState, RouterOutput, main_router, route_by_intent


class TestRouterOutput:
    """Tests for RouterOutput schema."""

    def test_router_output_valid_conversacional(self):
        """Test RouterOutput accepts valid 'conversacional' intent."""
        output = RouterOutput(intent="conversacional", confidence=0.95)
        assert output.intent == "conversacional"
        assert output.confidence == 0.95

    def test_router_output_valid_agendar(self):
        """Test RouterOutput accepts valid 'agendar' intent."""
        output = RouterOutput(intent="agendar", confidence=0.85)
        assert output.intent == "agendar"
        assert output.confidence == 0.85

    def test_router_output_valid_reagendar(self):
        """Test RouterOutput accepts valid 'reagendar' intent."""
        output = RouterOutput(intent="reagendar", confidence=0.75)
        assert output.intent == "reagendar"
        assert output.confidence == 0.75

    def test_router_output_valid_cancelar(self):
        """Test RouterOutput accepts valid 'cancelar' intent."""
        output = RouterOutput(intent="cancelar", confidence=0.90)
        assert output.intent == "cancelar"
        assert output.confidence == 0.90

    def test_router_output_confidence_bounds_minimum(self):
        """Test RouterOutput accepts minimum confidence of 0.0."""
        output = RouterOutput(intent="conversacional", confidence=0.0)
        assert output.confidence == 0.0

    def test_router_output_confidence_bounds_maximum(self):
        """Test RouterOutput accepts maximum confidence of 1.0."""
        output = RouterOutput(intent="conversacional", confidence=1.0)
        assert output.confidence == 1.0

    def test_router_output_rejects_invalid_intent(self):
        """Test RouterOutput rejects invalid intent."""
        with pytest.raises(ValueError):
            RouterOutput(intent="invalid_intent", confidence=0.5)

    def test_router_output_rejects_confidence_below_zero(self):
        """Test RouterOutput rejects confidence below 0.0."""
        with pytest.raises(ValueError):
            RouterOutput(intent="conversacional", confidence=-0.1)

    def test_router_output_rejects_confidence_above_one(self):
        """Test RouterOutput rejects confidence above 1.0."""
        with pytest.raises(ValueError):
            RouterOutput(intent="conversacional", confidence=1.1)


class TestMainRouterNode:
    """Tests for the main_router node."""

    @pytest.mark.asyncio
    async def test_main_router_returns_command_with_intent_and_confidence(self):
        """Test main_router returns Command with intent and confidence in state."""
        state = DatingAgentState(
            messages=[HumanMessage(content="Hola, cómo estás?")]
        )

        result = await main_router(state)

        assert isinstance(result, Command)
        assert "intent" in result.update
        assert "confidence" in result.update
        assert result.update["intent"] in ["conversacional", "agendar", "reagendar", "cancelar"]
        assert 0.0 <= result.update["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_main_router_detects_conversacional_intent(self):
        """Test main_router detects conversational intent."""
        state = DatingAgentState(
            messages=[HumanMessage(content="Hola, ¿cómo estás?")]
        )

        result = await main_router(state)

        # Conversational greeting should be detected with high confidence
        assert result.update["intent"] == "conversacional"
        assert result.update["confidence"] > 0.5

    @pytest.mark.asyncio
    async def test_main_router_detects_agendar_intent(self):
        """Test main_router detects scheduling intent."""
        state = DatingAgentState(
            messages=[HumanMessage(content="Quiero agendar una cita para mañana")]
        )

        result = await main_router(state)

        assert result.update["intent"] == "agendar"
        assert result.update["confidence"] > 0.5

    @pytest.mark.asyncio
    async def test_main_router_detects_reagendar_intent(self):
        """Test main_router detects rescheduling intent."""
        state = DatingAgentState(
            messages=[HumanMessage(content="Necesito reagendar mi cita del viernes")]
        )

        result = await main_router(state)

        assert result.update["intent"] == "reagendar"
        assert result.update["confidence"] > 0.5

    @pytest.mark.asyncio
    async def test_main_router_detects_cancelar_intent(self):
        """Test main_router detects cancellation intent."""
        state = DatingAgentState(
            messages=[HumanMessage(content="Quiero cancelar mi cita")]
        )

        result = await main_router(state)

        assert result.update["intent"] == "cancelar"
        assert result.update["confidence"] > 0.5


class TestRouteByIntent:
    """Tests for the route_by_intent routing function."""

    def test_route_by_intent_low_confidence_goes_to_conversacional(self):
        """Test route_by_intent routes low confidence to conversacional."""
        state = DatingAgentState(
            messages=[HumanMessage(content="test")],
            intent="agendar",
            confidence=0.5
        )

        result = route_by_intent(state)

        assert result == "conversacional"

    def test_route_by_intent_zero_confidence_goes_to_conversacional(self):
        """Test route_by_intent routes zero confidence to conversacional."""
        state = DatingAgentState(
            messages=[HumanMessage(content="test")],
            intent="agendar",
            confidence=0.0
        )

        result = route_by_intent(state)

        assert result == "conversacional"

    def test_route_by_intent_high_confidence_agendar(self):
        """Test route_by_intent routes high confidence agendar to agendar node."""
        state = DatingAgentState(
            messages=[HumanMessage(content="test")],
            intent="agendar",
            confidence=0.9
        )

        result = route_by_intent(state)

        assert result == "agendar"

    def test_route_by_intent_high_confidence_reagendar(self):
        """Test route_by_intent routes high confidence reagendar to reagendar node."""
        state = DatingAgentState(
            messages=[HumanMessage(content="test")],
            intent="reagendar",
            confidence=0.85
        )

        result = route_by_intent(state)

        assert result == "reagendar"

    def test_route_by_intent_high_confidence_cancelar(self):
        """Test route_by_intent routes high confidence cancelar to cancelar node."""
        state = DatingAgentState(
            messages=[HumanMessage(content="test")],
            intent="cancelar",
            confidence=0.95
        )

        result = route_by_intent(state)

        assert result == "cancelar"

    def test_route_by_intent_high_confidence_conversacional(self):
        """Test route_by_intent routes high confidence conversacional to conversacional node."""
        state = DatingAgentState(
            messages=[HumanMessage(content="test")],
            intent="conversacional",
            confidence=0.95
        )

        result = route_by_intent(state)

        assert result == "conversacional"

    def test_route_by_intent_boundary_just_above_threshold(self):
        """Test route_by_intent routes confidence just above 0.5 to intent node."""
        state = DatingAgentState(
            messages=[HumanMessage(content="test")],
            intent="agendar",
            confidence=0.51
        )

        result = route_by_intent(state)

        assert result == "agendar"


class TestDatingAgentGraph:
    """Tests for the dating agent graph construction."""

    @pytest.mark.asyncio
    async def test_graph_compiles_successfully(self):
        """Test that the dating agent graph compiles without errors."""
        from app.core.langgraph.dating_agent import create_dating_agent_graph

        graph = await create_dating_agent_graph()

        assert graph is not None

    @pytest.mark.asyncio
    async def test_graph_routes_to_conversacional_node(self):
        """Test graph routes conversational messages to conversacional node."""
        from app.core.langgraph.dating_agent import create_dating_agent_graph

        graph = await create_dating_agent_graph()

        result = await graph.ainvoke({
            "messages": [HumanMessage(content="Hola, ¿cómo estás?")]
        })

        # Should have processed through conversacional node
        assert "messages" in result
        assert len(result["messages"]) > 1

    @pytest.mark.asyncio
    async def test_graph_routes_to_agendar_node(self):
        """Test graph routes scheduling messages to agendar node."""
        from app.core.langgraph.dating_agent import create_dating_agent_graph

        graph = await create_dating_agent_graph()

        result = await graph.ainvoke({
            "messages": [HumanMessage(content="Quiero agendar una cita para mañana")]
        })

        assert "messages" in result
        assert result["intent"] == "agendar"

    @pytest.mark.asyncio
    async def test_graph_routes_to_reagendar_node(self):
        """Test graph routes rescheduling messages to reagendar node."""
        from app.core.langgraph.dating_agent import create_dating_agent_graph

        graph = await create_dating_agent_graph()

        result = await graph.ainvoke({
            "messages": [HumanMessage(content="Necesito reagendar mi cita")]
        })

        assert "messages" in result
        assert result["intent"] == "reagendar"

    @pytest.mark.asyncio
    async def test_graph_routes_to_cancelar_node(self):
        """Test graph routes cancellation messages to cancelar node."""
        from app.core.langgraph.dating_agent import create_dating_agent_graph

        graph = await create_dating_agent_graph()

        result = await graph.ainvoke({
            "messages": [HumanMessage(content="Quiero cancelar mi cita")]
        })

        assert "messages" in result
        assert result["intent"] == "cancelar"
