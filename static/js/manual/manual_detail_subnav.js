/**
 * manual_detail_subnav.js
 * - 섹션 목차(Subnav) 클릭 시 “헤더 + subnav 높이”를 고려한 부드러운 스크롤
 * - 스크롤 위치에 따라 활성 링크(active) 자동 처리
 * - (옵션) TOP 버튼 동작(있으면)
 */
(() => {
  const subnav = document.getElementById("manualSubnav");
  if (!subnav) return;

  const links = Array.from(document.querySelectorAll(".jsSubnavLink"));
  if (!links.length) return;

  // base.html navbar 높이(대략). 프로젝트에서 값이 달라지면 여기만 수정하면 됨.
  const MAIN_NAV_H = 70;

  const getOffsetTop = () => {
    const subNavH = subnav.getBoundingClientRect().height || 0;
    return MAIN_NAV_H + subNavH + 10;
  };

  // ---------- smooth scroll on click ----------
  links.forEach((a) => {
    a.addEventListener("click", (e) => {
      const id = a.dataset.target;
      const target = document.getElementById(id);
      if (!target) return;

      e.preventDefault();
      const y = window.scrollY + target.getBoundingClientRect().top - getOffsetTop();
      window.scrollTo({ top: y, behavior: "smooth" });
    });
  });

  // ---------- active link by intersection observer ----------
  const sections = links
    .map((a) => document.getElementById(a.dataset.target))
    .filter(Boolean);

  const linkById = new Map(links.map((a) => [a.dataset.target, a]));

  const clearActive = () => links.forEach((a) => a.classList.remove("active"));
  const setActive = (id) => {
    clearActive();
    const a = linkById.get(id);
    if (a) a.classList.add("active");
  };

  const io = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((en) => en.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);

      if (visible.length) setActive(visible[0].target.id);
    },
    {
      root: null,
      rootMargin: `-${getOffsetTop()}px 0px -70% 0px`,
      threshold: [0.1, 0.2, 0.3],
    }
  );

  sections.forEach((sec) => io.observe(sec));
  setActive(sections[0]?.id);

  // ---------- optional: go top button ----------
  const btnTop = document.getElementById("btnManualGoTop");
  if (btnTop) {
    btnTop.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }
})();
