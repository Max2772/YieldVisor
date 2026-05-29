"use strict";

(function () {
  const ASSET_STEAM = "steam";
  const STEAM_QTY_ERROR = "Steam items can only be traded in whole units.";

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  function parsePositiveDecimal(raw) {
    const s = String(raw || "").trim().replace(",", ".");
    if (!s) return null;
    const n = Number(s);
    if (!Number.isFinite(n) || n <= 0) return null;
    return s;
  }

  function isWholeQuantity(raw) {
    const s = String(raw || "").trim().replace(",", ".");
    if (!/^\d+$/.test(s)) return false;
    const n = Number(s);
    return Number.isFinite(n) && n > 0;
  }

  function clearErrors(el) {
    el.textContent = "";
    el.classList.remove("is-visible");
  }

  function showErrors(el, errors) {
    const lines = [];
    if (typeof errors === "string") {
      lines.push(errors);
    } else if (errors && typeof errors === "object") {
      Object.keys(errors).forEach((key) => {
        const msgs = errors[key];
        (Array.isArray(msgs) ? msgs : [msgs]).forEach((m) => {
          lines.push(key === "__all__" ? m : `${key}: ${m}`);
        });
      });
    }
    el.textContent = lines.join("\n") || "Something went wrong.";
    el.classList.add("is-visible");
  }

  async function postDelete(urlDelete, positionId, nextPath, errEl, onSuccess) {
    const fd = new FormData();
    fd.append("csrfmiddlewaretoken", getCookie("csrftoken"));
    fd.append("position_id", positionId);
    fd.append("next", nextPath);
    try {
      const r = await fetch(urlDelete, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: fd,
      });
      const data = await r.json().catch(() => null);
      if (data && data.ok) {
        onSuccess();
        return;
      }
      if (data && data.errors) {
        showErrors(errEl, data.errors);
        return;
      }
      showErrors(errEl, "Unexpected response.");
    } catch {
      showErrors(errEl, "Network error.");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const overlay = document.getElementById("holdingTradeOverlay");
    if (!overlay) return;

    const form = document.getElementById("holdingModalForm");
    const titleEl = document.getElementById("holdingModalTitle");
    const errEl = document.getElementById("holdingModalErrors");
    const fieldsWrap = document.getElementById("holdingModalFields");
    const submitBtn = document.getElementById("holdingModalSubmit");
    const removeBtn = document.getElementById("holdingModalRemove");
    const qtyInput = document.getElementById("holdingModalQuantity");
    const priceInput = document.getElementById("holdingModalPrice");
    const priceLabel = document.getElementById("holdingModalPriceLabel");
    const nextInput = document.getElementById("holdingModalNext");
    const positionIdInput = document.getElementById("holdingModalPositionId");
    const assetTypeInput = document.getElementById("holdingModalAssetType");
    const assetNameInput = document.getElementById("holdingModalAssetName");
    const appIdInput = document.getElementById("holdingModalAppId");

    const urlBuy = overlay.dataset.urlBuy;
    const urlSell = overlay.dataset.urlSell;
    const urlDelete = overlay.dataset.urlDelete;

    let mode = "buy";
    let sellMaxQty = "";
    let currentTicker = "";
    let wholeQtyOnly = false;

    function setRemoveVisible(visible) {
      if (visible) {
        removeBtn.removeAttribute("hidden");
      } else {
        removeBtn.setAttribute("hidden", "");
      }
    }

    function configureQuantityInput() {
      if (wholeQtyOnly) {
        qtyInput.setAttribute("inputmode", "numeric");
        qtyInput.setAttribute("pattern", "[0-9]*");
        qtyInput.setAttribute("step", "1");
      } else {
        qtyInput.setAttribute("inputmode", "decimal");
        qtyInput.removeAttribute("pattern");
        qtyInput.removeAttribute("step");
      }
    }

    function openOverlay() {
      overlay.hidden = false;
      overlay.classList.add("is-open");
      document.body.style.overflow = "hidden";
    }

    function closeOverlay() {
      overlay.classList.remove("is-open");
      overlay.hidden = true;
      document.body.style.overflow = "";
      clearErrors(errEl);
      form.reset();
      setRemoveVisible(false);
      wholeQtyOnly = false;
      configureQuantityInput();
    }

    document.querySelectorAll("[data-close-holding-modal]").forEach((el) => {
      el.addEventListener("click", () => closeOverlay());
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && overlay.classList.contains("is-open")) {
        closeOverlay();
      }
    });

    removeBtn.addEventListener("click", async () => {
      if (mode !== "sell") return;
      clearErrors(errEl);
      removeBtn.disabled = true;
      await postDelete(
        urlDelete,
        positionIdInput.value,
        nextInput.value,
        errEl,
        () => {
          closeOverlay();
          window.location.reload();
        },
      );
      removeBtn.disabled = false;
    });

    document.querySelectorAll(".holding-open-modal").forEach((btn) => {
      btn.addEventListener("click", () => {
        clearErrors(errEl);
        mode = btn.dataset.modal || "buy";
        sellMaxQty = btn.dataset.qtyMax || "";
        currentTicker = btn.dataset.ticker || "";
        const assetType = btn.dataset.assetType || "";
        wholeQtyOnly = assetType === ASSET_STEAM;
        const nextPath =
          btn.dataset.next || window.location.pathname + window.location.search;

        nextInput.value = nextPath;
        positionIdInput.value = btn.dataset.positionId || "";
        assetTypeInput.value = assetType;
        assetNameInput.value = btn.dataset.assetName || "";
        appIdInput.value = btn.dataset.appId || "";

        fieldsWrap.hidden = false;
        setRemoveVisible(mode === "sell");
        submitBtn.textContent = mode === "buy" ? "Buy" : "Sell";
        const defPrice = btn.dataset.defaultPrice || "";
        const defQty = mode === "sell" ? btn.dataset.qtyMax || "" : "";
        qtyInput.value = wholeQtyOnly && defQty ? String(Math.trunc(Number(defQty))) : defQty;
        priceInput.value = defPrice;
        priceLabel.textContent =
          mode === "buy" ? "Buy price (USD)" : "Sell price (USD)";
        qtyInput.setAttribute("name", "quantity");
        priceInput.setAttribute(
          "name",
          mode === "buy" ? "buy_price" : "sell_price",
        );
        titleEl.textContent =
          mode === "buy" ? `Buy ${currentTicker}` : `Sell ${currentTicker}`;

        configureQuantityInput();
        openOverlay();
        qtyInput.focus();
      });
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearErrors(errEl);

      const qtyRaw = wholeQtyOnly
        ? isWholeQuantity(qtyInput.value)
          ? String(qtyInput.value).trim().replace(",", ".")
          : null
        : parsePositiveDecimal(qtyInput.value);

      if (!qtyRaw) {
        showErrors(errEl, {
          quantity: [
            wholeQtyOnly
              ? STEAM_QTY_ERROR
              : "Enter a valid positive quantity.",
          ],
        });
        return;
      }

      const priceRaw = parsePositiveDecimal(priceInput.value);
      if (!priceRaw) {
        showErrors(errEl, {
          [mode === "buy" ? "buy_price" : "sell_price"]: [
            "Enter a valid price (USD).",
          ],
        });
        return;
      }

      if (mode === "sell" && sellMaxQty) {
        if (Number(qtyRaw) > Number(sellMaxQty)) {
          showErrors(errEl, {
            quantity: [`Quantity cannot exceed ${sellMaxQty}.`],
          });
          return;
        }
      }

      const fd = new FormData();
      fd.append("csrfmiddlewaretoken", getCookie("csrftoken"));
      fd.append("next", nextInput.value);

      let actionUrl = urlBuy;
      if (mode === "buy") {
        fd.append("asset_type", assetTypeInput.value);
        fd.append("asset_name", assetNameInput.value);
        if (appIdInput.value) fd.append("app_id", appIdInput.value);
        fd.append("quantity", qtyRaw);
        fd.append("buy_price", priceRaw);
        actionUrl = urlBuy;
      } else {
        fd.append("position_id", positionIdInput.value);
        fd.append("quantity", qtyRaw);
        fd.append("sell_price", priceRaw);
        actionUrl = urlSell;
      }

      try {
        const r = await fetch(actionUrl, {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          body: fd,
        });
        const data = await r.json().catch(() => null);
        if (data && data.ok) {
          closeOverlay();
          window.location.reload();
          return;
        }
        if (data && data.errors) {
          showErrors(errEl, data.errors);
          return;
        }
        showErrors(errEl, "Unexpected response.");
      } catch {
        showErrors(errEl, "Network error.");
      }
    });
  });
})();
