import os, time, hmac, random, secrets, json
from datetime import datetime, timezone, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-only-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///necromante.db').replace('postgres://', 'postgresql://', 1)
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql://') and '+psycopg' not in app.config['SQLALCHEMY_DATABASE_URI']:
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgresql://', 'postgresql+psycopg://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
db = SQLAlchemy(app)

class State(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resistance_xp = db.Column(db.Integer, default=0, nullable=False)
    agility_xp = db.Column(db.Integer, default=0, nullable=False)
    combat_xp = db.Column(db.Integer, default=0, nullable=False)
    skill_points = db.Column(db.Integer, default=0, nullable=False)
    hp = db.Column(db.Integer, default=100, nullable=False)
    max_hp = db.Column(db.Integer, default=10, nullable=False)
    gold = db.Column(db.Integer, default=0, nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    last_odd_chapter = db.Column(db.Integer, default=0, nullable=False)
    last_even_chapter = db.Column(db.Integer, default=0, nullable=False)
    last_odd_date = db.Column(db.String(10), default='', nullable=False)
    last_even_date = db.Column(db.String(10), default='', nullable=False)

class Training(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(20), nullable=False)
    started_at = db.Column(db.Float, nullable=False)
    planned_seconds = db.Column(db.Integer, nullable=False)
    ended_at = db.Column(db.Float)
    awarded_xp = db.Column(db.Integer, default=0, nullable=False)

class OwnedSkill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    skill_key = db.Column(db.String(80), unique=True, nullable=False)
    bought_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_key = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)

class QuestionProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_questions = db.Column(db.Integer, default=0, nullable=False)
    remainder = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class QuestionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class DungeonRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    run_date = db.Column(db.String(10), nullable=False, index=True)
    dungeon_level = db.Column(db.Integer, nullable=False)
    floor = db.Column(db.Integer, default=1, nullable=False)
    enemies_left = db.Column(db.Text, default='[]', nullable=False)
    current_enemy = db.Column(db.Text, default='{}', nullable=False)
    player_hp = db.Column(db.Integer, nullable=False)
    enemy_hp = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False)
    log = db.Column(db.Text, default='[]', nullable=False)

class TutorAccess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    access_date = db.Column(db.String(10), unique=True, nullable=False)
    remaining_seconds = db.Column(db.Integer, default=2400, nullable=False)
    active_since = db.Column(db.Float)

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    unlocked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

