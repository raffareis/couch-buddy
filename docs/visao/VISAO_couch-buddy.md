# VISÃO — couch-buddy

Atualizada: 2026-07-20 · Fonte: prompts do usuário (log cru da sessão de retomada)

## Norte

Assistente de jogos com IA que acompanha a partida e ajuda o jogador sem tirá-lo do jogo ("AI-powered buddy to help you with games").

## Intenções ativas

1. **Rogue Trader primeiro.** O jogo-alvo imediato é Warhammer 40,000: Rogue Trader, jogado agora (save no Ato 2).
2. **Tela com tudo do mapa atual.** Uma tela mostra todos os itens e tudo que há para fazer no mapa em que o jogador está, baseado em **walkthroughs completos**.
3. **Não perder nada.** Nenhum item importante nem interação importante pode passar batido, **na ordem sugerida** pelos walkthroughs.
4. **Zero alt+tab.** A tela vive fora do jogo (2º monitor) e **atualiza sozinha**: o sistema diz automaticamente os próximos passos, sem o jogador informar onde está.
5. **Projeto integrado à família workshop** (submodule do repo pai).

## Decisões de execução registradas

- Abordagem "save-file primeiro": estado do jogo lido dos autosaves (.zks); visão computacional é complemento futuro (Fase 2), RAG/Q&A Fase 3.
- Conteúdo: itens + interações + quests + decisões com consequência + dicas de combate (tudo, confirmado pelo usuário).
- Tracking híbrido: mapa/quests automáticos via save; ticks manuais com 1 clique para o restante.
- Modo autônomo: usuário delegou decisões de design/execução; entregar trabalho pronto.
