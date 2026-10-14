# Sistema do Soberano — Update 0.5

Aplicação web progressiva (PWA-ready) em Flask, com interface em português, banco SQL, registro de atividades, atributos, XP/níveis, missões especiais que desbloqueiam habilidades, biblioteca de questões e histórico de resultados do Strength Level/Human Benchmark.

## O que funciona nesta primeira versão
- Cadastro, login e logout com senhas armazenadas em hash.
- Perfil inicial com cinco atributos: Corpo, Mente, Disciplina, Vitalidade e Espírito.
- Registro de atividades que concede pontos ao atributo correspondente e XP.
- Progressão de nível com curva gradual.
- Missões especiais concluíveis uma vez por conta, cada uma desbloqueando uma habilidade.
- Biblioteca de questões: criar, filtrar e responder questões; correção automática por comparação textual exata (ignorando maiúsculas/minúsculas).
- Importação de questões CSV/JSON para administradores.
- Registro manual e histórico de resultados do Strength Level e Human Benchmark, com links para os serviços.
- Painel administrativo para criar missões, remover outras contas e exportar backup JSON.
- SQLite para desenvolvimento e PostgreSQL via `DATABASE_URL` em produção.

## Rodar localmente
Requer Python 3.11+.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Defina uma chave secreta e, se quiser, uma conta administrativa via variáveis de ambiente:

```bash
# Linux/macOS
export SECRET_KEY='substitua-por-uma-chave-longa-e-aleatoria'
export ADMIN_USERNAME='admin'
export ADMIN_PASSWORD='use-uma-senha-forte'
python app.py
```

No Windows PowerShell, use `$env:SECRET_KEY='...'`, `$env:ADMIN_USERNAME='admin'` e `$env:ADMIN_PASSWORD='...'`.
Abra `http://127.0.0.1:5000`.

## Publicar
O projeto pode ser enviado a um repositório GitHub e implantado num serviço compatível com Flask/Gunicorn. Configure `SECRET_KEY`, `DATABASE_URL`, `ADMIN_USERNAME` e `ADMIN_PASSWORD` como variáveis de ambiente. Use PostgreSQL persistente em produção; o SQLite local não é adequado para hospedagem efêmera/múltiplas instâncias.

O arquivo `render.yaml` é um modelo de configuração, não cria sozinho uma base PostgreSQL. Crie a base no provedor e configure `DATABASE_URL` com a URL interna apropriada.

## Formato de importação de questões
CSV UTF-8 com cabeçalhos obrigatórios:
`subject,level,topic,prompt,answer`

Cabeçalhos opcionais: `difficulty,explanation,source,options`. Em `options`, use opções separadas por `|`, ou um array JSON em arquivo JSON.

Exemplo JSON:
```json
[
  {
    "subject": "Física",
    "level": "Ensino superior",
    "topic": "Eletromagnetismo",
    "difficulty": "Intermediária",
    "prompt": "Qual é a expressão da força magnética?",
    "options": ["qE", "q(v × B)", "mv", "qB"],
    "answer": "q(v × B)",
    "explanation": "A força magnética depende do produto vetorial entre velocidade e campo magnético.",
    "source": "Questão original"
  }
]
```

## Limitações conhecidas do MVP
- A integração com Strength Level e Human Benchmark é por links e registro manual; não se presume que existam APIs públicas disponíveis.
- A correção de questões é textual exata (ignorando caixa), adequada ao MVP para múltipla escolha e respostas curtas; não avalia respostas discursivas semanticamente.
- O backup administrativo atual exporta JSON. A restauração de backups ainda não está implementada; para PostgreSQL, use `pg_dump`/`pg_restore` no ambiente do provedor.
- O módulo de combate, a punição especial por contato externo, a árvore completa de classes e o modo PWA instalável com service worker são etapas posteriores.
- Antes de uso público, recomenda-se acrescentar proteção CSRF, limitação de tentativas de login, migrações de esquema e testes automatizados.

## Update 0.2 — Ciclo I e Provação

Esta atualização acrescenta:

- Campanha narrativa inicial com sete capítulos desbloqueados de acordo com o dia da semana (segunda a domingo), escolhas registradas e pequenas repercussões narrativas.
- Registro de capítulos e recompensa de 10 XP por capítulo, sem permitir registrar capítulos de dias futuros.
- **Provação de Fundação** para criar uma linha de base física e mental.
- **Dia da Provação** semanal, com envio permitido aos domingos, registro de resultados numéricos, unidades, notas e fotografia dos atributos/nível/XP.
- Página **Evolução**, com valores atuais, histórico de cada provação e gráficos simples para testes repetidos.
- Persistência dos novos registros na base de dados e inclusão deles na exportação JSON de backup.

### Atualização do projeto já publicado no Render

1. Substitui os arquivos do repositório pelos arquivos desta versão e faz commit/push.
2. O Render deve iniciar um novo deploy automaticamente se o repositório estiver conectado.
3. Mantém o mesmo `DATABASE_URL` PostgreSQL e define um `SECRET_KEY` forte nas variáveis de ambiente. `db.create_all()` cria as novas tabelas sem apagar as tabelas anteriores; não apagues nem recries a base de dados para atualizar o app.
4. Após o deploy, testa login, `/story`, `/trial?kind=baseline` e `/evolution`. Registra a Provação de Fundação com resultados reais; não uses valores inventados para preencher a linha de base.

