const form = document.getElementById("form");
const tipoSel = document.getElementById("tipo");
const checklistDiv = document.getElementById("checklist");
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
  const pf = tipoSel.value === "PF";
  if (docLabel) docLabel.textContent = pf ? "documento de identidade (RG/CNH)" : "Cartão CNPJ";
  // usa style.display (vence o display:flex do .linha; o atributo hidden não venceria)
  document.querySelectorAll(".pfonly").forEach((el) => (el.style.display = pf ? "" : "none"));
  // placeholders: no PJ os dados vêm do documento; no PF você digita cidade/UF/nome
  if (form.municipio) form.municipio.placeholder = pf ? "digite a cidade" : "(vem do documento)";
  if (form.uf) form.uf.placeholder = pf ? "UF" : "(doc)";
  if (form.nome) form.nome.placeholder = pf ? "(complete se não vier)" : "(vem do documento)";
}

// Lê o documento anexado (Cartão CNPJ ou identidade) e preenche os campos
async function lerDocumento() {
  if (!docFile.files[0]) {
    lerStatus.textContent = "Anexe o arquivo (imagem ou PDF) primeiro.";
    return;
  }
  lerStatus.textContent = "Lendo o documento… (pode levar alguns segundos)";
  const fd = new FormData();
  fd.append("tipo", tipoSel.value);
  fd.append("arquivo", docFile.files[0]);
  let d;
  try {
    const r = await fetch("/ler-documento", { method: "POST", body: fd });
    d = await r.json();
  } catch (e) {
    lerStatus.textContent = "Falha ao enviar o documento.";
    return;
  }
  const set = (campo, v) => { if (form[campo] && v) form[campo].value = v; };
  set("documento", d.documento);
  set("nome", d.nome);
  set("uf", d.uf);
  set("municipio", d.municipio);
  set("endereco", d.endereco);
  set("rg", d.rg);
  set("nome_mae", d.nome_mae);
  set("data_nascimento", d.data_nascimento);
  lerStatus.textContent = d.ok
    ? "✅ Li o documento. Confira os campos e complete o que faltar (e o endereço)."
    : "⚠️ " + (d.erro || "Não consegui ler tudo.") + " Preencha os campos à mão.";
  carregarChecklist();
  buscarMunicipal();
}

tipoSel.addEventListener("change", ajustarTipo);
ajustarTipo();
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
    `/checklist?tipo=${tipoSel.value}&uf=${encodeURIComponent(uf)}&municipio=${encodeURIComponent(mun)}`
  );
  render(await r.json(), false);
}
tipoSel.addEventListener("change", carregarChecklist);
form.uf.addEventListener("input", carregarChecklist);
form.municipio.addEventListener("input", carregarChecklist);
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

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const resp = await fetch("/emitir", { method: "POST", body: new FormData(form) });
  const { job_id } = await resp.json();
  jobAtual = job_id;
  outroBox.hidden = false;
  processoBox.hidden = false;
  acoes.hidden = false;
  ultimoRender = "";
  acompanhar();
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
  processosDiv.innerHTML = lista
    .map((p) => {
      const partes = Object.entries(p.partes || {}).map(([k, v]) => `${k}: ${v}`).join(" · ") || "—";
      const valores = (p.valores || []).join(", ") || "—";
      const riscos = (p.riscos || []).length ? p.riscos.join(", ") : "nenhum risco óbvio detectado";
      const semTexto = p.tem_texto ? "" : '<br><span class="obs">⚠️ PDF sem texto (imagem) — leitura limitada.</span>';
      return `<div class="proc${p.criminal || p.fraude ? " alerta" : ""}">
        <b>${p.arquivo || "Processo"}</b> — nº ${p.numero}<br>
        <span class="obs">Partes:</span> ${partes}<br>
        <span class="obs">Valores:</span> ${valores}<br>
        <span class="obs">Riscos:</span> <b>${riscos}</b>${semTexto}
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
  btnParecer.textContent = "⚖️ Gerar parecer de risco";
});

function renderParecer(d) {
  const COR = { ok: "#1a7d3c", alerta: "#c0392b", revisar: "#b8860b" };
  const IC = { ok: "✅", alerta: "⚠️", revisar: "🔎" };
  const linhas = d.criterios
    .map(
      (c) =>
        `<tr><td style="color:${COR[c.status]};white-space:nowrap">${IC[c.status]} ${c.status}</td>
         <td>${c.texto}<br><span class="obs">${c.obs}</span></td></tr>`
    )
    .join("");
  const corR = d.risco.startsWith("ALTO") ? "#c0392b" : d.risco.startsWith("MÉDIO") ? "#b8860b" : "#1a7d3c";
  parecerBox.innerHTML = `<h3>⚖️ Parecer de risco — <span style="color:${corR}">${d.risco}</span></h3>
    <p><b>Conclusão:</b> ${d.conclusao || ""}</p>
    <table class="cl"><tbody>${linhas}</tbody></table>
    <p class="obs">Documento <b>parecer.html</b> salvo na pasta da franquia. Revise antes de concluir.</p>`;
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
  renderProcessos(job.processos);
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
