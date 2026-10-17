async function postJSON(url,data={}){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});let j={};try{j=await r.json()}catch{}if(!r.ok)throw new Error(j.error||`Erro ${r.status}`);return j}
function showMessage(el,msg,isError=false){if(!el)return;el.textContent=msg;el.classList.toggle('error-text',isError)}
