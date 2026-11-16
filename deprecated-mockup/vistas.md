# Mapa de vistas por tipo de usuario

Maqueta estática de **Hito**. Este documento lista las vistas de la maqueta y el linkeo real entre archivos, separado por tipo de usuario.

> **Tipo de usuario** es la clasificación de la cuenta (profesor o estudiante) y es independiente del **rol dentro de un proyecto** (gestor o colaborador), según §1.3 del SRS. En la maqueta, el profesor se representa como **Camila Soto** (profesora guía, gestora) y el estudiante como **Javiera Contreras** (memorista, colaboradora).

El menú incluye **Volver a inicio** como acceso independiente a la presentación, fuera de las vistas por tipo de usuario. El menú flotante de la esquina superior izquierda es andamiaje para revisores: el botón hamburguesa abre las vistas y el selector **Profesor** / **Estudiante**. Al elegir un tipo de usuario, la barra muestra solo las vistas que le corresponden; la elección se recuerda entre páginas. No forma parte del linkeo del producto y no se considera en los flujos de abajo.

## Resumen por tipo de usuario

| Vista | Profesor | Estudiante |
|---|:---:|:---:|
| Presentación (`index.html`) | ✓ | ✓ |
| Ingreso (`ingreso.html`) | ✓ | ✓ |
| Tus proyectos (`proyectos.html`) | ✓ | ✓ |
| Detalle del proyecto (`proyecto.html`) | ✓ | ✓ |
| Tablero (`kanban.html`) | ✓ | ✓ |
| Entregable, vista profesor (`entregable.html`) | ✓ | — |
| Entregable, vista estudiante (`entregable-colaborador.html`) | — | ✓ |
| Crear proyecto (`proyecto-crear.html`) | ✓ | — |
| Editar proyecto (`proyecto-editar.html`) | ✓ | — |

Las cuatro vistas compartidas se adaptan al tipo elegido en la barra **Maqueta**: cambian la cuenta de la cabecera, ocultan las acciones de profesor y enlazan al entregable que corresponde. El estudiante solo tiene un archivo propio: el detalle del entregable.

## 1. Vistas compartidas

| Vista | Archivo | Enlaces de salida |
|---|---|---|
| Presentación | [`index.html`](index.html) | **Iniciar demo** → [`ingreso.html`](ingreso.html). |
| Ingreso | [`ingreso.html`](ingreso.html) | **Ingresar** → [`proyectos.html`](proyectos.html) (formulario con `action`). **¿Olvidaste tu contraseña?** muestra un aviso, sin navegar. |
| Tus proyectos | [`proyectos.html`](proyectos.html) | Tarjeta completa del proyecto → [`proyecto.html`](proyecto.html). En la variante de profesor: **Revisar** → [`entregable.html`](entregable.html) y **Nuevo proyecto** → [`proyecto-crear.html`](proyecto-crear.html). Menú de cuenta: **Cerrar sesión** → [`ingreso.html`](ingreso.html). |
| Detalle del proyecto | [`proyecto.html`](proyecto.html) | **Proyectos** (barra superior) → [`proyectos.html`](proyectos.html). Pestaña **Tablero** → [`kanban.html`](kanban.html). Entregables → [`entregable.html`](entregable.html) con Profesor y → [`entregable-colaborador.html`](entregable-colaborador.html) con Estudiante. En la variante de profesor: **Editar proyecto** → [`proyecto-editar.html`](proyecto-editar.html); **Nuevo hito**, **Editar hito**, **Nuevo entregable** y **Editar entregable** abren modales en la misma página. |
| Tablero | [`kanban.html`](kanban.html) | **Proyectos** (barra superior) → [`proyectos.html`](proyectos.html). Pestaña **Estructura** → [`proyecto.html`](proyecto.html). Tarjetas con enlace → [`entregable.html`](entregable.html) con Profesor y → [`entregable-colaborador.html`](entregable-colaborador.html) con Estudiante. El arrastre es solo una demo del gesto y no navega. |

> En el producto, estas vistas son para ambos tipos de usuario, con acciones distintas según el rol. En la maqueta hay un solo archivo por vista: al elegir **Profesor** o **Estudiante** en la barra Maqueta, la página adapta la cuenta, las acciones y los enlaces al entregable correspondiente.

## 2. Vistas del profesor (gestor)

Además de las vistas compartidas, el profesor cuenta con:

| Vista | Archivo | Enlaces de salida |
|---|---|---|
| Entregable (profesor) | [`entregable.html`](entregable.html) | **Volver al proyecto** → [`proyecto.html`](proyecto.html). Proyecto en la ficha → [`proyecto.html`](proyecto.html). **Descargar**, **Registrar revisión** y **Publicar mensaje** muestran avisos. Incluye revisión e historial de versiones. |
| Crear proyecto | [`proyecto-crear.html`](proyecto-crear.html) | **Proyectos** (barra superior) y **Cancelar** → [`proyectos.html`](proyectos.html). **Crear proyecto** muestra un aviso (en la aplicación real volvería a la lista o al proyecto creado). |
| Editar proyecto | [`proyecto-editar.html`](proyecto-editar.html) | **Volver al proyecto**, **Cancelar** e **Ir a los hitos del proyecto** → [`proyecto.html`](proyecto.html). **Guardar cambios**, invitar y quitar participantes muestran avisos. |

### Flujo del profesor

