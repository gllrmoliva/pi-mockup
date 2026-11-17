# Checklist manual WCAG 2.1 AA

**RNF:** RNF-U-1  
**Fecha:** 17 de noviembre de 2026  
**Responsable:** Matías Olivas (calidad)  
**Estado:** plantilla; completar antes de E4

La auditoría automática con axe-core cubre solo una parte de WCAG 2.1 AA. Este checklist registra lo que requiere revisión humana.

## Cómo usarlo

1. Ejecutar la aplicación con datos sintéticos.
2. Recorrer cada pantalla en escritorio y a 360 px.
3. Marcar `OK`, `Hallazgo` o `N/A` y registrar evidencia.
4. Abrir un issue o corregir antes de declarar conformidad.

## 1. Teclado y foco

| Ítem | Pantallas | Resultado | Nota |
|---|---|---|---|
| El skip link es el primer foco y lleva al contenido | Autenticadas | | |
| Todo control es operable con Tab/Shift+Tab | Todas | | |
| El foco es visible en todos los controles | Todas | | |
| Los diálogos atrapan el foco y se cierran con Escape | Hitos, entregables | | |
| Al cerrar un diálogo el foco vuelve al disparador | Hitos, entregables | | |
| No hay trampas de foco fuera de diálogos | Todas | | |

## 2. Formularios y errores

| Ítem | Pantallas | Resultado | Nota |
|---|---|---|---|
| Cada campo tiene etiqueta asociada | Login, proyecto, entregable | | |
| Los errores se anuncian con `role="alert"` o `aria-live` | Todas | | |
| Los campos inválidos usan `aria-invalid` | Proyecto, entregable | | |
| El error indica cómo corregirlo | Todas | | |
| El orden de lectura coincide con el orden visual | Todas | | |

## 3. Lectura y contraste

| Ítem | Pantallas | Resultado | Nota |
|---|---|---|---|
| Zoom 200 % sin pérdida de contenido ni scroll horizontal | Todas | | |
| Contraste de texto ≥ 4.5:1 (≥ 3:1 en texto grande) | Todas | | |
| Los estados no dependen solo del color | Estados, tablero | | |
| Las imágenes decorativas tienen `aria-hidden` o alt vacío | Todas | | |
| Los encabezados respetan una jerarquía lógica | Todas | | |

## 4. Lectores de pantalla

| Ítem | Pantallas | Resultado | Nota |
|---|---|---|---|
| El nombre del progreso se anuncia correctamente | Portafolio | | |
| Los chips de estado se leen como texto | Entregables | | |
| El foro anuncia autor, fecha y mensaje | Entregable | | |
| Los diálogos anuncian su título | Hitos, entregables | | |

## 5. Movimiento y medios

| Ítem | Pantallas | Resultado | Nota |
|---|---|---|---|
| Se respeta `prefers-reduced-motion` | Todas | | |
| No hay animaciones que impidan completar una tarea | Todas | | |
| No hay audio o video obligatorio | Todas | | |

## 6. Responsive y dispositivos

| Ítem | Pantallas | Resultado | Nota |
|---|---|---|---|
| Sin scroll horizontal a 360 px | Todas | | |
| Los botones tienen un área táctil suficiente | Todas | | |
| Los formularios se completan en móvil | Proyecto, entregable | | |
| La tabla o lista de hitos sigue siendo legible | Proyecto | | |

## Evidencia

- Reporte axe: `reports/nfr/playwright/`.
- Capturas o notas de esta checklist: agregar al Anexo B del informe.
- Resultado global: `OK` / `Hallazgos pendientes` / `No verificado`.
