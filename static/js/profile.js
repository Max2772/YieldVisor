/**
 * profile.js
 * ──────────────────────────────────────────────
 * JS для страницы профиля пользователя.
 * Подключается через {% block page_js %} в profile.html.
 *
 * Зависит от: base.js (initTabs уже вызван глобально)
 *
 * Содержит:
 *   - initProfileTabs      — переключение секций профиля
 *   - initAvatarUpload     — preview картинки до загрузки
 *   - initCharCounters     — счётчик символов для textarea
 *   - initUnsavedWarning   — предупреждение при уходе со страницы
 *   - initSessionRevoke    — подтверждение отзыва сессии
 *   - initDeleteConfirm    — подтверждение удаления аккаунта
 */

"use strict";

/* ── Переключение вкладок профиля ────────────────────────────────────── */
/**
 * Активирует .profile-tab и соответствующий .profile-panel
 * по data-tab атрибуту.
 *
 * HTML-пример:
 *   <div class="profile-tab active" data-tab="overview">Overview</div>
 *   <div class="profile-panel active" id="panel-overview">...</div>
 */
function initProfileTabs() {
  const tabs   = document.querySelectorAll(".profile-tab");
  const panels = document.querySelectorAll(".profile-panel");

  if (!tabs.length) return;

  // Restore tab from URL hash
  const hash = window.location.hash.replace("#", "");
  if (hash) activateTab(hash);

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      activateTab(target);
      // Update URL hash without scrolling
      history.replaceState(null, "", `#${target}`);
    });
  });

  function activateTab(name) {
    tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    panels.forEach((p) => p.classList.toggle("active", p.id === `panel-${name}`));
  }
}

function initAvatarUpload() {
  const input = document.getElementById("id_image");
  const avatar = document.querySelector(".profile-avatar");
  if (!input || !avatar) return;

  input.addEventListener("change", () => {
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      let img = avatar.querySelector(".profile-avatar-img");
      if (!img) {
        avatar.textContent = "";
        img = document.createElement("img");
        img.className = "profile-avatar-img";
        img.alt = "Avatar preview";
        avatar.insertBefore(img, avatar.querySelector(".profile-avatar-overlay"));
      }
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
  });
}

/* ── Character counters ───────────────────────────────────────────────── */
/**
 * Для каждого .sfield-textarea / .sfield-input с data-maxlength
 * показывает счётчик оставшихся символов.
 */
function initCharCounters() {
  document.querySelectorAll("[data-maxlength]").forEach((input) => {
    const max     = parseInt(input.dataset.maxlength, 10);
    const counter = input.closest(".sfield")?.querySelector(".sfield-counter");
    if (!counter) return;

    counter.textContent = `0 / ${max}`;

    input.addEventListener("input", () => {
      const len = input.value.length;
      counter.textContent = `${len} / ${max}`;
      counter.classList.toggle("near-limit", len >= max * 0.85);
      counter.classList.toggle("at-limit",   len >= max);
    });
  });
}

/* ── Unsaved changes warning ─────────────────────────────────────────── */
let _unsaved = false;

function markUnsaved() { _unsaved = true; }
function clearUnsaved() { _unsaved = false; }

function initUnsavedWarning() {
  const forms = document.querySelectorAll(".settings-form");

  forms.forEach((form) => {
    form.querySelectorAll("input, textarea, select").forEach((el) => {
      el.addEventListener("change", markUnsaved);
      el.addEventListener("input",  markUnsaved);
    });

    form.addEventListener("submit", clearUnsaved);
  });

  window.addEventListener("beforeunload", (e) => {
    if (_unsaved) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
}

/* ── Session revoke ───────────────────────────────────────────────────── */
function initSessionRevoke() {
  document.querySelectorAll(".btn-revoke-session").forEach((btn) => {
    btn.addEventListener("click", () => {
      const deviceName = btn.dataset.device || "this device";
      if (confirm(`Revoke session for ${deviceName}? You'll be logged out on that device.`)) {
        // In real app: fetch(btn.dataset.url, { method: 'POST', headers: { 'X-CSRFToken': getCsrf() } })
        const row = btn.closest(".session-item");
        row?.remove();
        showToast("✓ Session revoked.");
      }
    });
  });
}

/* ── Delete account confirmation ─────────────────────────────────────── */
function initDeleteConfirm() {
  const btn = document.getElementById("btnDeleteAccount");
  if (!btn) return;

  btn.addEventListener("click", () => {
    const username = btn.dataset.username || "your account";
    const confirmed = prompt(
      `This will permanently delete ${username} and all portfolio data.\n\nType DELETE to confirm:`
    );
    if (confirmed === "DELETE") {
      // In real app: submit delete form
      document.getElementById("deleteAccountForm")?.submit();
    }
  });
}

/* ── Toast notification ──────────────────────────────────────────────── */
/**
 * Показывает временное уведомление в правом нижнем углу.
 * @param {string} message
 * @param {number} duration — мс
 */
function showToast(message, duration = 3000) {
  let container = document.getElementById("toast-container");

  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.style.cssText = `
      position: fixed; bottom: 24px; right: 24px;
      display: flex; flex-direction: column; gap: 10px;
      z-index: 9999;
    `;
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.style.cssText = `
    background: #181c22;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 12px 18px;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    color: #e8eaf0;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    animation: fadeUp 0.25s ease both;
    max-width: 280px;
    line-height: 1.4;
  `;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function initPasswordToggles() {
  document.querySelectorAll(".pw-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = btn.closest(".sfield, div")?.querySelector("input[type='password']");
      if (!input) return;
      const isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      btn.textContent = isHidden ? "Hide" : "Show";
      btn.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initProfileTabs();
  initAvatarUpload();
  initCharCounters();
  initUnsavedWarning();
  initSessionRevoke();
  initDeleteConfirm();
  initPasswordToggles();
});