SKILLS = [
 {'key':'shadow_step','name':'Passo Sombrio','cost':3,'type':'Defesa','desc':'Uma vez por combate, reduz em 25% o dano do primeiro golpe recebido.'},
 {'key':'soul_bolt','name':'Projétil de Alma','cost':4,'type':'Ataque mágico','desc':'Há 35% de chance por turno de lançar energia espiritual e causar dano extra.'},
 {'key':'grave_guard','name':'Guardião da Cripta','cost':5,'type':'Invocação','desc':'Um guardião espectral reduz o dano do primeiro ataque recebido em 50%.'},
 {'key':'life_drain','name':'Dreno Vital','cost':6,'type':'Ataque mágico','desc':'Há 25% de chance de causar dano adicional e recuperar parte da vida.'},
 {'key':'mana_sense','name':'Percepção de Mana','cost':2,'type':'Passiva','desc':'Permite observar os atributos e a característica do monstro antes da luta.'},
 {'key':'soul_armory','name':'Fortuna da Cripta','cost':7,'type':'Passiva','desc':'Aumenta a chance de encontrar um Fragmento de Alma após a vitória.'},
 {'key':'undead_bond','name':'Vínculo dos Mortos','cost':8,'type':'Invocação','desc':'A energia dos aliados espectrais reduz levemente os ataques inimigos.'},
 {'key':'last_stand','name':'Última Resistência','cost':10,'type':'Passiva','desc':'Uma vez por combate, impede que um golpe reduza sua vida abaixo de 1.'},
 {'key':'soul_burst','name':'Explosão Espiritual','cost':5,'type':'Ataque mágico','desc':'30% de chance de liberar uma explosão que causa dano adicional.'},
 {'key':'bone_prison','name':'Prisão Óssea','cost':6,'type':'Controle','desc':'25% de chance de enfraquecer o próximo ataque do inimigo.'},
 {'key':'spectral_aegis','name':'Égide Espectral','cost':7,'type':'Defesa','desc':'Reduz em 15% o dano recebido durante o combate.'},
 {'key':'curse_mark','name':'Marca da Ruína','cost':6,'type':'Maldição','desc':'A marca aumenta em 3 o dano de cada golpe causado por você.'},
 {'key':'soul_chain','name':'Corrente de Almas','cost':8,'type':'Ataque mágico','desc':'20% de chance de atingir o inimigo uma segunda vez com dano reduzido.'},
 {'key':'grave_mend','name':'Restauração Sepulcral','cost':8,'type':'Passiva','desc':'Recupera 3 HP ao final de cada turno, até o limite máximo.'},
 {'key':'wraith_form','name':'Forma Etérea','cost':7,'type':'Defesa','desc':'Há 30% de chance de evitar completamente um ataque recebido.'},
 {'key':'soul_fortress','name':'Fortaleza da Alma','cost':9,'type':'Passiva','desc':'Reduz em 3 o dano de cada ataque inimigo.'},
 {'key':'blood_pact','name':'Pacto do Crepúsculo','cost':9,'type':'Passiva','desc':'Quando sua vida cai abaixo de 40%, seus ataques causam 5 de dano adicional.'},
 {'key':'death_pulse','name':'Pulso da Morte','cost':10,'type':'Ataque mágico','desc':'Causa dano extra quando o inimigo está com menos de 30% de vida.'},
 {'key':'mana_siphon','name':'Drenagem Arcana','cost':8,'type':'Passiva','desc':'20% de chance por turno de recuperar 3 HP e acrescentar dano ao ataque.'},
 {'key':'fortune_ritual','name':'Ritual da Fortuna','cost':6,'type':'Passiva','desc':'Aumenta a chance de receber recompensas extras após vencer.'},
]
MONSTERS = [
 {'name':'Lodo Errante','tier':1,'hp':24,'atk':5,'def':0,'trait':'Regeneração lenta: recupera 2 HP a cada dois turnos.','drop':'Gelatina Sombria','chance':0.18},
 {'name':'Rato de Túnel','tier':1,'hp':27,'atk':6,'def':1,'trait':'Ágil: pode esquivar de um ataque.','drop':'Presa Rachada','chance':0.16},
 {'name':'Mariposa do Breu','tier':1,'hp':22,'atk':7,'def':0,'trait':'Pó ofuscante: seu próximo ataque pode causar menos dano.','drop':'Pó Luminoso','chance':0.15},
 {'name':'Gato Espectral','tier':2,'hp':42,'atk':9,'def':2,'trait':'Caçador: causa dano extra quando está com pouca vida.','drop':'Bigode Etéreo','chance':0.14},
 {'name':'Carapaça Oca','tier':2,'hp':50,'atk':8,'def':4,'trait':'Armadura: reduz parte de cada golpe recebido.','drop':'Placa Oca','chance':0.16},
 {'name':'Esqueleto Errante','tier':2,'hp':45,'atk':10,'def':1,'trait':'Persistente: o primeiro golpe recebido é reduzido.','drop':'Osso Antigo','chance':0.13},
 {'name':'Serpente de Cinzas','tier':3,'hp':72,'atk':13,'def':3,'trait':'Veneno arcano: dano leve adicional no turno seguinte.','drop':'Escama Cinzenta','chance':0.12},
 {'name':'Caranguejo de Ruína','tier':3,'hp':88,'atk':11,'def':6,'trait':'Pinças defensivas: alterna entre atacar e se proteger.','drop':'Quitina de Ruína','chance':0.13},
 {'name':'Cavaleiro Afogado','tier':4,'hp':125,'atk':17,'def':5,'trait':'Desafio: fica mais forte após perder metade da vida.','drop':'Insígnia Encharcada','chance':0.10},
 {'name':'Grifo do Subsolo','tier':4,'hp':112,'atk':20,'def':3,'trait':'Mergulho: a cada três turnos executa um ataque forte.','drop':'Pena Sombria','chance':0.09},
 {'name':'Colosso da Fenda','tier':5,'hp':190,'atk':25,'def':8,'trait':'Abalo: ataques pesados a cada dois turnos.','drop':'Núcleo da Fenda','chance':0.07},
]
ITEMS = [
 {'key':'small_potion','name':'Poção de Vida','cost':3,'desc':'Consumível: recupera 30 HP, sem ultrapassar sua vida máxima.','kind':'consumable','heal':30},
 {'key':'greater_potion','name':'Poção Vital Maior','cost':7,'desc':'Consumível: recupera 65 HP, sem ultrapassar sua vida máxima.','kind':'consumable','heal':65},
 {'key':'soul_tonic','name':'Tônico de Alma','cost':6,'desc':'Consumível: restaura 15 HP e concede 2 de ouro ao encontrar um monstro derrotado.','kind':'consumable','heal':15},
 {'key':'soul_shard','name':'Fragmento de Alma','cost':5,'desc':'Cristal raro de energia espiritual; também pode aparecer como recompensa.','kind':'material'},
 {'key':'shadow_cloak','name':'Manto de Sombra','cost':8,'desc':'Relíquia equipada: reduz em 2 o dano recebido em combate.','kind':'equipment'},
 {'key':'crypt_amulet','name':'Amuleto da Cripta','cost':10,'desc':'Relíquia equipada: reduz em 3 o dano recebido em combate.','kind':'equipment'},
 {'key':'regen_ring','name':'Anel da Regeneração','cost':12,'desc':'Relíquia equipada: recupera 2 HP ao final de cada turno.','kind':'equipment'},
 {'key':'guardian_seal','name':'Selo Guardião','cost':9,'desc':'Relíquia equipada: reduz em 40% o primeiro golpe recebido em cada combate.','kind':'equipment'},
 {'key':'fortune_charm','name':'Talismã da Fortuna','cost':10,'desc':'Relíquia equipada: aumenta a chance de encontrar recompensas extras.','kind':'equipment'},
 {'key':'mana_crystal','name':'Cristal de Mana','cost':8,'desc':'Cristal raro que pode ser encontrado após combates difíceis.','kind':'material'},
 {'key':'ash_scale','name':'Escama de Cinzas','cost':4,'desc':'Material deixado por criaturas arcanas; guardado no inventário.','kind':'material'},
 {'key':'rift_core','name':'Núcleo da Fenda','cost':15,'desc':'Material raro de monstros poderosos; guardado no inventário.','kind':'material'},
]
RANKS = ['F', 'E', 'D', 'C', 'B', 'A', 'S']
def rank_index(xp):
    # XP thresholds are cumulative: 90, then +180, +360, +720, ...
    total = 0
    for i, cost in enumerate([90, 180, 360, 720, 1440, 2880]):
        total += cost
        if xp < total:
            return i
    return 6

