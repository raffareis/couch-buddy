# Rogue Trader Companion — Plano de implementação (MVP Fase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Companion no 2º monitor que detecta o mapa atual do Rogue Trader pelo save e mostra checklist ordenada de itens/interações/quests/decisões do mapa, com ticks manuais persistidos.

**Architecture:** Watcher inotify na pasta de saves → parser do `.zks` (ZIP+JSON) → GameState; reconciliador cruza com guias JSON por mapa (scraping curado offline) e progresso manual; FastAPI+WebSocket empurra o ViewModel pra UI web.

**Tech Stack:** Python 3.11, pydantic v2, watchdog, FastAPI+uvicorn, vanilla JS. Sem chamadas de API no runtime do MVP.

## Global Constraints

- Porta do servidor: `8017`.
- Saves: `~/Storage/SteamLibrary/steamapps/compatdata/2186680/pfx/drive_c/users/steamuser/AppData/LocalLow/Owlcat Games/Warhammer 40000 Rogue Trader/Saved Games`.
- Dados versionados: `data/games/rogue-trader/maps/` (curado), `guid_map.json`. Gitignored: `data/games/rogue-trader/raw/`, `data/progress/`.
- JSON com chaves `snake_case`; docs PT-BR; nomes próprios do jogo em inglês.
- Testes: pytest, fixtures extraídas de saves reais (só JSONs necessários, nunca o ZIP de 10MB inteiro).
- Commits frequentes na `main`, mensagem imperativa 1 linha.

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/couch_buddy/state/models.py` | `QuestState`, `GameState` (pydantic) |
| `src/couch_buddy/state/save_parser.py` | `parse_save(path, guid_map) -> GameState`; heurísticas de nome de área |
| `src/couch_buddy/state/watcher.py` | `SaveWatcher(dir, on_save)` com debounce |
| `src/couch_buddy/knowledge/schema.py` | `Step`, `MapGuide` (pydantic) |
| `src/couch_buddy/knowledge/library.py` | `GuideLibrary(maps_dir)`: carrega e casa área↔guia |
| `src/couch_buddy/brain/progress.py` | `ProgressStore(data_dir)`: ticks por campanha |
| `src/couch_buddy/brain/reconciler.py` | `build_view(state, library, progress) -> dict` |
| `src/couch_buddy/app/server.py` | FastAPI: `/`, `/api/state`, `/api/tick`, WS `/ws` |
| `src/couch_buddy/app/main.py` | fiação: watcher+parser+server, CLI |
| `src/couch_buddy/app/static/{index.html,app.js,style.css}` | UI dark ultrawide |
| `tools/build_guid_map.py` | bootstrap guid_map a partir dos 79 saves |
| `tools/curate_knowledge.py` | valida/normaliza `raw/` → `maps/` |
| `tools/bbp_parser.py` | (agente) parser blueprints-pack.bbp |

### Task 1: Modelos + schema de conhecimento

**Files:** Create `state/models.py`, `knowledge/schema.py`, `tests/test_schema.py`.
**Produces:** `GameState(area_guid, area_name, chapter, quests: list[QuestState], save_id, game_id, save_name, saved_at)`; `QuestState(blueprint, state, objectives: list[ObjectiveState])`; `MapGuide(area_name, aliases, act, sources, steps: list[Step])`; `Step(order, type, title, details, quest, missable, spoiler, source_url)` com `type ∈ {item, interaction, quest_step, decision, combat_tip}` e `spoiler ∈ {low, medium, high}`.

- [ ] Teste: `MapGuide.model_validate` aceita exemplo mínimo válido e rejeita `type` inválido.
- [ ] Implementar modelos; rodar pytest; commit.

### Task 2: Parser de save

**Files:** Create `state/save_parser.py`, `tests/test_save_parser.py`, fixture `tests/fixtures/` (header.json real + player.json real reduzido + namelist real em txt).
**Interfaces:** `parse_save(path: Path, guid_map: dict[str, str]) -> GameState`; `derive_area_names(namelist: list[str]) -> dict[str, str]` (heurística: fog `"<guid>.<Scene>_Static..."` e mechanics `"<guid><Scene>[_estado]_Mechanics.json"`, prefixo comum por GUID).

```python
def parse_save(path, guid_map):
    with zipfile.ZipFile(path) as z:
        header = json.loads(z.read("header.json"))
        player = json.loads(z.read("player.json"))
        names = derive_area_names(z.namelist())
    guid = player["CurrentArea"]
    ...
