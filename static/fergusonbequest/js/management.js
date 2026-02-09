document.addEventListener("DOMContentLoaded", () => {

  // confirm delete
  document.querySelectorAll(".js-confirm").forEach(link => {
    link.addEventListener("click", e => {
      if (!confirm(link.dataset.confirm || "Are you sure?")) {
        e.preventDefault();
      }
    });
  });

  // auto-submit selects
  document.querySelectorAll(".mng-controls select").forEach(sel => {
    sel.addEventListener("change", () => sel.form.submit());
  });

  // search debounce
  const searchInput = document.querySelector(".mng-search input");
  let timer = null;
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => searchInput.form.submit(), 300);
    });
  }

  // tab switching
  document.querySelectorAll(".mng-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      const url = new URL(window.location);
      url.searchParams.set("tab", tab.dataset.tab);
      window.location = url.toString();
    });
  });
});
//delete config
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".js-open-confirm");
  if (!btn) return;

  const modal = document.getElementById("mngConfirm");
  const titleEl = document.getElementById("mngConfirmTitle");
  const textEl = document.getElementById("mngConfirmText");
  const yesBtn = document.getElementById("mngConfirmYes");

  titleEl.textContent = btn.dataset.title || "Confirm";
  textEl.textContent = btn.dataset.message || "Are you sure?";

  const form = btn.closest("form");
  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");

  const close = () => {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    yesBtn.onclick = null;
  };

  modal.querySelectorAll("[data-close]").forEach(el => {
    el.onclick = close;
  });

  yesBtn.onclick = () => form.submit();
});
