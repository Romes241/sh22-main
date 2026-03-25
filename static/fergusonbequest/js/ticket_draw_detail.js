document.addEventListener("DOMContentLoaded", function () {
  const config = window.ticketDrawConfig || {};
  const maxAllowed = parseInt(config.remainingAllowance || 0, 10);

  const selector = document.getElementById("slot-selector");
  const display = document.getElementById("tickets-left");
  const ticketInput = document.getElementById("ticket-count");

  const drawForm = document.getElementById("drawEntryForm");
  const openTermsModalBtn = document.getElementById("openTermsModal");
  const termsModal = document.getElementById("termsModal");
  const closeTermsModalBtn = document.getElementById("closeTermsModal");
  const confirmTermsBtn = document.getElementById("confirmTerms");
  const agreeTermsCheckbox = document.getElementById("agreeTerms");
  const agreedTermsInput = document.getElementById("agreedTermsInput");

  function updateUI() {
    if (!selector || !display || !ticketInput) return;

    const selected = selector.options[selector.selectedIndex];
    if (!selected || !selected.dataset.remaining) return;

    const remaining = parseInt(selected.dataset.remaining, 10);
    display.textContent = remaining + " Left";

    const maxTickets = Math.min(remaining, maxAllowed);
    ticketInput.max = maxTickets;

    if (parseInt(ticketInput.value || "0", 10) > maxTickets) {
      ticketInput.value = maxTickets;
    }
  }

  if (selector) {
    selector.addEventListener("change", updateUI);
    updateUI();
  }

  if (ticketInput) {
    ticketInput.addEventListener("input", function () {
      const currentValue = parseInt(this.value || "0", 10);
      if (currentValue > maxAllowed) {
        alert("You cannot exceed the entry limit for this draw!");
        this.value = maxAllowed;
      }
    });
  }

  if (openTermsModalBtn && termsModal) {
    openTermsModalBtn.addEventListener("click", function () {
      termsModal.classList.remove("hidden");

      if (agreeTermsCheckbox) {
        agreeTermsCheckbox.checked = false;
      }
      if (confirmTermsBtn) {
        confirmTermsBtn.disabled = true;
      }
      if (agreedTermsInput) {
        agreedTermsInput.value = "false";
      }
    });
  }

  if (closeTermsModalBtn && termsModal) {
    closeTermsModalBtn.addEventListener("click", function () {
      termsModal.classList.add("hidden");
    });
  }

  if (agreeTermsCheckbox && confirmTermsBtn) {
    agreeTermsCheckbox.addEventListener("change", function () {
      confirmTermsBtn.disabled = !this.checked;
    });
  }

  if (confirmTermsBtn && drawForm) {
    confirmTermsBtn.addEventListener("click", function () {
      if (agreedTermsInput) {
        agreedTermsInput.value = "true";
      }
      drawForm.submit();
    });
  }

  if (termsModal) {
    termsModal.addEventListener("click", function (e) {
      if (e.target === termsModal) {
        termsModal.classList.add("hidden");
      }
    });
  }
});