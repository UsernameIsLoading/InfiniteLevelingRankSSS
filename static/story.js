(()=>{
  const dialog=document.querySelector('#reader');
  const title=document.querySelector('#readerTitle');
  const text=document.querySelector('#readerText');
  let active=1;
  document.querySelectorAll('.chapter-card').forEach(button=>{
    button.addEventListener('click',()=>{
      active=Number(button.dataset.chapter);
      title.textContent='Capítulo '+active;
      text.value=localStorage.getItem('necromante.chapter.'+active)||'';
      dialog.showModal();
    });
  });
  document.querySelector('#closeReader').addEventListener('click',()=>dialog.close());
  document.querySelector('#saveReaderText').addEventListener('click',()=>{
    localStorage.setItem('necromante.chapter.'+active,text.value);
    alert('Texto guardado neste navegador.');
  });
  document.querySelectorAll('.unlock-chapter').forEach(button=>{
    button.addEventListener('click',async()=>{
      const input=document.getElementById(button.dataset.input);
      const n=Number(input.value);
      if(!Number.isInteger(n)||n<1||n>9999){showMessage(document.querySelector('#storyMessage'),'Número de capítulo inválido.',true);return;}
      const expected=button.dataset.input==='oddChapter'?1:0;
      if(n%2!==expected){showMessage(document.querySelector('#storyMessage'),'Use um capítulo '+(expected?'ímpar':'par')+'.',true);return;}
      button.disabled=true;
      try{
        await postJSON('/api/chapter/unlock',{number:n});
        showMessage(document.querySelector('#storyMessage'),'Capítulo desbloqueado! Atualizando biblioteca…');
        setTimeout(()=>location.reload(),700);
      }catch(error){showMessage(document.querySelector('#storyMessage'),error.message,true);button.disabled=false;}
    });
  });
})();
