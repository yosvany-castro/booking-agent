"""Script para verificar la estructura del sub-grafo de reagendar."""

import asyncio

from app.core.langgraph.dating_agent import (
    ReagendarState,
    create_rescheduling_subgraph,
    get_available_slots,
    update_appointment,
)


async def test_subgraph_structure():
    """Verifica que el sub-grafo se construye correctamente."""
    print("\n" + "="*70)
    print("TEST: Estructura del sub-grafo de reagendar")
    print("="*70)

    try:
        graph = await create_rescheduling_subgraph()

        print("\n✅ Sub-grafo creado exitosamente")
        print(f"   Tipo: {type(graph)}")

        # Verificar que tiene los nodos esperados
        nodes = graph.nodes
        print(f"\n📊 Nodos del grafo: {list(nodes.keys())}")

        expected_nodes = [
            "ask_confirmation_number",
            "extract_number",
            "validate",
            "retry_validation",
            "escalate",
            "fetch_slots",
            "extract_selection",
            "retry_selection",
            "confirm_reschedule",
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
    print("TEST: Estructura del ReagendarState")
    print("="*70)

    try:
        # Crear una instancia del estado
        state = ReagendarState(
            messages=[],
            confirmation_number="ABC12345",
            validation_attempts=1,
            is_valid=True,
            current_booking={"date": "2025-11-15", "time": "10:00 AM"},
            available_slots=[
                {"date": "2025-11-21", "time": "09:00 AM"},
                {"date": "2025-11-22", "time": "02:00 PM"},
            ],
            selected_index=1,
            selected_date="2025-11-21",
            selected_time="09:00 AM",
            selection_attempts=0,
            escalated=False
        )

        print("\n✅ ReagendarState creado exitosamente")
        print(f"   confirmation_number: {state.confirmation_number}")
        print(f"   validation_attempts: {state.validation_attempts}")
        print(f"   is_valid: {state.is_valid}")
        print(f"   current_booking: {state.current_booking}")
        print(f"   available_slots: {len(state.available_slots)} slots")
        print(f"   selected_date: {state.selected_date}")
        print(f"   selected_time: {state.selected_time}")
        print(f"   escalated: {state.escalated}")

        print("\n" + "="*70)

    except Exception as e:
        print(f"\n❌ Error al crear el estado: {e}")
        import traceback
        traceback.print_exc()


async def test_tools():
    """Verifica que las tools funcionan."""
    print("\n" + "="*70)
    print("TEST: Tools de reagendar")
    print("="*70)

    try:
        # Test Tool 3: get_available_slots
        print("\n🔧 Testing get_available_slots tool...")

        result1 = await get_available_slots.ainvoke({
            "start_date": "2025-11-19",
            "duration_days": 14
        })
        print(f"   Input: start_date='2025-11-19', duration_days=14")
        print(f"   Output: {result1['total_available']} slots disponibles")
        if result1['slots']:
            print(f"   Primer slot: {result1['slots'][0]}")
            print(f"   Último slot: {result1['slots'][-1]}")

        # Test Tool 4: update_appointment
        print("\n🔧 Testing update_appointment tool...")
        result2 = await update_appointment.ainvoke({
            "confirmation_number": "ABC12345",
            "new_date": "2025-11-25",
            "new_time": "02:00 PM"
        })
        print(f"   Input: confirmation='ABC12345', date='2025-11-25', time='02:00 PM'")
        print(f"   Success: {result2['success']}")
        print(f"   Updated booking: {result2['updated_booking']}")

        print("\n✅ Todas las tools funcionan correctamente")
        print("\n" + "="*70)

    except Exception as e:
        print(f"\n❌ Error al testear las tools: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Ejecuta todos los tests de estructura."""
    print("\n🧪 TESTING RESCHEDULING SUB-GRAPH STRUCTURE\n")

    await test_state_structure()
    await test_tools()
    await test_subgraph_structure()

    print("\n✅ Todos los tests de estructura completados\n")


if __name__ == "__main__":
    asyncio.run(main())
