(() => {
  // Filter auto-submit
  const venue = document.querySelector('select[name="venue"]');
  const sort = document.querySelector('select[name="sort"]');

  if (venue) venue.addEventListener("change", () => venue.form.submit());
  if (sort) sort.addEventListener("change", () => sort.form.submit());

  // Upload/Edit modal open/close
  function setModalOpen(isOpen) {
    const modal = document.getElementById("uploadModal");
    if (!modal) return;

    modal.classList.toggle("is-open", isOpen);
    modal.setAttribute("aria-hidden", isOpen ? "false" : "true");
    modal.style.display = ""; // CSS controls actual display
  }

  function updateModalMode(mode) {
  const modal = document.getElementById("uploadModal");
  if (!modal) return;

  modal.dataset.mode = mode;

  document.querySelectorAll(".tu-bulk-only").forEach(el => {
    el.style.display = mode === "bulk" ? "" : "none";
  });

  document.querySelectorAll(".tu-individual-only").forEach(el => {
    el.style.display = mode === "individual" ? "" : "none";
  });
}
let currentRowIndex = -1;
let bookingButtons = [];

function refreshBookingButtons() {
  bookingButtons = Array.from(
    document.querySelectorAll('.tu-btn--primary[onclick*="openIndividualTicketModal"]')
  );
}

function openBookingAtIndex(index) {
  refreshBookingButtons();
  if (index < 0 || index >= bookingButtons.length) return;
  currentRowIndex = index;
  bookingButtons[index].click();
}

const prevBtn = document.getElementById("prevBookingBtn");
const nextBtn = document.getElementById("nextBookingBtn");

if (prevBtn) {
  prevBtn.addEventListener("click", () => {
    openBookingAtIndex(currentRowIndex - 1);
  });
}

if (nextBtn) {
  nextBtn.addEventListener("click", () => {
    openBookingAtIndex(currentRowIndex + 1);
  });
}

  function closeUploadModal() {
    setModalOpen(false);
  }

  // Backdrop click and ESC (upload modal)
  document.addEventListener("click", (e) => {
    const modal = document.getElementById("uploadModal");
    if (!modal || modal.getAttribute("aria-hidden") === "true") return;
    if (e.target === modal) closeUploadModal();
  });

  document.addEventListener("keydown", (e) => {
    const modal = document.getElementById("uploadModal");
    if (!modal || modal.getAttribute("aria-hidden") === "true") return;
    if (e.key === "Escape") closeUploadModal();
  });

  // Ticket type tabs and panels
  function panelKeyForType(type) {
    if (type === "codes") return "codes";
    if (type === "pdf_template_random") return "pdfs";
    if (type === "qr_individual") return "qr";
    if (type === "booking_code") return "booking_code";
    if (type === "instructions") return "instructions";
    if (type === "box_office") return "box_office";
    return "codes";
  }

  function activateTicketType(type) {
    const hiddenType = document.getElementById("ticketType");
    if (hiddenType) hiddenType.value = type || "codes";

    document.querySelectorAll(".tu-type").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.type === type);
    });

    const targetPanelKey = panelKeyForType(type);

    document.querySelectorAll(".tu-type-panel").forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.panel === targetPanelKey);
    });
  }

  document.querySelectorAll(".tu-type").forEach((btn) => {
    btn.addEventListener("click", () => activateTicketType(btn.dataset.type));
  });

  document.addEventListener("DOMContentLoaded", () => {
    const hiddenType = document.getElementById("ticketType");
    const initialType = hiddenType?.value || "codes";
    activateTicketType(initialType);
  });

  // Modal form reset helpers
  function resetModalFields() {
    const form = document.getElementById("ticketUploadForm");
    if (!form) return;

    form.querySelectorAll("input, textarea").forEach((el) => {
      const name = el.getAttribute("name") || "";
      const type = (el.getAttribute("type") || "").toLowerCase();

      if (name === "csrfmiddlewaretoken") return;
      if (type === "hidden") return;

      if (type === "checkbox") {
        el.checked = el.defaultChecked;
        return;
      }

      if (type === "file") {
        el.value = "";
        return;
      }

      el.value = "";
    });

    activateTicketType("codes");
  }


  // Open modal: Individual booking
