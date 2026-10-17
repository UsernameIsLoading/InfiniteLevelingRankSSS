import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3, random, time, json, urllib.request, urllib.parse, threading, webbrowser
from pathlib import Path
from datetime import date, datetime
HOME=Path.home()/'.necromante_system'; HOME.mkdir(exist_ok=True); DB=HOME/'game.db'; CFG=HOME/'config.json'
MONSTERS=[('Slime',1,34,7,2,'Resistente'),('Rato Sombrio',1,30,9,1,'Ágil'),('Fantasma',1,32,8,2,'Intangível'),('Morcego',1,29,9,1,'Veloz'),('Golem Rachado',1,42,7,4,'Defesa alta'),('Espírito Guardião',1,36,8,3,'Proteção'),('Inseto Feroz',2,54,12,3,'Golpe especial'),('Serpente',2,50,14,2,'Ataque alto'),('Tentáculo Vivo',2,58,11,4,'Resistente'),('Cavaleiro Caído',2,62,12,5,'Armadura'),('Espectro Blindado',2,56,13,4,'Barreira'),('Bruto das Ruínas',2,68,15,3,'Golpe pesado'),('Predador Abissal',3,82,18,5,'Caçador'),('Demônio Alado',3,76,20,4,'Evasivo'),('Guardião Antigo',3,95,16,7,'Muralha'),('Colosso',3,110,17,8,'Lento e forte'),('Lorde Espectral',3,88,21,5,'Dreno leve'),('Carrasco',3,92,22,4,'Golpe especial'),('Monstro Ancestral',4,132,25,8,'Adaptação'),('Cavaleiro Amaldiçoado',4,125,27,9,'Contra-ataque'),('Devorador',4,145,24,7,'Regeneração'),('Hidra',4,152,26,7,'Ataques múltiplos'),('Tirano',4,140,29,8,'Fúria'),('Quimera',4,135,28,8,'Efeito variável'),('Arquidemônio',5,190,34,11,'Chefe'),('Soberano Morto-vivo',5,205,32,13,'Resistência'),('Behemoth',5,230,36,12,'Colossal'),('Dragão Espectral',5,198,39,10,'Veloz'),('Chefe da Estação',5,240,37,14,'Chefe'),('Arauto do Abismo',5,215,40,11,'Instável')]
# Habilidades de fantasia abstratas para o protótipo; catálogo externo completo ainda requer importação validada.
SKILLS=[('Golpe Concentrado','Ataque',3,'Causa dano aumentado.','Foco'),('Onda Sombria','Ataque',5,'Causa dano arcano.','Catalisador'),('Barreira','Defesa',4,'Reduz o próximo dano recebido.','Amuleto'),('Regeneração','Suporte',5,'Recupera HP.','Talismã'),('Passo Veloz','Suporte',3,'Aumenta chance de esquiva.','Botas'),('Dreno Vital','Ataque',6,'Causa dano e recupera parte como HP.','Relíquia'),('Enfraquecer','Controle',4,'Reduz ataque inimigo por 2 turnos.','Selo'),('Explosão Arcana','Ataque',8,'Causa dano alto.','Orbe')]
class Game(tk.Tk):
 def __init__(self):
  super().__init__(); self.title('Necromante System — Python'); self.geometry('980x700'); self.configure(bg='#0a0d17')
  self.db=sqlite3.connect(DB); self.db.row_factory=sqlite3.Row
  self.db.executescript('''CREATE TABLE IF NOT EXISTS p(id INTEGER PRIMARY KEY CHECK(id=1),hp INTEGER DEFAULT 100,maxhp INTEGER DEFAULT 100,res INTEGER DEFAULT 0,agi INTEGER DEFAULT 0,combat INTEGER DEFAULT 0,sp INTEGER DEFAULT 0,potions INTEGER DEFAULT 2); INSERT OR IGNORE INTO p(id) VALUES(1); CREATE TABLE IF NOT EXISTS skills(id INTEGER PRIMARY KEY,name TEXT UNIQUE,cat TEXT,cost INTEGER,descr TEXT,item TEXT); CREATE TABLE IF NOT EXISTS owned(skill_id INTEGER PRIMARY KEY); CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY,day TEXT,exercise TEXT,secs INTEGER,xp REAL); CREATE TABLE IF NOT EXISTS seen(qid TEXT PRIMARY KEY,answered TEXT); CREATE TABLE IF NOT EXISTS chapters(n INTEGER PRIMARY KEY,source TEXT,unlocked TEXT); CREATE TABLE IF NOT EXISTS inv(item TEXT PRIMARY KEY,qty INTEGER DEFAULT 1); CREATE TABLE IF NOT EXISTS battles(id INTEGER PRIMARY KEY,day TEXT,monster TEXT,result TEXT,reward INTEGER,drop TEXT);''')
  for s in SKILLS:self.db.execute('INSERT OR IGNORE INTO skills(name,cat,cost,descr,item) VALUES(?,?,?,?,?)',s)
  self.db.commit(); self.cfg=self.loadcfg(); self.ex='Prancha'; self.running=False; self.elapsed=0; self.started=0; self.enemy=None; self.ehp=0; self.status={}
  st=ttk.Style(self); st.theme_use('clam'); st.configure('TNotebook',background='#0a0d17'); st.configure('TNotebook.Tab',background='#202941',foreground='#fff',padding=9); st.map('TNotebook.Tab',background=[('selected','#59438a')]); st.configure('TLabel',background='#111827',foreground='#edf1ff'); st.configure('TFrame',background='#111827'); st.configure('TButton',background='#35476c',foreground='white',padding=7); st.configure('Treeview',background='#0b1020',foreground='#fff',fieldbackground='#0b1020')
  h=tk.Frame(self,bg='#0a0d17'); h.pack(fill='x',padx=18,pady=14); tk.Label(h,text='NECROMANTE SYSTEM',font=('Segoe UI',22,'bold'),fg='#c6a9ff',bg='#0a0d17').pack(anchor='w'); tk.Label(h,text='Treino • estudos • combate • leitura',fg='#aab5d0',bg='#0a0d17').pack(anchor='w')
  self.nb=ttk.Notebook(self); self.nb.pack(fill='both',expand=True,padx=14,pady=8); self.tabs={}
  for name in ['Painel','Treino','QuestHub','Combate','Skill Shop','Biblioteca','Integração']:
   f=ttk.Frame(self.nb,padding=14); self.nb.add(f,text=name); self.tabs[name]=f
  self.build_dash(); self.build_train(); self.build_quest(); self.build_combat(); self.build_shop(); self.build_library(); self.build_config(); self.refresh(); self.after(250,self.tick)
 def loadcfg(self):
  try:return json.loads(CFG.read_text())
  except:return {'url':'','token':'','user_id':''}
 def lab(self,p,t,**kw):return tk.Label(p,text=t,bg='#111827',fg='#edf1ff',**kw)
 def p(self):return self.db.execute('SELECT * FROM p WHERE id=1').fetchone()
 def build_dash(self):
  self.dash=self.lab(self.tabs['Painel'],'',font=('Segoe UI',14),justify='left'); self.dash.pack(anchor='w',pady=8); self.logdash=tk.Text(self.tabs['Painel'],bg='#0b1020',fg='#dbe4ff',height=18,relief='flat'); self.logdash.pack(fill='both',expand=True)
 def build_train(self):
  f=self.tabs['Treino']; self.lab(f,'Cronômetro de treino',font=('Segoe UI',16,'bold')).pack(anchor='w'); self.exvar=tk.StringVar(value='Prancha'); row=tk.Frame(f,bg='#111827'); row.pack(anchor='w',pady=8)
  for x in ['Prancha','Pular corda','Sparring']:tk.Radiobutton(row,text=x,variable=self.exvar,value=x,command=self.changeex,bg='#111827',fg='white',selectcolor='#59438a').pack(side='left',padx=8)
  self.clock=self.lab(f,'00:00',font=('Consolas',44,'bold'),fg='#c5a5ff'); self.clock.pack(pady=20); self.hint=self.lab(f,'1 XP por segundo'); self.hint.pack(); row=tk.Frame(f,bg='#111827'); row.pack(pady=10)
  ttk.Button(row,text='Iniciar/Pausar',command=self.toggle).pack(side='left',padx=4); ttk.Button(row,text='Zerar',command=self.reset).pack(side='left',padx=4); ttk.Button(row,text='Finalizar e salvar',command=self.finish).pack(side='left',padx=4)
  self.sess=ttk.Treeview(f,columns=('d','e','t','x'),show='headings',height=10)
  for c,t in [('d','Data'),('e','Exercício'),('t','Tempo'),('x','XP')]:self.sess.heading(c,text=t)
  self.sess.pack(fill='both',expand=True,pady=10)
 def changeex(self):
  if self.running:messagebox.showinfo('Cronômetro','Pause antes de trocar.'); self.exvar.set(self.ex); return
  self.ex=self.exvar.get(); self.elapsed=0; self.hint.config(text='30 XP por minuto' if self.ex=='Sparring' else '1 XP por segundo'); self.clock.config(text='00:00')
 def secs(self):return self.elapsed+(time.monotonic()-self.started if self.running else 0)
 def toggle(self):
  if self.running:self.elapsed=self.secs(); self.running=False
  else:self.started=time.monotonic(); self.running=True
 def reset(self):self.running=False; self.elapsed=0; self.clock.config(text='00:00')
 def tick(self):
  s=int(self.secs()); self.clock.config(text=f'{s//60:02d}:{s%60:02d}'); self.after(250,self.tick)
 def finish(self):
  s=int(self.secs())
  if s<1:messagebox.showwarning('Treino','Registre pelo menos um segundo.'); return
  xp=s if self.ex!='Sparring' else s*.5; col={'Prancha':'res','Pular corda':'agi','Sparring':'combat'}[self.ex]; self.db.execute(f'UPDATE p SET {col}={col}+? WHERE id=1',(xp,)); self.db.execute('INSERT INTO sessions(day,exercise,secs,xp) VALUES(?,?,?,?)',(date.today().isoformat(),self.ex,s,xp))
  if not self.db.execute("SELECT 1 FROM chapters WHERE source='physical' AND unlocked LIKE ?",(date.today().isoformat()+'%',)).fetchone():
   n=max([r[0] for r in self.db.execute("SELECT n FROM chapters WHERE source='physical'")]+[-1])+2; self.db.execute('INSERT OR IGNORE INTO chapters VALUES(?,?,?)',(n,'physical',datetime.now().isoformat()))
  self.db.commit(); self.reset(); self.refresh(); messagebox.showinfo('Treino',f'+{xp:g} XP. Capítulo ímpar liberado se ainda não foi liberado hoje.')
 def build_quest(self):
  f=self.tabs['QuestHub']; self.lab(f,'Sincronização de questões respondidas',font=('Segoe UI',16,'bold')).pack(anchor='w'); self.qstatus=self.lab(f,'Configure a integração na aba Integração.'); self.qstatus.pack(anchor='w',pady=8); ttk.Button(f,text='Sincronizar agora',command=self.sync).pack(anchor='w',pady=5); self.qtree=ttk.Treeview(f,columns=('id','date'),show='headings',height=16); self.qtree.heading('id',text='ID questão'); self.qtree.heading('date',text='Respondida em'); self.qtree.pack(fill='both',expand=True,pady=8)
 def build_combat(self):
  f=self.tabs['Combate']; self.lab(f,'Combate por turnos',font=('Segoe UI',16,'bold')).pack(anchor='w'); row=tk.Frame(f,bg='#111827'); row.pack(fill='both',expand=True); left=tk.Frame(row,bg='#111827'); left.pack(side='left',fill='y',padx=(0,12)); self.ml=tk.Listbox(left,width=30,bg='#0b1020',fg='white',selectbackground='#59438a',relief='flat')
  for m in MONSTERS:self.ml.insert('end',f'Nível {m[1]} • {m[0]}')
  self.ml.pack(fill='y',expand=True); self.ml.bind('<<ListboxSelect>>',self.selectmonster); right=tk.Frame(row,bg='#111827'); right.pack(side='left',fill='both',expand=True); self.binfo=self.lab(right,'Selecione um monstro.',font=('Segoe UI',12),justify='left'); self.binfo.pack(anchor='w'); self.blog=tk.Text(right,bg='#0b1020',fg='#dbe4ff',height=13,relief='flat',wrap='word'); self.blog.pack(fill='both',expand=True,pady=8); self.skillvar=tk.StringVar(); self.skillbox=ttk.Combobox(right,textvariable=self.skillvar,state='readonly'); self.skillbox.pack(anchor='w',pady=4); row=tk.Frame(right,bg='#111827'); row.pack(anchor='w'); ttk.Button(row,text='Ataque básico',command=self.attack).pack(side='left',padx=3); ttk.Button(row,text='Habilidade',command=self.skill).pack(side='left',padx=3); ttk.Button(row,text='Poção',command=self.potion).pack(side='left',padx=3)
 def selectmonster(self,e=None):
  sel=self.ml.curselection()
  if not sel:return
  self.enemy=MONSTERS[sel[0]]; self.ehp=self.enemy[2]; self.status={}; self.blog.delete('1.0','end'); self.say(f'{self.enemy[0]} aparece!'); self.binfo.config(text=f'{self.enemy[0]} • Nível {self.enemy[1]}\nHP {self.ehp} • Ataque {self.enemy[3]} • Defesa {self.enemy[4]}\nTraço: {self.enemy[5]}')
 def say(self,s):self.blog.insert('end',s+'\n'); self.blog.see('end')
 def stats(self):p=self.p();return 8+p['combat']//30,4+p['agi']//100,p['hp'],p['maxhp']
 def attack(self):
  if not self.enemy or self.ehp<=0:messagebox.showinfo('Combate','Escolha um monstro vivo.'); return
  atk,agi,_,_=self.stats(); d=max(1,atk+random.randint(1,6)-self.enemy[4]); self.ehp-=d; self.say(f'Você causa {d} de dano.'); self.endturn()
 def skill(self):
  if not self.enemy or self.ehp<=0:return
  sk=self.db.execute('SELECT s.* FROM skills s JOIN owned o ON s.id=o.skill_id WHERE s.name=?',(self.skillvar.get(),)).fetchone()
  if not sk:messagebox.showinfo('Habilidade','Compre uma habilidade no Skill Shop.'); return
  atk,agi,hp,mhp=self.stats(); n=sk['name']
  if n=='Regeneração':heal=min(mhp-hp,max(12,mhp//3)); self.db.execute('UPDATE p SET hp=hp+? WHERE id=1',(heal,)); self.db.commit(); self.say(f'Regeneração recupera {heal} HP.')
  elif n=='Barreira':self.status['barrier']=1; self.say('Barreira reduz o próximo dano.')
  elif n=='Passo Veloz':self.status['dodge']=2; self.say('Passo Veloz ativo.')
  elif n=='Enfraquecer':self.status['weak']=2; self.say('Ataque inimigo reduzido por 2 turnos.')
  else:
   d=max(2,int(atk*(1.8 if n in ('Explosão Arcana','Onda Sombria') else 1.35)+random.randint(2,8))-self.enemy[4]); self.ehp-=d; self.say(f'{n} causa {d} de dano.')
   if n=='Dreno Vital':heal=max(1,d//4); self.db.execute('UPDATE p SET hp=min(maxhp,hp+?) WHERE id=1',(heal,)); self.db.commit(); self.say(f'Você recupera {heal} HP.')
  self.endturn()
 def potion(self):
  p=self.p()
  if p['potions']<=0:messagebox.showinfo('Poção','Sem poções.'); return
  h=min(35,p['maxhp']-p['hp']); self.db.execute('UPDATE p SET hp=hp+?,potions=potions-1 WHERE id=1',(h,)); self.db.commit(); self.say(f'Poção recupera {h} HP.'); self.enemyturn(); self.refresh()
 def endturn(self):
  if self.ehp<=0:
   m=self.enemy; reward=10*m[1]+random.randint(4,12); self.db.execute('UPDATE p SET combat=combat+? WHERE id=1',(reward,)); drop=None
   if random.random()<.06:drop=random.choice(['Fragmento Sombrio','Amuleto Antigo','Núcleo Arcano']); self.db.execute('INSERT INTO inv(item,qty) VALUES(?,1) ON CONFLICT(item) DO UPDATE SET qty=qty+1',(drop,))
   self.db.execute('INSERT INTO battles(day,monster,result,reward,drop) VALUES(?,?,?,?,?)',(date.today().isoformat(),m[0],'Vitória',reward,drop)); self.db.commit(); self.say(f'Vitória! +{reward} XP.'+(f' Drop raro: {drop}' if drop else ' Nenhum item dropado.')); self.ehp=0
  else:self.enemyturn()
  self.refresh()
  if self.enemy:self.binfo.config(text=f'{self.enemy[0]} • Nível {self.enemy[1]}\nHP restante: {max(0,self.ehp)}\nTraço: {self.enemy[5]}')
 def enemyturn(self):
  if not self.enemy or self.ehp<=0:return
  p=self.p(); atk=self.enemy[3]
  if self.status.get('weak',0):atk=max(1,int(atk*.7)); self.status['weak']-=1
  if self.status.get('dodge',0) and random.random()<.35:self.status['dodge']-=1; self.say('Você esquiva do ataque.'); return
  d=max(1,atk+random.randint(-2,4)-int(self.stats()[1]*.25))
  if self.status.get('barrier',0):d=max(1,d//2); self.status['barrier']=0
  if 'Golpe pesado' in self.enemy[5] and random.random()<.25:d=int(d*1.5)
  hp=max(0,p['hp']-d); self.db.execute('UPDATE p SET hp=? WHERE id=1',(hp,)); self.db.commit(); self.say(f'{self.enemy[0]} causa {d}. Seu HP: {hp}/{p["maxhp"]}.')
  if hp<=0:self.db.execute('UPDATE p SET hp=maxhp/2 WHERE id=1'); self.db.commit(); self.say('Derrota. Você retorna com metade do HP; progresso preservado.')
 def build_shop(self):
  f=self.tabs['Skill Shop']; self.lab(f,'Skill Shop',font=('Segoe UI',16,'bold')).pack(anchor='w'); self.lab(f,'Catálogo inicial de protótipo; ainda não é a lista completa do site externo.').pack(anchor='w',pady=5); self.skills=ttk.Treeview(f,columns=('cat','cost','item','status'),show='headings',height=14)
  for c,t in [('cat','Categoria'),('cost','Custo SP'),('item','Item associado'),('status','Status')]:self.skills.heading(c,text=t)
  self.skills.pack(fill='both',expand=True,pady=8); ttk.Button(f,text='Comprar habilidade selecionada',command=self.buy).pack(anchor='w'); self.invlabel=self.lab(f,'Inventário: vazio'); self.invlabel.pack(anchor='w',pady=8)
 def buy(self):
  sel=self.skills.selection()
  if not sel:return
  s=self.db.execute('SELECT * FROM skills WHERE id=?',(int(sel[0]),)).fetchone()
  if self.db.execute('SELECT 1 FROM owned WHERE skill_id=?',(s['id'],)).fetchone():messagebox.showinfo('Skill Shop','Já comprada.'); return
  if self.p()['sp']<s['cost']:messagebox.showwarning('SP','Pontos insuficientes.'); return
  self.db.execute('UPDATE p SET sp=sp-? WHERE id=1',(s['cost'],)); self.db.execute('INSERT INTO owned VALUES(?)',(s['id'],)); self.db.commit(); self.refresh()
 def build_library(self):
  f=self.tabs['Biblioteca']; self.lab(f,'Necromante da Estação de Seul',font=('Segoe UI',16,'bold')).pack(anchor='w'); self.lab(f,'Capítulos ímpares: treino físico • pares: estudos. Texto da novel não está embutido; importe conteúdo autorizado.').pack(anchor='w',pady=8); row=tk.Frame(f,bg='#111827'); row.pack(anchor='w'); ttk.Button(row,text='Abrir leitor flutuante',command=self.reader).pack(side='left',padx=3); ttk.Button(row,text='Importar texto autorizado',command=self.importchapter).pack(side='left',padx=3); self.chapters=ttk.Treeview(f,columns=('source','date'),show='tree headings',height=16); self.chapters.heading('#0',text='Capítulo'); self.chapters.heading('source',text='Origem'); self.chapters.heading('date',text='Data'); self.chapters.pack(fill='both',expand=True,pady=8); self.chapters.bind('<Double-1>',lambda e:self.reader())
 def importchapter(self):
  n=simpledialog.askinteger('Capítulo','Número do capítulo:',minvalue=1)
  if not n:return
  txt=simpledialog.askstring('Texto autorizado','Cole texto que você tem autorização para reproduzir:')
  if txt:(HOME/f'chapter_{n}.txt').write_text(txt,encoding='utf-8'); messagebox.showinfo('Leitor','Texto importado.')
 def reader(self):
  sel=self.chapters.selection()
  try:n=int(sel[0]) if sel else 0
  except:n=0
  if not n:
   rows=self.db.execute('SELECT n FROM chapters ORDER BY n').fetchall(); n=rows[-1]['n'] if rows else 0
  if not n or not self.db.execute('SELECT 1 FROM chapters WHERE n=?',(n,)).fetchone():messagebox.showinfo('Biblioteca','Selecione um capítulo desbloqueado.'); return
  w=tk.Toplevel(self); w.title(f'Leitor — Capítulo {n}'); w.geometry('620x650+100+80'); w.attributes('-topmost',True); tk.Label(w,text=f'Necromante da Estação de Seul • Capítulo {n}',font=('Segoe UI',14,'bold'),bg='#111827',fg='#d2bcff').pack(fill='x',pady=10); text=tk.Text(w,wrap='word',font=('Georgia',12),bg='#0b1020',fg='#edf1ff',padx=16,pady=16); text.pack(fill='both',expand=True,padx=12,pady=8); path=HOME/f'chapter_{n}.txt'; content=path.read_text(encoding='utf-8') if path.exists() else f'Capítulo {n} desbloqueado.\n\nO texto integral não está incluído. Importe texto autorizado ou abra a página oficial.'; text.insert('1.0',content); text.config(state='disabled'); ttk.Button(w,text='Abrir página original',command=lambda:webbrowser.open('https://novelmania.com.br/novels/necromante-da-estacao-de-seul')).pack(pady=8)
 def build_config(self):
  f=self.tabs['Integração']; self.lab(f,'Integração automática com QuestHub',font=('Segoe UI',16,'bold')).pack(anchor='w'); self.lab(f,'O cliente consulta um endpoint autenticado. O patch de servidor precisa ser instalado no QuestHub para expor IDs das questões respondidas.').pack(anchor='w',pady=8); self.url=tk.StringVar(value=self.cfg.get('url','')); self.token=tk.StringVar(value=self.cfg.get('token','')); self.uid=tk.StringVar(value=str(self.cfg.get('user_id','')))
  for lab,var,show in [('URL do QuestHub',self.url,None),('Token de integração',self.token,'*'),('ID do usuário no QuestHub',self.uid,None)]:self.lab(f,lab).pack(anchor='w'); tk.Entry(f,textvariable=var,show=show,bg='#0b1020',fg='white',insertbackground='white').pack(fill='x',pady=(3,9),ipady=6)
  ttk.Button(f,text='Salvar configuração',command=self.savecfg).pack(anchor='w',pady=4); ttk.Button(f,text='Testar/sincronizar agora',command=self.sync).pack(anchor='w',pady=4); self.cfgstatus=self.lab(f,''); self.cfgstatus.pack(anchor='w',pady=8)
 def savecfg(self):self.cfg={'url':self.url.get().strip().rstrip('/'),'token':self.token.get().strip(),'user_id':self.uid.get().strip()}; CFG.write_text(json.dumps(self.cfg,indent=2)); self.cfgstatus.config(text='Configuração salva localmente.')
 def sync(self):
  c=self.cfg
  if not c.get('url') or not c.get('token') or not c.get('user_id'):messagebox.showinfo('QuestHub','Preencha URL, token e ID na aba Integração.'); return
  def worker():
   try:
    url=c['url']+'/api/integration/answered-questions?user_id='+urllib.parse.quote(str(c['user_id'])); req=urllib.request.Request(url,headers={'Authorization':'Bearer '+c['token']})
    with urllib.request.urlopen(req,timeout=15) as r:payload=json.loads(r.read())
    # A thread faz apenas a requisição HTTP. Todas as operações SQLite/Tkinter
    # são agendadas na thread principal para evitar erros de thread-safety.
    self.after(0, lambda data=payload: self.process_sync(data))
   except Exception as e:
    err=str(e)
    self.after(0, lambda err=err: messagebox.showerror('Sincronização falhou',f'{err}\nConfira o patch do QuestHub, URL e token.'))
  threading.Thread(target=worker,daemon=True).start()
 def process_sync(self,payload):
  new=[]
  for q in payload.get('questions',[]):
   qid=str(q.get('question_id',''))
   if qid and not self.db.execute('SELECT 1 FROM seen WHERE qid=?',(qid,)).fetchone():
    self.db.execute('INSERT INTO seen VALUES(?,?)',(qid,q.get('answered_at',''))); new.append(qid)
  if new:
   self.db.execute('UPDATE p SET sp=sp+? WHERE id=1',(len(new),))
   if not self.db.execute("SELECT 1 FROM chapters WHERE source='study' AND unlocked LIKE ?",(date.today().isoformat()+'%',)).fetchone():
    n=max([r[0] for r in self.db.execute("SELECT n FROM chapters WHERE source='study'")]+[0])+2
    self.db.execute('INSERT OR IGNORE INTO chapters VALUES(?,?,?)',(n,'study',datetime.now().isoformat()))
  self.db.commit()
  self.synced(len(new),len(payload.get('questions',[])))
 def synced(self,n,total):self.qstatus.config(text=f'Sincronizado: {n} questões novas de {total}. +{n} SP.'); self.refresh(); messagebox.showinfo('QuestHub',f'{n} questões novas; +{n} SP.')
 def refresh(self):
  p=self.p(); self.dash.config(text=f"HP {p['hp']}/{p['maxhp']}   •   SP {p['sp']}   •   Poções {p['potions']}\n\nResistência: {p['res']} XP\nAgilidade: {p['agi']} XP\nCombate: {p['combat']} XP\nCapítulos liberados: {self.db.execute('SELECT COUNT(*) FROM chapters').fetchone()[0]}"); self.logdash.delete('1.0','end')
  for b in self.db.execute('SELECT * FROM battles ORDER BY id DESC LIMIT 10'):self.logdash.insert('end',f"{b['day']} — {b['monster']}: {b['result']} (+{b['reward']} XP)"+(f" • drop {b['drop']}" if b['drop'] else '')+'\n')
  for i in self.sess.get_children():self.sess.delete(i)
  for s in self.db.execute('SELECT * FROM sessions ORDER BY id DESC LIMIT 20'):self.sess.insert('','end',values=(s['day'],s['exercise'],f"{s['secs']//60:02d}:{s['secs']%60:02d}",s['xp']))
  for i in self.qtree.get_children():self.qtree.delete(i)
  for q in self.db.execute('SELECT * FROM seen ORDER BY answered DESC LIMIT 100'):self.qtree.insert('','end',values=(q['qid'],q['answered']))
  for i in self.chapters.get_children():self.chapters.delete(i)
  for c in self.db.execute('SELECT * FROM chapters ORDER BY n'):self.chapters.insert('','end',iid=str(c['n']),text=f"Capítulo {c['n']}",values=('Treino físico' if c['source']=='physical' else 'Estudos',c['unlocked'][:10]))
  owned={r[0] for r in self.db.execute('SELECT skill_id FROM owned')}
  for i in self.skills.get_children():self.skills.delete(i)
  for s in self.db.execute('SELECT * FROM skills ORDER BY cost,name'):self.skills.insert('','end',iid=str(s['id']),values=(s['cat'],s['cost'],s['item'],'Comprada' if s['id'] in owned else 'Disponível'))
  self.skillbox['values']=[r[0] for r in self.db.execute('SELECT s.name FROM skills s JOIN owned o ON s.id=o.skill_id')]; inv=[f"{r['item']} ×{r['qty']}" for r in self.db.execute('SELECT * FROM inv')]; self.invlabel.config(text='Inventário: '+(', '.join(inv) if inv else 'vazio'))
 def onclose(self):self.db.close(); self.destroy()
if __name__=='__main__':
 app=Game(); app.protocol('WM_DELETE_WINDOW',app.onclose); app.mainloop()
