# Implementación del Sub-grafo de Reagendar

## ✅ Implementación Completada

Se ha implementado exitosamente el **sub-grafo de reagendamiento** para el nodo `reagendar` del Dating Agent.

---

## 📋 Resumen de la Implementación

### **Arquitectura: Sub-grafo Independiente**

El nodo `reagendar` ahora utiliza un sub-grafo completo con flujo multi-turno que incluye:

- ✅ Solicitud y validación de número de confirmación
- ✅ Cálculo dinámico de fecha actual
- ✅ Obtención de slots disponibles (próximas 2 semanas)
- ✅ Selección numérica de fecha y hora
- ✅ Actualización de la cita
- ✅ Confirmación final al usuario
- ✅ Sistema de reintentos y escalamiento

---

## 🏗️ Componentes Implementados

### **1. Estado del Sub-grafo (ReagendarState)**

```python
class ReagendarState(BaseModel):
    messages: Annotated[list, add_messages]  # Mensajes conversacionales
    confirmation_number: Optional[str]        # Número proporcionado
    validation_attempts: int                  # Contador validación (0-2)
    is_valid: bool                           # ¿Número válido?
    current_booking: Optional[dict]          # Cita actual del usuario
    available_slots: Optional[list]          # Lista de slots disponibles
    selected_index: Optional[int]            # Opción seleccionada (1-N)
    selected_date: Optional[str]             # Fecha seleccionada
    selected_time: Optional[str]             # Hora seleccionada
    selection_attempts: int                  # Reintentos de selección
    escalated: bool                          # ¿Escalado a humano?
```

### **2. Tools Implementadas**

#### Tool 1 y 2: Reutilizadas de Cancelar ✅
- `validate_confirmation_number`: Valida número contra BD
- `escalate_to_human`: Escala a soporte humano

#### Tool 3: `get_available_slots` ⭐ NUEVA
- **Propósito:** Obtener slots disponibles en próximas 2 semanas
- **Input:**
  - `start_date`: Fecha inicial (YYYY-MM-DD)
  - `duration_days`: Días a buscar (default 14)
- **Output:**
  ```python
  {
    "slots": [
      {"date": "2025-11-20", "time": "09:00 AM"},
      {"date": "2025-11-20", "time": "10:00 AM"},
      ...
    ],
    "total_available": 12
  }
  ```
- **Lógica MOCK actual:**
  - Genera slots desde hoy + 1 día hasta hoy + 14 días
  - Salta fines de semana (sábado/domingo)
  - Genera 3 horarios por día: 09:00 AM, 10:00 AM, 11:00 AM
  - Limita a 12 slots totales
- **Para producción:** Query a sistema de citas real

#### Tool 4: `update_appointment` ⭐ NUEVA
- **Propósito:** Actualizar fecha/hora de cita existente
- **Input:**
  - `confirmation_number`: Número de confirmación
  - `new_date`: Nueva fecha (YYYY-MM-DD)
  - `new_time`: Nueva hora ("10:00 AM")
- **Output:**
  ```python
  {
    "success": True,
    "updated_booking": {
      "confirmation_number": "ABC12345",
      "new_date": "2025-11-25",
      "new_time": "02:00 PM",
      "updated_at": "2025-11-20T00:00:24Z"
    }
  }
  ```
- **Lógica MOCK actual:** Simula actualización exitosa
- **Para producción:** UPDATE en BD real

### **3. Nodos del Sub-grafo (9 nodos)**

```
FASE 1: VALIDACIÓN (Reutiliza lógica de cancelar)
├─ 1. ask_confirmation_number_reagendar_node
├─ 2. extract_number_reagendar_node
├─ 3. validate_number_reagendar_node (Tool 1)
├─ 4. route_reagendar_validation (routing)
├─ 5. retry_validation_reagendar_node
└─ 6. escalate_reagendar_node (Tool 2)

FASE 2: DISPONIBILIDAD Y SELECCIÓN ⭐ NUEVA
├─ 7. fetch_available_slots_node (Tool 3)
├─ 8. extract_selection_node
├─ 9. route_selection_validation (routing)
└─ 10. retry_selection_node

FASE 3: CONFIRMACIÓN ⭐ NUEVA
└─ 11. confirm_reschedule_node (Tool 4)
```

