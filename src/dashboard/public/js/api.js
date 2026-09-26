/* api.js — U2-01: fetch wrapper with error->toast. Never innerHTML with unescaped data. */
"use strict";

/** Escape helper — same pattern as reportData escHtml (server). */
export function esc(v) {
  return String(v ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function toast(message, kind = "error") {
  const c = document.getElementById("toasts");
  const text = String(message ?? "unknown error");
  if (!c) {
    alert(text);
    return;
  }
  const d = document.createElement("div");
  d.className = "toast toast-" + (kind === "ok" ? "ok" : kind === "warn" ? "warn" : "error");
  d.setAttribute("role", kind === "error" ? "alert" : "status");
  // textContent only: never interpret payload as HTML.
  d.textContent = text;
  c.appendChild(d);
  while (c.children.length > 5) c.removeChild(c.firstChild);
  setTimeout(() => {
    if (d.parentNode === c) c.removeChild(d);
  }, 6000);
}

async function readError(res) {
  try {
    const data = await res.json();
    if (data && typeof data.error === "string" && data.error) return data.error;
    return "HTTP " + res.status + " for " + res.url;
  } catch {
    return "HTTP " + res.status + " for " + res.url;
  }
}

export async function apiGet(path) {
  let res;
  try {
    res = await fetch(path, { headers: { Accept: "application/json" } });
  } catch (e) {
    toast("network error GET " + path + ": " + (e && e.message ? e.message : String(e)));
    throw e;
  }
  if (!res.ok) {
    const msg = await readError(res);
    toast(msg);
    throw new Error(msg);
  }
  return res.json();
}

export async function apiPost(path, body) {
  let res;
  try {
    res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body ?? {}),
    });
  } catch (e) {
    toast("network error POST " + path + ": " + (e && e.message ? e.message : String(e)));
    throw e;
  }
  if (!res.ok) {
    const msg = await readError(res);
    toast(msg);
    throw new Error(msg);
  }
  // 204/empty -> null; JSON otherwise.
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
