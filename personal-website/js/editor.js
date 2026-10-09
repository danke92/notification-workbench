/* ============================================================
   蛋壳egg · 网页内容编辑模式
   ------------------------------------------------------------
   点右下角「✏️ 编辑内容」进入编辑模式：
   - 直接点击页面上的文字修改（名字、介绍、项目、文章……）
   - 编辑模式下点击链接不会跳转，放心改
   - 改完点「💾 保存并下载」，用下载的文件替换原文件即可
   ============================================================ */
(function () {
  'use strict';

  /* 可以直接在网页上编辑的元素 */
  var EDITABLE_SELECTOR = [
    '.logo',
    '.hero-badge',
    '.hero h1',
    '.hero-desc',
    '.social-label', '.social-pill', '.btn',
    '.section-index', '.section-head h2', '.section-en', '.section-desc',
    '.about-info li', '.about-main p', '.stat-label',
    '.skill-group h3', '.chip',
    '.project-card h3', '.project-card > p', '.project-tags span',
    '.blog-card h3', '.blog-card > p', '.blog-meta time',
    '.contact-title', '.contact-desc',
    '.page-desc', '.post-group-year', '.post-date', '.post-main h3', '.post-main p',
    '.article-back', '.article-meta', '.article-header h1',
    '.article-content h2', '.article-content p', '.article-content li', '.article-content blockquote',
    '.article-nav-title',
    '.footer-inner p'
  ].join(',');

  /* ---------- 后台门禁：只有从 admin.html 登录过的浏览器才显示编辑按钮 ---------- */
  var AUTH_KEY = 'eggAdmin';
  function isAuthed() {
    try { return localStorage.getItem(AUTH_KEY) === '1'; } catch (e) { return false; }
  }
  if (!isAuthed()) return; // 普通访客：什么都不渲染

  var editing = false;

  /* ---------- 工具条 & 提示条 ---------- */
  var toolbar = document.createElement('div');
  toolbar.className = 'egg-editor-bar';
  toolbar.setAttribute('data-egg-editor', '');
  toolbar.innerHTML =
    '<button type="button" class="egg-btn egg-btn-save" hidden>💾 保存并下载</button>' +
    '<button type="button" class="egg-btn egg-btn-toggle">✏️ 编辑内容</button>' +
    '<button type="button" class="egg-btn egg-btn-logout" title="退出后台，在本浏览器隐藏编辑按钮">🚪 退出后台</button>';

  var banner = document.createElement('div');
  banner.className = 'egg-editor-banner';
  banner.setAttribute('data-egg-editor', '');
  banner.hidden = true;
  banner.innerHTML =
    '<span>🛠 编辑模式：直接点击文字修改（链接不会误触跳转）。改完点「💾 保存并下载」，用下载的文件替换原文件。</span>';

  document.body.appendChild(toolbar);
  document.body.appendChild(banner);

  var btnToggle = toolbar.querySelector('.egg-btn-toggle');
  var btnSave = toolbar.querySelector('.egg-btn-save');

  function setEditable(on) {
    document.querySelectorAll(EDITABLE_SELECTOR).forEach(function (el) {
      if (on) {
        el.setAttribute('contenteditable', 'true');
        el.setAttribute('spellcheck', 'false');
      } else {
        el.removeAttribute('contenteditable');
        el.removeAttribute('spellcheck');
      }
    });
    document.body.classList.toggle('egg-editing', on);
    banner.hidden = !on;
    btnSave.hidden = !on;
    btnToggle.textContent = on ? '✅ 完成编辑' : '✏️ 编辑内容';
  }

  btnToggle.addEventListener('click', function () {
    if (editing) {
      if (!window.confirm('退出后，尚未「保存并下载」的修改会丢失（刷新页面也会丢失）。\n\n确定退出编辑模式吗？')) {
        return;
      }
    }
    editing = !editing;
    setEditable(editing);
  });

  var btnLogout = toolbar.querySelector('.egg-btn-logout');
  btnLogout.addEventListener('click', function () {
    if (editing && !window.confirm('当前还在编辑模式，退出后台会丢失未保存的修改。\n\n确定退出吗？')) return;
    try { localStorage.removeItem(AUTH_KEY); } catch (e) {}
    location.reload();
  });

  /* 编辑模式下拦截所有链接跳转，避免误触离开页面 */
  document.addEventListener('click', function (e) {
    if (!editing) return;
    var a = e.target.closest ? e.target.closest('a') : null;
    if (a) {
      e.preventDefault();
      e.stopPropagation();
    }
  }, true);

  /* ---------- 保存：导出干净的 HTML 并触发下载 ---------- */
  function buildCleanHTML() {
    var clone = document.documentElement.cloneNode(true);
    /* 移除编辑器自身的 UI */
    clone.querySelectorAll('[data-egg-editor]').forEach(function (el) { el.remove(); });
    /* 还原脚本造成的临时状态，让导出文件和手写的一样干净 */
    clone.querySelectorAll('.reveal').forEach(function (el) { el.classList.remove('visible'); });
    clone.querySelectorAll('.stat-num').forEach(function (el) { el.textContent = '0'; });
    var typing = clone.querySelector('#typing');
    if (typing) typing.textContent = '';
    var body = clone.querySelector('body');
    if (body) body.classList.remove('egg-editing');
    clone.querySelectorAll('[contenteditable]').forEach(function (el) { el.removeAttribute('contenteditable'); });
    clone.querySelectorAll('[spellcheck]').forEach(function (el) { el.removeAttribute('spellcheck'); });
    return '<!DOCTYPE html>\n' + clone.outerHTML;
  }

  btnSave.addEventListener('click', function () {
    var html = buildCleanHTML();
    var name = location.pathname.split('/').pop() || 'index.html';
    var blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    btnSave.textContent = '✅ 已下载，请替换原文件';
    setTimeout(function () { btnSave.textContent = '💾 保存并下载'; }, 2500);
  });
})();
