"""Dating agent with router-based intent detection."""

import re
from typing import Annotated, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import Command, CompiledStateGraph
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import logger


class RouterOutput(BaseModel):
    """Schema for router LLM output."""

    intent: Literal["conversacional", "agendar", "reagendar", "cancelar"]
    confidence: float = Field(ge=0.0, le=1.0)


class DatingAgentState(BaseModel):
    """State for the dating agent graph."""

    messages: Annotated[list, add_messages] = Field(
        default_factory=list, description="The messages in the conversation"
    )
    intent: str = Field(default="", description="The detected intent")
    confidence: float = Field(default=0.0, description="Confidence score for the intent")


class CancelacionState(BaseModel):
    """State for the cancellation sub-graph."""

    messages: Annotated[list, add_messages] = Field(
        default_factory=list, description="The messages in the conversation"
    )
    confirmation_number: Optional[str] = Field(default=None, description="User's confirmation number")
    validation_attempts: int = Field(default=0, description="Number of validation attempts")
    is_valid: bool = Field(default=False, description="Whether the confirmation number is valid")
    escalated: bool = Field(default=False, description="Whether the case was escalated to human")


# ============================================================================
# TOOLS FOR CANCELLATION
# ============================================================================


@tool
async def validate_confirmation_number(confirmation_number: str) -> dict:
    """Validate if the confirmation number exists in the business database.

    Args:
        confirmation_number: The confirmation number to validate

    Returns:
        dict with:
          - is_valid: bool indicating if the number is valid
          - booking_details: dict with booking info if valid, None otherwise
    """
    logger.info("validating_confirmation_number", confirmation_number=confirmation_number)

    # MOCK IMPLEMENTATION
    # En el futuro: query a BD real del negocio
    # Por ahora: válido si tiene exactamente 8 caracteres alfanuméricos

    if confirmation_number and len(confirmation_number) == 8 and confirmation_number.isalnum():
        logger.info("confirmation_number_valid", confirmation_number=confirmation_number)
        return {
            "is_valid": True,
            "booking_details": {
                "confirmation_number": confirmation_number,
                "date": "2025-01-15",
                "time": "10:00 AM",
                "doctor": "Dr. Smith",
            },
        }
    else:
        logger.warning("confirmation_number_invalid", confirmation_number=confirmation_number)
        return {"is_valid": False, "booking_details": None}


@tool
async def escalate_to_human(user_id: str, session_id: str, confirmation_number: str, reason: str) -> dict:
    """Escalate the case to human support.

    Args:
        user_id: User identifier
        session_id: Session identifier
        confirmation_number: The confirmation number that failed validation
        reason: Reason for escalation

    Returns:
        dict with:
          - escalated: bool
          - ticket_id: str
          - message: str
    """
    # MOCK IMPLEMENTATION
    # En el futuro: integrar con sistema de tickets/CRM

    logger.warning(
        "case_escalated_to_human",
        user_id=user_id,
        session_id=session_id,
        confirmation_number=confirmation_number,
        reason=reason,
    )

    ticket_id = f"TICKET-{session_id[:8]}" if session_id else "TICKET-UNKNOWN"

    return {"escalated": True, "ticket_id": ticket_id, "message": "Este caso será escalado"}


ROUTER_PROMPT = """Eres un asistente que clasifica la intención del usuario en conversaciones sobre citas médicas.

Analiza el mensaje del usuario y determina:
1. La intención: "conversacional", "agendar", "reagendar", o "cancelar"
2. Tu nivel de confianza (0.0 a 1.0)

Reglas:
- "conversacional": Saludos, preguntas generales, conversación casual
- "agendar": Usuario quiere programar una nueva cita
- "reagendar": Usuario quiere cambiar una cita existente
- "cancelar": Usuario quiere cancelar una cita

Responde con alta confianza (>0.7) solo si estás seguro de la intención.
Si hay ambigüedad, usa confianza baja (≤0.5) y clasifica como "conversacional"."""


async def main_router(state: DatingAgentState) -> Command:
    """Nodo que clasifica la intención del usuario."""
    user_message = state.messages[-1].content

    llm = ChatOpenAI(model=settings.DEFAULT_LLM_MODEL).with_structured_output(RouterOutput)
    response = await llm.ainvoke([SystemMessage(content=ROUTER_PROMPT), HumanMessage(content=user_message)])

    logger.info("router_intent_detected", intent=response.intent, confidence=response.confidence)

    return Command(update={"intent": response.intent, "confidence": response.confidence})


def route_by_intent(state: DatingAgentState) -> str:
    """
    Función que determina a qué nodo ir según intent y confidence.
    RETORNA el nombre del nodo destino como string.
    """
    if state.confidence <= 0.5:
        return "conversacional"

    return state.intent