```

- [ ] Teste com save real (o mais recente): area_guid == `48cdcd77...`, chapter == 2, >300 quests, area_name resolvido.
- [ ] Implementar; pytest verde; commit.

### Task 3: Bootstrap do guid_map

**Files:** Create `tools/build_guid_map.py`.
**Interfaces:** CLI `python tools/build_guid_map.py [--saves-dir D] [--out data/games/rogue-trader/guid_map.json]`; mescla com existente, nunca sobrescreve nome aprendido manualmente (chaves com `"manual": true` preservadas — formato `{guid: {"name": str, "manual": bool}}`).

- [ ] Rodar contra os 79 saves reais; conferir que CurrentArea do último save ganha nome; commit do guid_map gerado.

### Task 4: Watcher

**Files:** Create `state/watcher.py`, `tests/test_watcher.py`.
**Interfaces:** `SaveWatcher(saves_dir: Path, on_save: Callable[[Path], None], debounce_s: float = 2.0)` com `.start()/.stop()`; dispara callback quando um `.zks` novo/modificado fica estável (mtime parado por debounce_s).

- [ ] Teste com tmp_path simulando escrita em 2 chunks; callback dispara 1x.
- [ ] Implementar com watchdog + timer; pytest; commit.

### Task 5: Biblioteca de guias + curadoria

**Files:** Create `knowledge/library.py`, `tools/curate_knowledge.py`, `tests/test_library.py`.
**Interfaces:** `GuideLibrary(maps_dir)`: `.find(area_name: str) -> MapGuide | None` (casa por `area_name`/`aliases`, case-insensitive, normalizando `_`/`-`/espaço; ex.: `Footfall_Crematory` casa alias `Footfall Crematory`); `.all() -> list[MapGuide]`. Curadoria: valida raw contra schema, normaliza ordem (`order` 1..n), grava em `maps/<slug>.json`, relatório de falhas.

- [ ] Testes de matching (exato, alias, normalização, miss) com 2 guias sintéticos.
- [ ] Implementar; curar saída dos agentes de scraping; pytest; commit (inclui `maps/`).

### Task 6: Progresso + reconciliador

**Files:** Create `brain/progress.py`, `brain/reconciler.py`, `tests/test_reconciler.py`.
**Interfaces:** `ProgressStore.get(game_id) -> dict[step_key, bool]`, `.set(game_id, step_key, done)` (step_key = `f"{slug}:{order}"`, persiste em `data/progress/<game_id>.json`). `build_view(state, library, progress) -> dict` com chaves: `area_name`, `chapter`, `save_name`, `saved_at`, `guide` (None ou `{slug, steps: [...cada step + done: bool]}`), `unknown_area: bool`.

- [ ] Testes: área com guia (steps + done), área sem guia, tick round-trip.
- [ ] Implementar; pytest; commit.

### Task 7: Servidor + UI

**Files:** Create `app/server.py`, `app/static/*`, `tests/test_server.py`.
**Interfaces:** `create_app(companion: Companion) -> FastAPI` onde `Companion` (em `main.py`) guarda estado atual e expõe `.view()`, `.tick(step_key, done)`, `.subscribe()`. REST: `GET /api/state` → view JSON; `POST /api/tick {step_key, done}`; WS `/ws` recebe view a cada mudança. UI: header (mapa/capítulo/último sync), checklist ordenada com badge por tipo, missable/decision em destaque, spoiler high desfocado até hover, dicas de combate colapsáveis, clique → POST tick.

- [ ] Teste de fumaça com TestClient: `/api/state` 200, tick altera view.
- [ ] Implementar server + UI; pytest; commit.

### Task 8: Main + launcher

**Files:** Create `app/main.py`, Modify `app/config.py` (paths reais, porta, modelos `claude-sonnet-5`/`claude-haiku-4-5`), Modify `pyproject.toml` (deps: fastapi, uvicorn, watchdog; entry point ok).
**Interfaces:** `couch-buddy` CLI: sobe watcher + uvicorn; `--saves-dir`, `--port`, `--no-open`; ao iniciar, parseia o save mais recente imediatamente; abre Chrome `--window-position` no 2º monitor.

- [ ] Rodar de verdade contra a pasta real; ver estado "Administratum" na UI; commit.

### Task 9: Integração de conhecimento + verificação end-to-end

- [ ] Curar JSONs dos agentes (`raw/` → `maps/`) com relatório; commit dos curados.
- [ ] Rodar app, capturar screenshot da UI (agent-browser), validar checklist do mapa atual.
- [ ] Se parser bbp entregue: gerar nomes de quests/itens e ligar auto-check ao reconciliador (tarefa extra documentada em issue se não der tempo).
- [ ] Atualizar CLAUDE.md do projeto + README; commit final; bump submodule no workshop.

## Self-review

- Cobertura do spec: erros (banner GUID desconhecido → coberto pela view `unknown_area` + UI; save corrompido → parser lança, main mantém último estado e loga). Fase 2/3 fora do escopo, registradas no spec.
- Sem placeholders; assinaturas consistentes entre tasks (GameState/MapGuide/build_view/step_key).