**Limitação consciente do primeiro arco:** o conteúdo narrativo foi escrito para a semana de 12 a 18 de outubro de 2026. O próximo arco precisa ser adicionado numa atualização posterior; o app não gera automaticamente uma nova história toda segunda-feira. Os capítulos, resultados e escolhas já registrados ficam persistidos na base de dados.

### Segurança e interpretação dos testes

Os resultados físicos e mentais são registros informados pelo usuário, não medições automáticas. Para testes físicos, prioriza técnica válida e testes submáximos/estimativas quando apropriado; não é necessário tentar uma repetição máxima absoluta em todos os exercícios semanalmente. Resultados como tempo de reação podem melhorar quando o número diminui, então a variação numérica não é automaticamente classificada como melhoria ou piora.

## Update 0.4 — Administração, capítulos e combate

### Configurar o administrador no Render

Em **Dashboard → serviço → Environment**, configure:

- `ADMIN_USERNAME`: nome exclusivo da conta administrativa.
- `ADMIN_PASSWORD`: senha forte para essa conta (use pelo menos 16 caracteres).
- `SECRET_KEY`: segredo longo e aleatório para assinar sessões.
- `DATABASE_URL`: URL do PostgreSQL persistente.

A conta administrativa entra pela tela normal de login, usando `ADMIN_USERNAME` e `ADMIN_PASSWORD`. A autorização para abrir `/admin`, importar capítulos, publicar/arquivar conteúdo e administrar contas é verificada no servidor. Não use senha administrativa fixa no código-fonte nem publique essas variáveis no GitHub. Se uma conta com o nome configurado já existir, a inicialização a promove para administradora; por segurança, defina `ADMIN_USERNAME` como um nome reservado só para essa função.

### Importar capítulos

No painel **ADM → Importar capítulo em JSON**, envie o arquivo exportado no formato `sistema-do-soberano-narrative` (por exemplo, `sistema_do_soberano_capitulo_01_v1_2.json`). O sistema valida o formato, as cenas, as decisões e as opções antes de salvar. Arquivos até 5 MB são aceitos. Um capítulo com o mesmo `chapter.id` é atualizado; escolhas já salvas pelos jogadores são mantidas. Capítulos podem ser publicados ou arquivados no painel. O conteúdo fica armazenado no banco, não no disco efêmero do servidor.

### Decisões narrativas persistentes

As escolhas dos capítulos importados são registradas uma única vez por jogador e decisão. Flags, inventário, conhecimentos, relações e sinais de karma são guardados no banco. Os sinais de karma não mudam uma classificação imediatamente; a avaliação do ciclo semanal fica reservada ao encerramento do ciclo, conforme as regras narrativas do projeto.

### Combate inicial

A página **Combate** implementa turnos com ataque, defesa e fuga. Corpo influencia o dano do jogador; vitalidade aumenta HP e reduz parte do dano recebido. Vitória concede XP; derrota ou fuga não concedem XP. Este é o primeiro módulo funcional de combate e serve como base para depois acrescentar habilidades, efeitos de estado, custos, cooldowns e encontros narrativos.

### Atualização de banco

As tabelas novas são criadas pelo `db.create_all()` na inicialização. Em bancos já existentes, isso cria as novas tabelas sem apagar as tabelas antigas. Para alterações futuras de colunas, use migrações de banco em vez de depender apenas de `create_all()`.


## Update 0.5 — Importação e geração de questões

A Biblioteca do Conhecimento agora oferece:

- **Importação online** da Open Trivia Database (opentdb.com), com filtros de categoria, dificuldade e quantidade (1–20), alternativas embaralhadas e deduplicação por enunciado.
- **Geração de questões originais por IA** através da API da OpenAI, com disciplina, nível, assunto, dificuldade e quantidade (1–10). A resposta precisa corresponder exatamente a uma das quatro alternativas para ser salva.
- **Edição e exclusão administrativa** de questões existentes, incluindo fonte e explicação. A criação manual e a importação CSV/JSON continuam disponíveis.
- A fonte é guardada em cada questão para distinguir conteúdo original, importado e gerado por IA. Questões geradas por IA devem ser revisadas antes de serem usadas em avaliações.

### Configurar geração por IA no Render

Em **Dashboard → serviço → Environment**, adicione `OPENAI_API_KEY` com uma chave válida da API da OpenAI. Opcionalmente, configure `OPENAI_MODEL` (o padrão é `gpt-4o-mini`). A geração depende de acesso à API e pode gerar custos de uso. Sem a chave, a importação online e CSV/JSON continuam funcionando. Não coloque a chave no código nem no GitHub.

A importação online usa uma fonte pública fixa, não aceita URLs arbitrárias fornecidas por usuários, e pode retornar menos questões quando a categoria/filtros têm pouco conteúdo. A atribuição da fonte é mantida quando disponível.