def apply_derived_stats(s):
    # Base stats are deliberately weak; each rank advancement adds its attribute bonus.
    resistance_steps = rank_index(s.resistance_xp)
    s.max_hp = 10 + 15 * resistance_steps
    if s.hp > s.max_hp or s.hp <= 0:
        s.hp = s.max_hp
    return s

def player_level(s):
    return max(rank_index(s.combat_xp), rank_index(s.agility_xp), rank_index(s.resistance_xp)) + 1

def player_damage(s):
    return 1 + 2 * rank_index(s.combat_xp)

def player_dodge(s):
    return min(1.0, 0.05 * rank_index(s.agility_xp))

def json_list(value):
    try: return json.loads(value or '[]')
    except (TypeError, ValueError): return []

def make_enemy(level, boss=False):
    template = random.choice([m for m in MONSTERS if m['tier'] == min(5, max(1, level))])
    scale = max(1, level)
    return {'name': ('Boss: ' if boss else '') + template['name'], 'level': level,
            'hp': max(5, int(template['hp'] * (0.45 + 0.18 * (scale-1)) * (2.2 if boss else 1))),
            'atk': max(1, int(template['atk'] * (0.55 + 0.18 * (scale-1)) * (1.4 if boss else 1))),
            'def': max(0, int(template['def'] * (0.4 + 0.16 * (scale-1)))),
            'trait': template['trait'], 'drop': template['drop'], 'chance': template['chance'], 'boss': boss}

def get_state():
    s = db.session.get(State, 1)
    if not s:
        s = State(id=1, hp=10, max_hp=10); db.session.add(s); db.session.commit()
    apply_derived_stats(s)
    return s

def login_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if not session.get('authenticated'): return redirect(url_for('login', next=request.path))
        return fn(*a, **kw)
    return wrapped

