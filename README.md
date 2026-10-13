# Sistema do Soberano — Update 0.2

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
