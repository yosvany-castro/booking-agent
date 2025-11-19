"""Script para testear el flujo de cancelación del agente de citas."""

import asyncio

from langchain_core.messages import HumanMessage

from app.core.langgraph.dating_agent import create_dating_agent_graph


async def test_cancellation_successful():
    """Test caso exitoso: número válido en primer intento."""
    print("\n" + "="*70)
    print("TEST 1: Cancelación exitosa en primer intento")
    print("="*70)

    graph = await create_dating_agent_graph()

    # Usuario quiere cancelar
    result1 = await graph.ainvoke({"messages": [HumanMessage(content="Quiero cancelar mi cita")]})
    print(f"\nUsuario: Quiero cancelar mi cita")
    print(f"Intent detectado: {result1['intent']} (confidence: {result1['confidence']:.2f})")
    print(f"Bot: {result1['messages'][-1].content}")

    # Usuario proporciona número válido (8 caracteres alfanuméricos)
    result2 = await graph.ainvoke({
        "messages": result1['messages'] + [HumanMessage(content="ABC12345")]
    })
    print(f"\nUsuario: ABC12345")
    print(f"Bot: {result2['messages'][-1].content}")
    print("\n" + "="*70 + "\n")


async def test_cancellation_retry():
    """Test con retry: número inválido primero, luego válido."""
    print("\n" + "="*70)
    print("TEST 2: Cancelación con un reintento")
    print("="*70)

    graph = await create_dating_agent_graph()

    # Usuario quiere cancelar
    result1 = await graph.ainvoke({"messages": [HumanMessage(content="Cancelar cita")]})
    print(f"\nUsuario: Cancelar cita")
    print(f"Intent: {result1['intent']} (confidence: {result1['confidence']:.2f})")
    print(f"Bot: {result1['messages'][-1].content}")

    # Usuario proporciona número inválido (menos de 8 caracteres)
    result2 = await graph.ainvoke({
        "messages": result1['messages'] + [HumanMessage(content="123")]
    })
    print(f"\nUsuario: 123")
    print(f"Bot: {result2['messages'][-1].content}")

    # Usuario proporciona número válido
    result3 = await graph.ainvoke({
        "messages": result2['messages'] + [HumanMessage(content="XYZ98765")]
    })
    print(f"\nUsuario: XYZ98765")
    print(f"Bot: {result3['messages'][-1].content}")
    print("\n" + "="*70 + "\n")


async def test_cancellation_escalation():
    """Test escalamiento: dos intentos fallidos."""
    print("\n" + "="*70)
    print("TEST 3: Escalamiento después de 2 intentos fallidos")
    print("="*70)

    graph = await create_dating_agent_graph()

    # Usuario quiere cancelar
    result1 = await graph.ainvoke({"messages": [HumanMessage(content="Necesito cancelar")]})
    print(f"\nUsuario: Necesito cancelar")
    print(f"Intent: {result1['intent']} (confidence: {result1['confidence']:.2f})")
    print(f"Bot: {result1['messages'][-1].content}")

    # Primer intento fallido
    result2 = await graph.ainvoke({
        "messages": result1['messages'] + [HumanMessage(content="123")]
    })
    print(f"\nUsuario: 123")
    print(f"Bot: {result2['messages'][-1].content}")

    # Segundo intento fallido -> escalamiento
    result3 = await graph.ainvoke({
        "messages": result2['messages'] + [HumanMessage(content="456")]
    })
    print(f"\nUsuario: 456")
    print(f"Bot: {result3['messages'][-1].content}")
    print("\n" + "="*70 + "\n")


async def main():
    """Ejecuta todos los tests."""
    print("\n🧪 TESTING CANCELLATION SUB-GRAPH FLOW\n")

    try:
        await test_cancellation_successful()
        await asyncio.sleep(1)

        await test_cancellation_retry()
        await asyncio.sleep(1)

        await test_cancellation_escalation()

        print("✅ Todos los tests completados exitosamente\n")

    except Exception as e:
        print(f"\n❌ Error durante los tests: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
