const form = document.getElementById("form");
const tipoSel = document.getElementById("tipo");
const checklistDiv = document.getElementById("checklist");
const estadoTag = document.getElementById("estado");
const pastaP = document.getElementById("pasta");
const outroBox = document.getElementById("outroBox");
const acoes = document.getElementById("acoes");
const btnConcluir = document.getElementById("concluir");
const btnAbrirPasta = document.getElementById("abrirPasta");
const btnOutro = document.getElementById("btnOutro");
const outroNome = document.getElementById("outroNome");
const outroFile = document.getElementById("outroFile");

const META = {
  sucesso: ["✅", "Emitida (auto)"],
  enviado: ["✅", "Enviado"],
  manual: ["📤", "Envio manual"],
  aberta: ["📂", "Aberta — conclua no site"],
  pendente: ["⏳", "Pendente"],
  aguardando: ["🌐", "Abre automático"],
  executando: ["🔄", "Abrindo…"],
  erro: ["❌", "Erro"],
};

const MODO = {
  auto: ["🤖", "Automático (captura o PDF)"],
  abrir: ["🌐", "Abre no seu navegador"],
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
      const acao = comJob
        ? `<label class="upbtn">${p.arquivo ? "Trocar PDF" : "Enviar PDF"}<input type="file" data-item="${p.nome}" accept="application/pdf,image/*" hidden></label>${p.arquivo ? " 📄" : ""}`
        : "";
      const obs = comJob && p.mensagem ? `<br><span class="obs">${p.mensagem}</span>` : "";
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

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const resp = await fetch("/emitir", { method: "POST", body: new FormData(form) });
  const { job_id } = await resp.json();
  jobAtual = job_id;
  outroBox.hidden = false;
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

btnOutro.addEventListener("click", () => {
  if (outroNome.value && outroFile.files[0]) {
    enviar(outroNome.value, outroFile.files[0]);
    outroNome.value = "";
    outroFile.value = "";
  }
});

btnConcluir.addEventListener("click", async () => {
  btnConcluir.disabled = true;
  btnConcluir.textContent = "Gerando relatório…";
  await fetch("/concluir/" + jobAtual, { method: "POST" });
  atualizar();
});

btnAbrirPasta.addEventListener("click", () => {
  if (jobAtual) fetch("/abrir-pasta/" + jobAtual, { method: "POST" });
});

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
