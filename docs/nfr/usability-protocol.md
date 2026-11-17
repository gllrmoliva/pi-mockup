# Protocolo de validación de usabilidad

**RNF:** RNF-U-3  
**Objetivo:** verificar que profesores guía completan las tareas clave sin capacitación y con una usabilidad aceptable (SUS ≥ 68).  
**Fecha de referencia:** 17 de noviembre de 2026  
**Responsable:** Matías Olivas (calidad)

## 1. Participantes

- 3 a 5 profesores guía del DIICC.
- Cuando sea posible, uno o dos estudiantes por profesor.
- Al menos un participante de fuera de informática, para comprobar que el sistema no depende del contexto técnico.
- Participación voluntaria y con consentimiento informado (Anexo H de `spec/main.tex`).

Criterios de inclusión:

- Supervisa o ha supervisado memorias o tesis.
- Tiene una cuenta activa en el entorno de validación.
- No participó en el diseño detallado de la interfaz.

## 2. Materiales

- Aplicación desplegada con datos sintéticos.
- Guion de tareas de este documento.
- Planilla de observación (`docs/nfr/results-template.md`).
- Cuestionario SUS (`docs/nfr/sus-form.md`).
- Hoja informativa y consentimiento (Anexo H).
- Cronómetro y equipo para notas.
- Un facilitador y un observador; una tercera persona puede dar soporte técnico sin intervenir en la tarea.

## 3. Reglas de la sesión

- Duración: 20 a 30 minutos.
- El facilitador lee la tarea y no indica dónde hacer clic.
- Se permite repetir la tarea; no se permite explicar la interfaz.
- Se considera **ayuda** cualquier instrucción sobre qué control usar, dónde encontrarlo o qué paso seguir.
- El observador registra éxito, tiempo, errores y ayudas.
- No se evalúa el desempeño del profesor; se evalúa la interfaz.
- No se usan datos reales de estudiantes ni documentos reales.

## 4. Tareas

### PA-1 — Montar un proyecto

**Objetivo:** crear un proyecto de memoria con dos hitos, un entregable y un colaborador; comprobar que el estudiante lo ve.

**Guion para el participante:**

> Cree un proyecto de memoria con el tema “Validación de usabilidad”. Agregue dos hitos: “Propuesta” y “Desarrollo”. Dentro de “Propuesta”, cree un entregable llamado “Anteproyecto” con una fecha límite futura. Agregue al estudiante indicado como colaborador.

**Criterio de éxito:**

- El proyecto aparece en el portafolio.
- Tiene dos hitos y un entregable.
- El colaborador puede ver el proyecto al iniciar sesión.

**Tiempo máximo orientativo:** 5 minutos.

### PA-2 — Ciclo de revisión

**Objetivo:** completar el ciclo entrega → revisión → nueva versión → aprobación sin perder historial.

**Guion para el participante:**

> Abra el entregable “Anteproyecto”. Como estudiante, suba una primera versión usando un enlace HTTPS. Luego, como profesor, solicite cambios con un comentario en el foro. Vuelva a entrar como estudiante y suba una segunda versión. Finalmente, como profesor, apruebe la entrega y revise el historial de versiones.

**Criterio de éxito:**

- La versión 1 queda en estado “Entregado” y luego “Cambios solicitados”.
- La versión 2 queda “Entregado” y luego “Aprobado”.
- El historial muestra ambas versiones con su revisión.
- El comentario del foro queda asociado al entregable.

**Tiempo máximo orientativo:** 8 minutos.

### PA-5 — Vista del profesor

**Objetivo:** identificar sin ayuda qué entregas esperan revisión.

**Guion para el participante:**

> Tiene tres proyectos activos. Indique qué entregas están esperando su revisión y abra una de ellas.

**Criterio de éxito:**

- El participante identifica la sección “Esperan tu revisión”.
- Reconoce el título y el estudiante de al menos una entrega pendiente.
- Abre la entrega correcta.
- Completa la tarea en menos de 30 segundos, sin ayuda.

**Tiempo máximo:** 30 segundos para identificar la entrega; el resto de la navegación no cuenta para ese límite.

## 5. Cuestionario SUS

Al finalizar las tareas, aplicar `docs/nfr/sus-form.md`.

- Escala de 1 (muy en desacuerdo) a 5 (muy de acuerdo).
- Puntaje final de 0 a 100.
- Criterio: **SUS ≥ 68**.
- No explicar el cálculo al participante antes de responder.

## 6. Criterios de aceptación

| Métrica | Objetivo | Cálculo |
|---|---|---|
| Tareas completadas sin ayuda en el primer intento | ≥ 85 % | tareas exitosas sin ayuda / total de intentos |
| SUS | ≥ 68 | promedio de los puntajes SUS |
| PA-5 | < 30 s | tiempo desde la instrucción hasta identificar la entrega |
| Errores bloqueantes | 0 | errores que impiden completar una tarea |

Si un participante no completa una tarea, se registra el punto de abandono y se le permite continuar con la siguiente. No se corrige la interfaz durante la sesión.

## 7. Análisis y reporte

1. Calcular la tasa de éxito sin ayuda por tarea y global.
2. Calcular el SUS por participante y el promedio.
3. Agrupar hallazgos por pantalla y severidad.
4. Registrar acciones correctivas con responsable y fecha.
5. Guardar resultados anonimizados en el Anexo B de `spec/main.tex`.

Los resultados crudos se guardan fuera del repositorio; en el repositorio solo se conservan códigos (P1, P2, …) y datos agregados.

## 8. Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| Profesores sin disponibilidad | Agendar desde la semana 9; sesiones remotas de 20 min; participantes de respaldo. |
| Problemas técnicos | Probar el entorno antes de cada sesión; tener datos sintéticos precargados. |
| Participante con poca alfabetización digital | Recordar que se evalúa la interfaz; ofrecer la misma ayuda neutra a todos. |
| Sesgo por conocer el diseño | Evitar que participantes del equipo participen como usuarios finales. |

## 9. Evidencia

- Planilla de resultados por sesión.
- Consentimientos informados.
- Notas de observación anonimizadas.
- Reporte agregado y acciones derivadas.
