# Implementación del Sub-grafo de Cancelación

## ✅ Implementación Completada

Se ha implementado exitosamente el **sub-grafo de cancelación** para el nodo `cancelar` del Dating Agent.

---

## 📋 Resumen de la Implementación

### **Arquitectura: Sub-grafo Independiente**

El nodo `cancelar` ahora utiliza un sub-grafo completo con flujo multi-turno que incluye:

- ✅ Solicitud de número de confirmación
- ✅ Extracción y validación del número
- ✅ Sistema de reintentos (hasta 2 intentos)
- ✅ Escalamiento automático a soporte humano
- ✅ Confirmación de cancelación exitosa

---

## 🏗️ Componentes Implementados

### **1. Estado del Sub-grafo (CancelacionState)**

```python
class CancelacionState(BaseModel):
    messages: Annotated[list, add_messages]  # Mensajes conversacionales
    confirmation_number: Optional[str]        # Número proporcionado
    validation_attempts: int                  # Contador de intentos (0-2)
    is_valid: bool                           # ¿Número válido?
    escalated: bool                          # ¿Escalado a humano?
```

### **2. Tools Implementadas**

#### Tool 1: `validate_confirmation_number`
- **Propósito:** Validar número de confirmación contra BD del negocio
- **Estado actual:** MOCK - Valida si tiene 8 caracteres alfanuméricos
- **Futuro:** Conectar a BD/API real del negocio

**Lógica actual:**
```python
✅ Válido: 8 caracteres alfanuméricos (ej: "ABC12345")
❌ Inválido: Cualquier otra cosa
```

#### Tool 2: `escalate_to_human`
- **Propósito:** Escalar caso a soporte humano
- **Estado actual:** MOCK - Registra log y retorna mensaje
- **Futuro:** Integrar con sistema de tickets/CRM

**Comportamiento:**
```python
# Registra warning log
# Genera ticket_id: "TICKET-{session_id[:8]}"
# Retorna: {"escalated": True, "ticket_id": "...", "message": "..."}
```

### **3. Nodos del Sub-grafo**

```
1. ask_confirmation_number_node
   └─> Pregunta por número de confirmación
   └─> Mensaje diferente si es reintento

2. extract_number_node
   └─> Extrae número del mensaje del usuario
   └─> Usa regex para detectar patrones alfanuméricos

3. validate_number_node
   └─> Llama a Tool 1: validate_confirmation_number
   └─> Actualiza is_valid y validation_attempts

4. route_cancellation_decision (función de routing)
   └─> Decide siguiente nodo según validación y attempts

5. retry_node
   └─> Maneja flujo de reintento
   └─> Resetea confirmation_number y vuelve a ask_number

6. confirm_cancellation_node
   └─> Confirma cancelación exitosa
   └─> Muestra mensaje: "✅ Tu cita ha sido cancelada"

7. escalate_node
   └─> Llama a Tool 2: escalate_to_human
   └─> Informa al usuario sobre escalamiento
```

---

## 🔄 Flujo Completo

### **Caso 1: Éxito en Primer Intento**

```
Usuario: "Quiero cancelar mi cita"
    ↓
Router detecta intent="cancelar"
    ↓
cancelar_node → crea sub-grafo
    ↓
ask_confirmation_number_node
    → Bot: "Para cancelar tu cita, necesito el número de confirmación..."
    → ESPERA respuesta del usuario
    ↓
Usuario: "ABC12345"
    ↓
extract_number_node
    → confirmation_number = "ABC12345"
    ↓
validate_number_node
    → Tool 1: validate_confirmation_number("ABC12345")
    → is_valid = True
    → validation_attempts = 1
    ↓
route_cancellation_decision
    → is_valid == True → "confirm_cancellation"
    ↓
confirm_cancellation_node
    → Bot: "✅ Tu cita ha sido cancelada exitosamente. Número: ABC12345"
    → END
```

### **Caso 2: Reintento Exitoso**

