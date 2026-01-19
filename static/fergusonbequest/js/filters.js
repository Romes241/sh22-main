document.addEventListener('DOMContentLoaded', function () {
  const openBtn = document.getElementById('advanced-filters-btn');
  const modal = document.getElementById('advanced-filters-modal');
  const closeBtn = document.getElementById('advanced-filters-close');
  const backdrop = modal && modal.querySelector('.bh-modal__backdrop');

  function openModal() {
    if (!modal) return;
    modal.setAttribute('aria-hidden', 'false');
    modal.classList.add('open');
    // focus first input
    const first = modal.querySelector('input,select,button');
    if (first) first.focus();
    document.body.classList.add('bh-modal-open');
  }

  function closeModal() {
    if (!modal) return;
    modal.setAttribute('aria-hidden', 'true');
    modal.classList.remove('open');
    document.body.classList.remove('bh-modal-open');
    if (openBtn) openBtn.focus();
  }

  if (openBtn) openBtn.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (backdrop) backdrop.addEventListener('click', closeModal);

  // close on escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      if (modal && modal.classList.contains('open')) closeModal();
    }
  });
});
