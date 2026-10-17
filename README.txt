NECROMANTE SYSTEM — PYTHON BETA
Executar: python necromante.py (Python 3.10+ com Tkinter).
Dados SQLite: ~/.necromante_system/game.db

Inclui cronômetros de prancha, corda e sparring; combate por turnos com HP, habilidades, poções, XP e drops raros; 30 monstros provisórios em cinco níveis; Skill Shop inicial; leitor flutuante com capítulos ímpares por treino e pares por estudos; importação local de texto autorizado; cliente de sincronização QuestHub idempotente por ID de questão.

Limitações importantes:
- As habilidades incluídas são uma seleção de protótipo, não o catálogo completo do RPG Insanity. O catálogo integral precisa ser importado e conferido antes de dizer que está completo.
- O texto da novel não vem embutido. O leitor aceita texto autorizado localmente e oferece o link da página original.
- A sincronização automática exige instalar no QuestHub um endpoint autenticado /api/integration/answered-questions. O cliente está pronto para consultar esse endpoint, mas o servidor ainda precisa ser modificado e implantado.
- Os dados ficam no computador local, sem sincronização entre dispositivos.