@app.before_request
def ensure_configured():
    if request.endpoint not in ('login','static','health') and not os.getenv('SITE_PASSWORD'):
        return 'Configuração incompleta: defina SITE_PASSWORD nas variáveis de ambiente.', 503

@app.after_request
def security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    resp.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:;"
    return resp

@app.route('/health')
def health(): return {'status':'ok'}

@app.route('/login', methods=['GET','POST'])
def login():
    configured_password = os.getenv('SITE_PASSWORD', '')
    if len(configured_password) != 8 or not configured_password.isdigit(): return render_template('login.html', setup_error=True), 503
    now = time.time(); attempts = session.get('login_attempts', [])
    attempts = [t for t in attempts if now-t < 600]
    error = None
    if request.method == 'POST':
        if len(attempts) >= 8:
            error = 'Muitas tentativas. Aguarde alguns minutos.'
        else:
            candidate = request.form.get('password','')
            attempts.append(now); session['login_attempts'] = attempts
            if len(candidate)==8 and candidate.isdigit() and hmac.compare_digest(candidate, os.environ['SITE_PASSWORD']):
                session.clear(); session['authenticated'] = True; session.permanent = True
                app.permanent_session_lifetime = 60*60*24*14
                return redirect(url_for('dashboard'))
            error = 'Senha incorreta.'
    return render_template('login.html', error=error, setup_error=False)

@app.route('/logout', methods=['POST'])
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    s=get_state(); skills={x.skill_key for x in OwnedSkill.query.all()}
    recent=Training.query.order_by(Training.id.desc()).limit(5).all()
    return render_template('dashboard.html', s=s, skills=skills, recent=recent, total_questions=(db.session.get(QuestionProgress, 1).total_questions if db.session.get(QuestionProgress, 1) else 0), question_remainder=(db.session.get(QuestionProgress, 1).remainder if db.session.get(QuestionProgress, 1) else 0), chapters=Chapter.query.order_by(Chapter.number).all())

@app.route('/tutor')
@login_required
def tutor_page():
    today = date.today().isoformat()
    access = TutorAccess.query.filter_by(access_date=today).first()
    remaining = access.remaining_seconds if access else 2400
    if access and access.active_since:
        remaining = max(0, remaining - int(time.time() - access.active_since))
    start_of_day_dt = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    questions_today = sum(x.count for x in QuestionLog.query.filter(QuestionLog.created_at >= start_of_day_dt).all())
    return render_template('tutor.html', remaining=max(0, remaining), questions_today=questions_today, api_configured=bool(os.getenv('OPENAI_API_KEY')))

@app.post('/api/tutor/open')
@login_required
def tutor_open():
    today = date.today().isoformat()
    start_of_day_dt = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    questions_today = sum(x.count for x in QuestionLog.query.filter(QuestionLog.created_at >= start_of_day_dt).all())
    if questions_today < 10:
        return jsonify(error=f'Registre pelo menos 10 questões hoje para liberar o tutor. Você registrou {questions_today}/10.'), 403
    access = TutorAccess.query.filter_by(access_date=today).first()
    if access is None:
        access = TutorAccess(access_date=today, remaining_seconds=2400)
        db.session.add(access)
    if access.active_since is None and access.remaining_seconds > 0:
        access.active_since = time.time()
    db.session.commit()
    return jsonify(ok=True, remaining=max(0, access.remaining_seconds - int(time.time() - access.active_since)) if access.active_since else 0)

@app.post('/api/tutor/heartbeat')
@login_required
def tutor_heartbeat():
    access = TutorAccess.query.filter_by(access_date=date.today().isoformat()).first()
    if not access or not access.active_since:
        return jsonify(error='Sessão do tutor não está ativa.', remaining=access.remaining_seconds if access else 0), 400
    elapsed = max(0, int(time.time() - access.active_since))
    access.remaining_seconds = max(0, access.remaining_seconds - elapsed)
    access.active_since = time.time() if access.remaining_seconds > 0 else None
    db.session.commit()
    return jsonify(ok=True, remaining=access.remaining_seconds)

@app.post('/api/tutor/close')
@login_required
def tutor_close():
    access = TutorAccess.query.filter_by(access_date=date.today().isoformat()).first()
    if access and access.active_since:
        access.remaining_seconds = max(0, access.remaining_seconds - max(0, int(time.time() - access.active_since)))
        access.active_since = None
        db.session.commit()
    return jsonify(ok=True, remaining=access.remaining_seconds if access else 0)

