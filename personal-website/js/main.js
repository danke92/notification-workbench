/* ============================================================
   交互脚本：打字机效果 / 滚动进入动画 / 数字滚动 / 导航高亮 / 移动端菜单
   ============================================================ */

/* ▼▼ 首页打字机循环显示的文字，直接改这个数组即可 ▼▼ */
const TYPING_TEXTS = ['全栈开发者', '蒸汽波收藏家', 'AI 探索者', 'Y2K 冲浪选手'];

/* ---------- 打字机效果 ---------- */
(function initTyping() {
  const el = document.getElementById('typing');
  if (!el) return;
  let textIndex = 0;
  let charIndex = 0;
  let deleting = false;

  function tick() {
    const current = TYPING_TEXTS[textIndex];
    if (!deleting) {
      charIndex++;
      el.textContent = current.slice(0, charIndex);
      if (charIndex === current.length) {
        deleting = true;
        setTimeout(tick, 1800); // 打完一句停顿一下再删除
        return;
      }
      setTimeout(tick, 120);
    } else {
      charIndex--;
      el.textContent = current.slice(0, charIndex);
      if (charIndex === 0) {
        deleting = false;
        textIndex = (textIndex + 1) % TYPING_TEXTS.length;
        setTimeout(tick, 400);
        return;
      }
      setTimeout(tick, 55);
    }
  }
  tick();
})();

/* ---------- 滚动进入动画 ---------- */
const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        revealObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12 }
);
document.querySelectorAll('.reveal').forEach((el) => revealObserver.observe(el));

/* ---------- 数字滚动（关于我的统计） ---------- */
const countObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const target = parseInt(el.dataset.count, 10) || 0;
      const duration = 1300;
      const start = performance.now();
      function step(now) {
        const p = Math.min((now - start) / duration, 1);
        el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))); // ease-out
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
      countObserver.unobserve(el);
    });
  },
  { threshold: 0.5 }
);
document.querySelectorAll('.stat-num').forEach((el) => countObserver.observe(el));

/* ---------- 导航：滚动后加背景 + 当前区块高亮 ---------- */
const nav = document.getElementById('siteNav');
const navLinks = [...document.querySelectorAll('.nav-link')];
const sections = navLinks
  .map((link) => {
    const href = link.getAttribute('href');
    return href && href.startsWith('#') ? document.querySelector(href) : null;
  })
  .filter(Boolean);

function onScroll() {
  if (nav) nav.classList.toggle('scrolled', window.scrollY > 30);
  let currentId = '';
  sections.forEach((sec) => {
    if (window.scrollY >= sec.offsetTop - 130) currentId = sec.id;
  });
  navLinks.forEach((link) => {
    link.classList.toggle('active', link.getAttribute('href') === '#' + currentId);
  });
}
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();

/* ---------- 移动端汉堡菜单 ---------- */
const navToggle = document.getElementById('navToggle');
const navMenu = document.getElementById('navMenu');
if (navToggle && navMenu) {
  navToggle.addEventListener('click', () => {
    const open = navMenu.classList.toggle('open');
    navToggle.classList.toggle('open', open);
    navToggle.setAttribute('aria-expanded', String(open));
  });
  navMenu.querySelectorAll('a').forEach((a) => {
    a.addEventListener('click', () => {
      navMenu.classList.remove('open');
      navToggle.classList.remove('open');
    });
  });
}
