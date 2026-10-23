# Necromante da Estação de Seul — versão web

Aplicação Flask responsiva com acesso por senha, persistência via PostgreSQL/SQLite, treinos com temporizador regressivo, combate por turnos, habilidades, inventário, capítulos e endpoint de integração com o registro manual de questões.

## Publicar no Render

1. Extraia o ZIP e envie a pasta para um repositório GitHub.
2. No Render, escolha **New → Blueprint** e conecte o repositório. O `render.yaml` cria um serviço web e um banco PostgreSQL.
3. Configure `SITE_PASSWORD` com uma senha numérica de exatamente 8 dígitos. Não coloque essa senha no código nem no GitHub.
4. Configure `QUESTHUB_INTEGRATION_TOKEN` com um segredo aleatório forte, igual ao token usado pelo registro manual de questões. Configure também `QUESTHUB_BASE_URL` com a URL pública do registro manual de questões (sem barra final) e `QUESTHUB_USER_ID` com o ID da sua conta nele.
5. O `SECRET_KEY` é gerado pelo Render; `DATABASE_URL` vem do banco provisionado. O cookie seguro fica habilitado no serviço publicado.
6. Confirme que o health check `/health` responde `{"status":"ok"}`.

**Atenção importante sobre persistência:** o plano gratuito e as condições do PostgreSQL no Render podem ter limites, expiração ou mudanças de política. Antes de confiar seu progresso ao serviço, confirme a retenção vigente no Render. Para progresso duradouro, use um PostgreSQL que não expire e faça backups regulares. O banco, e não o disco local do serviço web, é a fonte principal dos dados.

## Rodar localmente

Requer Python 3.11 ou 3.12.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
# Defina variáveis no terminal antes de iniciar:
# Windows PowerShell: $env:SITE_PASSWORD="12345678"; $env:SECRET_KEY="uma-chave-local"
# Linux/macOS: export SITE_PASSWORD=12345678; export SECRET_KEY='uma-chave-local'
python app.py
```

Abra `http://127.0.0.1:5000`. Troque a senha de exemplo por uma sua; não use `12345678` como senha real.

## Integração registro manual de questões

Na página **Habilidades**, o botão **Sincronizar registro manual de questões** consulta automaticamente `GET /api/integration/answered-questions?user_id=ID` no registro manual de questões. Configure `QUESTHUB_BASE_URL`, `QUESTHUB_USER_ID` e o mesmo `QUESTHUB_INTEGRATION_TOKEN` nos dois serviços.

Endpoint alternativo de entrada: `POST /api/integration/answered-questions`

Header: `Authorization: Bearer <QUESTHUB_INTEGRATION_TOKEN>`

JSON:

```json
{"question_ids": ["id-unico-1", "id-unico-2"]}
```

O servidor guarda IDs únicos e só concede 1 SP na primeira vez que cada ID é recebido. A sincronização busca as questões objetivas e discursivas reportadas pela API do registro manual de questões. Configure os três valores de ambiente e teste no ambiente publicado para confirmar a integração de ponta a ponta. Capítulos ímpares exigem ao menos 60 segundos de treino físico registrado no dia; capítulos pares exigem uma questão única sincronizada no dia. Os capítulos são liberados em sequência por categoria.

## Como funciona o XP

- Resistência: 1 XP por segundo de treino encerrado.
- Agilidade: 1 XP por segundo de treino encerrado.
- Combate: 30 XP por minuto completo efetivamente registrado.
- O servidor calcula o tempo entre início e encerramento; não há pausa/retomada.

## Estado honesto do projeto

Este é um MVP web funcional, não uma reprodução completa da novel. O catálogo de habilidades é inicial e original, e os monstros são um conjunto inicial inspirado na imagem de referência fornecida, com nomes/estatísticas próprios. O leitor não distribui capítulos protegidos: usa texto autorizado fornecido pelo usuário e liga à fonte de leitura. Antes de uso real, teste os fluxos no Render e complete a integração registro manual de questões com o projeto correspondente.


## Registro de questões e SP
No painel, informe quantas questões você realizou. Cada grupo de 10 questões concede 1 SP; o restante é guardado para o próximo registro. Não há integração externa nem variáveis QuestHub necessárias.


## Tutor de estudos com IA

- Configure `OPENAI_API_KEY` nas variáveis de ambiente do Render para habilitar respostas. Opcional: `OPENAI_MODEL` (padrão `gpt-4o-mini`). A chave fica somente no servidor.
- O tutor libera até 40 minutos por dia após o registro de pelo menos 10 questões naquele dia. O saldo fica salvo no banco existente e pode ser pausado ao fechar a janela.
- A utilização da API é cobrada separadamente conforme a conta/provedor configurado; configure limites de gasto no painel do provedor.
- Não recrie nem apague o banco existente. A nova tabela é criada automaticamente pela inicialização da aplicação.
