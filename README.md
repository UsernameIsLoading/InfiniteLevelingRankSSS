# Sistema do Soberano — MVP 0.1

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
