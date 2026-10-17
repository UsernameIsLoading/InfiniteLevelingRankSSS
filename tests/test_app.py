import os
os.environ.setdefault('SITE_PASSWORD','12345678')
os.environ.setdefault('SECRET_KEY','test-secret')
os.environ.setdefault('DATABASE_URL','sqlite://')
import app as webapp
import pytest

@pytest.fixture()
def client():
    webapp.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://', WTF_CSRF_ENABLED=False)
    with webapp.app.app_context():
        webapp.db.drop_all(); webapp.db.create_all(); webapp.get_state()
    with webapp.app.test_client() as c:
        yield c
    with webapp.app.app_context():
        webapp.db.session.remove(); webapp.db.drop_all()

def login(c):
    return c.post('/login', data={'password':'12345678'}, follow_redirects=True)

def test_login_and_dashboard(client):
    r=login(client)
    assert r.status_code==200
    assert b'Bem-vindo de volta' in r.data

def test_training_start_and_finish(client):
    login(client)
    r=client.post('/api/training/start',json={'kind':'resistencia','seconds':30})
    assert r.status_code==200
    data=r.get_json()
    r2=client.post('/api/training/finish/'+str(data['id']))
    assert r2.status_code==200
    assert r2.get_json()['xp']>=0

def test_skill_purchase_requires_points(client):
    login(client)
    r=client.post('/api/skills/buy/soul_bolt',json={})
    assert r.status_code==400

def test_integration_deduplicates(client,monkeypatch=None):
    import app as module
    module.app.config['TESTING']=True
    with module.app.app_context():
        module.db.drop_all();module.db.create_all();module.get_state()
    os.environ['QUESTHUB_INTEGRATION_TOKEN']='integration-test'
    h={'Authorization':'Bearer integration-test','Content-Type':'application/json'}
    r=client.post('/api/integration/answered-questions',headers=h,json={'question_ids':['q1','q1','q2']})
    assert r.status_code==200
    assert r.get_json()['new_questions']==2
