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

function renderTicketInputs(numTickets) {
  const n = parseInt(numTickets, 10) || 1;
  const activeType = document.getElementById("ticketType")?.value || "codes";
  const mode = document.getElementById("uploadModal")?.dataset.mode || "individual";

  // Ticket codes
  if (activeType === "codes") {
    const ta = mode === "bulk"
      ? document.getElementById("bulkCodesText")
      : document.getElementById("singleCodesText");

    const hint = mode === "bulk"
      ? document.getElementById("bulkCodeCountHint")
      : document.getElementById("singleCodeCountHint");

    if (ta && hint) {
      const updateCodeCounter = () => {
        const count = ta.value
          .split(/\r?\n/)
          .map(x => x.trim())
          .filter(Boolean).length;

        hint.textContent = `${count} / ${n} codes entered (Required: ${n})`;
        hint.style.color = (count === n) ? "#28a745" : "#dc3545";
      };

      updateCodeCounter();
      ta.oninput = updateCodeCounter;
    }
  }

  // PDF tickets
  if (activeType === "pdf_template" || activeType === "pdf_template_random") {
    const input = document.getElementById("ticketFilesInput");
    const hint = document.getElementById("pdfUploadStatusHint");

    if (input && hint) {
      const updatePdfCounter = () => {
        const count = input.files.length;
        hint.textContent = `${count} / ${n} files selected (Required: ${n})`;
        hint.style.color = (count === n) ? "#28a745" : "#dc3545";
      };

      updatePdfCounter();
      input.onchange = updatePdfCounter;
    }
  }

  // QR ticket files
  if (activeType === "qr_individual") {
    const input = mode === "bulk"
      ? document.getElementById("qrFilesBulk")
      : document.getElementById("qrFilesIndividual");

    const hint = mode === "bulk"
      ? document.getElementById("qrBulkUploadStatusHint")
      : document.getElementById("qrIndividualUploadStatusHint");

    if (input && hint) {
      const updateQrCounter = () => {
        const count = input.files.length;
        hint.textContent = `${count} / ${n} files selected (Required: ${n})`;
        hint.style.color = (count === n) ? "#28a745" : "#dc3545";
      };

      updateQrCounter();
      input.onchange = updateQrCounter;
    }
  }
}

  function activateTicketType(type) {
    const hiddenType = document.getElementById("ticketType");
    if (hiddenType) hiddenType.value = type || "codes";

    document.querySelectorAll(".tu-type").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.type === type);
    });

    const targetPanelKey = panelKeyForType(type);
    const numTickets = document.getElementById("modalNumTickets")?.value || 1;
        renderTicketInputs(numTickets);

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



// Add a validation check to the form submission
const ticketUploadForm = document.getElementById("ticketUploadForm");

if (ticketUploadForm) {
  ticketUploadForm.onsubmit = function (e) {
    const mode = document.getElementById("uploadModal")?.dataset.mode || "individual";
    const type = document.getElementById("ticketType")?.value;
    const n = parseInt(document.getElementById("modalNumTickets")?.value, 10) || 1;

    if (type === "qr_individual") {
      const input = mode === "bulk"
        ? document.getElementById("qrFilesBulk")
        : document.getElementById("qrFilesIndividual");

      const count = input?.files.length || 0;

      if (count !== n) {
        e.preventDefault();
        alert(`Please upload exactly ${n} file(s). You have selected ${count}.`);
        return false;
      }
    }

    else if (["pdf_template", "pdf_template_random"].includes(type)) {
      const input = document.getElementById("ticketFilesInput");
      const files = Array.from(input?.files || []);
      const count = files.length;

      if (count !== n) {
        e.preventDefault();
        alert(`Please upload exactly ${n} PDF file(s). You have selected ${count}.`);
        return false;
      }

      const badFile = files.find(file => {
        const name = (file.name || "").toLowerCase();
        const mime = (file.type || "").toLowerCase();
        return !(name.endsWith(".pdf") || mime === "application/pdf");
      });

      if (badFile) {
        e.preventDefault();
        alert(`"${badFile.name}" is not a PDF. Please upload PDF files only.`);
        return false;
      }
    }

    else if (type === "codes") {
      const ta = mode === "bulk"
        ? document.querySelector('textarea[name="codes_text"]')
        : document.getElementById("singleCodesText");

      const codesFileInput = document.querySelector('input[name="codes_file"]');
      const hasCodesFile = mode === "bulk" && codesFileInput && codesFileInput.files && codesFileInput.files.length > 0;

      const count = (ta?.value || "")
        .split(/\r?\n/)
        .map(x => x.trim())
        .filter(Boolean).length;

      // If a file has been uploaded in bulk mode, let the backend parse and validate it.
      if (!hasCodesFile && count !== n) {
        e.preventDefault();
        alert(`Please enter exactly ${n} code(s). You have entered ${count}.`);
        return false;
      }
    }

    return true;
  };
}

