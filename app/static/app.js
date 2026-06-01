const form = document.getElementById("form");
const papelSel = document.getElementById("papel");
const tipoInput = document.getElementById("tipo");
const mesmaPessoa = document.getElementById("mesmaPessoa");
const checklistDiv = document.getElementById("checklist");

function tipoAtual() {
  return papelSel.value === "Franquia" ? "PJ" : "PF";
}

// Monta as opções de papel: se rep. legal e operador são a mesma pessoa, 2 opções; senão, 3.
function popularPapeis() {
  const atual = papelSel.value;
  const ops = mesmaPessoa.checked
    ? [["Franquia", "Franquia (CNPJ)"], ["Representante legal e Operador", "Representante legal e Operador (CPF)"]]
    : [["Franquia", "Franquia (CNPJ)"], ["Representante legal", "Representante legal (CPF)"], ["Operador", "Operador (CPF)"]];
  papelSel.innerHTML = ops.map(([v, t]) => `<option value="${v}">${t}</option>`).join("");
  if (ops.some((o) => o[0] === atual)) papelSel.value = atual;
}
const estadoTag = document.getElementById("estado");
const pastaP = document.getElementById("pasta");
const outroBox = document.getElementById("outroBox");
const acoes = document.getElementById("acoes");
const btnConcluir = document.getElementById("concluir");
const btnAbrirPasta = document.getElementById("abrirPasta");
const btnParecer = document.getElementById("parecer");
const parecerBox = document.getElementById("parecerBox");
const cnpjBox = document.getElementById("cnpjBox");
const docFile = document.getElementById("docFile");
const btnLer = document.getElementById("btnLer");
const lerStatus = document.getElementById("lerStatus");
const docLabel = document.getElementById("docLabel");

// Alterna o rótulo do upload e os campos só de PF conforme o tipo escolhido
function ajustarTipo() {
  const pf = tipoAtual() === "PF";
  if (tipoInput) tipoInput.value = tipoAtual();
  if (docLabel) docLabel.textContent = pf ? "documento de identidade (RG/CNH)" : "Cartão CNPJ";
  // usa style.display (vence o display:flex do .linha; o atributo hidden não venceria)
  document.querySelectorAll(".pfonly").forEach((el) => (el.style.display = pf ? "" : "none"));
  // placeholders: no PJ os dados vêm do documento; no PF você digita cidade/UF/nome
  if (form.municipio) form.municipio.placeholder = pf ? "digite a cidade" : "(vem do documento)";
  if (form.uf) form.uf.placeholder = pf ? "UF" : "(doc)";
  if (form.nome) form.nome.placeholder = pf ? "(complete se não vier)" : "(vem do documento)";
}

