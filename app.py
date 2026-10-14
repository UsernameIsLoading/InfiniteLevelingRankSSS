import os, io, csv, json, secrets, random, html, urllib.parse, urllib.request, urllib.error
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-before-deploying-' + secrets.token_hex(8))
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
db_url = os.environ.get('DATABASE_URL', 'sqlite:///sistema_soberano.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
# The deployment requirements install psycopg 3, so select its SQLAlchemy dialect explicitly.
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

ATTRIBUTES = ['corpo', 'mente', 'disciplina', 'vitalidade', 'espirito']
ATTR_LABELS = {'corpo':'Corpo','mente':'Mente','disciplina':'Disciplina','vitalidade':'Vitalidade','espirito':'Espírito'}
ACTIVITY_TYPES = {
    'Treino de força': ('corpo', 3), 'Treino aeróbico': ('corpo', 2), 'Calistenia': ('corpo', 3),
    'Estudo': ('mente', 2), 'Leitura técnica': ('mente', 2), 'Prática de questões': ('mente', 2),
    'Tarefa importante': ('disciplina', 2), 'Rotina cumprida': ('disciplina', 2),
    'Sono/recuperação': ('vitalidade', 2), 'Desafio pessoal': ('espirito', 2)
}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    xp = db.Column(db.Integer, default=0, nullable=False)
    corpo = db.Column(db.Integer, default=5, nullable=False)
    mente = db.Column(db.Integer, default=5, nullable=False)
    disciplina = db.Column(db.Integer, default=5, nullable=False)
    vitalidade = db.Column(db.Integer, default=5, nullable=False)
    espirito = db.Column(db.Integer, default=5, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    kind = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    minutes = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, default='')
    xp = db.Column(db.Integer, default=0)
    attribute = db.Column(db.String(30), nullable=False)
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class SpecialQuest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    skill_name = db.Column(db.String(120), nullable=False)
    skill_description = db.Column(db.Text, default='')
    xp_reward = db.Column(db.Integer, default=50)
    active = db.Column(db.Boolean, default=True)

class QuestCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('special_quest.id'), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id','quest_id', name='uq_user_quest'),)

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    source = db.Column(db.String(30), default='quest')
    acquired_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(160), nullable=False)
    difficulty = db.Column(db.String(30), default='Intermediária')
    prompt = db.Column(db.Text, nullable=False)
    options_json = db.Column(db.Text, default='[]')
    answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, default='')
    source = db.Column(db.String(255), default='Original')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

class TestAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_given = db.Column(db.Text, default='')
    correct = db.Column(db.Boolean, default=False)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class PerformanceEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service = db.Column(db.String(40), nullable=False)
    test_name = db.Column(db.String(120), nullable=False)
    result = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.Text, default='')
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class DietEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    meal_type = db.Column(db.String(30), nullable=False, default='Lanche')
    food = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.String(100), default='')
    calories = db.Column(db.Float, nullable=True)
    protein_g = db.Column(db.Float, nullable=True)
    carbs_g = db.Column(db.Float, nullable=True)
    fat_g = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

class WaterEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    amount_ml = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

class TrialSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    kind = db.Column(db.String(20), nullable=False)  # baseline or weekly
    title = db.Column(db.String(120), nullable=False)
    week_start = db.Column(db.Date, nullable=True, index=True)
    snapshot_json = db.Column(db.Text, default='{}', nullable=False)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

class TrialResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('trial_session.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    category = db.Column(db.String(20), nullable=False)  # fisico or mental
    test_name = db.Column(db.String(120), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(30), default='', nullable=False)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class CampaignChapterProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    arc_key = db.Column(db.String(40), nullable=False)
    chapter_index = db.Column(db.Integer, nullable=False)
    choice = db.Column(db.String(120), nullable=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'arc_key', 'chapter_index', name='uq_campaign_chapter'),)


class NarrativeChapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_key = db.Column(db.String(100), unique=True, nullable=False)
    number = db.Column(db.Integer, nullable=False, default=1)
    title = db.Column(db.String(200), nullable=False)
    weekday = db.Column(db.String(40), default='')
    location = db.Column(db.String(200), default='')
    timeline = db.Column(db.String(200), default='')
    summary = db.Column(db.Text, default='')
    content_json = db.Column(db.Text, nullable=False)
    word_count = db.Column(db.Integer, default=0)
    decision_count = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class NarrativeChoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('narrative_chapter.id'), nullable=False, index=True)
    decision_id = db.Column(db.String(100), nullable=False)
    option_id = db.Column(db.String(100), nullable=False)
    option_label = db.Column(db.String(300), nullable=False)
    effects_json = db.Column(db.Text, default='{}', nullable=False)
    chosen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'chapter_id', 'decision_id', name='uq_narrative_decision'),)


