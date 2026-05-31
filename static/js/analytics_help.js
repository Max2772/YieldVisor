/**
 * analytics_help.js — portal tooltips to body on hover (avoids overflow + transform clipping).
 */
(function () {
  const sidebar = document.querySelector(".analytics-sidebar");
  const helps = document.querySelectorAll(
    ".stats-grid .metric-help, .content-grid--analytics .metric-help",
  );

  helps.forEach((wrap) => {
    const btn = wrap.querySelector(".metric-help__btn");
    const tip = wrap.querySelector(".metric-help__tip");
    if (!btn || !tip) return;

    const homeParent = wrap;
    const homeNext = tip.nextSibling;
    const inSidebar = Boolean(wrap.closest(".analytics-sidebar"));

    const restore = () => {
      if (tip.parentNode !== homeParent) {
        homeParent.insertBefore(tip, homeNext);
      }
    };

    const place = () => {
      document.body.appendChild(tip);
      tip.classList.add("metric-help__tip--open");

      tip.style.visibility = "hidden";
      tip.style.top = "0px";
      tip.style.left = "0px";

      const btnRect = btn.getBoundingClientRect();
      const tipWidth = tip.offsetWidth || 220;

      const pad = 12;
      let minLeft = pad;
      let maxRight = window.innerWidth - pad;

      if (sidebar) {
        const sb = sidebar.getBoundingClientRect();
        if (inSidebar) {
          minLeft = sb.left + pad;
          maxRight = sb.right - pad;
        } else {
          maxRight = Math.min(maxRight, sb.left - 10);
        }
      }

      let left = btnRect.left + btnRect.width / 2 - tipWidth / 2;
      if (left < minLeft) left = minLeft;
      if (left + tipWidth > maxRight) left = maxRight - tipWidth;

      tip.style.setProperty("--tip-arrow-x", `${btnRect.left + btnRect.width / 2 - left}px`);
      tip.style.top = `${btnRect.bottom + 8}px`;
      tip.style.left = `${left}px`;
      tip.style.visibility = "visible";
    };

    const hide = () => {
      tip.classList.remove("metric-help__tip--open");
      tip.style.removeProperty("--tip-arrow-x");
      tip.style.top = "";
      tip.style.left = "";
      tip.style.visibility = "";
      restore();
    };

    wrap.addEventListener("mouseenter", place);
    wrap.addEventListener("mouseleave", hide);
  });
})();
