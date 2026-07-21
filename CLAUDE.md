# couch-buddy

Companion de jogos: tela no 2º monitor que mostra, para o mapa atual, a checklist ordenada de itens/interações/quests/decisões extraída de walkthroughs — sem alt+tab. Primeiro alvo: Warhammer 40,000: Rogue Trader (Steam/Proton nesta máquina).

## Arquitetura (MVP Fase 1)

Save-file primeiro: o jogo autosava em transição de área; os `.zks` são ZIP com JSON aberto. Sem chamadas de API no runtime.

- `state/` — `SaveWatcher` (inotify+debounce) e `parse_save` (lê só `header.json` + `player.json` do ZIP). Nome da área: guid_map (heurística por filenames dos saves) sobreposto por `blueprint_names.json`, sobreposto por nomes aprendidos manualmente (UI).
- `knowledge/` — guias por mapa em `data/games/rogue-trader/maps/*.json` (schema `MapGuide`; curados de walkthroughs via `tools/curate_knowledge.py`; brutos em `raw/`, gitignored). `GuideLibrary.find()` casa área↔guia por nome/alias/prefixo.
- `brain/` — `build_view()` cruza save + guia + ticks manuais (`data/progress/<game_id>.json`, gitignored); auto-marca `quest_step` cuja quest está `Completed` no save.
- `app/` — FastAPI + WebSocket na porta 8017; UI vanilla JS dark (ultrawide). `couch-buddy` (entry point) sobe tudo e abre Chrome no 2º monitor.

## Comandos

```bash
uv venv && uv pip install -e ".[dev]"      # setup
.venv/bin/python -m pytest -q              # testes (fixtures de saves reais em tests/fixtures/)
.venv/bin/couch-buddy                      # rodar (usa pasta de saves real; --no-open, --port, --saves-dir)
.venv/bin/python tools/build_guid_map.py   # regenerar guid_map dos saves
.venv/bin/python tools/curate_knowledge.py # validar raw/ -> maps/
.venv/bin/python tools/bbp_parser.py <bbp> --dump-names data/games/rogue-trader/blueprint_names.json
```

## Dados do ambiente (desta máquina)

- Saves (Proton, appid 2186680): `~/Storage/SteamLibrary/steamapps/compatdata/2186680/pfx/drive_c/users/steamuser/AppData/LocalLow/Owlcat Games/Warhammer 40000 Rogue Trader/Saved Games`
- Jogo: `~/Storage/SteamLibrary/steamapps/common/Warhammer 40,000 Rogue Trader` (`Bundles/blueprints-pack.bbp`, `WH40KRT_Data/StreamingAssets/Localization/enGB.json`)
- Monitores (X11): jogo no HDMI-0 (2560×1080 @ +1080+228); companion no HDMI-1 (+1080+1308).

## blueprints-pack.bbp

Formato decifrado (ReflectionBasedSerializer da Owlcat): TOC `uint32 count` + `count×(GUID bytes_le + uint32 offset)`; corpo por reflexão usando schema extraído dos DLLs (gerar com `tools/bbp_schema_dumper/` após patch do jogo → `tools/bbp_schema_rt.json.gz`). `tools/bbp_parser.py` é stdlib pura. Referências: xADDBx/BpBinReader (MIT), xADDBx/RogueTraderDecompiled.

## Convenções

- Specs/planos em `docs/superpowers/{specs,plans}/`. Fase 2 (visão entre autosaves) e 3 (RAG/Q&A) descritas no spec de 2026-07-20.
- Testes nunca versionam um `.zks` inteiro — só JSONs reduzidos + namelist.
- Herda as regras da família workshop (repo pai).