class NarrativePlayerState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False, index=True)
    flags_json = db.Column(db.Text, default='[]', nullable=False)
    inventory_json = db.Column(db.Text, default='[]', nullable=False)
    knowledge_json = db.Column(db.Text, default='[]', nullable=False)
    relationships_json = db.Column(db.Text, default='{}', nullable=False)
    karma_signals_json = db.Column(db.Text, default='[]', nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CombatEncounter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    enemy_name = db.Column(db.String(120), nullable=False)
    enemy_kind = db.Column(db.String(30), nullable=False, default='comum')
    enemy_hp = db.Column(db.Integer, nullable=False)
    enemy_max_hp = db.Column(db.Integer, nullable=False)
    player_hp = db.Column(db.Integer, nullable=False)
    player_max_hp = db.Column(db.Integer, nullable=False)
    xp_reward = db.Column(db.Integer, nullable=False, default=20)
    status = db.Column(db.String(20), nullable=False, default='active')
    log_json = db.Column(db.Text, default='[]', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)


def local_today():
    return datetime.now(ZoneInfo('America/Sao_Paulo')).date()

def current_user():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or not user.is_admin:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def xp_to_next(level):
    return 100 + max(0, level - 1) * 25

def grant_xp(user, amount):
    user.xp += max(0, amount)
    while user.xp >= xp_to_next(user.level):
        user.xp -= xp_to_next(user.level)
        user.level += 1

def quest_requirement_met(user, quest):
    # Starter quests have real prerequisites; admin-created quests are manually verified in this MVP.
    title = quest.title.casefold()
    if title == 'o primeiro registro':
        return Activity.query.filter_by(user_id=user.id).first() is not None
    if title == 'a provação do erudito':
        return TestAttempt.query.filter_by(user_id=user.id, correct=True).first() is not None
    if title == 'mapeamento do potencial':
        return PerformanceEntry.query.filter_by(user_id=user.id).first() is not None
    return True

@app.context_processor
def inject_globals():
    u = current_user()
    return {'current_user_obj': u, 'attr_labels': ATTR_LABELS, 'xp_to_next': xp_to_next}

@app.route('/')
def index():
    if not current_user(): return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        if len(username) < 3 or len(password) < 8:
            flash('Use um usuário com pelo menos 3 caracteres e senha com pelo menos 8.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Esse nome de usuário já existe.', 'error')
        else:
            user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(user); db.session.commit()
            session['user_id'] = user.id
            flash('Vínculo estabelecido. Bem-vindo ao Sistema.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        user = User.query.filter(func.lower(User.username) == username.lower()).first()
        if user and check_password_hash(user.password_hash, request.form.get('password','')):
            session.clear(); session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash('Credenciais inválidas.', 'error')
    return render_template('auth.html', mode='login')

@app.route('/nutrition', methods=['GET', 'POST'])
@login_required
def nutrition():
    u = current_user()
    today = local_today()
    local_tz = ZoneInfo('America/Sao_Paulo')
    today_start = datetime.combine(today, datetime.min.time(), tzinfo=local_tz).astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
    tomorrow_start = today_start + timedelta(days=1)
    if request.method == 'POST':
        action = request.form.get('action', 'diet')
        if action == 'water':
            try:
                amount = int(request.form.get('amount_ml', '0'))
            except (TypeError, ValueError):
                amount = 0
            if amount < 1 or amount > 5000:
                flash('Registra uma quantidade de água entre 1 e 5000 ml por vez.', 'error')
            else:
                db.session.add(WaterEntry(user_id=u.id, amount_ml=amount))
                db.session.commit()
                flash(f'{amount} ml de água registrados.', 'success')
            return redirect(url_for('nutrition'))
        food = request.form.get('food', '').strip()[:200]
        meal_type = request.form.get('meal_type', 'Lanche').strip()[:30]
        quantity = request.form.get('quantity', '').strip()[:100]
        notes = request.form.get('notes', '').strip()[:1000]
        if not food:
            flash('Informa o alimento ou a refeição.', 'error')
            return redirect(url_for('nutrition'))
        def optional_number(field):
            raw = request.form.get(field, '').strip().replace(',', '.')
            if not raw:
                return None
            value = float(raw)
            if value < 0 or value > 100000:
                raise ValueError()
            return value
        try:
            calories = optional_number('calories')
            protein = optional_number('protein_g')
            carbs = optional_number('carbs_g')
            fat = optional_number('fat_g')
        except ValueError:
            flash('Valores nutricionais devem ser números não negativos.', 'error')
            return redirect(url_for('nutrition'))
        db.session.add(DietEntry(user_id=u.id, meal_type=meal_type, food=food, quantity=quantity,
                                 calories=calories, protein_g=protein, carbs_g=carbs, fat_g=fat, notes=notes))
        db.session.commit()
        flash('Registro alimentar salvo.', 'success')
        return redirect(url_for('nutrition'))
    water_today = WaterEntry.query.filter(WaterEntry.user_id == u.id,
        WaterEntry.created_at >= today_start, WaterEntry.created_at < tomorrow_start).order_by(WaterEntry.created_at.desc()).all()
    diet_today = DietEntry.query.filter(DietEntry.user_id == u.id,
        DietEntry.created_at >= today_start, DietEntry.created_at < tomorrow_start).order_by(DietEntry.created_at.desc()).all()
    water_total = sum(entry.amount_ml for entry in water_today)
    water_history = WaterEntry.query.filter_by(user_id=u.id).order_by(WaterEntry.created_at.desc()).limit(30).all()
    diet_history = DietEntry.query.filter_by(user_id=u.id).order_by(DietEntry.created_at.desc()).limit(50).all()
    totals = {
        'calories': sum(e.calories or 0 for e in diet_today),
        'protein': sum(e.protein_g or 0 for e in diet_today),
        'carbs': sum(e.carbs_g or 0 for e in diet_today),
        'fat': sum(e.fat_g or 0 for e in diet_today),
        'has_macros': any(e.calories is not None or e.protein_g is not None or e.carbs_g is not None or e.fat_g is not None for e in diet_today)
    }
    return render_template('nutrition.html', today=today, water_today=water_today, water_total=water_total,
                           water_history=water_history, diet_today=diet_today, diet_history=diet_history, totals=totals)

@app.route('/service-worker.js')
def service_worker():
    return send_file(os.path.join(app.static_folder, 'service-worker.js'), mimetype='application/javascript')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    u = current_user()
    activities = Activity.query.filter_by(user_id=u.id).order_by(Activity.created_at.desc()).limit(6).all()
    skills = Skill.query.filter_by(user_id=u.id).order_by(Skill.acquired_at.desc()).all()
    completed = {x.quest_id for x in QuestCompletion.query.filter_by(user_id=u.id).all()}
    quests = SpecialQuest.query.filter_by(active=True).order_by(SpecialQuest.id).all()
    return render_template('dashboard.html', user=u, activities=activities, skills=skills, quests=quests, completed=completed)

@app.route('/activities', methods=['GET','POST'])
@login_required
def activities():
    u = current_user()
    if request.method == 'POST':
        kind = request.form.get('kind','')
        title = request.form.get('title','').strip()
        try: minutes = max(0, min(1440, int(request.form.get('minutes','0'))))
        except ValueError: minutes = 0
        notes = request.form.get('notes','').strip()[:2000]
        if kind not in ACTIVITY_TYPES or not title:
            flash('Escolha uma atividade válida e informe um título.', 'error')
        else:
            attr, rate = ACTIVITY_TYPES[kind]
            # Reward by activity and duration; cap each entry to avoid runaway XP.
            duration_bonus = min(30, minutes // 15)
            xp = min(100, rate * 10 + duration_bonus)
            points = max(1, min(10, 1 + minutes // 30))
            setattr(u, attr, getattr(u, attr) + points)
            grant_xp(u, xp)
            db.session.add(Activity(user_id=u.id, kind=kind, title=title, minutes=minutes, notes=notes, xp=xp, attribute=attr, points=points))
            db.session.commit()
            flash(f'Atividade registrada: +{xp} XP e +{points} em {ATTR_LABELS[attr]}.', 'success')
            return redirect(url_for('activities'))
    history = Activity.query.filter_by(user_id=u.id).order_by(Activity.created_at.desc()).limit(100).all()
    return render_template('activities.html', kinds=ACTIVITY_TYPES, history=history)

@app.route('/quests')
@login_required
def quests():
    u=current_user(); allq=SpecialQuest.query.filter_by(active=True).order_by(SpecialQuest.id).all()
    completed={x.quest_id for x in QuestCompletion.query.filter_by(user_id=u.id).all()}
    return render_template('quests.html', quests=allq, completed=completed)

@app.route('/quests/<int:quest_id>/complete', methods=['POST'])
@login_required
def complete_quest(quest_id):
    u=current_user(); q=db.session.get(SpecialQuest,quest_id)
    if not q or not q.active: abort(404)
    if QuestCompletion.query.filter_by(user_id=u.id,quest_id=q.id).first():
        flash('Essa missão especial já foi concluída.', 'error')
    elif not quest_requirement_met(u, q):
        title = q.title.casefold()
        requirement = {'o primeiro registro':'registra uma atividade real', 'a provação do erudito':'responde corretamente a pelo menos uma questão', 'mapeamento do potencial':'registra um resultado no Laboratório de Desempenho'}.get(title, 'cumpre a condição desta missão')
        flash(f'Requisito ainda não cumprido: {requirement}.', 'error')
    else:
        db.session.add(QuestCompletion(user_id=u.id,quest_id=q.id))
        db.session.add(Skill(user_id=u.id,name=q.skill_name,description=q.skill_description,source='quest'))
        grant_xp(u,q.xp_reward)
        db.session.commit()
        flash(f'Missão concluída. Habilidade desbloqueada: {q.skill_name}.', 'success')
    return redirect(url_for('quests'))

@app.route('/library', methods=['GET','POST'])
@login_required
def library():
    u=current_user()
    if request.method == 'POST':
        subject=request.form.get('subject','').strip(); level=request.form.get('level','').strip(); topic=request.form.get('topic','').strip()
        prompt=request.form.get('prompt','').strip(); answer=request.form.get('answer','').strip(); explanation=request.form.get('explanation','').strip()
        options=[x.strip() for x in request.form.get('options','').split('\n') if x.strip()]
        difficulty=request.form.get('difficulty','Intermediária')
        if not all([subject,level,topic,prompt,answer]): flash('Preencha disciplina, nível, assunto, enunciado e resposta.', 'error')
        else:
            db.session.add(Question(subject=subject,level=level,topic=topic,prompt=prompt,answer=answer,explanation=explanation,options_json=json.dumps(options,ensure_ascii=False),difficulty=difficulty,source='Criada manualmente',created_by=u.id))
            db.session.commit(); flash('Questão adicionada à Biblioteca do Conhecimento.', 'success'); return redirect(url_for('library'))
    subject=request.args.get('subject','').strip(); level=request.args.get('level','').strip(); topic=request.args.get('topic','').strip()
    query=Question.query
    if subject: query=query.filter(Question.subject.ilike(f'%{subject}%'))
    if level: query=query.filter(Question.level.ilike(f'%{level}%'))
    if topic: query=query.filter(Question.topic.ilike(f'%{topic}%'))
    questions=query.order_by(Question.id.desc()).limit(200).all()
    return render_template('library.html', questions=questions, subjects=[r[0] for r in db.session.query(Question.subject).distinct().all()], levels=[r[0] for r in db.session.query(Question.level).distinct().all()])

@app.route('/library/<int:qid>', methods=['GET','POST'])
@login_required
def answer_question(qid):
    q=db.session.get(Question,qid)
    if not q: abort(404)
    result=None
    if request.method=='POST':
        given=request.form.get('answer','').strip()
        correct=given.casefold()==q.answer.strip().casefold()
        db.session.add(TestAttempt(user_id=current_user().id,question_id=q.id,answer_given=given,correct=correct))
        if correct: grant_xp(current_user(),5)
        db.session.commit()
        result={'correct':correct,'given':given}
    try: options=json.loads(q.options_json or '[]')
    except Exception: options=[]
    return render_template('question.html', q=q, options=options, result=result)

@app.route('/library/import', methods=['POST'])
@login_required
@admin_required
def import_questions():
    file=request.files.get('file')
    if not file or not file.filename.lower().endswith(('.csv','.json')):
        flash('Envie um arquivo CSV ou JSON.', 'error'); return redirect(url_for('library'))
    try:
        raw=file.read().decode('utf-8-sig')
        if file.filename.lower().endswith('.json'):
            records=json.loads(raw)
        else:
            records=list(csv.DictReader(io.StringIO(raw)))
        added=0
        for r in records:
            required=['subject','level','topic','prompt','answer']
            if not all(str(r.get(k,'')).strip() for k in required): continue
            options=r.get('options',[])
            if isinstance(options,str):
                try: options=json.loads(options)
                except Exception: options=[x.strip() for x in options.split('|') if x.strip()]
            db.session.add(Question(subject=str(r['subject'])[:100],level=str(r['level'])[:100],topic=str(r['topic'])[:160],prompt=str(r['prompt']),answer=str(r['answer']),explanation=str(r.get('explanation','')),difficulty=str(r.get('difficulty','Intermediária')),source=str(r.get('source','Importada'))[:255],options_json=json.dumps(options,ensure_ascii=False)))
            added+=1
        db.session.commit(); flash(f'Importação concluída: {added} questões adicionadas.', 'success')
    except Exception as e:
        db.session.rollback(); flash('Não foi possível importar. Confira o formato do arquivo.', 'error')
    return redirect(url_for('library'))

@app.route('/admin/questions/import-online', methods=['POST'])
@login_required
@admin_required
def import_online_questions():
    """Import open multiple-choice questions from the Open Trivia Database."""
    try: amount = max(1, min(20, int(request.form.get('amount', 10) or 10)))
    except (TypeError, ValueError): amount = 10
    category = request.form.get('category', 'any').strip()
    difficulty = request.form.get('online_difficulty', 'any').strip().lower()
    categories = {
        '9': ('Conhecimentos gerais', 'Conhecimentos gerais'),
        '17': ('Ciências', 'Ciências e natureza'),
        '18': ('Informática', 'Computadores'),
        '19': ('Matemática', 'Matemática'),
        '21': ('Esportes', 'Esportes'),
        '22': ('Geografia', 'Geografia'),
        '23': ('História', 'História'),
        '27': ('Biologia', 'Animais'),
    }
    if category not in {'any', *categories.keys()}:
        flash('Categoria inválida para importação online.', 'error')
        return redirect(url_for('admin'))
    if difficulty not in {'any', 'easy', 'medium', 'hard'}:
        difficulty = 'any'
    params = {'amount': amount, 'type': 'multiple'}
    if category != 'any': params['category'] = category
    if difficulty != 'any': params['difficulty'] = difficulty
    url = 'https://opentdb.com/api.php?' + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SistemaDoSoberano/0.5 (question importer)'})
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read(2 * 1024 * 1024).decode('utf-8'))
        if payload.get('response_code') != 0:
            messages = {1:'A base não encontrou questões suficientes para esses filtros.', 2:'Parâmetros de importação inválidos.', 5:'Limite temporário da fonte atingido. Aguarde alguns segundos e tente novamente.'}
            raise ValueError(messages.get(payload.get('response_code'), 'A fonte online retornou uma resposta inesperada.'))
        added = 0
        for item in payload.get('results', []):
            prompt = html.unescape(urllib.parse.unquote(item.get('question', ''))).strip()
            if not prompt or Question.query.filter_by(prompt=prompt).first():
                continue
            correct = html.unescape(urllib.parse.unquote(item.get('correct_answer', ''))).strip()
            options = [html.unescape(urllib.parse.unquote(x)).strip() for x in item.get('incorrect_answers', [])]
            options.append(correct)
            random.shuffle(options)
            raw_category = html.unescape(urllib.parse.unquote(item.get('category','Conhecimentos gerais')))
            category_map = {'General Knowledge':('Conhecimentos gerais','Conhecimentos gerais'), 'Science & Nature':('Ciências','Ciências e natureza'), 'Science: Computers':('Informática','Computadores'), 'Science: Mathematics':('Matemática','Matemática'), 'Sports':('Esportes','Esportes'), 'Geography':('Geografia','Geografia'), 'History':('História','História'), 'Animals':('Biologia','Animais')}
            subject, topic = categories.get(str(category), category_map.get(raw_category, (raw_category, raw_category)))
            api_diff = item.get('difficulty', 'medium')
            diff_label = {'easy':'Básica','medium':'Intermediária','hard':'Avançada'}.get(api_diff, 'Intermediária')
            db.session.add(Question(subject=subject, level='Geral', topic=topic[:160], difficulty=diff_label,
                prompt=prompt, options_json=json.dumps(options, ensure_ascii=False), answer=correct,
                explanation='', source='Open Trivia Database — ' + html.unescape(item.get('category','Categoria geral'))[:180]))
            added += 1
        db.session.commit()
        skipped = len(payload.get('results', [])) - added
        flash(f'Importação online concluída: {added} questões adicionadas; {skipped} duplicadas ou vazias ignoradas.', 'success' if added else 'error')
    except (urllib.error.URLError, TimeoutError) as exc:
        db.session.rollback()
        app.logger.warning('Falha ao consultar Open Trivia Database: %s', exc)
        flash('Não foi possível acessar a base de questões agora. Tente novamente mais tarde.', 'error')
    except (ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        db.session.rollback()
        flash(f'Importação online não concluída: {str(exc)[:220]}', 'error')
    except Exception:
        db.session.rollback()
        app.logger.exception('Falha inesperada ao importar questões online')
        flash('Ocorreu um erro ao salvar as questões importadas.', 'error')
    return redirect(url_for('admin'))


@app.route('/admin/questions/generate', methods=['POST'])
@login_required
@admin_required
def generate_ai_questions():
    """Generate original Portuguese multiple-choice questions using the OpenAI API."""
    api_key = os.environ.get('OPENAI_API_KEY', '').strip()
    if not api_key:
        flash('Para gerar questões com IA, configure OPENAI_API_KEY nas variáveis de ambiente da hospedagem. A importação online e CSV/JSON continuam disponíveis sem essa chave.', 'error')
        return redirect(url_for('admin'))
    subject = request.form.get('subject', 'Conhecimentos gerais').strip()[:100]
    level = request.form.get('level', 'Ensino médio').strip()[:100]
    topic = request.form.get('topic', '').strip()[:160]
    difficulty = request.form.get('difficulty', 'Intermediária').strip()[:30]
    try: count = max(1, min(10, int(request.form.get('count', 5) or 5)))
    except (TypeError, ValueError): count = 5
    if not subject or not level or not topic:
        flash('Preencha disciplina, nível e assunto para gerar questões.', 'error')
        return redirect(url_for('admin'))
    model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini').strip() or 'gpt-4o-mini'
    instructions = (
        'Crie questões originais em português brasileiro para uma biblioteca de estudos. '
        'Retorne exclusivamente um objeto JSON com a chave questions, que contém uma lista. '
        'Cada item deve conter subject, level, topic, difficulty, prompt, options (array com exatamente 4 alternativas), '
        'answer (texto idêntico a uma das alternativas), explanation (explicação curta e verificável). '
        'Evite ambiguidades, alternativas repetidas e questões que dependam de informação não fornecida. '
        'Não copie questões protegidas de provas ou sites; crie formulações originais. '
        'Revise a resposta e a explicação antes de retornar.'
    )
    request_payload = {
        'model': model,
        'response_format': {'type': 'json_object'},
        'messages': [
            {'role':'system','content':instructions},
            {'role':'user','content':f'Gere {count} questões de múltipla escolha. Disciplina: {subject}. Nível: {level}. Assunto específico: {topic}. Dificuldade: {difficulty}. Todas as questões devem ter 4 alternativas plausíveis e somente uma resposta correta.'}
        ],
        'temperature': 0.7
    }
    try:
        req = urllib.request.Request('https://api.openai.com/v1/chat/completions',
            data=json.dumps(request_payload, ensure_ascii=False).encode('utf-8'),
            headers={'Authorization':'Bearer '+api_key, 'Content-Type':'application/json', 'User-Agent':'SistemaDoSoberano/0.5'}, method='POST')
        with urllib.request.urlopen(req, timeout=60) as response:
            api_result = json.loads(response.read(3 * 1024 * 1024).decode('utf-8'))
        content = api_result['choices'][0]['message']['content']
        generated = json.loads(content).get('questions', [])
        if not isinstance(generated, list): raise ValueError('A IA retornou um formato inesperado.')
        added = 0
        for item in generated[:count]:
            if not isinstance(item, dict): continue
            q_subject = str(item.get('subject') or subject).strip()[:100]
            q_level = str(item.get('level') or level).strip()[:100]
            q_topic = str(item.get('topic') or topic).strip()[:160]
            prompt = str(item.get('prompt') or '').strip()
            answer = str(item.get('answer') or '').strip()
            explanation = str(item.get('explanation') or '').strip()
            options = item.get('options', [])
            if not isinstance(options, list): continue
            options = [str(o).strip() for o in options if str(o).strip()]
            if not q_subject or not q_level or not q_topic or not prompt or not answer or len(options) != 4 or answer not in options:
                continue
            if Question.query.filter_by(prompt=prompt).first(): continue
            db.session.add(Question(subject=q_subject, level=q_level, topic=q_topic,
                difficulty=str(item.get('difficulty') or difficulty)[:30], prompt=prompt,
                options_json=json.dumps(options, ensure_ascii=False), answer=answer, explanation=explanation,
                source=f'Gerada por IA ({model}) — revisar antes de usar'))
            added += 1
        if added == 0:
            db.session.rollback()
            flash('A IA não retornou questões válidas. Tente outro assunto ou ajuste os parâmetros.', 'error')
        else:
            db.session.commit()
            flash(f'{added} questões geradas e adicionadas à biblioteca. Revise as respostas antes de usá-las em provas ou missões.', 'success')
    except urllib.error.HTTPError as exc:
        db.session.rollback()
        detail = ''
        try: detail = exc.read(1000).decode('utf-8', errors='replace')
        except Exception: pass
        app.logger.warning('OpenAI API respondeu HTTP %s: %s', exc.code, detail[:500])
        flash(f'A API de IA retornou erro HTTP {exc.code}. Verifique a chave, os créditos e o modelo configurado.', 'error')
    except (urllib.error.URLError, TimeoutError) as exc:
        db.session.rollback()
        app.logger.warning('Falha de conexão com a API de IA: %s', exc)
        flash('Não foi possível conectar à API de IA agora. Tente novamente mais tarde.', 'error')
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        db.session.rollback()
        app.logger.exception('Resposta inválida ao gerar questões')
        flash('A resposta da IA não pôde ser validada como questões. Nenhum item inválido foi salvo.', 'error')
    except Exception:
        db.session.rollback()
        app.logger.exception('Falha inesperada ao gerar questões')
        flash('Ocorreu um erro ao gerar ou salvar questões.', 'error')
    return redirect(url_for('admin'))


@app.route('/library/<int:qid>/edit', methods=['GET','POST'])
@login_required
@admin_required
def edit_question(qid):
    q = db.session.get(Question, qid)
    if not q: abort(404)
    if request.method == 'POST':
        subject=request.form.get('subject','').strip(); level=request.form.get('level','').strip()
        topic=request.form.get('topic','').strip(); prompt=request.form.get('prompt','').strip()
        answer=request.form.get('answer','').strip(); explanation=request.form.get('explanation','').strip()
        difficulty=request.form.get('difficulty','Intermediária').strip()
        options=[x.strip() for x in request.form.get('options','').splitlines() if x.strip()]
        source=request.form.get('source', q.source or 'Editada manualmente').strip()[:255]
        if not all([subject, level, topic, prompt, answer]):
            flash('Disciplina, nível, assunto, enunciado e resposta são obrigatórios.', 'error')
        elif options and answer not in options:
            flash('A resposta correta precisa corresponder exatamente a uma das alternativas.', 'error')
        else:
            q.subject=subject[:100]; q.level=level[:100]; q.topic=topic[:160]; q.prompt=prompt
            q.answer=answer; q.explanation=explanation; q.difficulty=difficulty[:30]
            q.options_json=json.dumps(options, ensure_ascii=False); q.source=source or 'Editada manualmente'
            db.session.commit(); flash('Questão atualizada.', 'success')
            return redirect(url_for('answer_question', qid=q.id))
    try: options=json.loads(q.options_json or '[]')
    except Exception: options=[]
    return render_template('question_edit.html', q=q, options=options)


@app.route('/library/<int:qid>/delete', methods=['POST'])
@login_required
@admin_required
def delete_question(qid):
    q=db.session.get(Question, qid)
    if not q: abort(404)
    TestAttempt.query.filter_by(question_id=q.id).delete(synchronize_session=False)
    db.session.delete(q); db.session.commit()
    flash('Questão removida da biblioteca.', 'success')
    return redirect(url_for('library'))


@app.route('/performance', methods=['GET','POST'])
@login_required
def performance():
    u=current_user()
    if request.method=='POST':
        service=request.form.get('service',''); test_name=request.form.get('test_name','').strip(); result=request.form.get('result','').strip(); notes=request.form.get('notes','').strip()
        if service not in ['Strength Level','Human Benchmark'] or not test_name or not result:
            flash('Preencha serviço, teste e resultado.', 'error')
        else:
            db.session.add(PerformanceEntry(user_id=u.id,service=service,test_name=test_name,result=result,notes=notes[:2000])); db.session.commit()
            flash('Resultado registrado no histórico.', 'success'); return redirect(url_for('performance'))
    entries=PerformanceEntry.query.filter_by(user_id=u.id).order_by(PerformanceEntry.recorded_at.desc()).limit(100).all()
    return render_template('performance.html', entries=entries)

@app.route('/trial', methods=['GET', 'POST'])
@login_required
def trial():
    u = current_user()
    today = local_today()
    monday = today - timedelta(days=today.weekday())
    kind = request.args.get('kind', 'baseline').strip().lower()
    if kind not in ('baseline', 'weekly'):
        kind = 'baseline'
    baseline_exists = TrialSession.query.filter_by(user_id=u.id, kind='baseline').first() is not None
    current_week_session = TrialSession.query.filter_by(user_id=u.id, kind='weekly', week_start=monday).first()
    if kind == 'baseline' and baseline_exists:
        flash('A Provação de Fundação já foi registrada. Podes consultar o histórico ou registrar a avaliação semanal.', 'success')
        return redirect(url_for('trial', kind='weekly'))
    if kind == 'weekly' and current_week_session:
        flash('A avaliação desta semana já foi registrada. Os resultados estão no histórico.', 'success')
        return redirect(url_for('evolution'))
    if request.method == 'POST':
        if kind == 'weekly' and today.weekday() != 6:
            flash('O Dia da Provação semanal acontece no domingo. A Provação de Fundação pode ser feita agora.', 'error')
            return redirect(url_for('trial', kind='weekly'))
        notes = request.form.get('session_notes', '').strip()[:2000]
        names = request.form.getlist('test_name[]')
        categories = request.form.getlist('category[]')
        values = request.form.getlist('value[]')
        units = request.form.getlist('unit[]')
        result_notes = request.form.getlist('result_notes[]')
        prepared = []
        errors = []
        for i, raw_name in enumerate(names):
            name = raw_name.strip()[:120]
            raw_value = values[i].strip() if i < len(values) else ''
            if not raw_value:
                continue
            category = categories[i] if i < len(categories) else ''
            unit = units[i].strip()[:30] if i < len(units) else ''
            detail = result_notes[i].strip()[:500] if i < len(result_notes) else ''
            if category not in ('fisico', 'mental') or not name or not raw_value:
                errors.append('Cada resultado preenchido precisa de categoria, nome do teste e valor.')
                break
            try:
                value = float(raw_value.replace(',', '.'))
                if value < 0 or value > 100000000:
                    raise ValueError()
            except ValueError:
                errors.append('Usa valores numéricos não negativos. Para tempo de reação, registra em milissegundos.')
                break
            prepared.append((category, name, value, unit, detail))
        if not errors and not prepared:
            errors.append('Registra pelo menos um resultado para salvar a provação.')
        if not errors and prepared and not {'fisico', 'mental'}.issubset({item[0] for item in prepared}):
            errors.append('A provação precisa de pelo menos um resultado físico e um resultado mental.')
        if errors:
            for err in errors: flash(err, 'error')
        else:
            snapshot = {key: getattr(u, key) for key in ATTRIBUTES}
            snapshot.update({'level': u.level, 'xp': u.xp, 'recorded_on': today.isoformat()})
            title = 'Provação de Fundação' if kind == 'baseline' else 'Dia da Provação'
            sess = TrialSession(user_id=u.id, kind=kind, title=title, week_start=None if kind == 'baseline' else monday,
                                snapshot_json=json.dumps(snapshot, ensure_ascii=False), notes=notes)
            db.session.add(sess)
            db.session.flush()
            for category, name, value, unit, detail in prepared:
                db.session.add(TrialResult(session_id=sess.id, user_id=u.id, category=category,
                                           test_name=name, value=value, unit=unit, notes=detail))
            db.session.commit()
            flash(f'{title} registrada. Foram salvos {len(prepared)} resultados e uma fotografia dos teus atributos.', 'success')
            return redirect(url_for('evolution'))
    suggested = [
        {'category':'fisico','name':'Flexões válidas','unit':'repetições'},
        {'category':'fisico','name':'Barra fixa válida','unit':'repetições'},
        {'category':'fisico','name':'Prancha','unit':'segundos'},
        {'category':'fisico','name':'Exercício com carga','unit':'kg'},
        {'category':'mental','name':'Tempo de reação','unit':'ms'},
        {'category':'mental','name':'Teste de memória','unit':'pontos'},
        {'category':'mental','name':'Prova de conhecimento','unit':'% ou pontos'},
        {'category':'mental','name':'Outro teste mental','unit':'pontos'},
    ]
    return render_template('trial.html', kind=kind, today=today, monday=monday,
                           baseline_exists=baseline_exists, current_week_session=current_week_session,
                           suggested=suggested)

@app.route('/evolution')
@login_required
def evolution():
    u = current_user()
    sessions = TrialSession.query.filter_by(user_id=u.id).order_by(TrialSession.created_at.asc()).all()
    session_rows = []
    for sess in sessions:
        try: snapshot = json.loads(sess.snapshot_json or '{}')
        except Exception: snapshot = {}
        results = TrialResult.query.filter_by(session_id=sess.id).order_by(TrialResult.category, TrialResult.test_name).all()
        session_rows.append({'session': sess, 'snapshot': snapshot, 'results': results})
    current_values = [{'key': key, 'label': ATTR_LABELS[key], 'value': getattr(u, key)} for key in ATTRIBUTES]
    # Match identical test names to show comparable measurements over time.
    grouped = {}
    for sess in sessions:
        for result in TrialResult.query.filter_by(session_id=sess.id).all():
            grouped.setdefault((result.category, result.test_name, result.unit), []).append({'date': sess.created_at.strftime('%d/%m/%Y'), 'value': result.value})
    comparisons = []
    for (category, name, unit), points in grouped.items():
        if len(points) >= 2:
            comparisons.append({'category': category, 'name': name, 'unit': unit, 'points': points, 'first': points[0]['value'], 'last': points[-1]['value'], 'delta': points[-1]['value'] - points[0]['value']})
    return render_template('evolution.html', user=u, sessions=list(reversed(session_rows)), current_values=current_values, comparisons=comparisons)

@app.route('/story')
@login_required
def story():
    today = local_today()
    monday = today - timedelta(days=today.weekday())
    # The first arc is intentionally authored for one Monday-to-Sunday cycle.
    arc_start = date(2026, 10, 12)
    day_index = (today - arc_start).days
    chapters = [
        {'day':'SEGUNDA','title':'Sinal de Ativação','mission':'Estabelece o primeiro vínculo com o Sistema.','body':['Às 00:00, o ecrã apaga-se por um instante. Uma janela azul surge sobre a rotina habitual: nenhum mapa, nenhuma explicação, apenas uma linha de diagnóstico que não reconhece cansaço nem intenção — somente ações verificáveis.','O Sistema pede um primeiro registro. O gesto parece pequeno, mas transforma uma promessa vaga em dado persistente. Pela primeira vez, a interface distingue aquilo que foi imaginado daquilo que realmente aconteceu.'],'objective':'Registra uma atividade real e escolhe como responder ao primeiro sinal.','choices':[('observar','Observar os dados antes de agir'),('agir','Agir primeiro e analisar depois')]},
        {'day':'TERÇA','title':'Leitura do Terreno','mission':'Descobre onde a consistência já existe.','body':['O diagnóstico inicial revela uma paisagem irregular: áreas de força, lacunas de conhecimento e hábitos que aparecem apenas quando tudo corre bem. O Sistema não chama isso de fracasso; chama de terreno ainda não cartografado.','Uma leitura detalhada mostra que progresso não é uma linha reta. O que importa agora é escolher uma ação que possa ser repetida, sem tentar compensar meses em uma única sessão.'],'objective':'Registra uma sessão de estudo, treino ou recuperação coerente com o teu plano.','choices':[('corpo','Priorizar uma ação física adequada'),('mente','Priorizar estudo e resolução de problemas'),('equilibrio','Distribuir o esforço com equilíbrio')]},
        {'day':'QUARTA','title':'Ruído no Sinal','mission':'Resolve uma pequena pendência em vez de fugir dela.','body':['No terceiro dia, os indicadores oscilam. O Sistema detecta interferência entre o que foi planejado e o que foi executado. Uma mensagem alerta que decisões repetidas deixam rastros — inclusive as decisões de adiar.','Não surge um inimigo para ser derrotado à força. O obstáculo é uma pendência concreta, suficientemente pequena para ser concluída e suficientemente real para exigir atenção. O Sistema aguarda um registro honesto, não uma história perfeita.'],'objective':'Conclui e registra uma tarefa importante que estava pendente.','choices':[('rapido','Resolver a tarefa mais curta primeiro'),('importante','Enfrentar a tarefa de maior impacto')]},
        {'day':'QUINTA','title':'Padrão Oculto','mission':'Combina observação e prática.','body':['Os dados dos dias anteriores começam a revelar um padrão. O painel não explica tudo; apresenta uma pergunta que exige raciocínio, teste e correção. Cada resposta errada reduz a certeza, não o valor do Portador.','A Biblioteca do Conhecimento torna-se uma ferramenta de campo. Uma questão resolvida ou uma nota técnica bem registrada vale mais do que fingir domínio. O Sistema passa a guardar também as razões por trás dos resultados.'],'objective':'Resolve uma questão da Biblioteca ou registra uma leitura técnica com notas.','choices':[('teoria','Investigar a teoria antes de responder'),('pratica','Tentar resolver e depois estudar o erro')]},
        {'day':'SEXTA','title':'Teste de Consistência','mission':'Escolhe uma conclusão sustentável para a semana útil.','body':['Uma notificação aparece: “A intenção não é um atributo. O comportamento repetido é evidência.” A interface compara os registros disponíveis e destaca os espaços vazios sem inventar explicações para eles.','O teste não exige ultrapassar limites físicos nem sacrificar o descanso. Exige uma decisão consciente: cumprir uma tarefa apropriada, adaptar o plano quando necessário e registrar o que de fato foi feito.'],'objective':'Registra uma atividade apropriada e revê os marcos conquistados nesta semana.','choices':[('progresso','Dar prioridade ao progresso mensurável'),('recuperacao','Priorizar recuperação para chegar bem à avaliação')]},
        {'day':'SÁBADO','title':'Preparação para a Provação','mission':'Prepara uma avaliação comparável e segura.','body':['O Sistema abre um protocolo de avaliação. Resultados sem unidade, testes feitos em condições muito diferentes e recordes sem técnica não permitem uma comparação justa. O Portador recebe autorização para preparar o método antes de procurar o número.','O equipamento é conferido, os testes são escolhidos e o descanso passa a fazer parte do plano. A preparação não concede um recorde automático; cria condições para que o resultado de amanhã tenha significado.'],'objective':'Revê a página Provação e escolhe testes seguros que possas repetir nas próximas semanas.','choices':[('padrao','Manter os testes mais comparáveis'),('adaptado','Adaptar os testes ao estado físico atual')]},
        {'day':'DOMINGO','title':'Dia da Provação','mission':'Converte a semana em uma referência concreta.','body':['A última janela abre sem música triunfal nem promessa de poder instantâneo. Há apenas registros, unidades, datas e a oportunidade de observar a distância entre o primeiro ponto e o ponto atual.','A avaliação não define o valor do Portador. Ela oferece informação para ajustar o próximo ciclo: o que melhorou, o que permaneceu estável e o que merece uma abordagem diferente. O arco termina com dados guardados — e não com uma conclusão definitiva sobre quem tu és.'],'objective':'Registra a Provação de Fundação ou a avaliação semanal e consulta o relatório.','choices':[('precisao','Valorizar a precisão e a técnica'),('consistencia','Valorizar a consistência de longo prazo')]},
    ]
    first_choice = CampaignChapterProgress.query.filter_by(user_id=current_user().id, arc_key='arc-01', chapter_index=0).first()
    third_choice = CampaignChapterProgress.query.filter_by(user_id=current_user().id, arc_key='arc-01', chapter_index=2).first()
    if first_choice and first_choice.choice == 'observar':
        chapters[2]['body'].append('A tua primeira decisão — observar antes de agir — deixa uma anotação no arquivo: o Portador procura contexto antes de comprometer recursos. O Sistema reduz a incerteza, mas exige que a análise termine numa ação concreta.')
    elif first_choice and first_choice.choice == 'agir':
        chapters[2]['body'].append('A tua primeira decisão — agir antes de analisar — fica registrada como iniciativa. O Sistema reconhece a rapidez, mas marca uma pergunta para o relatório: a ação produziu um resultado que possa ser verificado?')
    if third_choice and third_choice.choice == 'rapido':
        chapters[4]['body'].append('A pendência curta escolhida no meio da semana liberou espaço mental. O relatório de sexta destaca a vantagem de reduzir atrito sem transformar rapidez em pressa constante.')
    elif third_choice and third_choice.choice == 'importante':
        chapters[4]['body'].append('A tarefa de maior impacto escolhida no meio da semana tornou-se o marco central do relatório. O Sistema registra a decisão como uma aposta deliberada no que mais importa.')
    current_idx = today.weekday()
    is_first_arc_week = arc_start <= today < arc_start + timedelta(days=7)
    if not is_first_arc_week:
        current_idx = -1
    baseline_done = TrialSession.query.filter_by(user_id=current_user().id, kind='baseline').first() is not None
    completed_chapters = set()
    for prog in CampaignChapterProgress.query.filter_by(user_id=current_user().id, arc_key='arc-01').all():
        completed_chapters.add(prog.chapter_index)
    visible = [dict(ch if i <= current_idx else {'day': ch['day'], 'title': 'Capítulo selado', 'mission': 'Disponível no dia correspondente.', 'body': [], 'objective': '', 'choices': []}, index=i, unlocked=(i <= current_idx), completed=(i in completed_chapters), saved_choice=next((p.choice for p in CampaignChapterProgress.query.filter_by(user_id=current_user().id, arc_key='arc-01', chapter_index=i).all()), None)) for i,ch in enumerate(chapters)]
    return render_template('story.html', chapters=visible, current_idx=current_idx, arc_active=is_first_arc_week,
                           baseline_done=baseline_done, today=today)

@app.route('/story/chapter/<int:index>/complete', methods=['POST'])
@login_required
def complete_story_chapter(index):
    if index < 0 or index > 6: abort(404)
    today = local_today(); arc_start = date(2026, 10, 12)
    if not (arc_start <= today < arc_start + timedelta(days=7)) or index > today.weekday():
        flash('Este capítulo ainda não está disponível.', 'error')
        return redirect(url_for('story'))
    existing = CampaignChapterProgress.query.filter_by(user_id=current_user().id, arc_key='arc-01', chapter_index=index).first()
    selected_choice = request.form.get('choice', '').strip()[:120]
    if not existing:
        db.session.add(CampaignChapterProgress(user_id=current_user().id, arc_key='arc-01', chapter_index=index, choice=selected_choice or None))
        grant_xp(current_user(), 10)
        db.session.commit()
        flash('Capítulo registrado: +10 XP. A tua decisão foi guardada no histórico narrativo.', 'success')
    else:
        flash('Este capítulo já está registrado.', 'success')
    return redirect(url_for('story'))

@app.route('/story/archive')
@login_required
def story_archive():
    chapters = NarrativeChapter.query.filter_by(active=True).order_by(NarrativeChapter.number, NarrativeChapter.id).all()
    chosen = {c.chapter_id for c in NarrativeChoice.query.filter_by(user_id=current_user().id).all()}
    return render_template('story_archive.html', chapters=chapters, chosen=chosen)

@app.route('/story/archive/<int:chapter_id>')
@login_required
def read_narrative_chapter(chapter_id):
    chapter = db.session.get(NarrativeChapter, chapter_id)
    if not chapter or (not chapter.active and not current_user().is_admin): abort(404)
    payload = json.loads(chapter.content_json)
    narrative = payload['chapter']
    saved = {x.decision_id: x for x in NarrativeChoice.query.filter_by(user_id=current_user().id, chapter_id=chapter.id).all()}
    return render_template('narrative_chapter.html', chapter=chapter, narrative=narrative, saved=saved)

@app.route('/story/archive/<int:chapter_id>/decision/<decision_id>', methods=['POST'])
@login_required
def choose_narrative_option(chapter_id, decision_id):
    chapter = db.session.get(NarrativeChapter, chapter_id)
    if not chapter or not chapter.active: abort(404)
    narrative = json.loads(chapter.content_json)['chapter']
    decision = next((d for scene in narrative.get('scenes', []) for d in scene.get('decisions', []) or [] if d.get('id') == decision_id), None)
    if not decision: abort(404)
    option_id = request.form.get('option_id', '')
    option = next((o for o in decision.get('options', []) if o.get('id') == option_id), None)
    if not option: abort(400)
    existing = NarrativeChoice.query.filter_by(user_id=current_user().id, chapter_id=chapter.id, decision_id=decision_id).first()
    if existing:
        flash('Esta decisão já foi registrada e não pode ser alterada.', 'error')
        return redirect(url_for('read_narrative_chapter', chapter_id=chapter.id))
    user = current_user()
    state = NarrativePlayerState.query.filter_by(user_id=user.id).first()
    if not state:
        initial = narrative.get('initial_state', {}) or {}
        state = NarrativePlayerState(user_id=user.id,
            flags_json=json.dumps(initial.get('flags', []), ensure_ascii=False),
            inventory_json=json.dumps(initial.get('inventory', []), ensure_ascii=False),
            knowledge_json=json.dumps(initial.get('knowledge', []), ensure_ascii=False),
            relationships_json=json.dumps(initial.get('relationships', {}), ensure_ascii=False),
            karma_signals_json='[]')
        db.session.add(state)
        db.session.flush()
    def read_list(field):
        try: return json.loads(getattr(state, field) or '[]')
        except (TypeError, json.JSONDecodeError): return []
    def merge_unique(field, additions):
        current = read_list(field)
        for item in additions or []:
            if item not in current: current.append(item)
        setattr(state, field, json.dumps(current, ensure_ascii=False))
    effects = option.get('effects', {}) or {}
    merge_unique('flags_json', effects.get('flags_add', []))
    merge_unique('inventory_json', effects.get('inventory_add', []))
    merge_unique('knowledge_json', effects.get('knowledge_add', []))
    merge_unique('karma_signals_json', effects.get('karma_signals', []))
    try: relationships = json.loads(state.relationships_json or '{}')
    except (TypeError, json.JSONDecodeError): relationships = {}
    for relation in effects.get('relationship_updates', []) or []:
        char = str(relation.get('character', ''))
        if char:
            relationships[char] = int(relationships.get(char, 0)) + int(relation.get('trust', 0))
    state.relationships_json = json.dumps(relationships, ensure_ascii=False)
    for item in effects.get('inventory_remove', []) or []:
        inventory = read_list('inventory_json')
        if item in inventory:
            inventory.remove(item)
            state.inventory_json = json.dumps(inventory, ensure_ascii=False)
        else:
            # Partial consumption may refer to a portion of a larger inventory entry.
            wanted = {w for w in str(item).casefold().split() if len(w) > 3 and w not in {'parte', 'restante', 'pacote'}}
            for idx, held in enumerate(inventory):
                held_words = {w for w in str(held).casefold().split() if len(w) > 3 and w not in {'parte', 'restante', 'pacote'}}
                if wanted and wanted.issubset(held_words):
                    inventory[idx] = f'restante de {held}'
                    state.inventory_json = json.dumps(inventory, ensure_ascii=False)
                    break
    db.session.add(NarrativeChoice(user_id=user.id, chapter_id=chapter.id, decision_id=decision_id,
                                   option_id=option['id'], option_label=option['label'],
                                   effects_json=json.dumps(effects, ensure_ascii=False)))
    db.session.commit()
    flash('Decisão registrada. Seus efeitos persistentes foram guardados; o karma será avaliado no fechamento do ciclo.', 'success')
    return redirect(url_for('read_narrative_chapter', chapter_id=chapter.id))

@app.route('/combat')
@login_required
def combat():
    user = current_user()
    active = CombatEncounter.query.filter_by(user_id=user.id, status='active').order_by(CombatEncounter.id.desc()).first()
    history = CombatEncounter.query.filter_by(user_id=user.id).filter(CombatEncounter.status != 'active').order_by(CombatEncounter.id.desc()).limit(8).all()
    if active:
        try: battle_log = json.loads(active.log_json or '[]')
        except json.JSONDecodeError: battle_log = []
    else: battle_log = []
    return render_template('combat.html', active=active, battle_log=battle_log, history=history, user=user)

@app.route('/combat/start', methods=['POST'])
@login_required
def start_combat():
    user = current_user()
    if CombatEncounter.query.filter_by(user_id=user.id, status='active').first():
        flash('Termine ou fuja do combate atual antes de iniciar outro.', 'error')
        return redirect(url_for('combat'))
    enemy_kind = request.form.get('enemy_kind', 'comum')
    enemies = {
        'fraco': {'name':'Rastejante Cinzento', 'hp':24, 'damage':(2,5), 'xp':20},
        'comum': {'name':'Predador da Ruptura', 'hp':38, 'damage':(3,7), 'xp':35},
        'forte': {'name':'Sentinela Deformada', 'hp':52, 'damage':(4,9), 'xp':55},
    }
    if enemy_kind not in enemies: abort(400)
    enemy = enemies[enemy_kind]
    max_hp = 40 + user.corpo * 8 + user.vitalidade * 5
    log = [f'Combate iniciado contra {enemy["name"]}.', 'Você pode atacar, defender-se ou tentar fugir.']
    db.session.add(CombatEncounter(user_id=user.id, enemy_name=enemy['name'], enemy_kind=enemy_kind,
        enemy_hp=enemy['hp'], enemy_max_hp=enemy['hp'], player_hp=max_hp, player_max_hp=max_hp,
        xp_reward=enemy['xp'], status='active', log_json=json.dumps(log, ensure_ascii=False)))
    db.session.commit()
    return redirect(url_for('combat'))

@app.route('/combat/<int:encounter_id>/action', methods=['POST'])
@login_required
def combat_action(encounter_id):
    user = current_user()
    fight = db.session.get(CombatEncounter, encounter_id)
    if not fight or fight.user_id != user.id or fight.status != 'active': abort(404)
    try: log = json.loads(fight.log_json or '[]')
    except json.JSONDecodeError: log = []
    action = request.form.get('action', '')
    if action == 'fugir':
        fight.status = 'fled'; fight.finished_at = datetime.utcnow()
        log.append('Você recuou e encerrou o combate sem recompensa.')
    elif action in ('atacar', 'defender'):
        if action == 'atacar':
            damage = random.randint(1, 6) + max(1, user.corpo // 3)
            fight.enemy_hp = max(0, fight.enemy_hp - damage)
            log.append(f'Você acerta {fight.enemy_name} e causa {damage} de dano.')
        else:
            log.append('Você assume uma postura defensiva e reduz o próximo dano recebido.')
        if fight.enemy_hp <= 0:
            fight.status = 'victory'; fight.finished_at = datetime.utcnow()
            grant_xp(user, fight.xp_reward)
            log.append(f'{fight.enemy_name} foi derrotado. Você recebe {fight.xp_reward} XP.')
        else:
            low, high = {'fraco':(2,5), 'comum':(3,7), 'forte':(4,9)}[fight.enemy_kind]
            enemy_damage = random.randint(low, high)
            if action == 'defender': enemy_damage = max(1, (enemy_damage + 1) // 2)
            mitigation = max(0, user.vitalidade // 5)
            enemy_damage = max(1, enemy_damage - mitigation)
            fight.player_hp = max(0, fight.player_hp - enemy_damage)
            log.append(f'{fight.enemy_name} ataca e causa {enemy_damage} de dano.')
            if fight.player_hp <= 0:
                fight.status = 'defeat'; fight.finished_at = datetime.utcnow()
                log.append('Você foi derrotado. O combate terminou; nenhuma recompensa foi concedida.')
    else:
        abort(400)
    fight.log_json = json.dumps(log[-30:], ensure_ascii=False)
    db.session.commit()
    return redirect(url_for('combat'))

@app.route('/backup')
@login_required
@admin_required
def backup():
    # SQLite backup is portable; PostgreSQL backups should use pg_dump in the hosting environment.
    if not app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
        flash('O backup SQL direto de PostgreSQL deve ser feito com pg_dump no provedor. Esta exportação JSON contém dados essenciais.', 'error')
    payload={}
    for model in [User,Activity,SpecialQuest,QuestCompletion,Skill,Question,TestAttempt,PerformanceEntry,DietEntry,WaterEntry,TrialSession,TrialResult,CampaignChapterProgress,NarrativeChapter,NarrativeChoice,NarrativePlayerState,CombatEncounter]:
        rows=[]
        for obj in model.query.all():
            rows.append({c.name:(getattr(obj,c.name).isoformat() if isinstance(getattr(obj,c.name),(datetime,date)) else getattr(obj,c.name)) for c in model.__table__.columns})
        payload[model.__tablename__]=rows
    mem=io.BytesIO(json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8')); mem.seek(0)
    return send_file(mem,mimetype='application/json',as_attachment=True,download_name=f'sistema-soberano-backup-{date.today().isoformat()}.json')

@app.route('/admin')
@login_required
@admin_required
def admin():
    chapters = NarrativeChapter.query.order_by(NarrativeChapter.number, NarrativeChapter.id).all()
    return render_template('admin.html', users=User.query.order_by(User.id).all(), quests=SpecialQuest.query.order_by(SpecialQuest.id).all(), chapters=chapters, question_count=Question.query.count())

@app.route('/admin/chapters/import', methods=['POST'])
@login_required
@admin_required
def import_chapter():
    upload = request.files.get('chapter_file')
    if not upload or not upload.filename:
        flash('Escolha um arquivo JSON de capítulo.', 'error')
        return redirect(url_for('admin'))
    if not upload.filename.lower().endswith('.json'):
        flash('O importador aceita apenas arquivos .json.', 'error')
        return redirect(url_for('admin'))
    try:
        raw = upload.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise ValueError('O arquivo ultrapassa o limite de 5 MB.')
        payload = json.loads(raw.decode('utf-8-sig'))
        chapter = payload.get('chapter') if isinstance(payload, dict) else None
        if payload.get('format') != 'sistema-do-soberano-narrative' or not isinstance(chapter, dict):
            raise ValueError('Formato inválido. Use um JSON exportado no formato narrativo do Sistema do Soberano.')
        required = ['id', 'number', 'title', 'scenes']
        if any(k not in chapter for k in required) or not isinstance(chapter['scenes'], list) or not chapter['scenes']:
            raise ValueError('O capítulo precisa ter id, número, título e pelo menos uma cena.')
        if len(str(chapter['title'])) > 200 or len(str(chapter['id'])) > 100:
            raise ValueError('Título ou identificador muito longo.')
        decision_count = 0
        for scene in chapter['scenes']:
            if not isinstance(scene, dict) or not scene.get('id') or not scene.get('title'):
                raise ValueError('Cada cena precisa ter id e título.')
            if not isinstance(scene.get('text', ''), str):
                raise ValueError('O texto de cada cena precisa ser uma string.')
            for decision in scene.get('decisions', []) or []:
                if not isinstance(decision, dict) or not decision.get('id') or not isinstance(decision.get('options'), list) or len(decision['options']) < 2:
                    raise ValueError('Cada decisão precisa de id e pelo menos duas opções.')
                if any(not isinstance(opt, dict) or not opt.get('id') or not opt.get('label') for opt in decision['options']):
                    raise ValueError('Cada opção precisa ter id e rótulo.')
                decision_count += 1
        chapter_key = str(chapter['id']).strip()[:100]
        existing = NarrativeChapter.query.filter_by(chapter_key=chapter_key).first()
        serialized = json.dumps(payload, ensure_ascii=False)
        values = dict(number=max(1, int(chapter['number'])), title=str(chapter['title']).strip()[:200],
                      weekday=str(chapter.get('weekday',''))[:40], location=str(chapter.get('location',''))[:200],
                      timeline=str(chapter.get('timeline',''))[:200], summary=str(chapter.get('summary',''))[:5000],
                      content_json=serialized, word_count=max(0, int(chapter.get('word_count', 0) or 0)),
                      decision_count=decision_count, active=True)
        if existing:
            existing.title = values['title']
            existing.number = values['number']
            existing.weekday = values['weekday']
            existing.location = values['location']
            existing.timeline = values['timeline']
            existing.summary = values['summary']
            existing.content_json = values['content_json']
            existing.word_count = values['word_count']
            existing.decision_count = values['decision_count']
            existing.active = True
            flash('O capítulo com este identificador já existia e foi atualizado. Escolhas anteriores dos jogadores foram preservadas.', 'success')
        else:
            db.session.add(NarrativeChapter(chapter_key=chapter_key, **values))
            flash(f'Capítulo “{values["title"]}” importado com {len(chapter["scenes"])} cenas e {decision_count} decisões.', 'success')
        db.session.commit()
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
        db.session.rollback()
        flash(f'Não foi possível importar o capítulo: {exc}', 'error')
    except Exception:
        db.session.rollback()
        app.logger.exception('Falha ao importar capítulo narrativo')
        flash('Ocorreu um erro ao salvar o capítulo. Nenhuma alteração foi confirmada.', 'error')
    return redirect(url_for('admin'))

@app.route('/admin/chapters/<int:chapter_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_chapter(chapter_id):
    chapter = db.session.get(NarrativeChapter, chapter_id)
    if not chapter: abort(404)
    chapter.active = not chapter.active
    db.session.commit()
    flash('Capítulo publicado.' if chapter.active else 'Capítulo arquivado e ocultado dos jogadores.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/quests', methods=['POST'])
@login_required
@admin_required
def create_quest():
    title=request.form.get('title','').strip(); description=request.form.get('description','').strip(); skill_name=request.form.get('skill_name','').strip(); skill_description=request.form.get('skill_description','').strip()
    try: reward=max(0,min(10000,int(request.form.get('xp_reward','50'))))
    except ValueError: reward=50
    if not all([title,description,skill_name]): flash('Preencha título, descrição e nome da habilidade.', 'error')
    else:
        db.session.add(SpecialQuest(title=title,description=description,skill_name=skill_name,skill_description=skill_description,xp_reward=reward)); db.session.commit(); flash('Missão especial criada.', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/users/<int:uid>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(uid):
    u=db.session.get(User,uid)
    if not u: abort(404)
    if u.id==current_user().id: flash('Não podes apagar a própria conta administrativa.', 'error')
    else:
        for model in [Activity,QuestCompletion,Skill,TestAttempt,PerformanceEntry,DietEntry,WaterEntry,TrialResult,TrialSession,CampaignChapterProgress,NarrativeChoice,NarrativePlayerState,CombatEncounter]: model.query.filter_by(user_id=u.id).delete(synchronize_session=False)
        db.session.delete(u); db.session.commit(); flash('Conta removida.', 'success')
    return redirect(url_for('admin'))

@app.errorhandler(403)
def forbidden(e): return render_template('message.html', title='Acesso negado', message='Esta área exige permissões administrativas.'),403

with app.app_context():
    db.create_all()
    # Seed introductory special quests only once.
    if Question.query.count()==0:
        db.session.add_all([
            Question(subject='Física', level='Ensino superior', topic='Eletromagnetismo', difficulty='Intermediária', prompt='Qual expressão representa a força magnética sobre uma partícula de carga q e velocidade v em um campo magnético B?', options_json=json.dumps(['A) F = qE','B) F = q(v × B)','C) F = mv','D) F = qB'], ensure_ascii=False), answer='B) F = q(v × B)', explanation='A força magnética é dada por q(v × B), o produto vetorial entre a velocidade e o campo magnético multiplicado pela carga.', source='Questão original'),
            Question(subject='Eletrônica', level='Ensino técnico', topic='Lei de Ohm', difficulty='Básica', prompt='Um resistor de 1 kΩ está submetido a 5 V. Qual corrente o atravessa?', options_json=json.dumps(['A) 0,5 mA','B) 5 mA','C) 50 mA','D) 500 mA'], ensure_ascii=False), answer='B) 5 mA', explanation='Pela Lei de Ohm, I = V/R = 5/1000 A = 5 mA.', source='Questão original'),
            Question(subject='Matemática', level='Ensino médio', topic='Funções', difficulty='Básica', prompt='Se f(x) = 2x + 3, qual é o valor de f(4)?', options_json=json.dumps(['A) 8','B) 9','C) 11','D) 12'], ensure_ascii=False), answer='C) 11', explanation='Substituindo x por 4: f(4) = 2·4 + 3 = 11.', source='Questão original'),
            Question(subject='Física', level='Ensino médio', topic='Mecânica', difficulty='Básica', prompt='Um objeto de massa 2 kg sofre aceleração de 3 m/s². Qual é a força resultante?', options_json=json.dumps(['A) 1,5 N','B) 5 N','C) 6 N','D) 9 N'], ensure_ascii=False), answer='C) 6 N', explanation='Pela segunda lei de Newton, F = ma = 2 × 3 = 6 N.', source='Questão original'),
            Question(subject='Eletrônica', level='Ensino técnico', topic='Componentes', difficulty='Básica', prompt='Qual componente é normalmente usado para limitar a corrente em um circuito simples?', options_json=json.dumps(['A) Resistor','B) Fusível aberto','C) Antena','D) Transformador ideal sem resistência'], ensure_ascii=False), answer='A) Resistor', explanation='O resistor limita a corrente conforme a tensão aplicada e sua resistência, de acordo com a Lei de Ohm.', source='Questão original')
        ]); db.session.commit()
    if SpecialQuest.query.count()==0:
        db.session.add_all([
            SpecialQuest(title='O Primeiro Registro',description='Registra uma atividade real no Sistema para estabelecer o primeiro marco da tua jornada.',skill_name='Percepção do Sistema',skill_description='Permite ao Portador visualizar com clareza seus registros e marcos de progresso.',xp_reward=50),
            SpecialQuest(title='A Provação do Erudito',description='Responde corretamente a uma questão da Biblioteca do Conhecimento.',skill_name='Arquivo Mental I',skill_description='Um título de habilidade que simboliza o início do caminho do conhecimento.',xp_reward=75),
            SpecialQuest(title='Mapeamento do Potencial',description='Registra um resultado no Laboratório de Desempenho e estabelece uma linha de base.',skill_name='Leitura de Atributos',skill_description='Desbloqueia o registro narrativo do potencial do Portador.',xp_reward=50)
        ]); db.session.commit()
    admin_name=os.environ.get('ADMIN_USERNAME'); admin_password=os.environ.get('ADMIN_PASSWORD')
    if admin_name and admin_password:
        admin_user = User.query.filter_by(username=admin_name).first()
        if not admin_user:
            db.session.add(User(username=admin_name,password_hash=generate_password_hash(admin_password),is_admin=True))
            db.session.commit()
        else:
            # Deployment variables are authoritative for this reserved admin identity.
            changed = not admin_user.is_admin or not check_password_hash(admin_user.password_hash, admin_password)
            admin_user.is_admin = True
            if not check_password_hash(admin_user.password_hash, admin_password):
                admin_user.password_hash = generate_password_hash(admin_password)
            if changed:
                db.session.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=False)