function openIndividualTicketModal(
  bookingId,
  venueName,
  ticketType,
  ticketCode,
  ticketFileUrl,
  rowKind = 'b',
  ticketedCount = "0",
  totalCount = "0",
  triggerEl = null
) {  const form = document.getElementById("ticketUploadForm");
  if (!form) return;

  refreshBookingButtons();
  if (triggerEl) {
    currentRowIndex = bookingButtons.indexOf(triggerEl);
  }
  resetModalFields();
  const nav = document.getElementById("bookingNav");
  if (nav) nav.style.display = "";

  form.action = form.dataset.individualAction;
  updateModalMode("individual");

  const bookingIdEl = document.getElementById("modalBookingId");
  const venueEl = document.getElementById("modalVenue");
  const venueNameEl = document.getElementById("modalVenueName");

  // Get the hidden input for row_kind
  const rowKindEl = document.getElementById("modalRowKind");

  const ticketedEl = document.getElementById("ticketedCount");
  const totalEl = document.getElementById("ticketTotal");

  if (ticketedEl) ticketedEl.textContent = ticketedCount || "0";
  if (totalEl) totalEl.textContent = totalCount || "0";

  if (bookingIdEl) bookingIdEl.value = bookingId || "";

  // Set 'b' for booking or 'd' for draw
  if (rowKindEl) rowKindEl.value = rowKind;

  if (venueEl) venueEl.value = "";

  // Adjust label to show if it's a Draw or Booking
  const labelPrefix = rowKind === 'd' ? "Draw Entry" : "Booking";
  if (venueNameEl) venueNameEl.textContent = `${venueName || "—"} (${labelPrefix} #${bookingId})`;

  if (ticketType) activateTicketType(ticketType);

    if (ticketType === "booking_code") {
      const codeInput = document.querySelector('input[name="booking_code"]');
      if (codeInput) codeInput.value = ticketCode || "";
    }

    //  PDF hint
    if (ticketFileUrl) {
      const pdfPanel = document.querySelector('.tu-type-panel[data-panel="pdfs"]');
      if (pdfPanel) {
        let hint = pdfPanel.querySelector(".tu-existing-file-hint");
        if (!hint) {
          hint = document.createElement("div");
          hint.className = "tu-hint tu-existing-file-hint";
          pdfPanel.appendChild(hint);
        }
        hint.innerHTML = `Existing file: <a href="${ticketFileUrl}" target="_blank" rel="noopener">view</a> (upload to replace)`;
      }
    } else {
      document.querySelectorAll(".tu-existing-file-hint").forEach((el) => el.remove());
    }
    const labelEl = document.getElementById("ticketedLabel");
    const ticketedWrap = document.getElementById("ticketedInfo");

    if (rowKind === "d") {
      if (ticketedWrap) ticketedWrap.style.display = "none";
    } else {
      if (ticketedWrap) ticketedWrap.style.display = "";
      if (labelEl) labelEl.textContent = "Ticketed for specific attraction (excluding draws)";
    }
    setModalOpen(true);
  }

