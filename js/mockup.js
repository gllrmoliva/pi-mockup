/* Hito — maqueta estática.
   Interacciones de demostración: modales, toggles de estado, avisos,
   menú de cuenta y arrastre de tarjetas del tablero.
   Sin lógica de negocio, sin datos, sin backend. */

(() => {
  "use strict";

  const $ = (sel, raiz = document) => raiz.querySelector(sel);
  const $$ = (sel, raiz = document) => Array.from(raiz.querySelectorAll(sel));

  /* --- Modales -------------------------------------------------------- */

  $$("[data-abrir]").forEach((boton) => {
    boton.addEventListener("click", () => {
      const dialogo = document.getElementById(boton.dataset.abrir);
      if (dialogo) dialogo.showModal();
    });
  });

  $$("[data-cerrar]").forEach((boton) => {
    boton.addEventListener("click", () => {
      const dialogo = boton.closest("dialog");
      if (dialogo) dialogo.close();
    });
  });

  $$("dialog.modal").forEach((dialogo) => {
    dialogo.addEventListener("click", (evento) => {
      if (evento.target === dialogo) dialogo.close();
    });
  });

  /* --- Toggles de demostración ---------------------------------------- */
  /* Alternan la visibilidad de un bloque (y opcionalmente ocultan otro)
     para mostrar criterios de aceptación: errores, estados vacíos.    */

  $$("[data-demo]").forEach((boton) => {
    const mostrar = document.getElementById(boton.dataset.demo);
    const ocultar = boton.dataset.oculta ? document.getElementById(boton.dataset.oculta) : null;
    if (!mostrar) return;

    const etiquetaInicial = boton.textContent;
    const etiquetaFinal = boton.dataset.alternar || "Ocultar la demostración";
    let activo = false;

    boton.setAttribute("aria-pressed", "false");
    boton.setAttribute("aria-controls", boton.dataset.demo);

    boton.addEventListener("click", () => {
      activo = !activo;
      mostrar.classList.toggle("oculto", !activo);
      if (ocultar) ocultar.classList.toggle("oculto", activo);
      boton.setAttribute("aria-pressed", String(activo));
      boton.textContent = activo ? etiquetaFinal : etiquetaInicial;
    });
  });

  /* --- Menú de cuenta ------------------------------------------------- */

  $$(".cuenta").forEach((cuenta) => {
    $$(".cuenta-opcion", cuenta).forEach((opcion) => {
      opcion.addEventListener("click", () => { cuenta.open = false; });
    });
  });

  document.addEventListener("click", (evento) => {
    $$(".cuenta[open], .maqueta-rol[open]").forEach((abierto) => {
      if (!abierto.contains(evento.target)) abierto.open = false;
    });
  });

  document.addEventListener("keydown", (evento) => {
    if (evento.key !== "Escape") return;
    $$(".cuenta[open], .maqueta-rol[open]").forEach((abierto) => {
      abierto.open = false;
      const resumen = $("summary", abierto);
      if (resumen) resumen.focus();
    });
  });

  /* --- Selector de tipo de usuario de la maqueta ---------------------- */
  /* Filtra la barra de demo para mostrar solo las vistas de Profesor o
     Estudiante. La elección se recuerda entre páginas (localStorage); sin
     elección se muestra Profesor. Es andamiaje del mockup, no del producto. */

  const maqueta = $(".maqueta");
  const CLAVE_ROL = "hito-rol-maqueta";
  const ROLES = ["profesor", "estudiante"];

  const guardarRol = (rol) => {
    try {
      window.localStorage.setItem(CLAVE_ROL, rol);
    } catch (error) { /* almacenamiento no disponible */ }
  };

  const leerRol = () => {
    const desdeUrl = new URLSearchParams(window.location.search).get("rol");
    if (ROLES.includes(desdeUrl)) {
      guardarRol(desdeUrl);
      return desdeUrl;
    }
    try {
      const guardado = window.localStorage.getItem(CLAVE_ROL);
      if (ROLES.includes(guardado)) return guardado;
    } catch (error) { /* almacenamiento no disponible */ }
    return "profesor";
  };

  if (maqueta) {
    const detalle = $(".maqueta-rol", maqueta);
    const etiqueta = $("[data-rol-actual]", maqueta);
    const opciones = $$("[data-rol-opcion]", maqueta);
    const nombres = { profesor: "Profesor", estudiante: "Estudiante" };
    const PERSONAS = {
      profesor: { iniciales: "CS", nombre: "Camila Soto", rol: "Profesora guía" },
      estudiante: { iniciales: "JC", nombre: "Javiera Contreras", rol: "Memorista" }
    };

    /* Las vistas compartidas (proyectos, detalle, tablero) se adaptan al
       tipo elegido: ocultan las acciones de profesor, cambian la cuenta y
       apuntan al entregable que corresponde. Sin elección se ve Profesor. */
    const aplicarRol = (rol) => {
      maqueta.dataset.rolActivo = rol;
      if (etiqueta) etiqueta.textContent = nombres[rol] || nombres.profesor;
      opciones.forEach((opcion) => {
        const propia = (opcion.dataset.rolOpcion || "") === rol;
        opcion.setAttribute("aria-pressed", String(propia));
      });

      const efectivo = rol === "estudiante" ? "estudiante" : "profesor";

      $$("[data-solo-profesor]").forEach((elemento) => {
        elemento.classList.toggle("oculto", efectivo === "estudiante");
      });
      $$("[data-solo-estudiante]").forEach((elemento) => {
        elemento.classList.toggle("oculto", efectivo !== "estudiante");
      });

      const rutaEntregable = efectivo === "estudiante" ? "entregable-colaborador.html" : "entregable.html";
      $$("[data-entregable]").forEach((enlace) => {
        enlace.setAttribute("href", rutaEntregable);
      });

      $$("[data-texto-profesor]").forEach((elemento) => {
        const texto = efectivo === "estudiante"
          ? elemento.dataset.textoEstudiante
          : elemento.dataset.textoProfesor;
        if (texto) elemento.textContent = texto;
      });

      const persona = PERSONAS[efectivo];
      $$('[data-cuenta="compartida"]').forEach((cuenta) => {
        const avatar = $(".avatar", cuenta);
        const nombre = $(".cuenta-nombre", cuenta);
        const rolCuenta = $(".cuenta-rol", cuenta);
        if (avatar) avatar.textContent = persona.iniciales;
        if (nombre) nombre.textContent = persona.nombre;
        if (rolCuenta) rolCuenta.textContent = persona.rol;
      });
    };

    aplicarRol(leerRol());

    opciones.forEach((opcion) => {
      opcion.addEventListener("click", () => {
        const rol = opcion.dataset.rolOpcion;
        guardarRol(rol);
        aplicarRol(rol);
        if (detalle) detalle.open = false;
      });
    });
  }

  /* --- Avisos (toasts) ------------------------------------------------ */

  const zona = $(".toast-zona");

  const avisar = (texto) => {
    if (!zona) return;
    const aviso = document.createElement("div");
    aviso.className = "toast";
    aviso.setAttribute("role", "status");
    aviso.textContent = texto;
    zona.appendChild(aviso);
    requestAnimationFrame(() => aviso.classList.add("visible"));
    window.setTimeout(() => {
      aviso.classList.remove("visible");
      window.setTimeout(() => aviso.remove(), 250);
    }, 4200);
  };

  $$("[data-aviso]").forEach((elemento) => {
    elemento.addEventListener("click", (evento) => {
      if (elemento.getAttribute("href") === "#") evento.preventDefault();
      avisar(elemento.dataset.aviso);
    });
  });

  /* --- Tablero: arrastrar tarjetas entre columnas (demo, sin persistencia) --
     El gesto es solo visual: no cambia estados, no guarda nada y al recargar
     el tablero vuelve a su forma original. La vista avisa que es una demo
     de una pantalla que en la aplicación real es de solo lectura (RB-16). */

  const tablero = $(".tablero");

  if (tablero) {
    const columnas = $$(".columna", tablero);
    const aviso = $("#tablero-aviso");
    const menosMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)");
    const MARGEN = 8;             // margen inferior de .tarjeta
    const PULSACION_LARGA = 300;  // ms de pulsación que inicia el arrastre táctil
    let arrastre = null;
    let candidato = null;

    const limitar = (valor, minimo, maximo) => Math.max(minimo, Math.min(maximo, valor));

    const anunciar = (texto) => {
      if (aviso) aviso.textContent = texto;
    };

    const tarjetasDe = (raiz) => $$(".tarjeta", raiz);

    const detenerAnimaciones = (elemento) => {
      elemento.getAnimations().forEach((animacion) => animacion.cancel());
    };

    const actualizarCuentas = () => {
      columnas.forEach((columna) => {
        const cuenta = $(".columna-cuenta", columna);
        if (cuenta) cuenta.textContent = String(tarjetasDe(columna).length);
      });
    };

    const capturarPosiciones = () => {
      const mapa = new Map();
      tarjetasDe(tablero).forEach((tarjeta) => mapa.set(tarjeta, tarjeta.getBoundingClientRect()));
      return mapa;
    };

    /* Anima cada tarjeta desde su posición capturada hasta la actual. La que
       se suelta entra con inclinación y rebote; el resto se desliza. */
    const animar = (mapa, soltada, rotacion) => {
      if (menosMovimiento.matches) return;

      mapa.forEach((rect, elemento) => {
        if (!elemento.isConnected) return;
        const aqui = elemento.getBoundingClientRect();
        const dx = rect.left - aqui.left;
        const dy = rect.top - aqui.top;
        if (Math.abs(dx) < .5 && Math.abs(dy) < .5) return;

        if (elemento === soltada) {
          elemento.animate([
            { transform: `translate(${dx}px, ${dy}px) rotate(${rotacion}deg) scale(1.03)` },
            { transform: `translate(${dx * -.06}px, ${dy * -.02}px) rotate(${rotacion * -.18}deg) scale(1.01)`, offset: .6 },
            { transform: "translate(0, 0) rotate(0deg) scale(1)" }
          ], { duration: 430, easing: "cubic-bezier(.2, .8, .3, 1)" });
        } else {
          elemento.animate([
            { transform: `translate(${dx}px, ${dy}px)` },
            { transform: "translate(0, 0)" }
          ], { duration: 240, easing: "cubic-bezier(.2, .8, .3, 1)" });
        }
      });
    };

    // Columna bajo el puntero; si queda fuera del tablero, la más cercana.
    const columnaEnPunto = (x, y) => {
      const debajo = document.elementFromPoint(x, y);
      const columna = debajo && debajo.closest ? debajo.closest(".columna") : null;
      if (columna) return columna;

      let mejor = arrastre.columnaDestino;
      let distancia = Infinity;
      columnas.forEach((candidata) => {
        const rect = candidata.getBoundingClientRect();
        const separacion = x < rect.left ? rect.left - x : x > rect.right ? x - rect.right : 0;
        if (separacion < distancia) {
          distancia = separacion;
          mejor = candidata;
        }
      });
      return mejor;
    };

    // Puesto de inserción entre las tarjetas visibles de la columna.
    const indiceEnColumna = (columna, y, excluida) => {
      let indice = 0;
      tarjetasDe(columna).forEach((tarjeta) => {
        if (tarjeta === excluida) return;
        const rect = tarjeta.getBoundingClientRect();
        if (y > rect.top + rect.height / 2) indice += 1;
      });
      return indice;
    };

    // Corre las tarjetas que están bajo el hueco para dejarlo abierto.
    const acomodar = () => {
      const { tarjeta, columnaDestino, indice, paso } = arrastre;
      columnas.forEach((columna) => {
        const otras = tarjetasDe(columna).filter((otra) => otra !== tarjeta);
        otras.forEach((otra, posicion) => {
          const abreHueco = columna === columnaDestino && posicion >= indice;
          otra.style.transform = abreHueco ? `translateY(${paso}px)` : "";
        });
      });
    };

    const revisarDestino = (x, y) => {
      const columnaDestino = columnaEnPunto(x, y);
      const indice = indiceEnColumna(columnaDestino, y, arrastre.tarjeta);
      if (columnaDestino !== arrastre.columnaDestino || indice !== arrastre.indice) {
        arrastre.columnaDestino = columnaDestino;
        arrastre.indice = indice;
        acomodar();
      }
    };

    const ciclo = () => {
      if (!arrastre) return;

      // Desplazamiento del tablero cerca de los bordes (pantallas angostas).
      const rect = tablero.getBoundingClientRect();
      if (tablero.scrollWidth > tablero.clientWidth) {
        if (arrastre.punteroX < rect.left + 40) tablero.scrollLeft -= 9;
        else if (arrastre.punteroX > rect.right - 40) tablero.scrollLeft += 9;
      }

      // La tarjeta persigue al puntero con retraso y se inclina al avanzar.
      arrastre.x += (arrastre.objetivoX - arrastre.x) * .3;
      arrastre.y += (arrastre.objetivoY - arrastre.y) * .3;
      arrastre.objetivoTilt *= .86;
      arrastre.tilt += (arrastre.objetivoTilt - arrastre.tilt) * .22;

      const giro = menosMovimiento.matches
        ? ""
        : ` rotate(${arrastre.tilt.toFixed(2)}deg) scale(1.03)`;
      arrastre.tarjeta.style.transform =
        `translate(${arrastre.x.toFixed(1)}px, ${arrastre.y.toFixed(1)}px)${giro}`;

      revisarDestino(arrastre.punteroX, arrastre.punteroY);
      arrastre.frame = requestAnimationFrame(ciclo);
    };

    const moverPuntero = (evento) => {
      if (!arrastre || evento.pointerId !== arrastre.pointerId) return;
      arrastre.objetivoX = evento.clientX - arrastre.inicioX;
      arrastre.objetivoY = evento.clientY - arrastre.inicioY;
      arrastre.objetivoTilt = limitar((evento.clientX - arrastre.ultimoX) * .35, -6, 6);
      arrastre.ultimoX = evento.clientX;
      arrastre.punteroX = evento.clientX;
      arrastre.punteroY = evento.clientY;
      revisarDestino(evento.clientX, evento.clientY);
    };

    // En pantallas táctiles, mientras dura el gesto se frena el desplazamiento.
    const frenarScroll = (evento) => evento.preventDefault();
    const frenarArrastreNativo = (evento) => evento.preventDefault();

    const concluir = (columnaDestino, referencia, cambio) => {
      const { tarjeta, tilt, pointerId, pointerType } = arrastre;

      cancelAnimationFrame(arrastre.frame);
      document.removeEventListener("pointermove", moverPuntero);
      document.removeEventListener("pointerup", soltar);
      document.removeEventListener("pointercancel", cancelar);
      if (tarjeta.hasPointerCapture(pointerId)) tarjeta.releasePointerCapture(pointerId);
      if (pointerType !== "mouse") document.removeEventListener("touchmove", frenarScroll);
      document.body.classList.remove("reordenando-tarjeta");

      tarjetasDe(tablero).forEach(detenerAnimaciones);
      const mapa = capturarPosiciones();

      columnaDestino.insertBefore(tarjeta, referencia);

      // Se limpian los desplazamientos sin que las transiciones animen el salto.
      tablero.classList.add("tablero--quieto");
      tarjeta.classList.remove("tarjeta--arrastrando");
      tarjeta.style.cssText = "";
      tarjetasDe(tablero).forEach((otra) => { otra.style.transform = ""; });
      void tablero.offsetWidth;
      tablero.classList.remove("tablero--quieto");

      arrastre = null;
      animar(mapa, tarjeta, tilt);

      if (cambio) {
        actualizarCuentas();
        const titulo = $(".tarjeta-titulo", tarjeta).textContent.trim();
        const nombre = $(".columna-nombre", columnaDestino).textContent.trim();
        anunciar(`Tarjeta «${titulo}» movida a la columna ${nombre}.`);
      }
    };

    const soltar = (evento) => {
      if (!arrastre) return;
      if (evento && typeof evento.pointerId === "number" && evento.pointerId !== arrastre.pointerId) return;
      if (evento && typeof evento.clientX === "number") {
        arrastre.punteroX = evento.clientX;
        arrastre.punteroY = evento.clientY;
      }
      revisarDestino(arrastre.punteroX, arrastre.punteroY);
      const { tarjeta, columnaOrigen, columnaDestino, indice, referencia } = arrastre;
      const otras = tarjetasDe(columnaDestino).filter((otra) => otra !== tarjeta);
      const nuevaReferencia = otras[indice] || null;
      const cambio = columnaDestino !== columnaOrigen || nuevaReferencia !== referencia;
      concluir(columnaDestino, nuevaReferencia, cambio);
    };

    const cancelar = (evento) => {
      if (!arrastre) return;
      if (evento && typeof evento.pointerId === "number" && evento.pointerId !== arrastre.pointerId) return;
      const referencia = arrastre.referencia && arrastre.referencia.isConnected
        ? arrastre.referencia
        : null;
      concluir(arrastre.columnaOrigen, referencia, false);
    };

    const comenzar = (evento, tarjeta) => {
      tarjetasDe(tablero).forEach(detenerAnimaciones);

      const columna = tarjeta.closest(".columna");
      const rect = tarjeta.getBoundingClientRect();

      tarjeta.classList.add("tarjeta--arrastrando");
      tarjeta.style.left = `${rect.left}px`;
      tarjeta.style.top = `${rect.top}px`;
      tarjeta.style.width = `${rect.width}px`;

      arrastre = {
        tarjeta,
        columnaOrigen: columna,
        columnaDestino: columna,
        referencia: tarjeta.nextElementSibling,
        indice: tarjetasDe(columna).indexOf(tarjeta),
        paso: tarjeta.offsetHeight + MARGEN,
        pointerId: evento.pointerId,
        pointerType: evento.pointerType,
        inicioX: evento.clientX,
        inicioY: evento.clientY,
        ultimoX: evento.clientX,
        punteroX: evento.clientX,
        punteroY: evento.clientY,
        objetivoX: 0,
        objetivoY: 0,
        x: 0,
        y: 0,
        objetivoTilt: 0,
        tilt: 0,
        frame: 0
      };

      // El hueco original queda abierto desde el primer momento, sin saltos.
      tablero.classList.add("tablero--quieto");
      acomodar();
      void tablero.offsetWidth;
      tablero.classList.remove("tablero--quieto");

      // La captura puede perderse a mitad del gesto; los eventos se escuchan
      // en el documento para que el arrastre no se quede a medias.
      tarjeta.setPointerCapture(evento.pointerId);
      document.addEventListener("pointermove", moverPuntero);
      document.addEventListener("pointerup", soltar);
      document.addEventListener("pointercancel", cancelar);
      document.body.classList.add("reordenando-tarjeta");
      if (evento.pointerType !== "mouse") {
        document.addEventListener("touchmove", frenarScroll, { passive: false });
      }
      arrastre.frame = requestAnimationFrame(ciclo);
    };

    const iniciarArrastre = (evento) => {
      if (evento.button !== 0 || arrastre || candidato) return;
      const tarjeta = evento.currentTarget;

      candidato = {
        tarjeta,
        pointerId: evento.pointerId,
        pointerType: evento.pointerType,
        inicioX: evento.clientX,
        inicioY: evento.clientY,
        temporizador: 0
      };

      const limpiar = () => {
        if (!candidato) return;
        window.clearTimeout(candidato.temporizador);
        candidato = null;
        document.removeEventListener("pointermove", vigilar);
        document.removeEventListener("pointerup", limpiar);
        document.removeEventListener("pointercancel", limpiar);
      };

      const iniciar = (x, y) => {
        const punto = {
          clientX: x,
          clientY: y,
          pointerId: candidato.pointerId,
          pointerType: candidato.pointerType
        };
        const tarjetaCandidata = candidato.tarjeta;
        limpiar();
        comenzar(punto, tarjetaCandidata);
      };

      const vigilar = (movimiento) => {
        if (!candidato || movimiento.pointerId !== candidato.pointerId) return;
        const recorrido = Math.hypot(
          movimiento.clientX - candidato.inicioX,
          movimiento.clientY - candidato.inicioY
        );
        if (candidato.pointerType === "mouse") {
          // Un clic con algo de temblor no debe convertirse en arrastre.
          if (recorrido >= 4) iniciar(movimiento.clientX, movimiento.clientY);
        } else if (recorrido > 8) {
          limpiar(); // el gesto era un desplazamiento, no un arrastre
        }
      };

      document.addEventListener("pointermove", vigilar);
      document.addEventListener("pointerup", limpiar);
      document.addEventListener("pointercancel", limpiar);

      // En pantallas táctiles el arrastre se activa con una pulsación larga.
      if (evento.pointerType !== "mouse") {
        candidato.temporizador = window.setTimeout(() => {
          if (candidato) iniciar(candidato.inicioX, candidato.inicioY);
        }, PULSACION_LARGA);
      }
    };

    tarjetasDe(tablero).forEach((tarjeta) => {
      tarjeta.addEventListener("pointerdown", iniciarArrastre);
      tarjeta.addEventListener("dragstart", frenarArrastreNativo);
    });
  }

  /* Los formularios de la maqueta no envían nada. El formulario de
     ingreso sí navega (tiene atributo action) para simular el acceso. */

  $$("form").forEach((formulario) => {
    if (!formulario.getAttribute("action")) {
      formulario.addEventListener("submit", (evento) => evento.preventDefault());
    }
  });
})();
