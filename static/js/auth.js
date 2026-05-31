/**
 * auth.js
 * ──────────────────────────────────────────────
 * JS для страниц логина и регистрации.
 * Подключается через {% block page_js %} в login.html и register.html.
 *
 * Зависит от: base.js
 *
 * Содержит:
 *   - initPasswordToggle  — показать/скрыть пароль
 *   - initPasswordStrength — метр надёжности пароля (только register)
 *   - initFormValidation   — валидация перед submit
 */

"use strict";

/* ── Показать/скрыть пароль ──────────────────────────────────────────── */
function initPasswordToggle() {
  document.querySelectorAll(".form-input-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = btn.closest(".form-input-wrap").querySelector(".form-input");
      if (!input) return;

      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";
      btn.textContent = isPassword ? "Hide" : "Show";
      btn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
    });
  });
}

/* ── Метр надёжности пароля ─────────────────────────────────────────── */
/**
 * Оценивает пароль по 4 критериям и обновляет UI.
 * Используется только на странице регистрации.
 *
 * @param {string} password
 * @returns {number} 0–4 — уровень надёжности
 */
function scorePassword(password) {
  let score = 0;
  if (password.length >= 8)                  score++;
  if (/[A-Z]/.test(password))               score++;
  if (/[0-9]/.test(password))               score++;
  if (/[^A-Za-z0-9]/.test(password))        score++;
  return score;
}

function initPasswordStrength() {
  const input  = document.getElementById("id_password1");
  const fill   = document.querySelector(".pw-strength-fill");
  const label  = document.querySelector(".pw-strength-label");

  if (!input || !fill || !label) return;

  const LABELS = ["", "Weak", "Fair", "Good", "Strong"];

  input.addEventListener("input", () => {
    const score = input.value.length === 0 ? 0 : scorePassword(input.value);

    // Remove all strength classes
    fill.className  = "pw-strength-fill";
    label.className = "pw-strength-label";

    if (score > 0) {
      fill.classList.add(`s${score}`);
      label.classList.add(`s${score}`);
    }

    label.textContent = LABELS[score] || "";
  });
}

/* ── Client-side валидация ───────────────────────────────────────────── */
/**
 * Показывает .form-error под полем и добавляет .error на input.
 * @param {HTMLElement} input
 * @param {string}      message
 */
function showFieldError(input, message) {
  input.classList.add("error");
  const err = input.closest(".form-group")?.querySelector(".form-error");
  if (err) {
    err.textContent = message;
    err.classList.add("visible");
  }
}

/**
 * Сбрасывает состояние ошибки.
 * @param {HTMLElement} input
 */
function clearFieldError(input) {
  input.classList.remove("error");
  const err = input.closest(".form-group")?.querySelector(".form-error");
  if (err) err.classList.remove("visible");
}

function initFormValidation() {
  const form = document.querySelector(".auth-form");
  if (!form) return;

  // Live clear on input
  form.querySelectorAll(".form-input").forEach((input) => {
    input.addEventListener("input", () => clearFieldError(input));
  });

  form.addEventListener("submit", (e) => {
    let valid = true;

    // Required fields
    form.querySelectorAll(".form-input[required]").forEach((input) => {
      if (!input.value.trim()) {
        showFieldError(input, "This field is required.");
        valid = false;
      }
    });

    // Email format
    const emailInput = form.querySelector('input[type="email"]');
    if (emailInput && emailInput.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput.value)) {
      showFieldError(emailInput, "Enter a valid email address.");
      valid = false;
    }

    // Password confirmation match (register page)
    const pw1 = form.querySelector("#id_password1");
    const pw2 = form.querySelector("#id_password2");
    if (pw1 && pw2 && pw1.value && pw2.value && pw1.value !== pw2.value) {
      showFieldError(pw2, "Passwords do not match.");
      valid = false;
    }

    // Checkbox required (terms)
    const termsBox = form.querySelector(".form-checkbox[required]");
    if (termsBox && !termsBox.checked) {
      showFieldError(termsBox, "You must accept the terms.");
      valid = false;
    }

    if (!valid) e.preventDefault();
  });
}

/* ── Bootstrap ───────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initPasswordToggle();
  initPasswordStrength();
  initFormValidation();
});