// Open modal: Bulk venue distribute
function openUploadModal() {
  const form = document.getElementById("ticketUploadForm");
  if (!form) return;

  const venueSelect = document.querySelector('select[name="venue"]');
  const venueId = venueSelect?.value || "";

  if (!venueId) {
    const deleteModal = document.getElementById("deleteModal");
    const deleteTitle = document.getElementById("deleteTitle");
    const deleteModalText = document.getElementById("deleteModalText");
    const confirmBtn = deleteModal?.querySelector('button[type="submit"]');
    const cancelBtn = deleteModal?.querySelector('button[type="button"]');
    openAlertModal("No Venue Selected", "Please select a venue first from the dropdown.");
    return;

    if (deleteTitle) deleteTitle.textContent = "No Venue Selected";
    if (deleteModalText) {
      deleteModalText.textContent = "Please select a venue first from the dropdown.";
      deleteModalText.style.color = "#000";
    }

    if (confirmBtn) {
      confirmBtn.textContent = "OK";
      confirmBtn.style.background = "#002a4c";
      confirmBtn.style.color = "#fff";
      confirmBtn.style.marginLeft = "auto";
      confirmBtn.onclick = function (e) {
        e.preventDefault();
        setDeleteModalOpen(false);
      };
    }

    if (cancelBtn) {
      cancelBtn.style.display = "none";
    }

    setDeleteModalOpen(true);
    return;
  }

  const opt = venueSelect.options?.[venueSelect.selectedIndex];
  const ticketed = opt?.dataset.ticketed || "0";
  const total = opt?.dataset.total || "0";

  const ticketedEl = document.getElementById("ticketedCount");
  const totalEl = document.getElementById("ticketTotal");
  const labelEl = document.getElementById("ticketedLabel");

  if (ticketedEl) ticketedEl.textContent = ticketed;
  if (totalEl) totalEl.textContent = total;
  if (labelEl) labelEl.textContent = "Ticketed for specific attraction";

  resetModalFields();
  updateModalMode("bulk");
  form.action = form.dataset.venueAction;

  const venueEl = document.getElementById("modalVenue");
  const bookingIdEl = document.getElementById("modalBookingId");
  const venueNameEl = document.getElementById("modalVenueName");
  const rowKindEl = document.getElementById("modalRowKind");
  const nav = document.getElementById("bookingNav");

  if (venueEl) venueEl.value = venueId;
  if (bookingIdEl) bookingIdEl.value = "";
  if (venueNameEl) venueNameEl.textContent = opt?.text || "—";
  if (rowKindEl) rowKindEl.value = "b";
  if (nav) nav.style.display = "none";

  setModalOpen(true);
}

  // Delete modal open/close (single)
  function setDeleteModalOpen(isOpen) {
    const modal = document.getElementById("deleteModal");
    if (!modal) return;

    modal.classList.toggle("is-open", isOpen);
    modal.setAttribute("aria-hidden", isOpen ? "false" : "true");
    modal.style.display = "";
  }

  function closeDeleteModal() {
    setDeleteModalOpen(false);
  }

