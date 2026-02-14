document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("bookingForm");
  if (!form) return;

  const openBtn = document.getElementById("openTermsModal");
  const modal = document.getElementById("termsModal");
  const agreeCb = document.getElementById("termsAgreeCheckbox");
  const finalBtn = document.getElementById("finalConfirmBooking");

  // Hidden agreed_terms controlled by modal
  const agreedTermsHidden = document.getElementById("id_agreed_terms");

  // ---- helpers ----
  function openModal() {
    if (!modal) return;
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");

    if (agreeCb) agreeCb.checked = false;
    if (finalBtn) finalBtn.disabled = true;

    document.documentElement.classList.add("fb-modal-open");
    document.body.classList.add("fb-modal-open");
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");

    document.documentElement.classList.remove("fb-modal-open");
    document.body.classList.remove("fb-modal-open");
  }

  function setAgreedTermsTrue() {
    if (agreedTermsHidden) agreedTermsHidden.value = "true";
  }

  function setAgreedTermsFalse() {
    if (agreedTermsHidden) agreedTermsHidden.value = "false";
  }

  // ---- inline red popup errors ----
  function removeInlineError(el) {
    const next = el?.nextElementSibling;
    if (next && next.classList.contains("fb-field-error")) next.remove();
  }

  function markFieldInvalid(el, message) {
    el.classList.add("fb-invalid");
    removeInlineError(el);

    const msg = document.createElement("div");
    msg.className = "fb-field-error";
    msg.textContent = message || "Required.";
    el.insertAdjacentElement("afterend", msg);
  }

  function clearFieldError(el) {
    if (!el || !(el instanceof HTMLElement)) return;
    el.classList.remove("fb-invalid");
    removeInlineError(el);
  }

  function clearAllFieldErrors() {
    form.querySelectorAll(".fb-invalid").forEach((el) => el.classList.remove("fb-invalid"));
    form.querySelectorAll(".fb-field-error").forEach((m) => m.remove());
  }

  function validateRequiredFields() {
    clearAllFieldErrors();
    let firstInvalid = null;

    const fields = form.querySelectorAll("input, select, textarea");
    fields.forEach((el) => {
      if (el.type === "hidden" || el.disabled) return;

      // agreed_terms is handled by modal only
      if (el.name === "agreed_terms") return;

      const isRequired =
        el.required ||
        el.getAttribute("aria-required") === "true" ||
        el.dataset.required === "true";

      if (!isRequired) return;

      if (el.type === "checkbox") {
        if (!el.checked) {
          markFieldInvalid(el, "Required.");
          if (!firstInvalid) firstInvalid = el;
        }
        return;
      }

      if (!String(el.value || "").trim()) {
        markFieldInvalid(el, "Required.");
        if (!firstInvalid) firstInvalid = el;
      }
    });

    if (firstInvalid) {
      firstInvalid.focus({ preventScroll: false });
      return false;
    }
    return true;
  }

  // live clearing
  form.addEventListener("input", (e) => clearFieldError(e.target));
  form.addEventListener("change", (e) => clearFieldError(e.target));

  // Click "Confirm booking" -> validate -> open terms modal
  if (openBtn) {
    openBtn.addEventListener("click", () => {
      setAgreedTermsFalse();
      const ok = validateRequiredFields();
      if (!ok) return;
      openModal();
    });
  }

  // enable final confirm only when they tick agree
  if (agreeCb && finalBtn) {
    agreeCb.addEventListener("change", () => {
      finalBtn.disabled = !agreeCb.checked;
    });
  }

  // Final confirm -> set agreed_terms true -> submit
  if (finalBtn) {
    finalBtn.addEventListener("click", () => {
      if (agreeCb && !agreeCb.checked) return;
      setAgreedTermsTrue();
      closeModal();
      form.submit();
    });
  }

  // Close modal handlers
  if (modal) {
    modal.addEventListener("click", (e) => {
      const target = e.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.dataset.closeModal === "1") closeModal();
    });
  }

  // Escape closes modal
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal?.classList.contains("is-open")) closeModal();
  });
});