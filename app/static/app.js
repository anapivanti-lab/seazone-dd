const form = document.getElementById("form");
const tipoSel = document.getElementById("tipo");
const certidoesDiv = document.getElementById("certidoes");
const painel = document.getElementById("painel");
const tbody = document.querySelector("#tabela tbody");
const estadoTag = document.getElementById("estado");
const pastaP = document.getElementById("pasta");
const btnConcluir = document.getElementById("concluir");
const btnAbrirPasta = document.getElementById("abrirPasta");

const ICONES = {
  sucesso: "✅",
  pendente_captcha: "⏳",
  indisponivel: "⚠️",
  erro: "❌",
  aberta: "📂",
  executando: "🔄",
  aguardando: "•",
};
const TEXTO = {
  sucesso: "Emitida",
  pendente_captcha: "Pendente",
  indisponivel: "Indisponível",
  erro: "Erro",
  aberta: "Aberta — aguardando você",
  executando: "Abrindo…",
  aguardando: "Na fila",
};

let jobAtual = null;

// Carrega as caixinhas de certidões conforme o tipo (PJ/PF)
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
  acompanhar(job_id);
});

btnConcluir.addEventListener("click", async () => {
  btnConcluir.disabled = true;
  btnConcluir.textContent = "Gerando relatório…";
  await fetch("/concluir/" + jobAtual, { method: "POST" });
});

btnAbrirPasta.addEventListener("click", () => {
  if (jobAtual) fetch("/abrir-pasta/" + jobAtual, { method: "POST" });
});

async function acompanhar(jobId) {
  const tick = async () => {
    const r = await fetch(`/status/${jobId}`);
    if (!r.ok) return;
    const job = await r.json();
    estadoTag.textContent = job.estado.replace(/_/g, " ");
    pastaP.textContent = "Pasta: " + job.pasta;
    tbody.innerHTML = job.passos
      .map(
        (p) => `
        <tr>
          <td>${ICONES[p.status] || "•"} ${TEXTO[p.status] || p.status}</td>
          <td>${p.nome}</td>
          <td>${p.mensagem || ""}</td>
          <td>${p.arquivo ? "📄" : "—"}</td>
        </tr>`
      )
      .join("");

    btnConcluir.hidden = job.estado !== "aguardando_voce";
    if (job.estado === "concluido") {
      estadoTag.textContent = "concluído ✓";
      return; // para de checar
    }
    setTimeout(tick, 1500);
  };
  tick();
}
