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

  document.querySelectorAll("[data-consulta]").forEach(iniciarFormulario);
  document.querySelectorAll("[data-acoes]").forEach(iniciarAcoes);
})();
