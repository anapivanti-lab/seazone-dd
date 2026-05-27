const form = document.getElementById("form");
const tipoSel = document.getElementById("tipo");
const certidoesDiv = document.getElementById("certidoes");
const painel = document.getElementById("painel");
const checklistDiv = document.getElementById("checklist");
const estadoTag = document.getElementById("estado");
const pastaP = document.getElementById("pasta");
const btnConcluir = document.getElementById("concluir");
const btnAbrirPasta = document.getElementById("abrirPasta");
const btnOutro = document.getElementById("btnOutro");
const outroNome = document.getElementById("outroNome");
const outroFile = document.getElementById("outroFile");

const META = {
  sucesso: ["✅", "Emitida (auto)"],
  enviado: ["✅", "Enviado"],
  manual: ["📤", "Falta enviar"],
  aberta: ["📂", "Aberta — conclua no site"],
  pendente: ["⏳", "Pendente"],
  aguardando: ["•", "Na fila"],
  executando: ["🔄", "Abrindo…"],
  erro: ["❌", "Erro"],
};

let jobAtual = null;
let ultimoRender = "";

// Caixinhas das certidões com automação (quais sites abrir)
async function carregarProvedores() {
  certidoesDiv.innerHTML = "carregando…";
  const r = await fetch("/provedores?tipo=" + tipoSel.value);
  const nomes = await r.json();
  certidoesDiv.innerHTML = nomes
    .map(
      (n) =>
        `<label class="chk"><input type="checkbox" name="selecionados" value="${n}" checked> ${n}</label>`
    )
    .join("");
}
tipoSel.addEventListener("change", carregarProvedores);
carregarProvedores();

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const resp = await fetch("/emitir", { method: "POST", body: new FormData(form) });
  const { job_id } = await resp.json();
  jobAtual = job_id;
  painel.hidden = false;
  ultimoRender = "";
  acompanhar();
});

// Envio de arquivo (genérico)
async function enviar(item, file) {
  const fd = new FormData();
  fd.append("item", item);
  fd.append("arquivo", file);
  await fetch("/upload/" + jobAtual, { method: "POST", body: fd });
  atualizar();
}

// Upload por item (clique no botão "Enviar PDF" de cada linha)
checklistDiv.addEventListener("change", (e) => {
  const inp = e.target;
  if (inp.matches('input[type="file"]') && inp.files[0]) {
    enviar(inp.dataset.item, inp.files[0]);
  }
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

function renderChecklist(job) {
  const grupos = {};
  job.passos.forEach((p) => {
    (grupos[p.grupo || "Outros"] ||= []).push(p);
  });
  let html = "";
  for (const [grupo, itens] of Object.entries(grupos)) {
    html += `<h3>${grupo}</h3><table class="cl"><tbody>`;
    for (const p of itens) {
      const [ic, tx] = META[p.status] || ["•", p.status];
      html += `<tr>
        <td class="st">${ic} ${tx}</td>
        <td>${p.nome}${p.mensagem ? `<br><span class="obs">${p.mensagem}</span>` : ""}</td>
        <td class="ac">
          <label class="upbtn">${p.arquivo ? "Trocar PDF" : "Enviar PDF"}
            <input type="file" data-item="${p.nome}" accept="application/pdf,image/*" hidden>
          </label>
          ${p.arquivo ? " 📄" : ""}
        </td></tr>`;
    }
    html += `</tbody></table>`;
  }
  checklistDiv.innerHTML = html;
}

async function atualizar() {
  if (!jobAtual) return;
  const r = await fetch("/status/" + jobAtual);
  if (!r.ok) return;
  const job = await r.json();
  estadoTag.textContent = job.estado.replace(/_/g, " ");
  pastaP.textContent = "Pasta: " + job.pasta;
  btnConcluir.hidden = job.estado !== "aguardando_voce";
  // só re-renderiza se algo mudou (evita piscar)
  const assinatura = JSON.stringify(job.passos);
  if (assinatura !== ultimoRender) {
    renderChecklist(job);
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