```text
index.html ──Iniciar demo──▶ ingreso.html ──Ingresar──▶ proyectos.html
                              │
                              ├──Nuevo proyecto──▶ proyecto-crear.html ──Cancelar──▶ proyectos.html
                              ├──Revisar entrega──▶ entregable.html ──Volver──▶ proyecto.html
                              └──Abrir proyecto──▶ proyecto.html
                                                       │
                                                       ├──Tablero──▶ kanban.html ──Estructura──▶ proyecto.html
                                                       │                  └──Tarjeta──▶ entregable.html
                                                       ├──Entregable──▶ entregable.html ──Volver──▶ proyecto.html
                                                       └──Editar proyecto──▶ proyecto-editar.html ──Cancelar──▶ proyecto.html
```

**Cerrar sesión** (menú de cuenta, en las vistas con cabecera) → `ingreso.html`.

## 3. Vistas del estudiante (colaborador)

Además de las vistas compartidas:

| Vista | Archivo | Enlaces de salida |
|---|---|---|
| Entregable (estudiante) | [`entregable-colaborador.html`](entregable-colaborador.html) | **Volver al proyecto** → [`proyecto.html`](proyecto.html). Proyecto en la ficha → [`proyecto.html`](proyecto.html). **Descargar**, **Enviar entrega** y **Publicar mensaje** muestran avisos; **Elegir archivo** abre el selector del sistema. No muestra historial de versiones ni la evaluación del gestor (RB-17). |

Con el selector en **Estudiante**, las vistas compartidas ocultan las acciones de profesor y enlazan al entregable estudiantil, así que este flujo se puede recorrer completo desde la barra.

### Flujo del estudiante

```text
index.html ──Iniciar demo──▶ ingreso.html ──Ingresar──▶ proyectos.html
                              │
                              └──Abrir proyecto──▶ proyecto.html
                                                       │
                                                       ├──Tablero──▶ kanban.html
                                                       │                  └──Tarjeta──▶ entregable-colaborador.html
                                                       └──Entregable──▶ entregable-colaborador.html ──Volver──▶ proyecto.html
```

**Cerrar sesión** (menú de cuenta, en las vistas con cabecera) → `ingreso.html`.

**La marca Hito de la cabecera** es estática. El enlace **Proyectos** de la navegación principal permite volver a la lista.

## 4. Enlaces simulados y elementos que no son vistas

- **Feedback de acciones:** registrar revisión, publicar mensaje, enviar entrega y crear/guardar proyecto muestran una confirmación persistente junto a la acción, identificada como demostración. Configuración, recuperar contraseña, exportar plazos, descargar archivo, invitar o quitar participantes muestran un aviso cerrable, sin caducidad. No cambian de página ni guardan datos.
- **Selección de archivos:** muestra los nombres elegidos desde el equipo y aclara que no se suben archivos. El filtro del selector ofrece PDF y ZIP; no se validan ni procesan archivos.
- **Arrastre del tablero:** al soltar una tarjeta, un mensaje visible recuerda que el movimiento es visual, no cambia su estado y se restablece al recargar.
- **Modales:** nuevo hito, editar hito, nuevo entregable y editar entregable se abren dentro de `proyecto.html`.
- **Estados de demostración:** error de credenciales en `ingreso.html`; proyecto sin hitos y errores de validación en `proyecto.html`; error sin colaboradores en `proyecto-crear.html` y `proyecto-editar.html`; error de formato en `entregable-colaborador.html`; error de comentario vacío en ambas vistas de entregable.

## 5. Cómo se adapta la maqueta al tipo de usuario elegido

Al elegir **Estudiante** en la barra **Maqueta**, las vistas compartidas cambian para representar a Javiera Contreras (memorista):

1. La cuenta de la cabecera muestra a Javiera Contreras con el rol Memorista.
2. `proyectos.html` saluda a Javiera y oculta la bandeja **Esperan tu revisión** y la acción **Nuevo proyecto**.
3. `proyecto.html` oculta exportar plazos, editar proyecto, crear/editar hito y crear/editar entregable: la estructura queda en modo consulta.
4. Los enlaces a entregables de `proyecto.html` y `kanban.html` apuntan a `entregable-colaborador.html`.
5. La barra de demo muestra solo Ingreso, Proyectos, Detalle del proyecto, Tablero y Entregable (estudiante).

Limitaciones que siguen siendo de maqueta:

- No hay archivos separados por rol: las vistas compartidas son un solo HTML que se adapta por JavaScript. En la aplicación real cada usuario solo accede a sus proyectos y ve acciones según su rol en cada proyecto.
- La lista de proyectos sigue mostrando los proyectos de ejemplo del profesor; no se filtra por participación (RB-4).
- Sin elección previa, la maqueta se muestra como Profesor.

## 6. Navegación principal y estudiantes

La cabecera de las vistas del producto incluye **Proyectos** y **Estudiantes**. Son enlaces a `proyectos.html` y `estudiantes.html`; la página activa se señala con un subrayado. En móvil, la navegación ocupa una segunda fila de la cabecera. **Estudiantes** solo aparece para Profesor.

`estudiantes.html` es una vista del profesor con cinco estudiantes de ejemplo y sus proyectos, avances, plazos y alertas existentes. Presionar una tarjeta de proyecto abre `proyecto.html`. No representa estados nuevos del estudiante. La marca **Hito** es estática; la navegación se realiza mediante los enlaces de la cabecera.

En la lista de estudiantes, cada persona agrupa uno o más proyectos con su contador y datos independientes. Javiera Contreras participa en la memoria de reconocimiento de gestos y en el proyecto de humedales, junto a Tomás Vargas; ambas listas reflejan esa participación. Esta relación corresponde a RB-3.

Los grupos de estudiantes comienzan cerrados y se abren o cierran únicamente al pulsar su cabecera: clic, toque o Enter/Espacio con teclado. Pasar el cursor solo resalta la cabecera. Escape cierra el grupo y devuelve el foco al estudiante. La apertura y el cierre conservan su animación y respetan la preferencia de movimiento reducido.