async def conversacional_node(state: DatingAgentState) -> Command:
    """Nodo para manejar conversación casual."""
    logger.info("conversacional_node_executing")

    response = AIMessage(content="Entiendo que quieres conversar. ¿En qué puedo ayudarte?")

    return Command(update={"messages": [response]}, goto=END)


async def agendar_node(state: DatingAgentState) -> Command:
    """Nodo para manejar agendamiento de citas."""
    logger.info("agendar_node_executing")

    response = AIMessage(content="Voy a ayudarte a agendar una cita.")

    return Command(update={"messages": [response]}, goto=END)


async def reagendar_node(state: DatingAgentState) -> Command:
    """Nodo para manejar reagendamiento de citas."""
    logger.info("reagendar_node_executing")

    response = AIMessage(content="Voy a ayudarte a reagendar tu cita.")

    return Command(update={"messages": [response]}, goto=END)


# ============================================================================
# CANCELLATION SUB-GRAPH NODES
# ============================================================================


async def ask_confirmation_number_node(state: CancelacionState) -> Command:
    """Ask user for their confirmation number.

    This is the entry point of the cancellation sub-graph.
    """
    logger.info("ask_confirmation_number_node_executing", attempts=state.validation_attempts)

    if state.validation_attempts == 0:
        # First time asking
        message_content = (
            "Para cancelar tu cita, necesito el número de confirmación. "
            "¿Cuál es tu número de confirmación?"
        )
    else:
        # Retry after failed attempt
        message_content = (
            "El número que proporcionaste no es válido. "
            "Por favor, verifica e ingresa nuevamente tu número de confirmación."
        )

    response = AIMessage(content=message_content)

    logger.info("waiting_for_confirmation_number", attempts=state.validation_attempts)

    # Return and wait for user response
    return Command(update={"messages": [response]})


async def extract_number_node(state: CancelacionState) -> Command:
    """Extract confirmation number from user's message."""
    logger.info("extract_number_node_executing")

    # Get the last user message
    user_message = state.messages[-1].content if state.messages else ""

    # Extract alphanumeric confirmation number
    # Try to find a sequence of 6-10 alphanumeric characters
    extracted_number = None

    # First, try to find a pattern like CONF-12345 or ABC12345
    pattern = r"\b[A-Z0-9]{6,10}\b"
    matches = re.findall(pattern, user_message.upper())

    if matches:
        extracted_number = matches[0]
    else:
        # If no match, try to clean the message and use it directly
        cleaned = re.sub(r"[^A-Z0-9]", "", user_message.upper())
        if 6 <= len(cleaned) <= 10:
            extracted_number = cleaned

    # If still no number, use the raw message (will fail validation)
    if not extracted_number:
        extracted_number = user_message.strip()

    logger.info("confirmation_number_extracted", extracted_number=extracted_number)

    return Command(update={"confirmation_number": extracted_number})


async def validate_number_node(state: CancelacionState) -> Command:
    """Validate the confirmation number using the validation tool."""
    logger.info("validate_number_node_executing", confirmation_number=state.confirmation_number)

    # Call the validation tool
    validation_result = await validate_confirmation_number.ainvoke({"confirmation_number": state.confirmation_number})

    is_valid = validation_result.get("is_valid", False)
    attempts = state.validation_attempts + 1

    logger.info(
        "validation_result",
        confirmation_number=state.confirmation_number,
        is_valid=is_valid,
        attempts=attempts,
    )

    return Command(update={"is_valid": is_valid, "validation_attempts": attempts})


def route_cancellation_decision(state: CancelacionState) -> str:
    """Decide next node based on validation result and attempts.

    Returns:
        str: Name of the next node to execute
    """
    logger.info(
        "route_cancellation_decision",
        is_valid=state.is_valid,
        attempts=state.validation_attempts,
        escalated=state.escalated,
    )

    # CASE 1: Valid number -> Confirm cancellation
    if state.is_valid:
        logger.info("routing_to_confirm_cancellation")
        return "confirm_cancellation"

    # CASE 2: Invalid but still has attempts left
    if state.validation_attempts < 2:
        logger.info("routing_to_retry", remaining_attempts=2 - state.validation_attempts)
        return "retry"

    # CASE 3: Invalid and no attempts left -> Escalate
    logger.info("routing_to_escalate", total_attempts=state.validation_attempts)
    return "escalate"


async def retry_node(state: CancelacionState) -> Command:
    """Handle retry flow - ask for confirmation number again."""
    logger.info("retry_node_executing", attempts=state.validation_attempts)

    # Don't add a message here - ask_confirmation_number_node will do it
    # Just reset the confirmation number to prepare for new input
    return Command(update={"confirmation_number": None}, goto="ask_confirmation_number")


