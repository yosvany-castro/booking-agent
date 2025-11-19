"""LangGraph Studio graph definition for Dating Agent.

This file exports the dating agent graph in a format compatible with LangGraph Studio.
"""

from typing import Annotated, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.graph.state import Command
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import logger


class RouterOutput(BaseModel):
    """Schema for router LLM output."""

    intent: Literal["conversacional", "agendar", "reagendar", "cancelar"]
    confidence: float = Field(ge=0.0, le=1.0)


class DatingAgentState(MessagesState):
    """State for the dating agent graph.

    MessagesState provides the `messages` key automatically with add_messages reducer,
    making it compatible with LangGraph Studio's Chat feature.
    """

    intent: str
    confidence: float


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
    user_message = state["messages"][-1].content

    llm = ChatOpenAI(model=settings.DEFAULT_LLM_MODEL).with_structured_output(RouterOutput)
    response = await llm.ainvoke([SystemMessage(content=ROUTER_PROMPT), HumanMessage(content=user_message)])

    logger.info("router_intent_detected", intent=response.intent, confidence=response.confidence)

    return Command(update={"intent": response.intent, "confidence": response.confidence})


def route_by_intent(state: DatingAgentState) -> str:
    """
    Función que determina a qué nodo ir según intent y confidence.
    RETORNA el nombre del nodo destino como string.
    """
    if state["confidence"] <= 0.5:
        return "conversacional"

    return state["intent"]


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


async def cancelar_node(state: DatingAgentState) -> Command:
    """Nodo para manejar cancelación de citas."""
    logger.info("cancelar_node_executing")

    response = AIMessage(content="Voy a ayudarte a cancelar tu cita.")

    return Command(update={"messages": [response]}, goto=END)


# Create the graph
graph_builder = StateGraph(DatingAgentState)

graph_builder.add_node("main_router", main_router)
graph_builder.add_node("conversacional", conversacional_node)
graph_builder.add_node("agendar", agendar_node)
graph_builder.add_node("reagendar", reagendar_node)
graph_builder.add_node("cancelar", cancelar_node)

graph_builder.set_entry_point("main_router")

graph_builder.add_conditional_edges(
    "main_router",
    route_by_intent,
    {
        "conversacional": "conversacional",
        "agendar": "agendar",
        "reagendar": "reagendar",
        "cancelar": "cancelar",
    },
)

# Compile without checkpointer - LangGraph Studio handles persistence automatically
graph = graph_builder.compile(name="Dating Agent (Studio)")

logger.info("studio_graph_compiled", graph_name="Dating Agent")