---

## 🔄 Flujo Completo

### **Caso 1: Reagendar Exitoso (Flujo Ideal)**

```
Usuario: "Quiero reagendar mi cita"
    ↓
Router detecta intent="reagendar"
    ↓
ask_confirmation_number_reagendar_node
    → Bot: "Para reagendar tu cita, necesito el número de confirmación..."
    → ESPERA
    ↓
Usuario: "ABC12345"
    ↓
extract_number_reagendar_node
    → confirmation_number = "ABC12345"
    ↓
validate_number_reagendar_node
    → Tool 1: validate_confirmation_number("ABC12345")
    → is_valid = True
    → current_booking = {"date": "2025-01-15", "time": "10:00 AM"}
    ↓
route_reagendar_validation
    → is_valid == True → "fetch_slots"
    ↓
fetch_available_slots_node
    → today = datetime.now() = "2025-11-20"
    → Tool 3: get_available_slots("2025-11-20", 14)
    → available_slots = [12 slots]
    → Bot: "Aquí están las fechas disponibles:
           1. 2025-11-20 - 09:00 AM
           2. 2025-11-20 - 10:00 AM
           3. 2025-11-21 - 09:00 AM
           ...
           12. 2025-11-25 - 11:00 AM

           Por favor, selecciona el número de tu opción preferida."
    → ESPERA
    ↓
Usuario: "3"
    ↓
extract_selection_node
    → selected_index = 3
    → selected_date = "2025-11-21"
    → selected_time = "09:00 AM"
    ↓
route_selection_validation
    → selected_date != None → "confirm_reschedule"
    ↓
confirm_reschedule_node
    → Tool 4: update_appointment("ABC12345", "2025-11-21", "09:00 AM")
    → Bot: "✅ Tu cita ha sido reagendada exitosamente!

           📅 Nueva fecha: 2025-11-21
           🕐 Nueva hora: 09:00 AM
           📋 Número de confirmación: ABC12345

           Recibirás un SMS de confirmación en breve."
    → END
```

### **Caso 2: Número Inválido → Reintento → Éxito**

```
Usuario: "Reagendar"
Bot: "¿Cuál es tu número de confirmación?"
Usuario: "123"
    → is_valid = False, attempts = 1
Bot: "El número no es válido. Verifica e ingresa nuevamente."
Usuario: "XYZ98765"
    → is_valid = True, attempts = 2
[Continúa con fetch_slots...]
```

### **Caso 3: Selección Inválida → Retry**

```
[...número validado...]
Bot: "Fechas disponibles:
     1. 2025-11-20 - 09:00 AM
     2. 2025-11-21 - 10:00 AM
     3. 2025-11-22 - 11:00 AM"
Usuario: "10"  [Fuera de rango]
Bot: "Opción inválida. Selecciona entre 1 y 3.

     1. 2025-11-20 - 09:00 AM
     2. 2025-11-21 - 10:00 AM
     3. 2025-11-22 - 11:00 AM"
Usuario: "2"
[Continúa con confirmación...]
```

### **Caso 4: Escalamiento (2 intentos fallidos)**

```
Usuario: "Cambiar cita"
Bot: "¿Número de confirmación?"
Usuario: "123"
    → attempts = 1, invalid
Usuario: "456"
    → attempts = 2, invalid
Bot: "Lo siento, no pudimos validar tu número.
     Este caso será escalado
     Nuestro equipo te ayudará a reagendar tu cita."
END
```

---

## 🎯 Características Especiales

### **1. Cálculo Dinámico de Fecha**
```python
# En fetch_available_slots_node:
today = datetime.now()
start_date = today.strftime("%Y-%m-%d")
```
**✅ Siempre muestra fechas desde HOY, no hardcodeado**

### **2. Solo Fecha y Hora en Slots**
```python
# Formato simplificado (sin doctor):
slots = [
  {"date": "2025-11-20", "time": "09:00 AM"},
  {"date": "2025-11-21", "time": "10:00 AM"}
]
```

