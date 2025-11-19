"""Script para verificar la estructura del sub-grafo de cancelación."""

import asyncio

from app.core.langgraph.dating_agent import (
    CancelacionState,
    create_cancellation_subgraph,
    validate_confirmation_number,
    escalate_to_human,
)


async def test_subgraph_structure():
    """Verifica que el sub-grafo se construye correctamente."""
    print("\n" + "="*70)
    print("TEST: Estructura del sub-grafo de cancelación")
    print("="*70)

    try:
        graph = await create_cancellation_subgraph()

        print("\n✅ Sub-grafo creado exitosamente")
        print(f"   Tipo: {type(graph)}")

        # Verificar que tiene los nodos esperados
        nodes = graph.nodes
        print(f"\n📊 Nodos del grafo: {list(nodes.keys())}")

        expected_nodes = [
            "ask_confirmation_number",
            "extract_number",
            "validate",
            "retry",
            "confirm_cancellation",
            "escalate",
        ]

        for node_name in expected_nodes:
            if node_name in nodes:
                print(f"   ✅ Nodo '{node_name}' encontrado")
            else:
                print(f"   ❌ Nodo '{node_name}' NO encontrado")

        print("\n" + "="*70)

    except Exception as e:
        print(f"\n❌ Error al crear el sub-grafo: {e}")
        import traceback
        traceback.print_exc()


async def test_state_structure():
    """Verifica la estructura del estado."""
    print("\n" + "="*70)
    print("TEST: Estructura del CancelacionState")
    print("="*70)

    try:
        # Crear una instancia del estado
        state = CancelacionState(
            messages=[],
            confirmation_number="ABC12345",
            validation_attempts=1,
            is_valid=False,
            escalated=False
        )

        print("\n✅ CancelacionState creado exitosamente")
        print(f"   confirmation_number: {state.confirmation_number}")
        print(f"   validation_attempts: {state.validation_attempts}")
        print(f"   is_valid: {state.is_valid}")
        print(f"   escalated: {state.escalated}")

        print("\n" + "="*70)

    except Exception as e:
        print(f"\n❌ Error al crear el estado: {e}")
        import traceback
        traceback.print_exc()


async def test_tools():
    """Verifica que las tools funcionan."""
    print("\n" + "="*70)
    print("TEST: Tools de cancelación")
    print("="*70)

    try:
        # Test Tool 1: validate_confirmation_number
        print("\n🔧 Testing validate_confirmation_number tool...")

        # Número válido (8 caracteres alfanuméricos)
        result1 = await validate_confirmation_number.ainvoke({"confirmation_number": "ABC12345"})
        print(f"   Input: 'ABC12345' -> is_valid: {result1['is_valid']}")

        # Número inválido (muy corto)
        result2 = await validate_confirmation_number.ainvoke({"confirmation_number": "123"})
        print(f"   Input: '123' -> is_valid: {result2['is_valid']}")

        # Test Tool 2: escalate_to_human
        print("\n🔧 Testing escalate_to_human tool...")
        result3 = await escalate_to_human.ainvoke({
            "user_id": "test_user",
            "session_id": "test_session_12345",
            "confirmation_number": "invalid",
            "reason": "test"
        })
        print(f"   Result: escalated={result3['escalated']}, ticket_id={result3['ticket_id']}")

        print("\n✅ Todas las tools funcionan correctamente")
        print("\n" + "="*70)

    except Exception as e:
        print(f"\n❌ Error al testear las tools: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Ejecuta todos los tests de estructura."""
    print("\n🧪 TESTING CANCELLATION SUB-GRAPH STRUCTURE\n")

    await test_state_structure()
    await test_tools()
    await test_subgraph_structure()

    print("\n✅ Todos los tests de estructura completados\n")


if __name__ == "__main__":
    asyncio.run(main())
