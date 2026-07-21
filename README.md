# couch-buddy

Companion de jogos no 2º monitor: mostra a checklist do mapa atual (itens, interações, quests, decisões, dicas de combate) extraída de walkthroughs completos, atualizando sozinha a partir dos saves do jogo — sem alt+tab.

Primeiro jogo suportado: **Warhammer 40,000: Rogue Trader**.

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/couch-buddy        # sobe o servidor (porta 8017) e abre o Chrome no 2º monitor
```

Detalhes de arquitetura e operação: `CLAUDE.md`. Spec e plano: `docs/superpowers/`.