// Open modal: Bulk venue distribute
function openUploadModal() {
  const form = document.getElementById("ticketUploadForm");
  if (!form) return;

  const venueSelect = document.querySelector('select[name="venue"]');
  const venueId = venueSelect?.value || "";

  if (!venueId) {
    openAlertModal("No Venue Selected", "Please select a venue first from the dropdown.");
    return;
  }

  const opt = venueSelect.options?.[venueSelect.selectedIndex];
  const ticketed = opt?.dataset.ticketed || "0";
  const total = opt?.dataset.total || "0";

  const needed = Math.max(0, (parseInt(total, 10) || 0) - (parseInt(ticketed, 10) || 0));
  const numTicketsEl = document.getElementById("modalNumTickets");
  if (numTicketsEl) numTicketsEl.value = needed;

  const ticketedEl = document.getElementById("ticketedCount");
  const totalEl = document.getElementById("ticketTotal");
  const labelEl = document.getElementById("ticketedLabel");
  const ticketedWrap = document.getElementById("ticketedInfo");

  if (venueId.startsWith("d-")) {
    if (ticketedWrap) ticketedWrap.style.display = "none";
  } else {
    if (ticketedWrap) ticketedWrap.style.display = "";
    if (ticketedEl) ticketedEl.textContent = ticketed;
    if (totalEl) totalEl.textContent = total;
    if (labelEl) labelEl.textContent = "Ticketed for specific attraction";
  }

  updateModalMode("bulk");

  if (form.dataset.venueAction) {
    form.action = form.dataset.venueAction;
  }

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

  // Always reset bulk modal to a supported bulk type
  activateTicketType("codes");

  setModalOpen(true);
}

let _ticketPages = [];
let _ticketIdx = 0;

function _showTicketPage(body) {
  const entry = _ticketPages[_ticketIdx];
  const prev = document.getElementById("ticketPrev");
  const next = document.getElementById("ticketNext");
  const multi = _ticketPages.length > 1;

  if (prev) prev.style.display = multi ? "" : "none";
  if (next) next.style.display = multi ? "" : "none";

  const counter = multi
    ? `<div style="text-align:center;font-size:0.85em;color:#666;margin-bottom:8px;">
         Ticket ${_ticketIdx + 1} of ${_ticketPages.length}
       </div>`
    : "";

  if (entry.type === "image") {
    body.innerHTML = `
      ${counter}
      <div style="display:flex;justify-content:center;">
        <img src="${entry.url}" alt="Ticket image" style="max-width:100%;height:auto;">
      </div>`;
  } else if (entry.type === "pdf") {
    body.innerHTML = `
      ${counter}
      <div style="height:60vh;">
        <iframe src="${entry.url}" style="width:100%;height:100%;border:0;"></iframe>
      </div>
      <div style="margin-top:12px;">
        <a class="tu-btn tu-btn--primary" href="${entry.url}" target="_blank" rel="noopener">Open PDF</a>
      </div>`;
  } else {
    body.innerHTML = `
      ${counter}
      <pre style="white-space:pre-wrap;margin:0;">${escapeHtml(entry.text)}</pre>`;
  }
}

