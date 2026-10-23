document.querySelector('#questionForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const input = document.querySelector('#questionCount');
  const button = form.querySelector('button[type="submit"]');
  const count = Number.parseInt(input.value, 10);
  if (!Number.isInteger(count) || count < 1 || count > 10000) { showMessage(document.querySelector('#questionMessage'), 'Informe um número entre 1 e 10.000.', true); return; }
  button.disabled = true;
  try {
    const result = await postJSON('/api/questions/add', { count });
    showMessage(document.querySelector('#questionMessage'), `${result.message} Total registrado: ${result.total_questions}. Saldo: ${result.skill_points} SP.`);
    setTimeout(() => location.reload(), 1100);
  } catch (error) {
    showMessage(document.querySelector('#questionMessage'), error.message, true);
    button.disabled = false;
  }
});
