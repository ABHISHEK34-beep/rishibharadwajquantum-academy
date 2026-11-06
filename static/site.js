/* RBQA public site: loads courses/workshops from the API, handles forms. */
(function () {
  const $ = (s, r = document) => r.querySelector(s);

  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeIcon = (v) => (/^fa-[a-z0-9-]+$/.test(v || "") ? v : "fa-atom");

  async function api(url, opts) {
    const res = await fetch(url, opts);
    let data = {};
    try { data = await res.json(); } catch (_) {}
    if (!res.ok) throw new Error(data.error || "Something went wrong. Please try again.");
    return data;
  }
  const post = (url, body) => api(url, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });

  let courses = [], workshops = [];
  let categories = [
    { key: "school", label: "School-Level Physics" },
    { key: "neet-jee", label: "NEET & JEE Physics" },
    { key: "practical", label: "Practical Physics & Experiments" },
    { key: "quantum", label: "Quantum Technology" },
    { key: "rf", label: "RF, Microwave & Electronics" },
  ];
  let activeCategory = "all";

  /* ---------------- Courses ---------------- */
  function renderFilters() {
    const wrap = $("#course-filters");
    // only show categories that currently have a published course
    const used = new Set(courses.map((c) => c.category));
    const tabs = [{ key: "all", label: "All" }, ...categories.filter((c) => used.has(c.key))];
    wrap.innerHTML = tabs.map((c) => {
      const on = c.key === activeCategory;
      return `<button role="tab" aria-selected="${on}" data-category="${esc(c.key)}"
        class="px-4 py-2 rounded-full text-sm font-medium border transition-colors ${on
          ? "bg-accent text-navy-900 border-accent"
          : "border-slate-600 text-slate-300 hover:border-accent hover:text-accent"}">${esc(c.label)}</button>`;
    }).join("");
  }

  function setCategory(key) {
    activeCategory = courses.some((c) => c.category === key) ? key : "all";
    renderFilters();
    renderCourses();
  }

  function fillClassCourseOptions() {
    const sel = $("#class_course");
    if (!sel) return;
    const opts = ["Class 9", "Class 10", "Class 11", "Class 12", "Dropper (NEET / JEE)", "Undergraduate", "Teacher / Researcher"];
    sel.innerHTML = '<option value="" selected>Select class or course</option>'
      + `<optgroup label="Class / Level">${opts.map((o) => `<option>${esc(o)}</option>`).join("")}</optgroup>`
      + `<optgroup label="Courses">${courses.map((c) => `<option>${esc(c.title)}</option>`).join("")}</optgroup>`;
  }

  function renderCourses() {
    const grid = $("#courses-grid");
    const visible = activeCategory === "all" ? courses : courses.filter((c) => c.category === activeCategory);
    const cards = visible.map((c) => `
      <div class="course-card bg-navy-800 rounded-xl p-8 border border-slate-700/50 flex flex-col h-full relative overflow-hidden group">
        <div class="absolute top-0 right-0 w-32 h-32 bg-accent/5 rounded-bl-full -mr-8 -mt-8 transition-transform group-hover:scale-110"></div>
        <div class="w-12 h-12 bg-navy-900 rounded-lg flex items-center justify-center mb-6 text-accent border border-accent/20">
          <i class="fa-solid ${safeIcon(c.icon)} text-xl"></i>
        </div>
        <h4 class="text-xl font-bold text-white mb-3">${esc(c.title)}</h4>
        <p class="text-sm text-accent mb-4">${esc(c.audience)}</p>
        <p class="text-slate-400 text-sm mb-6 flex-grow">${esc(c.description)}</p>
        <ul class="text-sm text-slate-300 space-y-2 mb-6">
          ${c.topics.slice(0, 3).map((t) => `<li><i class="fa-solid fa-angle-right text-accent mr-2"></i>${esc(t)}</li>`).join("")}
        </ul>
        <button data-course="${c.id}" class="mt-auto text-accent text-sm font-semibold hover:underline flex items-center text-left">
          View Curriculum <i class="fa-solid fa-arrow-right ml-2 text-xs"></i>
        </button>
      </div>`).join("");

    const lab = `
      <div class="course-card bg-gradient-to-br from-navy-700 to-navy-800 rounded-xl p-8 border border-accent/40 flex flex-col items-center justify-center text-center h-full group">
        <i class="fa-solid fa-flask-vial text-4xl text-accent mb-4 group-hover:animate-pulse"></i>
        <h4 class="text-xl font-bold text-white mb-2">Practical Physics Laboratory</h4>
        <p class="text-slate-400 text-sm mb-6">Explore dedicated resources for practical experiments, observations, and computational demonstrations.</p>
        <button data-lab class="px-6 py-2 border-2 border-accent text-accent rounded-full hover:bg-accent hover:text-navy-900 transition-colors font-medium text-sm">
          Explore Experiments
        </button>
      </div>`;
    const empty = '<p class="text-slate-400 col-span-full text-center">No courses in this category yet.</p>';
    grid.innerHTML = (cards || empty) + (activeCategory === "all" || activeCategory === "practical" ? lab : "");
  }

  /* ---------------- Workshops ---------------- */
  const TAG_COLORS = [
    "bg-blue-500/20 text-blue-400", "bg-purple-500/20 text-purple-400", "bg-green-500/20 text-green-400",
  ];

  function renderWorkshops() {
    const list = $("#workshops-list");
    if (!workshops.length) {
      list.innerHTML = '<p class="text-slate-400 text-center">No workshops are scheduled right now. Check back soon!</p>';
      return;
    }
    list.innerHTML = workshops.map((w) => {
      const active = w.status === "Upcoming";
      const closed = w.status === "Completed";
      const dim = active ? "" : "text-slate-500";
      return `
      <div class="bg-navy-900 rounded-xl p-6 md:p-8 border border-slate-700/50 hover:border-accent/50 transition-colors flex flex-col lg:flex-row gap-6 items-start lg:items-center">
        <div class="bg-navy-800 border border-slate-700 rounded-lg p-4 text-center min-w-[120px]">
          <span class="block ${active ? "text-accent" : "text-slate-500"} font-bold text-xs uppercase">${esc(w.status)}</span>
          <span class="block text-3xl font-bold ${active ? "text-white" : "text-slate-500"} mt-1">${esc(w.date_label)}</span>
          <span class="block ${active ? "text-slate-400" : "text-slate-500"} text-sm">${esc(w.mode)}</span>
        </div>
        <div class="flex-grow">
          <div class="flex flex-wrap items-center gap-3 mb-2">
            ${w.tags.map((t, i) => `<span class="${TAG_COLORS[i % 3]} text-xs px-2 py-1 rounded font-medium">${esc(t)}</span>`).join("")}
          </div>
          <h4 class="text-2xl font-bold text-white mb-2">${esc(w.title)}</h4>
          <p class="text-slate-400 text-sm max-w-3xl">${esc(w.description)}</p>
        </div>
        <div class="flex-shrink-0 mt-4 lg:mt-0 w-full lg:w-auto">
          ${closed
            ? '<span class="block text-center px-6 py-3 text-slate-500 border border-slate-700 rounded-md">Completed</span>'
            : `<button data-workshop="${w.id}" class="w-full lg:w-auto px-6 py-3 bg-navy-700 hover:bg-navy-600 text-white rounded-md transition-colors font-medium border border-slate-600">Register Interest</button>`}
        </div>
      </div>`;
    }).join("");
  }

  /* ---------------- Modal ---------------- */
  const modal = $("#modal"), modalBody = $("#modal-body");
  function openModal(html) {
    modalBody.innerHTML = html;
    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
    const first = modalBody.querySelector("input, button");
    if (first) first.focus();
  }
  function closeModal() {
    modal.classList.add("hidden");
    modalBody.innerHTML = "";
    document.body.style.overflow = "";
  }
  $("#modal-close").addEventListener("click", closeModal);
  $("#modal-backdrop").addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

  const inputCls = "w-full bg-navy-900 border border-slate-700 rounded-md py-2.5 px-4 text-white focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-colors";

  function showCourse(id) {
    const c = courses.find((x) => x.id === id);
    if (!c) return;
    openModal(`
      <div class="w-12 h-12 bg-navy-900 rounded-lg flex items-center justify-center mb-4 text-accent border border-accent/20">
        <i class="fa-solid ${safeIcon(c.icon)} text-xl"></i></div>
      <h3 class="text-2xl font-bold text-white mb-1">${esc(c.title)}</h3>
      <p class="text-sm text-accent mb-4">${esc(c.audience)}</p>
      <p class="text-slate-300 text-sm leading-relaxed mb-5">${esc(c.description)}</p>
      <h4 class="text-white font-semibold mb-2">What you'll cover</h4>
      <ul class="text-sm text-slate-300 space-y-2 mb-6">
        ${c.topics.map((t) => `<li><i class="fa-solid fa-angle-right text-accent mr-2"></i>${esc(t)}</li>`).join("")}
      </ul>
      <button data-enquire="${c.id}" class="w-full py-3 rounded-md bg-accent text-navy-900 font-bold hover:bg-cyan-300 transition-colors">Enquire about this course</button>`);
  }

  function showRegister(id) {
    const w = workshops.find((x) => x.id === id);
    if (!w) return;
    openModal(`
      <h3 class="text-2xl font-bold text-white mb-1">Register Interest</h3>
      <p class="text-accent text-sm mb-5">${esc(w.title)}</p>
      <form id="reg-form" class="space-y-4" novalidate>
        <div><label class="block text-sm text-slate-300 mb-1" for="r-name">Full Name *</label>
          <input id="r-name" class="${inputCls}" required maxlength="120"></div>
        <div><label class="block text-sm text-slate-300 mb-1" for="r-email">Email Address *</label>
          <input id="r-email" type="email" class="${inputCls}" required maxlength="200"></div>
        <div><label class="block text-sm text-slate-300 mb-1" for="r-phone">Mobile Number</label>
          <input id="r-phone" type="tel" class="${inputCls}" maxlength="30"></div>
        <div><label class="block text-sm text-slate-300 mb-1" for="r-note">Anything we should know?</label>
          <textarea id="r-note" rows="3" class="${inputCls} resize-none" maxlength="1000"></textarea></div>
        <div class="absolute -left-[9999px] h-0 w-0 overflow-hidden" aria-hidden="true">
          <label for="r-website">Leave this field empty</label>
          <input id="r-website" tabindex="-1" autocomplete="off"></div>
        <div id="reg-status" class="hidden text-sm rounded-md px-4 py-3" role="status"></div>
        <button id="reg-submit" class="w-full py-3 rounded-md bg-accent text-navy-900 font-bold hover:bg-cyan-300 transition-colors">Submit</button>
      </form>`);
    $("#reg-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = $("#reg-submit"), st = $("#reg-status");
      btn.disabled = true; btn.classList.add("opacity-60");
      try {
        const r = await post(`/api/workshops/${id}/register`, {
          name: $("#r-name").value, email: $("#r-email").value,
          phone: $("#r-phone").value, note: $("#r-note").value,
          website: $("#r-website").value,   // honeypot
        });
        showStatus(st, r.message, true);
        $("#reg-form").querySelectorAll("input,textarea").forEach((i) => (i.disabled = true));
      } catch (err) {
        showStatus(st, err.message, false);
        btn.disabled = false; btn.classList.remove("opacity-60");
      }
    });
  }

  function showStatus(el, msg, ok) {
    el.textContent = msg;
    el.className = "text-sm rounded-md px-4 py-3 " + (ok
      ? "bg-green-500/10 text-green-300 border border-green-500/30"
      : "bg-red-500/10 text-red-300 border border-red-500/30");
  }

  /* ---------------- Delegated clicks ---------------- */
  document.addEventListener("click", (e) => {
    // links that pre-select a category tab or the enquiry type
    const link = e.target.closest("a[data-filter], a[data-interest]");
    if (link) {
      if (link.dataset.filter) setCategory(link.dataset.filter);
      if (link.dataset.interest) $("#interest").value = link.dataset.interest;
      return;                                  // the href still scrolls to the section
    }
    const t = e.target.closest("button");
    if (!t) return;
    if (t.dataset.category) setCategory(t.dataset.category);
    else if (t.dataset.course) showCourse(Number(t.dataset.course));
    else if (t.dataset.workshop) showRegister(Number(t.dataset.workshop));
    else if (t.dataset.enquire) {
      const c = courses.find((x) => x.id === Number(t.dataset.enquire));
      closeModal();
      $("#interest").value = "course";
      if (c) $("#class_course").value = c.title;
      const msg = $("#message");
      if (c && !msg.value) msg.value = `I'd like to know more about "${c.title}".`;
      $("#contact").scrollIntoView({ behavior: "smooth" });
    } else if (t.hasAttribute("data-lab")) {
      $("#interest").value = "other";
      $("#contact").scrollIntoView({ behavior: "smooth" });
    }
  });

  /* ---------------- Contact form ---------------- */
  $("#contact-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("#contact-submit"), st = $("#contact-status");
    const body = {
      name: $("#name").value, email: $("#email").value, phone: $("#phone").value,
      interest: $("#interest").value, message: $("#message").value,
      class_course: $("#class_course").value, learning_mode: $("#learning_mode").value,
      website: $("#website").value,            // honeypot
    };
    if (!body.name.trim() || !body.email.trim() || !body.message.trim()) {
      showStatus(st, "Please fill in your name, email and message.", false); return;
    }
    btn.disabled = true; btn.classList.add("opacity-60");
    try {
      const r = await post("/api/contact", body);
      showStatus(st, r.message, true);
      e.target.reset();
    } catch (err) {
      showStatus(st, err.message, false);
    } finally {
      btn.disabled = false; btn.classList.remove("opacity-60");
    }
  });

  /* ---------------- Boot ---------------- */
  function applyConfig(cfg) {
    if (cfg.categories && cfg.categories.length) categories = cfg.categories;
    if (cfg.email) {
      const a = $("#contact-email");
      a.href = "mailto:" + cfg.email; a.textContent = cfg.email;
    }
    if (cfg.phone) { const p = $("#contact-phone"); p.textContent = cfg.phone; p.classList.remove("hidden"); }
    if (cfg.whatsapp) {
      const url = "https://wa.me/" + cfg.whatsapp + "?text=" +
        encodeURIComponent("Hello RBQA, I would like to enquire about your courses.");
      const btn = $("#wa-btn"), fl = $("#wa-float");
      btn.href = url; btn.classList.remove("hidden");
      fl.href = url; fl.classList.remove("hidden"); fl.classList.add("flex");
      const d = cfg.whatsapp;
      $("#wa-text").textContent = d.length === 12 && d.startsWith("91")
        ? `+91 ${d.slice(2, 7)} ${d.slice(7)}` : "+" + d;
    }
  }

  (async function init() {
    try { applyConfig(await api("/api/config")); } catch (_) { /* defaults stay */ }
    try {
      [courses, workshops] = await Promise.all([api("/api/courses"), api("/api/workshops")]);
      renderFilters();
      renderCourses();
      fillClassCourseOptions();
      renderWorkshops();
    } catch (err) {
      $("#courses-grid").innerHTML = `<p class="text-red-300 col-span-full text-center">Could not load courses: ${esc(err.message)}</p>`;
      $("#workshops-list").innerHTML = `<p class="text-red-300 text-center">Could not load workshops.</p>`;
    }
  })();
})();
