// Simple photo lightbox: click a gallery photo to enlarge; arrows/Esc to navigate.
(() => {
  const links = [...document.querySelectorAll("a.lightbox")];
  if (!links.length) return;
  const box = document.createElement("div");
  box.className = "lb";
  box.innerHTML = '<button class="close" aria-label="Close">×</button><button class="prev" aria-label="Previous">‹</button>' +
                  '<figure style="margin:0"><img alt=""><p></p></figure><button class="next" aria-label="Next">›</button>';
  document.body.append(box);
  const img = box.querySelector("img"), cap = box.querySelector("p");
  let group = [], i = 0;
  const show = () => { img.src = group[i].href; cap.textContent = group[i].dataset.caption || ""; };
  const step = d => { i = (i + d + group.length) % group.length; show(); };
  links.forEach(a => a.addEventListener("click", e => {
    e.preventDefault();
    group = links.filter(l => l.dataset.group === a.dataset.group);
    i = group.indexOf(a); show(); box.classList.add("open");
  }));
  box.querySelector(".close").onclick = () => box.classList.remove("open");
  box.querySelector(".prev").onclick = () => step(-1);
  box.querySelector(".next").onclick = () => step(1);
  box.addEventListener("click", e => { if (e.target === box) box.classList.remove("open"); });
  document.addEventListener("keydown", e => {
    if (!box.classList.contains("open")) return;
    if (e.key === "Escape") box.classList.remove("open");
    if (e.key === "ArrowLeft") step(-1);
    if (e.key === "ArrowRight") step(1);
  });
})();

// Turn on the ornament fonts only if their files exist in assets/fonts/
// (otherwise the coloured shapes defined in style.css stay visible).
if (document.fonts) {
  document.fonts.load("1em Autoctona").then(f => { if (f.length) document.documentElement.classList.add("dingbats"); });
  document.fonts.load("1em Desprecio").then(f => { if (f.length) document.documentElement.classList.add("figures-on"); });
}

// The lake: as you scroll down, the photos from content/lake/ fade one into
// the next (surface → deep), the water darkens and a depth gauge counts metres.
(() => {
  const lake = document.querySelector(".lake");
  if (!lake) return;
  const root = document.documentElement;
  const layers = [...lake.querySelectorAll(".layer")];
  const gauge = document.querySelector(".depth b");
  const MAX_DEPTH = 14;                      // metres at the bottom of the page
  const comma = root.lang === "es";
  let queued = false;
  const update = () => {
    queued = false;
    const room = root.scrollHeight - innerHeight;
    const p = room > 0 ? Math.min(1, Math.max(0, scrollY / room)) : 0;
    const t = p * (layers.length - 1);
    layers.forEach((l, i) => { if (i) l.style.opacity = Math.min(1, Math.max(0, t - i + 1)); });
    root.style.setProperty("--depth", p.toFixed(4));
    if (gauge) {
      const m = (p * MAX_DEPTH).toFixed(1);
      gauge.textContent = comma ? m.replace(".", ",") : m;
    }
  };
  addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(update); } }, { passive: true });
  addEventListener("resize", update);
  update();
})();

// Sections rise gently into view the first time they appear.
(() => {
  if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const sheets = document.querySelectorAll("main > section");
  const io = new IntersectionObserver(entries => entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add("seen"); io.unobserve(e.target); }
  }), { rootMargin: "0px 0px -8% 0px" });
  document.documentElement.classList.add("rise");
  sheets.forEach(s => io.observe(s));
})();