// Lê os documentos anexados (qualquer combinação — Cartão CNPJ + RG + …) e preenche os campos.
// O backend extrai PJ e PF de cada arquivo, mescla os resultados, e devolve tudo num único dict.
async function lerDocumento() {
  const arquivos = docFile.files;
  if (!arquivos || !arquivos.length) {
    lerStatus.textContent = "Anexe pelo menos um arquivo (imagem ou PDF) primeiro.";
    return;
  }
  const n = arquivos.length;
  lerStatus.textContent = `Lendo ${n} arquivo${n > 1 ? "s" : ""} e conferindo CPF/CNPJ (várias leituras)… pode levar uns ${15 * n} segundos.`;
  const fd = new FormData();
  fd.append("tipo", "auto");                       // detecção automática
  for (const f of arquivos) fd.append("arquivos", f);
  let d;
  try {
    const r = await fetch("/ler-documento", { method: "POST", body: fd });
    d = await r.json();
  } catch (e) {
    lerStatus.textContent = "Falha ao enviar os documentos.";
    return;
  }
  const set = (campo, v) => { if (form[campo] && v) form[campo].value = v; };
  // Preenche o documento principal conforme o Papel escolhido — PJ usa documento_pj, PF usa documento_pf.
  // Se não vier o do papel atual, cai no que veio (compatibilidade) ou no outro.
  const pj = tipoAtual() === "PJ";
  set("documento", (pj ? d.documento_pj : d.documento_pf) || d.documento || (pj ? d.documento_pf : d.documento_pj));
  set("nome",      (pj ? d.nome_pj      : d.nome_pf)      || d.nome      || (pj ? d.nome_pf      : d.nome_pj));
  set("uf", d.uf);
  set("municipio", d.municipio);
  set("endereco", d.endereco);
  set("rg", d.rg);
  set("nome_mae", d.nome_mae);
  set("data_nascimento", d.data_nascimento);
  set("orgao_expedidor", d.orgao_expedidor);
  set("nome_pai", d.nome_pai);

  const achados = [];
  if (d.documento_pj) achados.push("CNPJ");
  if (d.nome_pj) achados.push("razão social");
  if (d.endereco) achados.push("endereço");
  if (d.documento_pf) achados.push("CPF");
  if (d.nome_pf) achados.push("nome");
  if (d.rg) achados.push("RG");
  if (d.nome_mae) achados.push("mãe");
  if (d.data_nascimento) achados.push("nascimento");

  let msg;
  if (d.ok && achados.length) {
    msg = `✅ Li ${n} arquivo${n > 1 ? "s" : ""}. Encontrei: ${achados.join(", ")}. Confira e complete o que faltar.`;
  } else {
    msg = "⚠️ " + (d.erro || "Não consegui ler nada.") + " Preencha os campos à mão.";
  }
  if (!pj && !d.documento_pf && !d.documento) msg += " ⚠️ Não li o CPF com segurança — digite à mão.";
  if (pj && !d.documento_pj && !d.documento) msg += " ⚠️ Não li o CNPJ — digite à mão.";
  lerStatus.textContent = msg;
  carregarChecklist();
  buscarMunicipal();
}

if (btnLer) btnLer.addEventListener("click", lerDocumento);
if (docFile) docFile.addEventListener("change", lerDocumento);
const btnOutro = document.getElementById("btnOutro");
const outroNome = document.getElementById("outroNome");
const outroFile = document.getElementById("outroFile");
const processoBox = document.getElementById("processoBox");
const processoFile = document.getElementById("processoFile");
const btnProcesso = document.getElementById("btnProcesso");
const processosDiv = document.getElementById("processos");

const META = {
  sucesso: ["✅", "Emitida (auto)"],
  enviado: ["✅", "Enviado"],
  manual: ["📤", "Envio manual"],
  aberta: ["📂", "Aberta — conclua no site"],
  pendente: ["⏳", "Pendente"],
  aguardando: ["•", "Aguardando"],
  executando: ["🔄", "Abrindo…"],
  local: ["📍", "Preencha a UF/cidade"],
  erro: ["❌", "Erro"],
};

const MODO = {
  auto: ["🤖", "Automático (captura o PDF)"],
  abrir: ["🌐", "Abre no seu navegador"],
  local: ["📍", "Preencha a UF/cidade"],
  manual: ["📤", "Envio manual"],
};

let jobAtual = null;
let ultimoRender = "";
let ultimoProc = "";

// Desenha a checklist. comJob=false => prévia (só mostra tudo); comJob=true => com status e upload.
function render(itens, comJob) {
  const grupos = {};
  itens.forEach((p) => (grupos[p.grupo || "Outros"] ||= []).push(p));
  let html = "";
  for (const [grupo, its] of Object.entries(grupos)) {
    html += `<h3>${grupo}</h3><table class="cl"><tbody>`;
    for (const p of its) {
      let ic, tx;
      if (comJob) {
        [ic, tx] = META[p.status] || ["•", p.status];
      } else {
        [ic, tx] = MODO[p.modo] || MODO.manual;
      }
      let acao = "";
      if (comJob) {
        if (p.sob_demanda && p.status !== "sucesso" && p.status !== "enviado") {
          const txt = p.status === "aberta" ? "↻ Reabrir site" : "🌐 Abrir site";
          acao += `<button type="button" class="upbtn site" data-abrir-item="${p.nome}">${txt}</button> `;
        }
        if (p.arquivo) {
          acao += `<button type="button" class="upbtn abrir" data-abrir="${p.nome}">📄 Abrir PDF</button> `;
        }
        acao += `<label class="upbtn">${p.arquivo ? "Trocar PDF" : "Enviar PDF"}<input type="file" data-item="${p.nome}" accept="application/pdf,image/*" hidden></label>`;
      }
      const obs = comJob
        ? (p.mensagem ? `<br><span class="obs">${p.mensagem}</span>` : "")
        : (p.obs ? `<br><span class="obs">${p.obs}</span>` : "");
      html += `<tr><td class="st">${ic} ${tx}</td><td>${p.nome}${obs}</td><td class="ac">${acao}</td></tr>`;
    }
    html += `</tbody></table>`;
  }
  checklistDiv.innerHTML = html;
}

