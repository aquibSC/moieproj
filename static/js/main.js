// Progressive enhancement: forms work via normal POST + redirect even
// without JS. Here we intercept them to update the UI instantly instead.

document.addEventListener("submit", async (e) => {
  const form = e.target;

  // --- Watchlist toggle ---
  if (form.classList.contains("watchlist-toggle-form")) {
    e.preventDefault();
    const btn = form.querySelector(".watchlist-btn");
    try {
      const res = await fetch(form.action, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!res.ok) throw new Error("Request failed");
      const data = await res.json();
      if (data.in_watchlist) {
        btn.classList.add("active");
        btn.textContent = "✓ In Watchlist";
      } else {
        btn.classList.remove("active");
        btn.textContent = "+ Watchlist";
      }
    } catch (err) {
      // fall back to normal form submission on failure
      form.submit();
    }
  }

  // --- Star rating ---
  if (form.classList.contains("rating-form")) {
    e.preventDefault();
    const clicked = e.submitter; // the star button that was pressed
    const stars = parseInt(clicked.value, 10);
    const formData = new FormData();
    formData.append("stars", stars);

    try {
      const res = await fetch(form.action, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body: formData,
      });
      if (!res.ok) throw new Error("Request failed");
      const buttons = Array.from(form.querySelectorAll(".star-btn"));
      buttons.forEach((btn) => {
        const val = parseInt(btn.value, 10);
        btn.classList.toggle("filled", val <= stars);
      });
    } catch (err) {
      form.submit();
    }
  }
});
