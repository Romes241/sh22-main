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