### **3. Salta Fines de Semana**
```python
if current_date.weekday() >= 5:  # Sábado o Domingo
    continue
```

### **4. Extracción Inteligente de Selección**
```python
# Acepta: "3", "opción 3", "el número 3", etc.
numbers = re.findall(r"\d+", user_message)
selected_index = int(numbers[0])
```

---

## 🧪 Testing

### **Tests de Estructura (Completados ✅)**

Ejecutar:
```bash
uv run python test_rescheduling_structure.py
```

**Resultado:**
```
✅ Todos los tests de estructura completados

Estado verificado:
  ✅ ReagendarState creado correctamente

Tools verificadas:
  ✅ get_available_slots: 12 slots generados
  ✅ update_appointment: Actualización exitosa

Nodos verificados (9 nodos):
  ✅ ask_confirmation_number
  ✅ extract_number
  ✅ validate
  ✅ retry_validation
  ✅ escalate
  ✅ fetch_slots ⭐
  ✅ extract_selection ⭐
  ✅ retry_selection ⭐
  ✅ confirm_reschedule ⭐
```

---

## 📝 Código Modificado

**Archivo:** `app/core/langgraph/dating_agent.py`

**Cambios:**
- ✅ Agregado import `datetime, timedelta`
- ✅ Creada clase `ReagendarState`
- ✅ Implementadas 2 tools nuevas: `get_available_slots`, `update_appointment`
- ✅ Implementados 9 nodos del sub-grafo (+ 2 reutilizados)
- ✅ Creada función `create_rescheduling_subgraph()`
- ✅ Modificado `reagendar_node()` para invocar el sub-grafo

**Líneas agregadas:** ~500 líneas
**Patrón:** Sub-grafo anidado (consistente con cancelar)

---

## 📊 Comparación: Cancelar vs Reagendar

| Aspecto | Cancelar | Reagendar |
|---------|----------|-----------|
| **Estado** | 5 campos | 11 campos |
| **Tools** | 2 tools | 4 tools (2 reutilizadas + 2 nuevas) |
| **Nodos** | 7 nodos | 11 nodos |
| **Fases** | 1 fase | 3 fases |
| **Turnos usuario** | 2 turnos | 3 turnos |
| **Complejidad** | Baja | Media |
| **Cálculo fechas** | No | Sí (datetime) |
| **Selección lista** | No | Sí (numérica) |
| **Validación doble** | No | Sí (número + selección) |

---

## 🚀 Uso en Producción

### **1. Integración Actual**

El sub-grafo está **completamente funcional** con implementación MOCK:

```bash
# Endpoint
POST /api/v1/dating-agent/chat

Headers:
  X-Session-ID: <session_id>
  X-Org-ID: <org_id>

Body:
{
  "messages": [
    {"role": "user", "content": "Quiero reagendar mi cita"}
  ]
}
```

### **2. Próximos Pasos para Producción**

#### **A. Conectar Tool 3 a Sistema Real**

Modificar `get_available_slots`:

```python
@tool
async def get_available_slots(start_date: str, duration_days: int = 14) -> dict:
    # TODO: Reemplazar MOCK con query real

    # Ejemplo con API/BD real:
    # async with AsyncSession(engine) as session:
    #     result = await session.execute(
    #         select(Availability)
    #         .where(Availability.date >= start_date)
    #         .where(Availability.date <= end_date)
    #         .where(Availability.is_available == True)
    #     )
    #     slots = result.scalars().all()
    #
    #     return {
    #         "slots": [
    #             {"date": slot.date, "time": slot.time}
    #             for slot in slots
    #         ],
    #         "total_available": len(slots)
    #     }

    # Por ahora: MOCK
    ...
```

#### **B. Conectar Tool 4 a BD Real**

Modificar `update_appointment`:

```python
@tool
async def update_appointment(confirmation_number: str, new_date: str, new_time: str) -> dict:
    # TODO: Implementar UPDATE real

    # Ejemplo:
    # async with AsyncSession(engine) as session:
    #     result = await session.execute(
    #         update(Appointment)
    #         .where(Appointment.confirmation_number == confirmation_number)
    #         .values(
    #             date=new_date,
    #             time=new_time,
    #             updated_at=datetime.now()
    #         )
    #     )
    #     await session.commit()
    #
    #     # Enviar SMS de confirmación
    #     await send_sms(...)

    # Por ahora: MOCK
    ...
```