@app.post('/api/tutor/chat')
@login_required
def tutor_chat():
    api_key = os.getenv('OPENAI_API_KEY', '')
    if not api_key:
        return jsonify(error='Tutor ainda não configurado: adicione OPENAI_API_KEY nas variáveis de ambiente do Render.'), 503
    access = TutorAccess.query.filter_by(access_date=date.today().isoformat()).first()
    if not access or not access.active_since or access.remaining_seconds <= 0 or time.time() - access.active_since >= access.remaining_seconds:
        return jsonify(error='Seu tempo de tutor acabou ou a sessão está pausada. Reabra o tutor para continuar.', expired=True), 403
    data = request.get_json(silent=True) or {}
    message = str(data.get('message', '')).strip()
    history = data.get('history', [])
    if not message or len(message) > 5000:
        return jsonify(error='Escreva uma mensagem de até 5.000 caracteres.'), 400
    safe_history = []
    if isinstance(history, list):
        for item in history[-10:]:
            if isinstance(item, dict) and item.get('role') in ('user','assistant'):
                content = str(item.get('content',''))[:3000]
                if content: safe_history.append({'role':item['role'],'content':content})
    try:
        import requests
        response = requests.post('https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type':'application/json'},
            json={'model':os.getenv('OPENAI_MODEL','gpt-4o-mini'),'messages':[{'role':'system','content':'Você é um tutor de estudos paciente e claro, responde em português brasileiro. Explique o raciocínio passo a passo, adapte-se ao nível do estudante, faça perguntas de verificação e nunca invente fontes. Em vez de só dar respostas, ajude a compreender.'}]+safe_history+[{'role':'user','content':message}], 'max_tokens':900}, timeout=45)
        if response.status_code >= 400:
            return jsonify(error='A API de IA recusou a solicitação. Confira a chave, o modelo e o saldo da conta API.'), 502
        answer = response.json()['choices'][0]['message']['content']
        return jsonify(ok=True, answer=answer)
    except Exception:
        app.logger.exception('Tutor API error')
        return jsonify(error='Não foi possível contatar a IA agora. Tente novamente em instantes.'), 502

@app.route('/treino')
@login_required
def training_page(): return render_template('training.html', s=get_state(), history=Training.query.order_by(Training.id.desc()).limit(12).all())

