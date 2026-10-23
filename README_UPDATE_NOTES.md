# Atualização: Dungeon e combate por turnos

- A navegação principal substitui “Combate” por “Dungeon”; a rota antiga `/combate` redireciona para `/dungeon`.
- A dungeon usa um ticket diário, com nível derivado do maior rank de atributo e três pisos por nível.
- Cada piso gera de 3 a 7 monstros; no piso final, o último é um boss dois níveis acima do nível da dungeon.
- O combate acontece por turnos: cada clique em “Atacar / próximo turno” resolve uma rodada no servidor, incluindo prioridade e chance de esquiva.
- O progresso da dungeon (piso, inimigo atual, HP e log) é salvo em uma tabela nova `dungeon_run`, sem apagar tabelas existentes.
- HP base foi alterado para 10; Resistência acrescenta 15 HP por avanço de rank. Dano base é 1; Combate acrescenta 2 por avanço. Agilidade concede 5 pontos percentuais de esquiva por avanço.
- Ranks F, E, D, C, B, A, S usam custos de avanço de 90, 180, 360, 720, 1440 e 2880 XP. Os limites são cumulativos.

Nota: `db.create_all()` cria a nova tabela sem apagar o banco. A atualização não foi executada no Render; teste em ambiente de staging antes de publicar. O ambiente local desta sessão não tem Flask instalado, então foi possível validar a sintaxe Python (`py_compile`), mas não executar os testes HTTP/templates.
