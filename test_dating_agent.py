"""Script para testear el agente de citas desde la terminal."""

import asyncio

from langchain_core.messages import HumanMessage

from app.core.langgraph.dating_agent import create_dating_agent_graph


async def test_message(message: str):
    """Testea un mensaje con el agente de citas."""
    print(f"\n{'='*60}")
    print(f"Usuario: {message}")
    print(f"{'='*60}")

    graph = await create_dating_agent_graph()

    result = await graph.ainvoke({"messages": [HumanMessage(content=message)]})

    print(f"\nIntent detectado: {result['intent']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"\nRespuesta del agente:")
    print(f"{result['messages'][-1].content}")
    print(f"{'='*60}\n")


async def main():
    """Ejecuta tests de ejemplo."""
    test_cases = [
        "Hola, ¿cómo estás?",
        "Quiero agendar una cita para mañana",
        "Necesito reagendar mi cita del viernes",
        "Quiero cancelar mi cita",
        "¿Cuál es el horario de atención?",
    ]

    print("\n🤖 TESTING DATING AGENT ROUTER\n")

    for message in test_cases:
        await test_message(message)
        await asyncio.sleep(1)  # Pausa entre tests


async def interactive_mode():
    """Modo interactivo para testear mensajes personalizados."""
    print("\n🤖 MODO INTERACTIVO - DATING AGENT")
    print("Escribe 'salir' para terminar\n")

    graph = await create_dating_agent_graph()

    while True:
        try:
            user_input = input("Tú: ").strip()

            if user_input.lower() in ["salir", "exit", "quit"]:
                print("\n👋 ¡Hasta luego!\n")
                break

            if not user_input:
                continue

            result = await graph.ainvoke({"messages": [HumanMessage(content=user_input)]})

            print(f"\n[Intent: {result['intent']} | Confidence: {result['confidence']:.2f}]")
            print(f"Agente: {result['messages'][-1].content}\n")

        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "-i" or sys.argv[1] == "--interactive":
            # Modo interactivo
            asyncio.run(interactive_mode())
        else:
            # Test con mensaje específico
            message = " ".join(sys.argv[1:])
            asyncio.run(test_message(message))
    else:
        # Ejecuta tests de ejemplo
        asyncio.run(main())
