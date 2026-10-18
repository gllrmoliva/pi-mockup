# AGENTS.md

Este repositorio contiene la **maqueta visual (mockup estático)** del sistema **"Hito: gestión de memorias y tesis"** (escenario piloto: DIICC, UdeC): una web para que profesores guía sigan las memorias y tesis que supervisan (proyectos con hitos, entregables, entregas versionadas y revisiones).

## Regla dura: esto NO es la aplicación

La decisión del equipo es explícita: solo la parte visual.

- Nada de backend, base de datos, autenticación real ni lógica de negocio.
- Nada de frameworks, bundlers, npm ni dependencias externas. Solo HTML + un CSS compartido + un JS mínimo para interacciones de demo (modales, toggles, avisos).
- Los datos de ejemplo van **hardcodeados en el HTML** (proyectos, usuarios, hitos y entregables ficticios) y las vistas se conectan con enlaces entre archivos `.html`.
- No hay build, ni tests, ni servidor: no busques comandos para eso.
- Antes de "resolver" algo con código nuevo (fetch, JSON, router, API), recuerda que es una maqueta: la respuesta correcta suele ser HTML plano.

## Fuente de verdad

`vault/PI_Avance_Escrito_1.pdf` es el SRS IEEE 830 (41 págs., español) que define todo. No se puede leer como PDF directo; extraer texto con:

```
pdftotext -layout vault/PI_Avance_Escrito_1.pdf -
```

Secciones clave: §3 requisitos funcionales RF-1..18 (pantallas y criterios de aceptación), §4 RNF (accesibilidad y usabilidad), §6 reglas de negocio RB-1..19, §1.3 vocabulario del dominio, §2.4 perfiles de usuario.

`vault/` guarda el documento del proyecto: es la fuente de requisitos del equipo, no lo muevas ni lo edites.

## Convenciones de la maqueta

- Interfaz **en español** (Chile) con el vocabulario exacto de §1.3: hito, entregable, entrega, revisión, gestor, colaborador, profesor guía, memorista/tesista. No traducir ni renombrar estos términos.
- Estados de un entregable: **Pendiente, Entregado, Atrasado, Aprobado, Cambios solicitados**. "Atrasado" es calculado (fecha límite vencida sin entrega a tiempo), nunca un estado que se elige en la interfaz. No inventar estados nuevos.
- Reglas de negocio que la interfaz debe reflejar (equivocarlas es un bug de la maqueta):
  - Tablero kanban de **solo lectura**: las tarjetas cambian de columna solo cuando un colaborador entrega o un gestor registra una revisión, nunca como operación real (RB-16, RF-16). En la maqueta el arrastre existe únicamente como demo del gesto y la vista lo advierte.
  - Historial de versiones solo para el gestor; el colaborador ve solo la última entrega (RB-17, RF-12).
  - Solo el gestor evalúa (Aprobado / Cambios solicitados) y edita hitos y entregables (RB-5, RB-11, RF-14).
  - Todo proyecto exige al menos 1 gestor y 1 colaborador; la fecha límite no puede ser pasada (RB-2, RB-6).
- Estilo acordado: paleta azul #223C6A + neutros, con acentos amarillo #E69B0A y rojo #D21428; Poppins para títulos y Roboto para texto (archivos locales en `fuentes/`, sin CDN); tarjetas sobrias, colores de estado con contraste AA, HTML semántico (labels, foco visible), responsive (en móvil el kanban hace scroll horizontal).
- No incorporar logos, marcas ni referencias a instituciones reales en la interfaz: la identidad del producto es solo el nombre "Hito".

## Estructura (maqueta multipágina)

| Archivo | Vista |
|---|---|
| `index.html` | Login (RF-1) + estado de error |
| `proyectos.html` | Lista de proyectos + bloque "entregas por revisar" (RF-2) |
| `proyecto.html` | Detalle: hitos y entregables; modales crear/editar hito y entregable (RF-3, RF-6–9) |
| `kanban.html` | Tablero por estado, solo lectura (RF-16) |
| `entregable.html` | Detalle de entregable, vista **gestor**: revisar, historial de versiones, foro (RF-10–14) |
| `entregable-colaborador.html` | Misma vista como estudiante: subir entrega, sin historial ni evaluación (RB-17) |
| `proyecto-crear.html`, `proyecto-editar.html` | Crear con plantilla de hitos / editar (RF-4, RF-5, RF-15) |
| `css/estilos.css` | Sistema de diseño compartido |
| `js/mockup.js` | Solo interacciones de demo; sin lógica de negocio |
| `fuentes/` | Poppins y Roboto (SIL OFL) servidas localmente; no hay CDN ni Google Fonts |
| `vistas.md` | Mapa de vistas y linkeo por tipo de usuario (profesor / estudiante) |

`js/mockup.js` funciona por atributos en el HTML: `data-abrir` abre un diálogo, `data-cerrar` lo cierra, `data-demo` muestra un bloque de demostración (con `data-oculta` para esconder el normal y `data-alternar` para el texto del botón), y `data-aviso` muestra un toast. El selector de la barra de demo usa `data-rol` en los enlaces por tipo de usuario y `data-rol-opcion` en los botones Profesor/Estudiante; la elección se guarda en `localStorage` (`hito-rol-maqueta`). Al elegir un tipo, las vistas compartidas ocultan lo marcado con `data-solo-profesor`, cambian la cuenta con `data-cuenta="compartida"`, ajustan los enlaces `data-entregable` y alternan textos `data-texto-profesor` / `data-texto-estudiante`. Los formularios sin `action` no envían nada; el de ingreso navega a `proyectos.html` a propósito.

Además hay dos interacciones propias: el nombre de la persona en la cabecera (esquina derecha) despliega un menú con Configuración y Cerrar sesión, y en `kanban.html` se pueden arrastrar las tarjetas entre columnas como demo del gesto (sin persistencia y sin cambiar estados).

Cada página incluye una **barra de navegación de demo** (enlaces a todas las vistas y estados). El botón **Maqueta** abre un selector de tipo de usuario (**Profesor**, **Estudiante**) que filtra los enlaces de la barra y recuerda la elección entre páginas. Es andamiaje del mockup para revisores, no parte del producto: no confundirla con la navegación real de la app.

## Vista previa

Abrir `index.html` directamente en el navegador (funciona con `file://`) o levantar `python3 -m http.server` en la raíz.