```
Usuario: "Cancelar cita"
    ↓
ask_confirmation_number_node
    → Bot: "¿Cuál es tu número de confirmación?"
    ↓
Usuario: "123"
    ↓
validate_number_node
    → is_valid = False
    → validation_attempts = 1
    ↓
route_cancellation_decision
    → attempts < 2 → "retry"
    ↓
retry_node
    → confirmation_number = None (reset)
    → goto "ask_confirmation_number"
    ↓
ask_confirmation_number_node
    → Bot: "El número no es válido. Por favor, verifica..."
    ↓
Usuario: "XYZ98765"
    ↓
validate_number_node
    → is_valid = True
    → validation_attempts = 2
    ↓
confirm_cancellation_node
    → Bot: "✅ Tu cita ha sido cancelada exitosamente"
```

### **Caso 3: Escalamiento (2 intentos fallidos)**

```
Usuario: "Cancelar"
    ↓
ask_confirmation_number_node
    ↓
Usuario: "123"
    → is_valid = False, attempts = 1
    ↓
retry_node
    ↓
Usuario: "456"
    → is_valid = False, attempts = 2
    ↓
route_cancellation_decision
    → attempts >= 2 → "escalate"
    ↓
escalate_node
    → Tool 2: escalate_to_human()
    → Bot: "Lo siento, no pudimos validar tu número...
           Este caso será escalado
           Nuestro equipo de soporte te contactará pronto."
    → END
```

---

## 🧪 Testing

### **Tests de Estructura (Completados ✅)**

Ejecutar:
```bash
uv run python test_cancellation_structure.py
```

**Verifica:**
- ✅ CancelacionState se crea correctamente
- ✅ Tools funcionan (validate_confirmation_number, escalate_to_human)
- ✅ Sub-grafo se compila con todos los nodos

**Resultado:**
```
✅ Todos los tests de estructura completados

Nodos verificados:
  ✅ ask_confirmation_number
  ✅ extract_number
  ✅ validate
  ✅ retry
  ✅ confirm_cancellation
  ✅ escalate
```

### **Tests End-to-End (Requieren OpenAI API)**

Para ejecutar tests completos con flujos reales:

```bash
# 1. Configurar .env.development con tu OPENAI_API_KEY
OPENAI_API_KEY=sk-...

# 2. Ejecutar tests
uv run python test_cancellation_flow.py
```

**Tests incluidos:**
1. Cancelación exitosa en primer intento
2. Cancelación con un reintento
3. Escalamiento después de 2 intentos fallidos

---

## 📝 Código Modificado

**Archivo:** `app/core/langgraph/dating_agent.py`

**Cambios:**
- ✅ Agregado import `re` y `Optional`
- ✅ Agregado import `tool` de langchain_core
- ✅ Creada clase `CancelacionState`
- ✅ Implementadas tools: `validate_confirmation_number`, `escalate_to_human`
- ✅ Implementados 7 nodos del sub-grafo
- ✅ Creada función `create_cancellation_subgraph()`
- ✅ Modificado `cancelar_node()` para invocar el sub-grafo

**Líneas agregadas:** ~250 líneas
**Patrón:** Sub-grafo anidado (Opción A)

---

## 🚀 Uso en Producción

### **1. Integración Actual**

El sub-grafo está **completamente funcional** con implementación MOCK:

```bash
# Iniciar servidor
make dev

# Endpoint
POST /api/v1/dating-agent/chat

Headers:
  X-Session-ID: <session_id>
  X-Org-ID: <org_id>

Body:
{
  "messages": [
    {"role": "user", "content": "Quiero cancelar mi cita"}
  ]
}
```

### **2. Próximos Pasos para Producción**

#### **A. Conectar Tool 1 a BD Real**

Modificar `validate_confirmation_number`:

```python
@tool
async def validate_confirmation_number(confirmation_number: str) -> dict:
    # TODO: Reemplazar MOCK con query real

    # Ejemplo con SQLModel:
    # async with AsyncSession(engine) as session:
    #     result = await session.execute(
    #         select(Appointment).where(
    #             Appointment.confirmation_number == confirmation_number
    #         )
    #     )
    #     appointment = result.scalar_one_or_none()
    #
    #     if appointment:
    #         return {
    #             "is_valid": True,
    #             "booking_details": {
    #                 "confirmation_number": appointment.confirmation_number,
    #                 "date": appointment.date,
    #                 "time": appointment.time,
    #                 "doctor": appointment.doctor
    #             }
    #         }

    # Por ahora: MOCK
    if len(confirmation_number) == 8 and confirmation_number.isalnum():
        return {"is_valid": True, "booking_details": {...}}
    else:
        return {"is_valid": False, "booking_details": None}
```

