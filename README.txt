NECROMANTE SYSTEM — PACOTE PYTHON
================================

ARQUIVOS INCLUÍDOS
- necromante.py: aplicativo principal.
- iniciar_windows.bat: iniciador para Windows.
- iniciar_linux_mac.sh: iniciador para Linux/macOS (com Python e Tkinter instalados).
- requirements.txt: dependências; não há pacotes pip obrigatórios.
- config.example.json: exemplo de configuração do QuestHub (não contém token real).
- ferramentas/backup_banco.py: cria backup do banco local.
- testes/teste_sintaxe.py: teste de sintaxe automatizado.
- .gitignore: evita incluir banco e arquivos temporários em repositórios.

COMO ABRIR NO WINDOWS
1. Instale Python 3.10 ou superior em https://www.python.org/downloads/.
2. Durante a instalação, marque “Add Python to PATH”.
3. Extraia o ZIP inteiro para uma pasta.
4. Dê dois cliques em iniciar_windows.bat. Também é possível executar `python necromante.py`.
5. O Windows pode precisar da instalação completa do Python com Tcl/Tk para disponibilizar Tkinter.

LINUX / macOS
Execute `chmod +x iniciar_linux_mac.sh` e depois `./iniciar_linux_mac.sh`.
Se Tkinter não estiver instalado, instale o pacote Tk da sua distribuição Python/SO.

DADOS E BACKUP
O banco é criado automaticamente em ~/.necromante_system/game.db (Windows: dentro da pasta do usuário).
As configurações são gravadas em ~/.necromante_system/config.json e os textos de capítulos importados ficam nessa mesma pasta.
Para fazer backup, execute `python ferramentas/backup_banco.py`. A cópia é gravada em ~/.necromante_system/backups/.
Não apague a pasta .necromante_system se quiser preservar o progresso.

QUESTHUB
Na aba Integração, informe a URL base do QuestHub, o token configurado no servidor e o ID da conta.
O servidor QuestHub precisa ter o endpoint autenticado /api/integration/answered-questions implantado. O arquivo config.example.json é apenas um modelo: substitua os valores na interface do app.

LIMITAÇÕES CONHECIDAS (PARA NÃO PROMETER O QUE NÃO EXISTE)
- O catálogo de habilidades ainda é uma seleção de protótipo, não todas as habilidades do site RPG Insanity.
- Os monstros são uma lista provisória de 30 entradas em cinco níveis; não é possível garantir que corresponda à imagem/lista de monstros enviada anteriormente.
- O texto integral da novel não é incluído. O leitor permite importar texto que você tenha direito de usar e oferece acesso à página original.
- A sincronização não sincroniza o progresso entre computadores; ela apenas consulta as questões respondidas no QuestHub.
- O primeiro sincronismo contabiliza como novas todas as questões respondidas que ainda não estejam registradas no banco local. Faça backup antes do primeiro uso se já houver progresso.

TESTE DE SINTAXE
Execute: python -m unittest discover -s testes

Nenhum token ou senha real deve ser colocado no ZIP compartilhado.