// Prévia da checklist completa, já na abertura da página
async function carregarChecklist() {
  if (jobAtual) return;
  const uf = form.uf.value;
  const mun = form.municipio.value;
  const r = await fetch(
    `/checklist?tipo=${tipoAtual()}&uf=${encodeURIComponent(uf)}&municipio=${encodeURIComponent(mun)}`
  );
  render(await r.json(), false);
}
papelSel.addEventListener("change", () => { ajustarTipo(); carregarChecklist(); });
mesmaPessoa.addEventListener("change", () => { popularPapeis(); ajustarTipo(); carregarChecklist(); });
form.uf.addEventListener("input", carregarChecklist);
form.municipio.addEventListener("input", carregarChecklist);
popularPapeis();
ajustarTipo();
carregarChecklist();

// Acha o site da CND Municipal assim que você digita a cidade (com atraso)
const municipalBox = document.getElementById("municipalBox");
const municipalUrlInput = document.getElementById("municipal_url");
let municipalTimer = null;
function buscarMunicipal() {
  const cid = form.municipio.value.trim();
  const uf = form.uf.value.trim();
  if (municipalUrlInput) municipalUrlInput.value = "";
  clearTimeout(municipalTimer);
  if (!cid) { if (municipalBox) municipalBox.innerHTML = ""; return; }
  if (municipalBox) municipalBox.innerHTML = `🔎 Procurando o site da CND Municipal de ${cid}…`;
  municipalTimer = setTimeout(async () => {
    try {
      const r = await fetch(`/buscar-municipal?cidade=${encodeURIComponent(cid)}&uf=${encodeURIComponent(uf)}`);
      const d = await r.json();
      if (d.url) {
        if (municipalUrlInput) municipalUrlInput.value = d.url;
        municipalBox.innerHTML = `🏛️ CND Municipal de ${cid}: <a href="${d.url}" target="_blank" rel="noopener">abrir site oficial</a> — confira se é a página de emissão e baixe o PDF.`;
      } else {
        municipalBox.innerHTML = `🏛️ CND Municipal de ${cid}: não achei o link exato — <a href="${d.google}" target="_blank" rel="noopener">abrir busca do Google pronta</a> e clicar no site da prefeitura.`;
      }
    } catch (e) {
      if (municipalBox) municipalBox.innerHTML = "";
    }
  }, 900);
}
form.municipio.addEventListener("input", buscarMunicipal);

const btnIniciar = form.querySelector('button[type="submit"]');

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const doc = (form.documento.value || "").trim();
  if (!doc) {
    lerStatus.textContent = "⚠️ Preencha o CNPJ/CPF (anexe o documento acima, ou digite à mão no campo).";
    form.documento.focus();
    return;
  }
  btnIniciar.disabled = true;
  btnIniciar.textContent = "Iniciando…";
  try {
    const resp = await fetch("/emitir", { method: "POST", body: new FormData(form) });
    if (!resp.ok) {
      const txt = await resp.text();
      lerStatus.textContent = `⚠️ Erro ao iniciar (${resp.status}): ${txt.slice(0, 200)}`;
      btnIniciar.disabled = false;
      btnIniciar.textContent = "Iniciar DD";
      return;
    }
    const { job_id } = await resp.json();
    jobAtual = job_id;
    outroBox.hidden = false;
    processoBox.hidden = false;
    acoes.hidden = false;
    ultimoRender = "";
    btnIniciar.textContent = "DD em andamento ✓";
    acompanhar();
  } catch (err) {
    lerStatus.textContent = `⚠️ Não consegui iniciar a DD: ${err.message}. O servidor está ligado?`;
    btnIniciar.disabled = false;
    btnIniciar.textContent = "Iniciar DD";
  }
});

