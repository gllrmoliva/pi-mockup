# Plantilla de resultados de usabilidad

**RNF:** RNF-U-3  
**Protocolo:** `docs/nfr/usability-protocol.md`  
**Cuestionario:** `docs/nfr/sus-form.md`  
**Uso:** completar una planilla por sesión y luego consolidar.

## 1. Datos de la sesión

| Campo | Valor |
|---|---|
| Código de participante | P__ |
| Perfil | Profesor / Estudiante / Co-guía / Externo |
| Fecha y hora | |
| Modalidad | Presencial / Remota |
| Facilitador | |
| Observador | |
| Consentimiento firmado | Sí / No |
| Versión del prototipo | |

No registrar nombre, correo ni institución del participante.

## 2. Resultados por tarea

| Participante | Tarea | ¿Completó en el primer intento? | ¿Recibió ayuda? | Tiempo | Errores | Punto de abandono / notas |
|---|---|---|---|---|---|---|
| P__ | PA-1 | Sí / No | Sí / No | __ min __ s | | |
| P__ | PA-2 | Sí / No | Sí / No | __ min __ s | | |
| P__ | PA-5 | Sí / No | Sí / No | __ s | | |

Definiciones:

- **Primer intento:** no se reinició la tarea por un error propio del flujo.
- **Ayuda:** cualquier instrucción sobre qué control usar o dónde encontrarlo.
- **Error:** acción que impide avanzar hasta corregirla; indicar el mensaje o pantalla.
- **Punto de abandono:** último paso alcanzado si no se completó la tarea.

## 3. SUS

| Participante | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Q8 | Q9 | Q10 | Total (0–40) | SUS (0–100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P__ | | | | | | | | | | | | |

Fórmula:

- Impares: respuesta − 1.
- Pares: 5 − respuesta.
- Suma × 2,5.

## 4. Consolidado

| Métrica | Objetivo | Resultado | Estado |
|---|---:|---:|---|
| Tareas sin ayuda en el primer intento | ≥ 85 % | | |
| SUS promedio | ≥ 68 | | |
| PA-5 en menos de 30 s | 100 % | | |
| Errores bloqueantes | 0 | | |

## 5. Hallazgos

| ID | Pantalla / tarea | Hallazgo | Severidad | Participantes afectados | Acción propuesta | Responsable | Fecha |
|---|---|---|---|---|---|---|---|
| H-01 | | | Alta / Media / Baja | | | | |

## 6. Acciones derivadas

| Acción | Origen | Responsable | Fecha objetivo | Estado |
|---|---|---|---|---|
| | | | | |

## 7. Conclusión

- ¿Se cumplen los criterios de RNF-U-3? Sí / No / Parcial.
- ¿Qué cambios son obligatorios antes de E4?
- ¿Qué queda como mejora futura?

## 8. Privacidad y conservación

- Guardar los datos crudos fuera del repositorio.
- Conservar en el repositorio solo códigos, resultados agregados y hallazgos sin datos personales.
- Adjuntar el consolidado al Anexo B de `spec/main.tex`.
- Eliminar notas crudas al cierre del semestre, según el consentimiento.
