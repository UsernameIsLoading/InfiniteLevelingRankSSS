(()=>{
const $=id=>document.getElementById(id), openBtn=$('openTutor'), closeBtn=$('closeTutor'), gate=$('tutorGate'), chat=$('tutorChat'), clock=$('tutorClock'), form=$('tutorForm'), input=$('tutorInput'), messages=$('tutorMessages'), error=$('tutorError'), send=$('tutorSend');
let remaining=(Number(clock.textContent.split(':')[0])*60)+Number(clock.textContent.split(':')[1]), timer=null, heartbeat=null, history=[];
const fmt=n=>`${String(Math.floor(Math.max(0,n)/60)).padStart(2,'0')}:${String(Math.max(0,n)%60).padStart(2,'0')}`;
const post=async(url,body={})=>{const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw new Error(d.error||'Falha na solicitação.');return d};
const add=(role,text)=>{const el=document.createElement('div');el.className='tutor-bubble '+role;el.textContent=text;messages.appendChild(el);messages.scrollTop=messages.scrollHeight;};
const showTime=()=>{clock.textContent=fmt(remaining);if(remaining<=0){pause(false);$('tutorNotice').textContent='O tempo de hoje acabou.';openBtn.disabled=true;}};
async function sync(){try{const d=await post('/api/tutor/heartbeat');remaining=d.remaining;showTime();}catch(e){clearInterval(heartbeat);heartbeat=null;}}
function pause(sendClose=true){clearInterval(timer);clearInterval(heartbeat);timer=heartbeat=null;chat.hidden=true;gate.hidden=false;if(sendClose)post('/api/tutor/close').then(d=>{remaining=d.remaining;showTime()}).catch(()=>{});}
openBtn?.addEventListener('click',async()=>{try{const d=await post('/api/tutor/open');remaining=d.remaining;gate.hidden=true;chat.hidden=false;error.textContent='';showTime();timer=setInterval(()=>{remaining=Math.max(0,remaining-1);showTime()},1000);heartbeat=setInterval(sync,10000);input.focus();}catch(e){$('tutorNotice').textContent=e.message;}});
closeBtn?.addEventListener('click',()=>pause(true));
form?.addEventListener('submit',async e=>{e.preventDefault();const message=input.value.trim();if(!message||remaining<=0)return;add('user',message);history.push({role:'user',content:message});input.value='';send.disabled=true;error.textContent='A IA está pensando…';try{const d=await post('/api/tutor/chat',{message,history:history.slice(-10,-1)});add('assistant',d.answer);history.push({role:'assistant',content:d.answer});error.textContent='';}catch(err){error.textContent=err.message;}finally{send.disabled=false;input.focus();}});
window.addEventListener('pagehide',()=>{if(timer)navigator.sendBeacon('/api/tutor/close',new Blob(['{}'],{type:'application/json'}));});
showTime();
})();