#### **C. Agregar Validación de Disponibilidad**

Asegurar que el slot seleccionado aún esté disponible:

```python
# En confirm_reschedule_node:
# 1. Re-validar que el slot sigue disponible
# 2. Si no disponible, volver a mostrar opciones
# 3. Si disponible, actualizar
```

#### **D. Envío de SMS/Email**

```python
# En confirm_reschedule_node después de actualizar:
await send_confirmation_sms(
    phone_number=user.phone,
    confirmation_number=state.confirmation_number,
    new_date=state.selected_date,
    new_time=state.selected_time
)
```

---

## 🎨 Personalización

### **Cambiar Duración de Búsqueda**

```python
# De 2 semanas a 1 mes:
slots_result = await get_available_slots.ainvoke({
    "start_date": start_date,
    "duration_days": 30  # Era: 14
})
```

### **Incluir Fines de Semana**

```python
# En get_available_slots, comentar:
# if current_date.weekday() >= 5:
#     continue
```

### **Cambiar Horarios Disponibles**

```python
# En get_available_slots:
times = [
    "08:00 AM", "09:00 AM", "10:00 AM", "11:00 AM",
    "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
]
```

### **Limitar Slots Mostrados**

```python
# En get_available_slots:
if len(slots) >= 20:  # Era: 12
    break
```

---

## 📊 Métricas y Logging

Logs registrados en cada nodo:

```python
# Fase 1 - Validación:
- "ask_confirmation_number_reagendar_node_executing"
- "confirmation_number_extracted_reagendar"
- "validate_number_reagendar_node_executing"
- "validation_result_reagendar"
- "route_reagendar_validation"

# Fase 2 - Disponibilidad:
- "fetch_available_slots_node_executing"
- "fetching_available_slots"
- "available_slots_fetched"
- "available_slots_displayed"
- "selection_extracted"
- "selection_extraction_failed"
- "route_selection_validation"

# Fase 3 - Confirmación:
- "confirm_reschedule_node_executing"
- "updating_appointment"
- "appointment_updated_successfully"
- "rescheduling_confirmed"
```

**Todos los logs incluyen contexto:**
- confirmation_number
- validation_attempts
- selected_date/time
- environment

---

## ✨ Ventajas de la Implementación

1. **Reutilización de código:** Tools 1 y 2 de cancelar
2. **Cálculo dinámico:** Fechas siempre actualizadas
3. **Validación doble:** Número + selección
4. **UX simplificada:** Selección numérica (fácil para usuario)
5. **Escalamiento automático:** Cuando falla validación
6. **Logging completo:** Trazabilidad total del flujo
7. **Modular:** Fácil de mantener y extender
8. **Testeable:** Tests de estructura incluidos

---

## 🔧 Posibles Mejoras Futuras

1. **Confirmación antes de actualizar:**
   ```
   Bot: "¿Confirmas que quieres reagendar a 2025-11-21 - 09:00 AM?"
   Usuario: "Sí"
   → Actualizar
   ```

2. **Mostrar cita actual:**
   ```
   Bot: "Tu cita actual es:
        📅 Fecha: 2025-01-15
        🕐 Hora: 10:00 AM

        Fechas disponibles:..."
   ```

3. **Filtrar por doctor:**
   ```
   Bot: "¿Con qué doctor quieres reagendar? (Dr. Smith, Dr. Jones)"
   ```

4. **Agrupar por día:**
   ```
   📅 Lunes 20 de Noviembre:
     1. 09:00 AM
     2. 10:00 AM
   📅 Martes 21 de Noviembre:
     3. 09:00 AM
   ```

5. **Límite de reagendamientos:**
   Verificar cuántas veces el usuario ha reagendado esta cita.

---

**Implementación completada el:** 2025-11-20
**Versión:** 1.0.0
**Estado:** ✅ Listo para testing con API real
**Tests:** ✅ Passing (test_rescheduling_structure.py)