#### **B. Integrar Tool 2 con Sistema de Tickets**

Modificar `escalate_to_human`:

```python
@tool
async def escalate_to_human(...) -> dict:
    # TODO: Integrar con CRM/Sistema de Tickets

    # Ejemplo con API externa:
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(
    #         "https://api.ticket-system.com/create",
    #         json={
    #             "user_id": user_id,
    #             "session_id": session_id,
    #             "issue": "invalid_confirmation_number",
    #             "details": confirmation_number
    #         }
    #     )
    #     ticket_data = response.json()

    # Por ahora: MOCK
    logger.warning("case_escalated_to_human", ...)
    return {"escalated": True, "ticket_id": "TICKET-..."}
```

#### **C. Actualizar confirm_cancellation_node**

Agregar lógica para cancelar la cita en BD:

```python
async def confirm_cancellation_node(state: CancelacionState) -> Command:
    # TODO: Cancelar cita en BD

    # async with AsyncSession(engine) as session:
    #     await session.execute(
    #         update(Appointment)
    #         .where(Appointment.confirmation_number == state.confirmation_number)
    #         .values(status="cancelled", cancelled_at=datetime.now())
    #     )
    #     await session.commit()

    message_content = f"✅ Tu cita ha sido cancelada exitosamente."
    ...
```

#### **D. Pasar Contexto de Usuario**

Modificar `escalate_node` para recibir user_id y session_id del contexto:

```python
async def cancelar_node(state: DatingAgentState) -> Command:
    # En el futuro, pasar contexto al sub-grafo
    subgraph = await create_cancellation_subgraph()

    # Agregar user_id y session_id al estado inicial
    result = await subgraph.ainvoke({
        "messages": state.messages,
        "user_id": "...",  # Obtener del contexto
        "session_id": "..."  # Obtener del contexto
    })
    ...
```

---

## 📊 Métricas y Observabilidad

El sistema ya incluye logging estructurado completo:

```python
# Logs registrados:
- "ask_confirmation_number_node_executing"
- "confirmation_number_extracted"
- "validating_confirmation_number"
- "confirmation_number_valid" / "confirmation_number_invalid"
- "validation_result"
- "route_cancellation_decision"
- "routing_to_confirm_cancellation" / "routing_to_retry" / "routing_to_escalate"
- "retry_node_executing"
- "cancellation_confirmed"
- "case_escalated_to_human"
```

**Todos los logs incluyen:**
- `confirmation_number`
- `validation_attempts`
- `is_valid`
- `environment`

---

## 🎯 Características Implementadas

✅ **Flujo multi-turno:** El bot pregunta y espera respuesta del usuario
✅ **Extracción inteligente:** Usa regex para encontrar números en el texto
✅ **Validación robusta:** Tool dedicada con lógica extensible
✅ **Sistema de reintentos:** Hasta 2 intentos antes de escalar
✅ **Escalamiento automático:** Tool para notificar a soporte humano
✅ **Logging completo:** Trazabilidad de todo el flujo
✅ **Sub-grafo modular:** Fácil de mantener y extender
✅ **Tests incluidos:** Verificación de estructura y componentes

---

## 🔧 Personalización

### **Cambiar número de intentos permitidos**

En `route_cancellation_decision`:

```python
# Cambiar de 2 a 3 intentos:
if state.validation_attempts < 3:  # Era: < 2
    return "retry"
```

### **Cambiar formato del número de confirmación**

En `validate_confirmation_number`:

```python
# Ejemplo: Solo números de 6 dígitos
if confirmation_number and len(confirmation_number) == 6 and confirmation_number.isdigit():
    return {"is_valid": True, ...}
```

### **Agregar confirmación antes de cancelar**

Agregar un nodo adicional `confirm_action_node` antes de `confirm_cancellation_node`.

---

## 📞 Soporte

Para preguntas o problemas:
1. Revisar logs en `app/core/logging.py`
2. Ejecutar tests de estructura: `uv run python test_cancellation_structure.py`
3. Verificar estado del grafo en LangGraph Studio (si está configurado)

---

**Implementación completada el:** 2025-11-19
**Versión:** 1.0.0
**Estado:** ✅ Listo para testing con API real