async function _fetchAndPushPage(url) {
  const res = await fetch(url, {
    headers: { "X-Requested-With": "XMLHttpRequest" },
    credentials: "same-origin",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch ${url}: ${res.status}`);
  }

  const ct = (res.headers.get("content-type") || "").toLowerCase();

  if (ct.startsWith("image/")) {
    const blob = await res.blob();
    _ticketPages.push({ type: "image", url: URL.createObjectURL(blob) });
  } else if (ct.includes("application/pdf")) {
    const blob = await res.blob();
    _ticketPages.push({ type: "pdf", url: URL.createObjectURL(blob) });
  } else {
    const text = await res.text();
    _ticketPages.push({ type: "text", text });
  }
}

window.openTicketViewModal = openTicketViewModal;
window.closeTicketViewModal = closeTicketViewModal;

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
function openIndividualTicketModal(
  bookingId,
  venueName,
  firstName,
  lastName,
  guid,
  rowKind,
  ticketedCount,
  totalCount,
  numTickets,
  btn,
  ticketType,
  ticketCode,
  ticketInstructions,
  ticketQrValue,
  boxOfficeNotes,
  genericBookingCode
) {
  const form = document.getElementById("ticketUploadForm");
  if (!form) return;

  updateModalMode("individual");

  if (form.dataset.individualAction) {
    form.action = form.dataset.individualAction;
  }

  const venueEl = document.getElementById("modalVenue");
  const bookingIdEl = document.getElementById("modalBookingId");
  const venueNameEl = document.getElementById("modalVenueName");
  const rowKindEl = document.getElementById("modalRowKind");
  const numTicketsEl = document.getElementById("modalNumTickets");
  const ticketedEl = document.getElementById("ticketedCount");
  const totalEl = document.getElementById("ticketTotal");
  const ticketedWrap = document.getElementById("ticketedInfo");
  const nav = document.getElementById("bookingNav");

  if (venueEl) venueEl.value = "";
  if (bookingIdEl) bookingIdEl.value = bookingId || "";
  if (venueNameEl) venueNameEl.textContent = venueName || "—";
  if (rowKindEl) rowKindEl.value = rowKind || "b";
  if (numTicketsEl) numTicketsEl.value = numTickets || "1";

  if (ticketedWrap) ticketedWrap.style.display = "";
  if (ticketedEl) ticketedEl.textContent = ticketedCount || "0";
  if (totalEl) totalEl.textContent = totalCount || "0";
  if (nav) nav.style.display = "";

  // If editing an existing ticket, pre-fill the form with existing data
  if (ticketType && ticketType !== "—") {
    activateTicketType(ticketType);

    // Pre-fill based on ticket type
    if (ticketType === "codes") {
      const textarea = document.getElementById("singleCodesText");
      if (textarea && ticketCode) {
        textarea.value = ticketCode;
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
      }
    } else if (ticketType === "instructions") {
      const textarea = document.querySelector('[name="instructions"]');
      if (textarea && ticketInstructions) {
        textarea.value = ticketInstructions;
      }
    } else if (ticketType === "booking_code") {
      const input = document.querySelector('[name="booking_code"]');
      if (input && genericBookingCode) {
        input.value = genericBookingCode;
      }
    } else if (ticketType === "box_office") {
      const textarea = document.querySelector('[name="box_office_notes"]');
      if (textarea && boxOfficeNotes) {
        textarea.value = boxOfficeNotes;
      }
    } else if (ticketType === "qr_individual") {
      const textarea = document.querySelector('[name="ticket_qr_values_individual"]');
      if (textarea && ticketQrValue) {
        textarea.value = ticketQrValue;
      }
    }
  } else {
    activateTicketType("codes");
  }

  renderTicketInputs(numTickets || 1);
  setModalOpen(true);

  refreshBookingButtons();
  if (btn) currentRowIndex = bookingButtons.indexOf(btn);
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