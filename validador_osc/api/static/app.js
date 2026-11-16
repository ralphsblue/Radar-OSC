"use strict";

(() => {
  const TAMANHO = 14;
  const PESOS_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const PESOS_DV2 = [6, ...PESOS_DV1];
  const SEPARADORES_APOS = new Map([[2, "."], [5, "."], [8, "/"], [12, "-"]]);

  const normalizar = (texto) => texto.toUpperCase().replace(/[^0-9A-Z]/g, "");

  const formatar = (normalizado) => {
    let saida = "";
    for (let i = 0; i < normalizado.length; i += 1) {
      if (i > 0 && SEPARADORES_APOS.has(i)) {
        saida += SEPARADORES_APOS.get(i);
      }
      saida += normalizado[i];
    }
    return saida;
  };

  const digito = (valores, pesos) => {
    const resto = valores.reduce((soma, valor, i) => soma + valor * pesos[i], 0) % 11;
    return resto < 2 ? 0 : 11 - resto;
  };

  const dvEsperado = (base) => {
    const valores = Array.from(base, (c) => c.charCodeAt(0) - 48);
    const dv1 = digito(valores, PESOS_DV1);
    const dv2 = digito([...valores, dv1], PESOS_DV2);
    return `${dv1}${dv2}`;
  };

  const diagnosticar = (normalizado) => {
    if (normalizado.length === 0) {
      return "Informe o CNPJ da organização.";
    }
    if (!/^[0-9A-Z]{12}[0-9]{2}$/.test(normalizado)) {
      return "O CNPJ tem 14 caracteres: 12 letras ou números seguidos de 2 dígitos.";
    }
    if (new Set(normalizado.slice(0, 12)).size === 1) {
      return "O CNPJ não pode ser uma sequência de caracteres repetidos.";
    }
    const esperado = dvEsperado(normalizado.slice(0, 12));
    if (normalizado.slice(12) !== esperado) {
      return `Confira os números: o dígito verificador esperado é ${esperado}.`;
    }
    return "";
  };

  const aplicarMascara = (campo) => {
    const valor = campo.value;
    const cursor = campo.selectionStart ?? valor.length;
    const significativosAntes = normalizar(valor.slice(0, cursor)).length;
    const normalizado = normalizar(valor);
    if (normalizado.length > TAMANHO || /[^0-9A-Za-z.\/\-\s]/.test(valor)) {
      return;
    }
    const formatado = formatar(normalizado);
    if (formatado === valor) {
      return;
    }
    campo.value = formatado;
    let posicao = 0;
    let contados = 0;
    while (posicao < formatado.length && contados < significativosAntes) {
      if (/[0-9A-Z]/.test(formatado[posicao])) {
        contados += 1;
      }
      posicao += 1;
    }
    if (document.activeElement === campo) {
      campo.setSelectionRange(posicao, posicao);
    }
  };

  const mostrarDica = (mensagem, elemento, texto, campo) => {
    elemento.replaceChildren();
    elemento.classList.toggle("campo__mensagem--dica", texto !== "");
    campo.removeAttribute("aria-invalid");
    campo.closest(".campo")?.classList.remove("campo--erro");
    if (texto !== "") {
      mensagem.textContent = texto;
      elemento.append(mensagem);
    }
  };

  const iniciarFormulario = (formulario) => {
    const campo = formulario.querySelector("[data-cnpj]");
    const saida = formulario.querySelector("[data-cnpj-mensagem]");
    const botao = formulario.querySelector("[data-enviar]");
    const textoBotao = formulario.querySelector("[data-enviar-texto]");
    const espera = formulario.querySelector("[data-espera]");
    if (!campo || !saida || !botao || !textoBotao || !espera) {
      return;
    }
    const rotuloOriginal = textoBotao.textContent;
    const mensagem = document.createElement("span");
    let enviando = false;

    const restaurar = () => {
      enviando = false;
      botao.disabled = false;
      botao.classList.remove("botao--esperando");
      botao.removeAttribute("aria-busy");
      textoBotao.textContent = rotuloOriginal;
      espera.textContent = "";
    };

    aplicarMascara(campo);
    campo.addEventListener("input", () => aplicarMascara(campo));
    campo.addEventListener("blur", () => {
      const normalizado = normalizar(campo.value);
      if (normalizado.length > 0) {
        mostrarDica(mensagem, saida, diagnosticar(normalizado), campo);
      }
    });

    formulario.addEventListener("submit", (evento) => {
      if (enviando) {
        evento.preventDefault();
        return;
      }
      const normalizado = normalizar(campo.value);
      if (normalizado.length === 0) {
        evento.preventDefault();
        mostrarDica(mensagem, saida, diagnosticar(normalizado), campo);
        campo.focus();
        return;
      }
      enviando = true;
      botao.classList.add("botao--esperando");
      botao.setAttribute("aria-busy", "true");
      textoBotao.textContent = "Consultando…";
      espera.textContent = "Consultando as fontes públicas. Isso pode levar até 10 segundos.";
      window.setTimeout(() => {
        botao.disabled = true;
      }, 0);
    });

    window.addEventListener("pageshow", (evento) => {
      if (evento.persisted) {
        restaurar();
      }
    });
  };

  const iniciarAcoes = (acoes) => {
    const link = document.querySelector("[data-link-permanente]");
    const copiar = acoes.querySelector("[data-copiar-link]");
    const textoCopiar = acoes.querySelector("[data-copiar-texto]");
    const imprimir = acoes.querySelector("[data-imprimir]");
    acoes.hidden = false;

    imprimir?.addEventListener("click", () => window.print());

    const endereco = link ? new URL(link.getAttribute("href"), window.location.href).href : "";
    if (link) {
      link.textContent = endereco;
    }
    if (!link || !copiar || !textoCopiar || !navigator.clipboard) {
      copiar?.remove();
      return;
    }
    const rotuloOriginal = textoCopiar.textContent;
    let temporizador = 0;
    copiar.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(endereco);
        textoCopiar.textContent = "Link copiado";
      } catch {
        textoCopiar.textContent = "Não foi possível copiar";
      }
      window.clearTimeout(temporizador);
      temporizador = window.setTimeout(() => {
        textoCopiar.textContent = rotuloOriginal;
      }, 2500);
    });
  };

  const INTERVALO_POLLING_MS = 4000;
  const STATUS_LOTE_EM_ANDAMENTO = new Set(["PENDENTE", "PROCESSANDO"]);

  const assinaturaLote = (raiz) =>
    Array.from(raiz.querySelectorAll("[data-linha-item]"), (linha) =>
      `${linha.dataset.statusItem}:${linha.dataset.statusFinal}`,
    ).join("|") + `#${raiz.dataset.statusLote ?? ""}`;

  const iniciarPolling = (pagina) => {
    if (!STATUS_LOTE_EM_ANDAMENTO.has(pagina.dataset.statusLote ?? "")) {
      return;
    }
    let assinatura = assinaturaLote(pagina);
    const temporizador = window.setInterval(async () => {
      try {
        const resposta = await fetch(window.location.href, { headers: { Accept: "text/html" } });
        if (!resposta.ok) {
          return;
        }
        const documento = new DOMParser().parseFromString(await resposta.text(), "text/html");
        const nova = documento.querySelector("[data-lote-detalhe]");
        if (!nova) {
          return;
        }
        const novaAssinatura = assinaturaLote(nova);
        if (novaAssinatura === assinatura) {
          return;
        }
        assinatura = novaAssinatura;
        const filtroAtivo = pagina.querySelector('[data-filtro-chip][aria-pressed="true"]')?.dataset.filtro ?? "";
        pagina.dataset.statusLote = nova.dataset.statusLote ?? "";
        pagina.replaceChildren(...nova.childNodes);
        pagina.querySelectorAll("[data-filtros-lote]").forEach((container) => iniciarFiltrosChip(container, filtroAtivo));
        if (!STATUS_LOTE_EM_ANDAMENTO.has(pagina.dataset.statusLote)) {
          window.clearInterval(temporizador);
        }
      } catch {
        return;
      }
    }, INTERVALO_POLLING_MS);
  };

  function iniciarFiltrosChip(container, filtroInicial = "") {
    const botoes = Array.from(container.querySelectorAll("[data-filtro-chip]"));
    const raiz = container.closest("[data-lote-detalhe]") ?? document;
    const tabela = raiz.querySelector("[data-tabela-lote]");
    const semResultados = raiz.querySelector("[data-sem-resultados]");
    if (botoes.length === 0 || !tabela) {
      return;
    }
    const linhas = Array.from(tabela.querySelectorAll("[data-linha-item]"));

    const aplicarFiltro = (filtro) => {
      let visiveis = 0;
      linhas.forEach((linha) => {
        let mostrar = true;
        if (filtro.startsWith("item:")) {
          mostrar = linha.dataset.statusItem === filtro.slice(5);
        } else if (filtro.startsWith("final:")) {
          mostrar = linha.dataset.statusFinal === filtro.slice(6);
        }
        linha.hidden = !mostrar;
        if (mostrar) {
          visiveis += 1;
        }
      });
      if (semResultados) {
        semResultados.hidden = visiveis !== 0;
      }
    };

    const selecionar = (botao) => {
      botoes.forEach((outro) => outro.setAttribute("aria-pressed", String(outro === botao)));
      aplicarFiltro(botao.dataset.filtro ?? "");
    };

    botoes.forEach((botao) => {
      botao.addEventListener("click", () => selecionar(botao));
    });
    const inicial = botoes.find((botao) => botao.dataset.filtro === filtroInicial);
    if (inicial) {
      selecionar(inicial);
    }
  }

  const iniciarRecolhidas = (grupos) => {
    if (grupos.length === 0) {
      return;
    }
    const abrirAlvo = () => {
      const id = decodeURIComponent(window.location.hash.slice(1));
      const alvo = id ? document.getElementById(id) : null;
      const recolhida = alvo?.closest("[data-recolhidas]");
      if (recolhida && !recolhida.open) {
        recolhida.open = true;
        alvo.scrollIntoView();
      }
    };
    let abertasAntesDeImprimir = [];
    window.addEventListener("beforeprint", () => {
      abertasAntesDeImprimir = grupos.map((grupo) => grupo.open);
      grupos.forEach((grupo) => {
        grupo.open = true;
      });
    });
    window.addEventListener("afterprint", () => {
      grupos.forEach((grupo, i) => {
        grupo.open = abertasAntesDeImprimir[i] ?? false;
      });
    });
    window.addEventListener("hashchange", abrirAlvo);
    abrirAlvo();
  };

  const iniciarContadorLote = (campo) => {
    const contador = campo.closest(".campo")?.querySelector("[data-lote-contador]");
    if (!contador) {
      return;
    }
    const maximo = Number(campo.dataset.maximo ?? "20");
    const atualizar = () => {
      const cnpjs = campo.value.split(";").map(normalizar).filter((cnpj) => cnpj.length > 0);
      const invalidos = cnpjs.filter((cnpj) => diagnosticar(cnpj) !== "");
      contador.classList.toggle("contador--erro", cnpjs.length > maximo);
      contador.classList.toggle("contador--aviso", cnpjs.length <= maximo && invalidos.length > 0);
      if (cnpjs.length === 0) {
        contador.textContent = "";
        return;
      }
      const partes = [`${cnpjs.length} de ${maximo} CNPJs`];
      if (invalidos.length === 1) {
        partes.push(`1 com dígito verificador inválido (${formatar(invalidos[0])})`);
      } else if (invalidos.length > 1) {
        partes.push(`${invalidos.length} com dígito verificador inválido`);
      }
      if (cnpjs.length > maximo) {
        partes.push(`remova ${cnpjs.length - maximo} para enviar`);
      }
      contador.textContent = partes.join(" · ");
    };
    campo.addEventListener("input", atualizar);
    atualizar();
  };

  document.querySelectorAll("[data-lote-cnpjs]").forEach(iniciarContadorLote);
  const iniciarTema = (botao) => {
    const raiz = document.documentElement;
    const rotulo = botao.querySelector("[data-tema-rotulo]");
    const sistemaEscuro = window.matchMedia("(prefers-color-scheme: dark)");
    const efetivo = () => raiz.dataset.theme ?? (sistemaEscuro.matches ? "dark" : "light");
    const atualizar = () => {
      const texto = efetivo() === "dark" ? "Usar tema claro" : "Usar tema escuro";
      botao.title = texto;
      if (rotulo) {
        rotulo.textContent = texto;
      }
    };
    botao.addEventListener("click", () => {
      const novo = efetivo() === "dark" ? "light" : "dark";
      raiz.dataset.theme = novo;
      try {
        window.localStorage.setItem("tema", novo);
      } catch {
        return;
      } finally {
        atualizar();
      }
    });
    sistemaEscuro.addEventListener("change", atualizar);
    botao.hidden = false;
    atualizar();
  };

  document.querySelectorAll("[data-tema]").forEach(iniciarTema);
  iniciarRecolhidas(Array.from(document.querySelectorAll("[data-recolhidas]")));
  document.querySelectorAll("[data-consulta]").forEach(iniciarFormulario);
  document.querySelectorAll("[data-acoes]").forEach(iniciarAcoes);
  document.querySelectorAll("[data-lote-detalhe]").forEach(iniciarPolling);
  document.querySelectorAll("[data-filtros-lote]").forEach((container) => iniciarFiltrosChip(container));
})();