async function enviar(item, file) {
  const fd = new FormData();
  fd.append("item", item);
  fd.append("arquivo", file);
  await fetch("/upload/" + jobAtual, { method: "POST", body: fd });
  atualizar();
}

checklistDiv.addEventListener("change", (e) => {
  const inp = e.target;
  if (inp.matches('input[type="file"]') && inp.files[0]) enviar(inp.dataset.item, inp.files[0]);
});

checklistDiv.addEventListener("click", (e) => {
  // Abrir o PDF já capturado
  const pdf = e.target.closest("[data-abrir]");
  if (pdf && jobAtual) {
    const fd = new FormData();
    fd.append("nome", pdf.dataset.abrir);
    fetch("/abrir-arquivo/" + jobAtual, { method: "POST", body: fd });
    return;
  }
  // Abrir o SITE de uma certidão (um de cada vez)
  const site = e.target.closest("[data-abrir-item]");
  if (site && jobAtual) {
    site.disabled = true;
    site.textContent = "abrindo…";
    const fd = new FormData();
    fd.append("nome", site.dataset.abrirItem);
    fetch("/abrir-item/" + jobAtual, { method: "POST", body: fd }).then(() => {
      ultimoRender = "";
      atualizar();
    });
  }
});

btnOutro.addEventListener("click", () => {
  if (outroNome.value && outroFile.files[0]) {
    enviar(outroNome.value, outroFile.files[0]);
    outroNome.value = "";
    outroFile.value = "";
  }
});

btnProcesso.addEventListener("click", async () => {
  if (!processoFile.files[0]) return;
  btnProcesso.disabled = true;
  btnProcesso.textContent = "Lendo…";
  const fd = new FormData();
  fd.append("arquivo", processoFile.files[0]);
  await fetch("/ler-processo/" + jobAtual, { method: "POST", body: fd });
  processoFile.value = "";
  btnProcesso.disabled = false;
  btnProcesso.textContent = "Ler processo";
  atualizar();
});

function renderProcessos(lista) {
  if (!lista || !lista.length) {
    processosDiv.innerHTML = "";
    return;
  }
  const linha = (rot, val) => (val ? `<br><span class="obs">${rot}:</span> ${val}` : "");
  processosDiv.innerHTML = lista
    .map((p) => {
      const partes = (p.partes || []).map((x) => `${x.nome}${x.doc ? " (" + x.doc + ")" : ""}`).join(" · ") || "—";
      const riscos = (p.riscos || []).length ? p.riscos.join(", ") : "nenhum risco óbvio";
      const semTexto = p.tem_texto ? "" : '<br><span class="obs">⚠️ PDF sem texto (imagem) — leitura limitada.</span>';
      const sent = p.sentenca ? `<br><span class="obs">Sentença:</span> <b>${p.sentenca.resultado}</b> — ${p.sentenca.trecho}` : "";
      const ult = p.ultimo_andamento ? `${p.ultimo_andamento.data} — ${p.ultimo_andamento.descricao}` : "";
      const andamentos = (p.andamentos || []).slice(-10).reverse().map((a) => `<li>${a.data} — ${a.descricao}</li>`).join("");
      const detalhes = p.fatos || andamentos
        ? `<details><summary>Ver fatos e andamentos</summary>${p.fatos ? `<p class="obs"><b>Fatos:</b> ${p.fatos}</p>` : ""}${andamentos ? `<b>Andamentos (mais recentes):</b><ul>${andamentos}</ul>` : ""}</details>`
        : "";
      const resumo = p.resumo
        ? `<div style="background:#f0f6fa;border-left:3px solid #0b4f6c;padding:.5rem .7rem;margin:.5rem 0;border-radius:4px;text-align:justify"><b>📋 Resumo do processo:</b> ${p.resumo}</div>`
        : "";
      return `<div class="proc${p.criminal || p.fraude ? " alerta" : ""}">
        <b>${p.classe || "Processo"}</b> — nº ${p.numero}
        ${resumo}
        ${linha("Objeto", p.assunto)}
        ${linha("Papel na DD", p.papel_dd)}
        ${linha("Partes", partes)}
        ${linha("Valor da causa", p.valor_causa)}
        ${linha("Vara/Juízo", p.orgao)}${linha("Juiz(a)", p.juiz)}
        ${linha("Situação atual", p.situacao)}${linha("Réu preso", p.reu_preso)}
        ${linha("Riscos", "<b>" + riscos + "</b>")}${sent}
        ${linha("Último andamento", ult)}
        ${detalhes}
        <br><span class="obs">Arquivo: ${p.arquivo || "—"}</span>${semTexto}
      </div>`;
    })
    .join("");
}

