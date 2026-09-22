document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const voteForm = document.querySelector("#vote-form");
  if (voteForm) {
    voteForm.addEventListener("submit", (event) => {
      const selected = voteForm.querySelector("input[name='candidate_id']:checked");
      if (!selected) {
        event.preventDefault();
        window.alert("Please select one candidate before confirming your vote.");
        return;
      }
      if (!window.confirm("Confirm this vote? Once submitted, it cannot be changed.")) {
        event.preventDefault();
      }
    });
  }
});