async def confirm_cancellation_node(state: CancelacionState) -> Command:
    """Confirm successful cancellation."""
    logger.info("confirm_cancellation_node_executing", confirmation_number=state.confirmation_number)

    # TODO: In the future, actually cancel the appointment in the database

    message_content = f"✅ Tu cita ha sido cancelada exitosamente. Número de confirmación: {state.confirmation_number}"

    response = AIMessage(content=message_content)

    logger.info("cancellation_confirmed", confirmation_number=state.confirmation_number)

    return Command(update={"messages": [response]}, goto=END)


async def escalate_node(state: CancelacionState) -> Command:
    """Escalate case to human support after failed validation attempts."""
    logger.info("escalate_node_executing", confirmation_number=state.confirmation_number)

    # Call the escalation tool
    escalation_result = await escalate_to_human.ainvoke(
        {
            "user_id": "unknown",  # Will be provided from context in the future
            "session_id": "unknown",  # Will be provided from context in the future
            "confirmation_number": state.confirmation_number or "none",
            "reason": "invalid_confirmation_number",
        }
    )

    message_content = (
        "Lo siento, no pudimos validar tu número de confirmación después de varios intentos. "
        f"{escalation_result.get('message', 'Este caso será escalado')} "
        "Nuestro equipo de soporte te contactará pronto."
    )

    response = AIMessage(content=message_content)

    logger.info("case_escalated", ticket_id=escalation_result.get("ticket_id"))

    return Command(update={"messages": [response], "escalated": True}, goto=END)


async def create_cancellation_subgraph() -> CompiledStateGraph:
    """Create and compile the cancellation sub-graph.

    This sub-graph handles the complete flow of canceling an appointment:
    1. Ask for confirmation number
    2. Extract and validate it
    3. Retry if invalid (up to 2 attempts)
    4. Escalate to human if validation fails twice
    5. Confirm cancellation if valid

    Returns:
        CompiledStateGraph: The compiled cancellation sub-graph
    """
    logger.info("creating_cancellation_subgraph")

    builder = StateGraph(CancelacionState)

    # Add nodes
    builder.add_node("ask_confirmation_number", ask_confirmation_number_node)
    builder.add_node("extract_number", extract_number_node)
    builder.add_node("validate", validate_number_node)
    builder.add_node("retry", retry_node)
    builder.add_node("confirm_cancellation", confirm_cancellation_node)
    builder.add_node("escalate", escalate_node)

    # Set entry point
    builder.set_entry_point("ask_confirmation_number")

    # Add linear edges
    builder.add_edge("ask_confirmation_number", "extract_number")
    builder.add_edge("extract_number", "validate")

    # Add conditional edges from validate
    builder.add_conditional_edges(
        "validate",
        route_cancellation_decision,
        {
            "confirm_cancellation": "confirm_cancellation",
            "retry": "retry",
            "escalate": "escalate",
        },
    )

    # End nodes
    builder.add_edge("confirm_cancellation", END)
    builder.add_edge("escalate", END)

    graph = builder.compile()

    logger.info("cancellation_subgraph_created")

    return graph


async def cancelar_node(state: DatingAgentState) -> Command:
    """Nodo para manejar cancelación de citas.

    This node invokes the cancellation sub-graph which handles the complete
    cancellation flow including validation and escalation.
    """
    logger.info("cancelar_node_executing")

    # Create the cancellation sub-graph
    subgraph = await create_cancellation_subgraph()

    # Invoke the sub-graph with current messages
    # The sub-graph will handle the multi-turn conversation
    result = await subgraph.ainvoke({"messages": state.messages})

    logger.info("cancelar_subgraph_completed", escalated=result.get("escalated", False))

    # Return the updated messages from the sub-graph
    return Command(update={"messages": result["messages"]}, goto=END)


async def create_dating_agent_graph() -> CompiledStateGraph:
    """Crea y compila el grafo del agente de citas."""
    workflow = StateGraph(DatingAgentState)

    workflow.add_node("main_router", main_router)
    workflow.add_node("conversacional", conversacional_node)
    workflow.add_node("agendar", agendar_node)
    workflow.add_node("reagendar", reagendar_node)
    workflow.add_node("cancelar", cancelar_node)

    workflow.set_entry_point("main_router")

    workflow.add_conditional_edges(
        "main_router",
        route_by_intent,
        {
            "conversacional": "conversacional",
            "agendar": "agendar",
            "reagendar": "reagendar",
            "cancelar": "cancelar",
        },
    )

    graph = workflow.compile()

    logger.info("dating_agent_graph_created")

    return graph
