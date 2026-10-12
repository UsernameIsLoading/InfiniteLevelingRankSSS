import os, io, csv, json, secrets
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-before-deploying-' + secrets.token_hex(8))
db_url = os.environ.get('DATABASE_URL', 'sqlite:///sistema_soberano.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
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
        user = User.query.filter_by(username=request.form.get('username','').strip()).first()
        if user and check_password_hash(user.password_hash, request.form.get('password','')):
            session.clear(); session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash('Credenciais inválidas.', 'error')
    return render_template('auth.html', mode='login')

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
            db.session.add(Question(subject=subject,level=level,topic=topic,prompt=prompt,answer=answer,explanation=explanation,options_json=json.dumps(options,ensure_ascii=False),difficulty=difficulty,created_by=u.id))
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

@app.route('/story')
@login_required
def story(): return render_template('story.html')

@app.route('/backup')
@login_required
@admin_required
def backup():
    # SQLite backup is portable; PostgreSQL backups should use pg_dump in the hosting environment.
    if not app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
        flash('O backup SQL direto de PostgreSQL deve ser feito com pg_dump no provedor. Esta exportação JSON contém dados essenciais.', 'error')
    payload={}
    for model in [User,Activity,SpecialQuest,QuestCompletion,Skill,Question,TestAttempt,PerformanceEntry]:
        rows=[]
        for obj in model.query.all():
            rows.append({c.name:(getattr(obj,c.name).isoformat() if isinstance(getattr(obj,c.name),datetime) else getattr(obj,c.name)) for c in model.__table__.columns})
        payload[model.__tablename__]=rows
    mem=io.BytesIO(json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8')); mem.seek(0)
    return send_file(mem,mimetype='application/json',as_attachment=True,download_name=f'sistema-soberano-backup-{date.today().isoformat()}.json')

@app.route('/admin')
@login_required
@admin_required
def admin(): return render_template('admin.html', users=User.query.order_by(User.id).all(), quests=SpecialQuest.query.order_by(SpecialQuest.id).all())

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
        for model in [Activity,QuestCompletion,Skill,TestAttempt,PerformanceEntry]: model.query.filter_by(user_id=u.id).delete(synchronize_session=False)
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
    if admin_name and admin_password and not User.query.filter_by(username=admin_name).first():
        db.session.add(User(username=admin_name,password_hash=generate_password_hash(admin_password),is_admin=True)); db.session.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=False)
