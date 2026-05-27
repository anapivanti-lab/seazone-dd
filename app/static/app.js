const form = document.getElementById("form");
const painel = document.getElementById("painel");
const tbody = document.querySelector("#tabela tbody");
const estadoTag = document.getElementById("estado");
const pastaP = document.getElementById("pasta");

const ICONES = {
  sucesso: "✅",
  pendente_captcha: "⏳",
  indisponivel: "⚠️",
  erro: "❌",
  executando: "🔄",
  aguardando: "•",
};

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const resp = await fetch("/emitir", { method: "POST", body: new FormData(form) });
  const { job_id } = await resp.json();
  painel.hidden = false;
  acompanhar(job_id);
});

async function acompanhar(jobId) {
  const tick = async () => {
    const r = await fetch(`/status/${jobId}`);
    if (!r.ok) return;
    const job = await r.json();
    estadoTag.textContent = job.estado;
    pastaP.textContent = "Pasta: " + job.pasta;
    tbody.innerHTML = job.passos
      .map(
        (p) => `
        <tr>
          <td>${ICONES[p.status] || "•"} ${p.status}</td>
          <td>${p.nome}</td>
          <td>${p.mensagem || ""}</td>
          <td>${p.arquivo ? "📄" : "—"}</td>
        </tr>`
      )
      .join("");
    if (job.estado !== "concluido") setTimeout(tick, 1500);
  };
  tick();
}
