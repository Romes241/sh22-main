document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("termsModal");
  const checkbox = document.getElementById("agreeTermsCheckbox");
  const confirmBtn = document.getElementById("confirmTermsBtn");
  const cancelBtn = document.getElementById("cancelTermsBtn");
  const backdrop = document.querySelector(".terms-modal-backdrop");

  let currentFormId = null;

  document.querySelectorAll(".open-terms-modal").forEach((btn) => {
    btn.addEventListener("click", function () {
      currentFormId = this.dataset.targetForm;
      modal.classList.remove("hidden");
      checkbox.checked = false;
      confirmBtn.disabled = true;
    });
  });

  checkbox.addEventListener("change", function () {
    confirmBtn.disabled = !this.checked;
  });

  confirmBtn.addEventListener("click", function () {
    if (!currentFormId) return;

    const form = document.getElementById(currentFormId);
    if (!form) return;

    const agreedInput = form.querySelector(".agreed-terms-input");
    if (agreedInput) {
      agreedInput.value = "true";
    }

    form.submit();
  });

  function closeModal() {
    modal.classList.add("hidden");
  }

  cancelBtn.addEventListener("click", closeModal);

  if (backdrop) {
    backdrop.addEventListener("click", closeModal);
  }
});