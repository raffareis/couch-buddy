"use strict";

const $ = (id) => document.getElementById(id);
let ultimaView = null;

function render(view) {
  ultimaView = view;
  $("mapa").textContent = view.area_name || "—";
  $("meta").textContent = view.chapter
    ? `Capítulo ${view.chapter} · ${view.save_name || ""}`
    : "aguardando save…";
  $("sync").textContent = view.saved_at
    ? `último save: ${new Date(view.saved_at).toLocaleString("pt-BR")}`
    : "sem sync";
  $("banner-desconhecida").classList.toggle("oculto", !view.unknown_area);

  const quests = $("quests-lista");
  quests.innerHTML = "";
  for (const nome of view.quests_ativas || []) {
    const el = document.createElement("div");
    el.className = "quest-ativa";
    el.textContent = nome;
    quests.appendChild(el);
  }
  if (!quests.children.length)
    quests.innerHTML = '<div class="contador">nenhuma</div>';

  const guia = view.guide;
  $("sem-guia").classList.toggle("oculto", !!guia || !view.area_name);
  const checklist = $("checklist");
  const alertas = $("alertas-lista");
  const combate = $("combate-lista");
  checklist.innerHTML = alertas.innerHTML = combate.innerHTML = "";
  if (!guia) return;

  const principais = guia.steps.filter((s) => s.type !== "combat_tip");
  const feitos = principais.filter((s) => s.done).length;
  checklist.insertAdjacentHTML(
    "beforeend",
    `<div class="contador">${feitos}/${principais.length} concluídos — ${guia.area_name}</div>`
  );

  for (const step of guia.steps) {
    const el = document.createElement("div");
    el.className = `passo t-${step.type}` +
      (step.done ? " done" : "") +
      (step.missable ? " missable" : "") +
      (step.spoiler === "high" ? " spoiler-high" : "");
    el.innerHTML = `
      <span class="ordem">${step.type === "combat_tip" ? "•" : step.order}</span>
      <div style="flex:1">
        <div class="titulo"></div>
        <div class="detalhes"></div>
        ${step.quest ? '<div class="quest-ref"></div>' : ""}
      </div>
      <span class="badge b-${step.type}">${rotulo(step.type)}</span>`;
    el.querySelector(".titulo").textContent = step.title;
    el.querySelector(".detalhes").textContent = step.details || "";
    if (step.quest) el.querySelector(".quest-ref").textContent = `Quest: ${step.quest}`;
    el.addEventListener("click", () => tick(step.step_key, !step.done));

    if (step.type === "combat_tip") combate.appendChild(el);
    else {
      checklist.appendChild(el);
      if ((step.type === "decision" || step.missable) && !step.done)
        alertas.appendChild(clonarResumo(step));
    }
  }
  if (!combate.children.length)
    combate.innerHTML = '<div class="contador">nenhuma para este mapa</div>';
  if (!alertas.children.length)
    alertas.innerHTML = '<div class="contador">nada pendente</div>';
}

function clonarResumo(step) {
  const el = document.createElement("div");
  el.className = `passo t-${step.type}` + (step.missable ? " missable" : "");
  el.innerHTML = `<span class="ordem">${step.order}</span><div class="titulo"></div>`;
  el.querySelector(".titulo").textContent = step.title;
  el.addEventListener("click", () => tick(step.step_key, true));
  return el;
}

const rotulo = (t) =>
  ({ item: "item", interaction: "interação", quest_step: "quest",
     decision: "decisão", combat_tip: "combate" }[t] || t);

async function tick(stepKey, done) {
  const res = await fetch("/api/tick", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ step_key: stepKey, done }),
  });
  render(await res.json());
}

$("salvar-area").addEventListener("click", async () => {
  const nome = $("nome-area").value.trim();
  if (!nome) return;
  const res = await fetch("/api/learn-area", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: nome }),
  });
  render(await res.json());
});

function conectar() {
  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = (ev) => render(JSON.parse(ev.data));
  ws.onclose = () => setTimeout(conectar, 2000);
}
fetch("/api/state").then((r) => r.json()).then(render);
conectar();