btnConcluir.addEventListener("click", async () => {
  btnConcluir.disabled = true;
  btnConcluir.textContent = "Gerando relatório…";
  await fetch("/concluir/" + jobAtual, { method: "POST" });
  atualizar();
});

btnAbrirPasta.addEventListener("click", () => {
  if (jobAtual) fetch("/abrir-pasta/" + jobAtual, { method: "POST" });
});

btnParecer.addEventListener("click", async () => {
  btnParecer.disabled = true;
  btnParecer.textContent = "Gerando…";
  const r = await fetch("/parecer/" + jobAtual, { method: "POST" });
  renderParecer(await r.json());
  btnParecer.disabled = false;
  btnParecer.textContent = "⚖️ Gerar parecer jurídico";
});

function renderParecer(d) {
  parecerBox.innerHTML = `<iframe id="pframe" style="width:100%;height:640px;border:1px solid #d3dde3;border-radius:8px;background:#fff"></iframe>
    <p class="obs">📄 Salvo como <b>Parecer_Juridico_DD.docx</b> (Word <b>editável</b>) na pasta da franquia — abra pelo botão "Abrir pasta dos PDFs". Revise e ajuste antes de enviar ao setor de Franquias.</p>`;
  const f = document.getElementById("pframe");
  if (f) f.srcdoc = d.html || "";
}

function renderCnpj(d) {
  if (!d || !d.razao_social) {
    cnpjBox.innerHTML = "";
    return;
  }
  const irregular = d.situacao && d.situacao !== "ATIVA";
  const socios = (d.socios || []).join(", ") || "—";
  cnpjBox.innerHTML = `<div class="cnpj${irregular ? " alerta" : ""}">
    <b>${d.razao_social}</b>${d.nome_fantasia ? " (" + d.nome_fantasia + ")" : ""}<br>
    <span class="obs">Situação:</span> <b style="color:${irregular ? "#c0392b" : "#1a7d3c"}">${d.situacao || "—"}</b>
    · <span class="obs">CNAE:</span> ${d.cnae_codigo || "—"} ${d.cnae_descricao || ""}<br>
    <span class="obs">Sócios:</span> ${socios}
  </div>`;
}

async function atualizar() {
  if (!jobAtual) return;
  const r = await fetch("/status/" + jobAtual);
  if (!r.ok) return;
  const job = await r.json();
  estadoTag.textContent = job.estado.replace(/_/g, " ");
  pastaP.textContent = "Pasta: " + job.pasta;
  btnConcluir.hidden = job.estado !== "aguardando_voce";
  const assinatura = JSON.stringify(job.passos);
  if (assinatura !== ultimoRender) {
    render(job.passos, true);
    ultimoRender = assinatura;
  }
  const sigProc = JSON.stringify(job.processos);
  if (sigProc !== ultimoProc) {   // só re-desenha quando muda (senão o "Ver detalhes" fechava sozinho)
    renderProcessos(job.processos);
    ultimoProc = sigProc;
  }
  renderCnpj(job.cnpj_dados);
  return job;
}

function acompanhar() {
  const tick = async () => {
    const job = await atualizar();
    if (job && job.estado !== "concluido") setTimeout(tick, 1500);
    else if (job) estadoTag.textContent = "concluído ✓";
  };
  tick();
}