@app.post('/api/training/start')
@login_required
def training_start():
    data=request.get_json(silent=True) or request.form
    kind=str(data.get('kind','')); seconds=data.get('seconds',0)
    if kind not in ('resistencia','agilidade','combate'): return jsonify(error='Tipo de treino inválido.'),400
    try: seconds=int(seconds)
    except: return jsonify(error='Duração inválida.'),400
    max_seconds=3600 if kind!='combate' else 7200
    if seconds<1 or seconds>max_seconds: return jsonify(error=f'Duração deve ser entre 1 e {max_seconds} segundos.'),400
    # Only one open session; stale sessions are safely closed by elapsed server time.
    active=Training.query.filter_by(ended_at=None).first()
    if active:
        # Recover sessions left open when the browser was closed or the timer reached zero in the background.
        if time.time() - active.started_at >= active.planned_seconds:
            elapsed=active.planned_seconds; active.ended_at=active.started_at+elapsed; active.awarded_xp=elapsed
            state=get_state()
            if active.kind=='resistencia': state.resistance_xp+=elapsed
            elif active.kind=='agilidade': state.agility_xp+=elapsed
            else: state.combat_xp+=(elapsed//60)*30
            db.session.commit()
        else:
            return jsonify(error='Já existe um treino em andamento. Encerre-o antes de iniciar outro.'),409
    t=Training(kind=kind,started_at=time.time(),planned_seconds=seconds); db.session.add(t); db.session.commit()
    return jsonify(id=t.id, started_at=t.started_at, planned_seconds=t.planned_seconds)

@app.post('/api/training/finish/<int:training_id>')
@login_required
def training_finish(training_id):
    t=db.session.get(Training,training_id)
    if not t: return jsonify(error='Treino não encontrado.'),404
    if t.ended_at is not None: return jsonify(error='Treino já encerrado.',xp=t.awarded_xp),409
    elapsed=max(0,min(t.planned_seconds,int(time.time()-t.started_at)))
    # If called after the planned end, award the planned duration. If ended early, award elapsed seconds.
    t.ended_at=time.time(); t.awarded_xp=elapsed
    s=get_state()
    if t.kind=='resistencia': s.resistance_xp+=elapsed
    elif t.kind=='agilidade': s.agility_xp+=elapsed
    else: s.combat_xp+=(elapsed//60)*30
    apply_derived_stats(s)
    db.session.commit()
    gained = t.awarded_xp if t.kind in ('resistencia','agilidade') else (t.awarded_xp//60)*30
    return jsonify(xp=gained, elapsed_seconds=t.awarded_xp, awarded_to=t.kind, total=getattr(s, {'resistencia':'resistance_xp','agilidade':'agility_xp','combate':'combat_xp'}[t.kind]))

@app.route('/habilidades')
@login_required
def skills_page():
    s=get_state(); owned={x.skill_key for x in OwnedSkill.query.all()}
    return render_template('skills.html', s=s, skills=SKILLS, owned=owned)

@app.post('/api/skills/buy/<skill_key>')
@login_required
def buy_skill(skill_key):
    skill=next((x for x in SKILLS if x['key']==skill_key),None)
    if not skill: return jsonify(error='Habilidade não encontrada.'),404
    if OwnedSkill.query.filter_by(skill_key=skill_key).first(): return jsonify(error='Você já possui esta habilidade.'),409
    s=get_state()
    if s.skill_points<skill['cost']: return jsonify(error='SP insuficientes.'),400
    s.skill_points-=skill['cost']; db.session.add(OwnedSkill(skill_key=skill_key)); db.session.commit()
    return jsonify(ok=True, skill_points=s.skill_points)

@app.route('/inventario')
@login_required
def inventory_page():
    return render_template('inventory.html', items=Inventory.query.order_by(Inventory.id).all(), catalog=ITEMS, s=get_state())

@app.post('/api/items/buy/<item_key>')
@login_required
def buy_item(item_key):
    item=next((x for x in ITEMS if x['key']==item_key),None)
    if not item: return jsonify(error='Item não encontrado.'),404
    s=get_state()
    if s.gold<item['cost']: return jsonify(error='Ouro insuficiente. Ganhe ouro vencendo monstros.'),400
    s.gold-=item['cost']; owned=Inventory.query.filter_by(item_key=item_key).first()
    if owned: owned.quantity+=1
    else: db.session.add(Inventory(item_key=item_key,name=item['name'],quantity=1))
    db.session.commit(); return jsonify(ok=True,gold=s.gold)

@app.post('/api/items/use/<item_key>')
@login_required
def use_item(item_key):
    item=next((x for x in ITEMS if x['key']==item_key),None)
    if not item or item.get('kind')!='consumable': return jsonify(error='Este item não pode ser consumido.'),400
    owned=Inventory.query.filter_by(item_key=item_key).first()
    if not owned or owned.quantity<1: return jsonify(error='Você não possui esse item.'),400
    s=get_state(); before=s.hp; s.hp=min(s.max_hp,s.hp+int(item.get('heal',0))); healed=s.hp-before
    owned.quantity-=1
    if owned.quantity<=0: db.session.delete(owned)
    db.session.commit()
    return jsonify(ok=True,hp=s.hp,max_hp=s.max_hp,healed=healed,message=f'{item["name"]}: +{healed} HP.')

@app.route('/combate')
@login_required
def combat_page():
    return redirect(url_for('dungeon_page'))

@app.route('/dungeon')
@login_required
def dungeon_page():
    s=get_state(); today=date.today().isoformat()
    run=DungeonRun.query.filter_by(run_date=today).order_by(DungeonRun.id.desc()).first()
    return render_template('dungeon.html', s=s, run=run, player_level=player_level(s),
                           player_damage=player_damage(s), dodge_percent=int(player_dodge(s)*100),
                           ranks=RANKS, combat_rank=RANKS[rank_index(s.combat_xp)],
                           agility_rank=RANKS[rank_index(s.agility_xp)], resistance_rank=RANKS[rank_index(s.resistance_xp)],
                           current_enemy=(json.loads(run.current_enemy) if run else {}))

@app.post('/api/dungeon/start')
@login_required
def dungeon_start():
    today=date.today().isoformat(); s=get_state()
    existing=DungeonRun.query.filter_by(run_date=today).first()
    if existing:
        return jsonify(error='Seu ticket diário já foi usado. Você pode continuar a dungeon em andamento.' if existing.status=='active' else 'Seu ticket diário já foi usado hoje.'),409
    level=player_level(s); floors=level*3
    count=random.randint(3,7)
    enemies=[make_enemy(level if random.random()<0.7 else level+1) for _ in range(count)]
    first=enemies.pop(0)
    run=DungeonRun(run_date=today,dungeon_level=level,floor=1,enemies_left=json.dumps(enemies),current_enemy=json.dumps(first),player_hp=max(1,s.hp),enemy_hp=first['hp'],status='active',log=json.dumps([f'Dungeon nível {level}: {floors} pisos. Você entrou no piso 1.']))
    db.session.add(run); db.session.commit()
    return jsonify(ok=True, run_id=run.id, floor=run.floor, floors=floors, enemy=first, enemy_hp=run.enemy_hp, player_hp=run.player_hp, log=json_list(run.log))

@app.post('/api/dungeon/action')
@login_required
def dungeon_action():
    data=request.get_json(silent=True) or {}
    run=DungeonRun.query.filter_by(run_date=date.today().isoformat(),status='active').order_by(DungeonRun.id.desc()).first()
    if not run: return jsonify(error='Não há dungeon ativa para continuar.'),404
    s=get_state(); enemy=json.loads(run.current_enemy or '{}'); log=json_list(run.log)
    if not enemy: return jsonify(error='Estado da batalha inválido.'),409
    # One click = one full turn: player acts first unless the enemy wins priority via level/agility.
    player_first=rank_index(s.agility_xp) >= max(0, enemy['level']-player_level(s))
    def player_attack():
        nonlocal_enemy = None
        damage=max(1, player_damage(s)-int(enemy.get('def',0)))
        run.enemy_hp=max(0,run.enemy_hp-damage)
        log.append(f'Você causa {damage} de dano em {enemy["name"]}.')
    def enemy_attack():
        if run.enemy_hp<=0: return
        if random.random()<player_dodge(s):
            log.append('Você esquivou do ataque!'); return
        damage=max(1,int(enemy['atk'])+random.randint(-1,2))
        owned={x.skill_key for x in OwnedSkill.query.all()}
        if 'spectral_aegis' in owned: damage=int(damage*.85)
        if 'undead_bond' in owned: damage=max(1,damage-2)
        if Inventory.query.filter_by(item_key='shadow_cloak').first(): damage=max(1,damage-2)
        if Inventory.query.filter_by(item_key='crypt_amulet').first(): damage=max(1,damage-3)
        run.player_hp=max(0,run.player_hp-damage)
        log.append(f'{enemy["name"]} causa {damage} de dano.')
    if player_first:
        player_attack(); enemy_attack()
    else:
        enemy_attack(); player_attack()
    outcome='ongoing'
    if run.enemy_hp<=0:
        s.combat_xp += max(5, enemy['level']*12); s.gold += max(2, enemy['level']*2)
        log.append(f'{enemy["name"]} derrotado! Você ganhou XP e ouro.')
        if random.random()<float(enemy.get('chance',0.1)):
            db.session.add(Inventory(item_key='dungeon_drop_'+str(run.id)+'_'+str(random.randint(1,999999)),name=enemy['drop'],quantity=1)); log.append('Item encontrado: '+enemy['drop']+'.')
        enemies=json_list(run.enemies_left)
        floors=run.dungeon_level*3
        if enemies:
            next_enemy=enemies.pop(0); run.current_enemy=json.dumps(next_enemy); run.enemy_hp=next_enemy['hp']; run.enemies_left=json.dumps(enemies)
            log.append('Próximo monstro do piso.')
        else:
            if run.floor >= floors:
                run.status='victory'; outcome='victory'; log.append('Dungeon concluída!')
            else:
                run.floor+=1
                count=random.randint(3,7)
                new_enemies=[make_enemy(run.dungeon_level if random.random()<0.7 else run.dungeon_level+1) for _ in range(count)]
                if run.floor==floors:
                    new_enemies[-1]=make_enemy(run.dungeon_level+2, boss=True)
                next_enemy=new_enemies.pop(0); run.current_enemy=json.dumps(next_enemy); run.enemy_hp=next_enemy['hp']; run.enemies_left=json.dumps(new_enemies)
                log.append(f'Piso {run.floor}/{floors}: novos inimigos. O último piso guarda o boss.')
    if run.player_hp<=0:
        run.status='defeat'; outcome='defeat'; log.append('Você foi derrotado. A dungeon terminou.')
    s.hp=max(1,run.player_hp) if run.status!='defeat' else max(1,min(s.max_hp,run.player_hp))
    if run.status=='victory': s.hp=max(1,min(s.max_hp,run.player_hp))
    run.player_hp=s.hp
    run.log=json.dumps(log[-100:]); db.session.commit()
    return jsonify(outcome=outcome, floor=run.floor, floors=run.dungeon_level*3, enemy=json.loads(run.current_enemy or '{}'), enemy_hp=run.enemy_hp, player_hp=run.player_hp, max_hp=s.max_hp, log=log[-12:], status=run.status, level=run.dungeon_level)

@app.route('/historia')
@login_required
def story_page():
    return render_template('story.html', chapters=Chapter.query.order_by(Chapter.number).all(), s=get_state())

@app.post('/api/chapter/unlock')
@login_required
def unlock_chapter():
    data=request.get_json(silent=True) or {}
    try: number=int(data.get('number',0))
    except: return jsonify(error='Número inválido.'),400
    if number<1 or number>9999: return jsonify(error='Número de capítulo inválido.'),400
    s=get_state(); today=date.today().isoformat(); odd=number%2==1
    last_num=s.last_odd_chapter if odd else s.last_even_chapter; last_date=s.last_odd_date if odd else s.last_even_date
    if Chapter.query.filter_by(number=number).first(): return jsonify(error='Este capítulo já está desbloqueado.'),409
    if last_date==today: return jsonify(error='Você já desbloqueou um capítulo desta categoria hoje.'),409
    expected = (last_num + 2) if last_num else (1 if odd else 2)
    if number != expected: return jsonify(error=f'O próximo capítulo desta categoria é o {expected}.'),400
    if odd:
        start_of_day = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc).timestamp()
        seconds_today = db.session.query(func.coalesce(func.sum(Training.awarded_xp), 0)).filter(Training.kind.in_(['resistencia','agilidade']), Training.ended_at.isnot(None), Training.started_at >= start_of_day).scalar() or 0
        if seconds_today < 60: return jsonify(error='Para capítulo ímpar, registre ao menos 60 segundos de treino físico hoje.'),400
    else:
        start_of_day_dt = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
        if QuestionLog.query.filter(QuestionLog.created_at >= start_of_day_dt, QuestionLog.count > 0).count()<1: return jsonify(error='Para capítulo par, registre ao menos uma questão estudada hoje.'),400
    db.session.add(Chapter(number=number))
    if odd: s.last_odd_chapter=number; s.last_odd_date=today
    else: s.last_even_chapter=number; s.last_even_date=today
    db.session.commit(); return jsonify(ok=True)

@app.post('/api/questions/add')
@login_required
def add_questions():
    data = request.get_json(silent=True) or request.form
    try:
        count = int(data.get('count', 0))
    except (TypeError, ValueError):
        return jsonify(error='Informe um número inteiro de questões.'), 400
    if count < 1 or count > 10000:
        return jsonify(error='Registre entre 1 e 10.000 questões por vez.'), 400
    progress = db.session.get(QuestionProgress, 1)
    if progress is None:
        progress = QuestionProgress(id=1, total_questions=0, remainder=0)
        db.session.add(progress)
        db.session.flush()
    accumulated = progress.remainder + count
    earned = accumulated // 10
    progress.remainder = accumulated % 10
    progress.total_questions += count
    progress.updated_at = datetime.now(timezone.utc)
    state = get_state()
    state.skill_points += earned
    db.session.add(QuestionLog(count=count))
    db.session.commit()
    return jsonify(ok=True, added=count, total_questions=progress.total_questions,
                   remainder=progress.remainder, sp_earned=earned,
                   skill_points=state.skill_points,
                   message=f'{count} questões registradas; +{earned} SP. {progress.remainder}/10 para o próximo SP.')

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback(); return render_template('error.html', message='Ocorreu um erro interno. Seus dados foram protegidos; tente novamente.'),500

with app.app_context():
    db.create_all()
    get_state()

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.getenv('PORT','5000')), debug=False)
