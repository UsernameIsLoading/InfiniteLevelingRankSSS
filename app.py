import os, time, hmac, random, secrets
from datetime import datetime, timezone, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import requests

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
    max_hp = db.Column(db.Integer, default=100, nullable=False)
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

class SeenQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.String(160), unique=True, nullable=False)
    seen_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    unlocked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

SKILLS = [
 {'key':'shadow_step','name':'Passo Sombrio','cost':3,'type':'utility','desc':'Uma vez por combate, reduz em 25% o dano do próximo golpe recebido.'},
 {'key':'soul_bolt','name':'Projétil de Alma','cost':4,'type':'attack','desc':'Ataque mágico que causa dano extra baseado no nível.'},
 {'key':'grave_guard','name':'Guardião da Cripta','cost':5,'type':'summon','desc':'Invoca um guardião por um turno para absorver parte do dano.'},
 {'key':'life_drain','name':'Dreno Vital','cost':6,'type':'attack','desc':'Causa dano e recupera parte do dano causado como vida.'},
 {'key':'mana_sense','name':'Percepção de Mana','cost':2,'type':'passive','desc':'Revela informações adicionais sobre o inimigo antes do combate.'},
 {'key':'soul_armory','name':'Arsenal de Almas','cost':7,'type':'passive','desc':'Aumenta a chance de encontrar itens após vencer um monstro.'},
 {'key':'undead_bond','name':'Vínculo dos Mortos','cost':8,'type':'summon','desc':'Fortalece seus aliados invocados durante um combate.'},
 {'key':'last_stand','name':'Última Resistência','cost':10,'type':'passive','desc':'Uma vez por combate, evita ser derrotado por um único golpe.'},
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
 {'key':'small_potion','name':'Poção de Vida','cost':3,'desc':'Recupera 30 HP durante a preparação do combate.'},
 {'key':'soul_shard','name':'Fragmento de Alma','cost':5,'desc':'Fragmento raro encontrado após algumas vitórias.'},
 {'key':'shadow_cloak','name':'Manto de Sombra','cost':8,'desc':'Item equipável que concede +2 de defesa em combate.'},
]
def get_state():
    s = db.session.get(State, 1)
    if not s:
        s = State(id=1); db.session.add(s); db.session.commit()
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
    return render_template('dashboard.html', s=s, skills=skills, recent=recent, total_questions=SeenQuestion.query.count(), chapters=Chapter.query.order_by(Chapter.number).all())

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

@app.route('/combate')
@login_required
def combat_page():
    return render_template('combat.html', s=get_state(), monsters=MONSTERS, skills=SKILLS, owned={x.skill_key for x in OwnedSkill.query.all()})