function openDeleteSingleModal(rowId, venueName, rowKind = "b") {
  const text = document.getElementById("deleteModalText");
  const idInput = document.getElementById("deleteRowId");
  const kindInput = document.getElementById("deleteRowKind");

  if (idInput) idInput.value = rowId || "";
  if (kindInput) kindInput.value = rowKind || "b";

  if (text) {
    const label = rowKind === "d" ? "Draw booking" : "Booking";
    text.textContent = `Are you sure you want to delete the ticket for ${venueName || "this booking"} (${label} #${rowId})?`;
  }

  setDeleteModalOpen(true);
}

  // Backdrop click and ESC (delete modal)
  document.addEventListener("click", (e) => {
    const modal = document.getElementById("deleteModal");
    if (!modal || modal.getAttribute("aria-hidden") === "true") return;
    if (e.target === modal) closeDeleteModal();
  });

  document.addEventListener("keydown", (e) => {
    const modal = document.getElementById("deleteModal");
    if (!modal || modal.getAttribute("aria-hidden") === "true") return;
    if (e.key === "Escape") closeDeleteModal();
  });

  // Bulk select-all and counter
  const selectAll = document.getElementById("selectAllBookings");
  const countHint = document.getElementById("selectedCountHint");

  function updateSelectedCount() {
    const checks = document.querySelectorAll(".rowChk");
    const checked = document.querySelectorAll(".rowChk:checked");
    if (countHint) countHint.textContent = `${checked.length} selected`;
    if (selectAll && checks.length) selectAll.checked = checked.length === checks.length;
  }

  if (selectAll) {
    selectAll.addEventListener("change", () => {
      document.querySelectorAll(".rowChk").forEach((c) => (c.checked = selectAll.checked));
      updateSelectedCount();
    });
  }

  document.querySelectorAll(".rowChk").forEach((chk) => {
    chk.addEventListener("change", updateSelectedCount);
  });

  updateSelectedCount();

  // Bulk delete confirmation modal
  const bulkDeleteForm = document.getElementById("bulkDeleteForm");
  const deleteModal = document.getElementById("deleteModal");
  const deleteTitle = document.getElementById("deleteTitle");
  const deleteModalText = document.getElementById("deleteModalText");
  // Get the "Delete selected" button
  const deleteSelectedBtn = document.querySelector('button[form="bulkDeleteForm"]');

  if (deleteSelectedBtn && bulkDeleteForm) {
    // Override form submission
    deleteSelectedBtn.addEventListener('click', function(e) {
      e.preventDefault();

      // Count checked items
      const checkedBoxes = bulkDeleteForm.querySelectorAll('input[name="selected_ids"]:checked');
      const count = checkedBoxes.length;

      if (count === 0) {
        openAlertModal("Error", "Please select at least one ticket to delete.");
        return;
      }

      // Update modal text with count
      deleteTitle.textContent = 'Delete selected tickets';
      deleteModalText.textContent = `Are you sure you want to delete ${count} ticket(s)? This action cannot be undone.`;
      deleteModalText.style.color = '';  // Reset color
      // Reset confirm button text and action for actual deletion
      const confirmBtn = deleteModal.querySelector('button[type="submit"]');
      const cancelBtn = deleteModal.querySelector('button[type="button"]');

      if (confirmBtn) {
        confirmBtn.textContent = 'confirm';
        confirmBtn.style.background = '';
        confirmBtn.style.color = '';
        confirmBtn.onclick = function(e) {
          e.preventDefault();
          bulkDeleteForm.submit();
        };
      }

      // Show modal
      setDeleteModalOpen(true);
    });
  }

  // Expose functions used inline HTML onclick=
  window.openUploadModal = openUploadModal;
  window.closeUploadModal = closeUploadModal;
  window.openIndividualTicketModal = openIndividualTicketModal;
  window.closeAlertModal = closeAlertModal;
  window.openAlertModal = openAlertModal;
  window.openDeleteSingleModal = openDeleteSingleModal;
  window.closeDeleteModal = closeDeleteModal;
})();

function setAlertModalOpen(isOpen) {
  const modal = document.getElementById("alertModal");
  if (!modal) return;

  modal.classList.toggle("is-open", isOpen);
  modal.setAttribute("aria-hidden", isOpen ? "false" : "true");
  modal.style.display = "";
}

function closeAlertModal() {
  setAlertModalOpen(false);
}

function openAlertModal(title, message) {
  const titleEl = document.getElementById("alertTitle");
  const textEl = document.getElementById("alertModalText");

  if (titleEl) titleEl.textContent = title || "Notice";
  if (textEl) textEl.textContent = message || "";

  setAlertModalOpen(true);
}

//ticket count
function updateCodeCountHint(){
  const el = document.getElementById("tuCodeCount");
  const ta = document.querySelector('textarea[name="codes_text"]');
  if(!el || !ta) return;

  const count = ta.value.split(/\r?\n/).map(x => x.trim()).filter(Boolean).length;
  el.textContent = `Codes entered: ${count}`;
}

document.addEventListener("input", e=>{
    if(e.target.name === "codes_text"){
        updateCodeCountHint();
    }
});

// Advanced filters modal
(function () {
  const modal = document.getElementById("advanced-filters-modal");
  const openBtn = document.getElementById("advanced-filters-btn");
  const closeBtn = document.getElementById("advanced-filters-close");

  if (!modal || !openBtn || !closeBtn) return;

  function setAdvancedFiltersOpen(isOpen) {
    modal.classList.toggle("is-open", isOpen);
    modal.setAttribute("aria-hidden", isOpen ? "false" : "true");
  }

  openBtn.addEventListener("click", () => setAdvancedFiltersOpen(true));
  closeBtn.addEventListener("click", () => setAdvancedFiltersOpen(false));

  modal.addEventListener("click", (e) => {
    if (
      e.target === modal ||
      e.target.classList.contains("tu-advanced-modal__backdrop")
    ) {
      setAdvancedFiltersOpen(false);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setAdvancedFiltersOpen(false);
  });
})();