@app.post('/api/combat/resolve')
@login_required
def combat_resolve():
    data=request.get_json(silent=True) or {}
    try: idx=int(data.get('monster',0)); tier=int(data.get('tier',1))
    except: return jsonify(error='Escolha inválida.'),400
    candidates=[m for m in MONSTERS if m['tier']==tier]
    if not candidates: return jsonify(error='Não há monstros neste nível.'),400
    m=candidates[idx % len(candidates)]
    s=get_state(); owned={x.skill_key for x in OwnedSkill.query.all()}
    maxhp=s.max_hp; playerhp=max(1,min(s.hp,maxhp)); monsterhp=m['hp']; log=[]; turn=0; bonus_def=2 if Inventory.query.filter_by(item_key='shadow_cloak').first() else 0
    while playerhp>0 and monsterhp>0 and turn<20:
        turn+=1
        base=random.randint(7,13)+min(10,(s.combat_xp//300))
        if 'soul_bolt' in owned and random.random()<0.35: base+=random.randint(5,12); log.append(f'Turno {turn}: Projétil de Alma atinge o inimigo.')
        if 'life_drain' in owned and random.random()<0.25:
            drain=random.randint(4,10); base+=drain; playerhp=min(maxhp,playerhp+drain//2); log.append(f'Turno {turn}: Dreno Vital recupera vida.')
        damage=max(1,base-m['def']); monsterhp-=damage; log.append(f'Você causa {damage} de dano.')
        if monsterhp<=0: break
        enemy=random.randint(max(1,m['atk']-3),m['atk']+3)
        if 'shadow_step' in owned and turn==1: enemy=int(enemy*.75); log.append('Passo Sombrio reduz o primeiro golpe.')
        if 'grave_guard' in owned and turn==1: enemy=max(1,enemy//2); log.append('Guardião da Cripta absorve parte do ataque.')
        enemy=max(1,enemy-bonus_def); playerhp-=enemy; log.append(f'{m["name"]} causa {enemy} de dano.')
    victory=monsterhp<=0
    if victory:
        s.combat_xp+=m['tier']*12; s.gold+=m['tier']*2+random.randint(1,4)
        if random.random()<m['chance']:
            db.session.add(Inventory(item_key='drop_'+m['name'].lower().replace(' ','_'),name=m['drop'],quantity=1)); log.append('Item raro obtido: '+m['drop']+'.')
        if 'soul_armory' in owned and random.random()<0.15: db.session.add(Inventory(item_key='soul_shard',name='Fragmento de Alma',quantity=1)); log.append('Arsenal de Almas: você encontrou um Fragmento de Alma.')
        s.hp=max(1,min(maxhp,playerhp+8)); outcome='vitória'
    else:
        s.hp=max(1,playerhp); outcome='derrota'; s.gold=max(0,s.gold-1)
    db.session.commit()
    return jsonify(outcome=outcome, monster=m['name'], monster_hp=max(0,monsterhp), player_hp=s.hp, max_hp=s.max_hp, xp=s.combat_xp, gold=s.gold, log=log)

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
        if SeenQuestion.query.filter(SeenQuestion.seen_at >= start_of_day_dt).count()<1: return jsonify(error='Para capítulo par, responda ao menos uma questão hoje no QuestHub e sincronize.'),400
    db.session.add(Chapter(number=number))
    if odd: s.last_odd_chapter=number; s.last_odd_date=today
    else: s.last_even_chapter=number; s.last_even_date=today
    db.session.commit(); return jsonify(ok=True)

@app.post('/api/integration/sync')
@login_required
def sync_questhub():
    base=os.getenv('QUESTHUB_BASE_URL','').strip().rstrip('/')
    token=os.getenv('QUESTHUB_INTEGRATION_TOKEN','').strip()
    user_id=os.getenv('QUESTHUB_USER_ID','').strip()
    if not base or not token or not user_id:
        return jsonify(error='Configure QUESTHUB_BASE_URL, QUESTHUB_USER_ID e QUESTHUB_INTEGRATION_TOKEN no Render.'),503
    try:
        response=requests.get(base+'/api/integration/answered-questions',params={'user_id':user_id},headers={'Authorization':'Bearer '+token},timeout=12)
        if response.status_code != 200:
            return jsonify(error=f'QuestHub respondeu com status {response.status_code}. Confira URL, ID e token.'),502
        payload=response.json()
        questions=payload.get('questions',[])
        if not isinstance(questions,list): return jsonify(error='Resposta do QuestHub em formato inesperado.'),502
        added=0; s=get_state()
        for item in questions[:5000]:
            qid=str(item.get('question_id','')).strip()[:160]
            if not qid or SeenQuestion.query.filter_by(question_id=qid).first(): continue
            stamp=None
            raw_stamp=item.get('answered_at')
            if raw_stamp:
                try: stamp=datetime.fromisoformat(str(raw_stamp).replace('Z','+00:00'))
                except ValueError: stamp=None
            if stamp is None: stamp=datetime.now(timezone.utc)
            elif stamp.tzinfo is None: stamp=stamp.replace(tzinfo=timezone.utc)
            db.session.add(SeenQuestion(question_id=qid,seen_at=stamp)); s.skill_points+=1; added+=1
        db.session.commit()
        return jsonify(received=len(questions),new_questions=added,skill_points=s.skill_points)
    except requests.RequestException:
        db.session.rollback()
        return jsonify(error='Não foi possível conectar ao QuestHub. Confira se o serviço está online e se a URL pública está correta.'),502


@app.post('/api/integration/answered-questions')
def integration_questions():
    token=os.getenv('QUESTHUB_INTEGRATION_TOKEN')
    if not token: return jsonify(error='Integração não configurada no servidor.'),503
    auth=request.headers.get('Authorization','')
    if not auth.startswith('Bearer ') or not hmac.compare_digest(auth[7:],token): return jsonify(error='Não autorizado.'),401
    data=request.get_json(silent=True) or {}; ids=data.get('question_ids',[])
    if not isinstance(ids,list): return jsonify(error='question_ids deve ser uma lista.'),400
    added=0; s=get_state()
    for qid in ids[:500]:
        qid=str(qid).strip()[:160]
        if qid and not SeenQuestion.query.filter_by(question_id=qid).first():
            db.session.add(SeenQuestion(question_id=qid)); s.skill_points+=1; added+=1
    db.session.commit(); return jsonify(received=len(ids),new_questions=added,skill_points=s.skill_points)

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback(); return render_template('error.html', message='Ocorreu um erro interno. Seus dados foram protegidos; tente novamente.'),500

with app.app_context():
    db.create_all()
    get_state()

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.getenv('PORT','5000')), debug=False)
