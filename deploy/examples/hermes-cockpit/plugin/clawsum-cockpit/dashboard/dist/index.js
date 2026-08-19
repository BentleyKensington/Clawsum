/**
 * Clawsum Home — dashboard plugin
 *
 * Tab /home: overview + Brief | Archive | Approvals | Health
 * Header crest → /home
 * Data: /api/plugins/clawsum-cockpit/{authority,brief,inbox,archive,approvals,links}
 */
(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  var PLUGINS = window.__HERMES_PLUGINS__;
  if (!SDK || !PLUGINS) return;

  var React = SDK.React;
  var useState = SDK.hooks.useState;
  var useEffect = SDK.hooks.useEffect;
  function clawsumFetchJSON(url) {
    var headers = {};
    var tok = typeof window !== "undefined" && window.__HERMES_SESSION_TOKEN__;
    if (tok) headers["X-Hermes-Session-Token"] = tok;
    return fetch(url, { credentials: "same-origin", headers: headers }).then(function (r) {
      return r.json().then(function (j) {
        if (!j || typeof j !== "object") j = { ok: false, error: "bad response" };
        if (!r.ok) {
          if (j.ok === undefined) j.ok = false;
          if (!j.error) j.error = j.detail || j.hint || ("HTTP " + r.status);
        }
        return j;
      });
    });
  }
  var fetchJSON = SDK.fetchJSON
    ? function (url) {
        return SDK.fetchJSON(url).then(function (j) {
          if (j && typeof j === "object" && j.ok === false && !j.error && (j.detail || j.hint)) {
            j.error = j.detail || j.hint;
          }
          return j;
        }).catch(function () {
          return clawsumFetchJSON(url);
        });
      }
      : clawsumFetchJSON;

  function postJSON(url, body) {
    var headers = { "Content-Type": "application/json" };
    var tok = typeof window !== "undefined" && window.__HERMES_SESSION_TOKEN__;
    if (tok) headers["X-Hermes-Session-Token"] = tok;
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: headers,
      body: JSON.stringify(body || {}),
    }).then(function (r) {
      return r.json().catch(function () { return { ok: false, error: "HTTP " + r.status }; });
    });
  }

  var API = "/api/plugins/clawsum-cockpit";
  var NAME = "clawsum-cockpit";
  var ICONS = {
    start: "🏠",
    dash: "📊",
    catalog: "🗂️",
    brief: "📋",
    approvals: "✅",
    jarvis: "🧠",
    archive: "🗄️",
    ops: "🛰️",
    health: "🛰️",
    chat: "💬",
    team: "👥",
    agents: "👥",
    skills: "🛠️",
    inbox: "📨",
    paperclip: "📎",
    connect: "🔌",
    openclaw: "🦞",
    grafana: "📈",
    arcade: "🔮",
    login: "🔑",
    progress: "⚡",
    active: "🎯",
    upcoming: "📅",
    next: "▶️",
    last: "🕘",
    greet: "🫡",
    mic: "🎙️",
    speak: "🔊",
    fire: "🔥",
    cell: "🏢",
    blocked: "⛔",
    todo: "📥",
    cron: "⏱️",
    channels: "📡",
    graph: "🕸️",
    ads: "📣",
    legal: "⚖️",
  };
  function Icon(name, fallback) {
    return ICONS[name] || fallback || "•";
  }
  function withIcon(name, label) {
    return Icon(name) + "  " + label;
  }

  var CLAWSUM_ASCII = [
    " ██████╗██╗      █████╗ ██╗    ██╗███████╗██╗   ██╗███╗   ███╗",
    "██╔════╝██║     ██╔══██╗██║    ██║██╔════╝██║   ██║████╗ ████║",
    "██║     ██║     ███████║██║ █╗ ██║███████╗██║   ██║██╔████╔██║",
    "██║     ██║     ██╔══██║██║███╗██║╚════██║██║   ██║██║╚██╔╝██║",
    "╚██████╗███████╗██║  ██║╚███╔███╔╝███████║╚██████╔╝██║ ╚═╝ ██║",
    " ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝ ╚═════╝ ╚═╝     ╚═╝",
  ];

  function clawsumAsciiHtml() {
    return (
      '<div class="clawsum-logo-ascii" aria-hidden="true">' +
      CLAWSUM_ASCII.map(function (line, i) {
        return '<span class="ln' + i + '">' + line + "</span>";
      }).join("") +
      "</div>"
    );
  }

  function HudAscii(kind) {
    var slim = kind === "slim";
    if (slim) {
      return React.createElement(
        "pre",
        { className: "clawsum-ascii-art is-slim", "aria-hidden": true },
        "CLAWSUM  ·  COMMS LINK  ·  escalate → frontier"
      );
    }
    return React.createElement(
      "div",
      { className: "clawsum-logo-ascii", "aria-hidden": true },
      CLAWSUM_ASCII.map(function (line, i) {
        return React.createElement("span", { key: i, className: "ln" + i }, line);
      })
    );
  }

  function ensureChatAscii(panel) {
    if (!panel) return;
    var path = "";
    try { path = window.location.pathname || ""; } catch (e) {}
    var onChat = path === "/chat" || path.indexOf("/chat/") === 0;
    var head = panel.querySelector(".clawsum-chatpanel-head");
    if (!head) return;
    var art = head.querySelector(".clawsum-logo-ascii, .clawsum-ascii-art");
    if (onChat) {
      if (art) art.remove();
      return;
    }
    if (head.querySelector(".clawsum-logo-ascii")) return;
    var box = document.createElement("div");
    box.innerHTML = clawsumAsciiHtml();
    if (art) art.replaceWith(box.firstChild);
    else head.insertBefore(box.firstChild, head.firstChild);
  }

  var SIDEBAR_PALETTE = [
    "#e23b2a", "#3b82f6", "#f8fafc", "#f5c518", "#bf0a30",
    "#60a5fa", "#a78bfa", "#fb923c", "#22d3ee", "#2dd4bf",
    "#f472b6", "#818cf8", "#6ee7b7", "#fbbf24", "#fb7185", "#38bdf8",
  ];

  function paintSidebarUnique() {
    if (typeof document === "undefined") return;
    var ours = document.querySelectorAll(".clawsum-sidebar-btn");
    for (var i = 0; i < ours.length; i++) {
      var btn = ours[i];
      if (btn.getAttribute("data-clawsum-painted") === "1") continue;
      var tone = "";
      var cls = btn.className || "";
      var m = cls.match(/tone-([a-z]+)/);
      if (m) tone = m[1];
      var hex = {
        lobster: "#e23b2a", navy: "#3b82f6", star: "#f8fafc", gold: "#f5c518",
        crimson: "#bf0a30", sky: "#60a5fa", violet: "#a78bfa", orange: "#fb923c",
        cyan: "#22d3ee", teal: "#2dd4bf", pink: "#f472b6", indigo: "#818cf8",
        mint: "#6ee7b7", amber: "#fbbf24", rose: "#fb7185", lime: "#a3e635",
        white: "#e8eef4",
      }[tone] || SIDEBAR_PALETTE[i % SIDEBAR_PALETTE.length];
      btn.style.setProperty("--tone", hex);
      btn.style.setProperty("--tone-border", hex);
      btn.style.color = hex;
      btn.style.borderColor = hex;
      btn.style.boxShadow = "inset 3px 0 0 " + hex;
      btn.setAttribute("data-clawsum-painted", "1");
    }
    var rail = document.querySelector("aside") || document.querySelector("[class*='Sidebar' i]");
    if (!rail) return;
    var native = [];
    rail.querySelectorAll("a, button").forEach(function (el) {
      if (el.closest && el.closest(".clawsum-sidebar, #clawsum-chat-panel, #clawsum-chat-host")) return;
      var t = (el.textContent || "").replace(/\s+/g, " ").trim();
      if (!t || t.length > 36) return;
      native.push(el);
    });
    native.forEach(function (el, idx) {
      var c = SIDEBAR_PALETTE[idx % SIDEBAR_PALETTE.length];
      el.style.setProperty("--item", c);
      el.style.setProperty("--tone", c);
      el.style.color = c;
      el.style.borderLeft = "3px solid " + c;
      el.style.paddingLeft = "0.45rem";
    });
  }

  function hideEl(el) {
    if (!el) return;
    el.classList.add("clawsum-killed-banner");
    el.setAttribute("hidden", "");
    el.style.cssText = "display:none!important;height:0!important;max-height:0!important;margin:0!important;padding:0!important;overflow:hidden!important;border:0!important;";
  }

  function hideChatJunkSection(el) {
    if (!el || el.classList.contains("clawsum-killed-banner")) return;
    if (el.closest && el.closest("#clawsum-chat-panel, #clawsum-chat-host, textarea, [contenteditable='true']")) return;
    var box = el.parentElement && (el.textContent || "").trim().length < 80 ? el.parentElement : el;
    if (box.querySelector && box.querySelector("textarea, [contenteditable='true'], input")) return;
    if ((box.textContent || "").length > 280) return;
    hideEl(box);
  }

  function stripHermesColorBanner() {
    if (typeof document === "undefined") return;
    var path = "";
    try { path = window.location.pathname || ""; } catch (e) {}
    var onChat = path === "/chat" || path.indexOf("/chat/") === 0;
    if (!onChat) return;
    var nodes = document.querySelectorAll("span, div, p, button");
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.classList && el.classList.contains("clawsum-killed-banner")) continue;
      if (el.closest && el.closest(".clawsum-killed-banner, #clawsum-chat-panel, #clawsum-chat-host, textarea, [contenteditable='true']")) continue;
      var kids = el.children ? el.children.length : 0;
      var t = (el.textContent || "").replace(/\s+/g, " ").trim();
      if (!t || t.length > 80 || kids > 6) continue;
      var isToggle = /^(?:[▸▾►▼▶▷]\s*)?Available (?:Tools|Skills|Commands|Models)$/i.test(t);
      var isRichDump = /^\[(?:bold\s+)?#[0-9a-fA-F]{3,8}\]/.test(t);
      if (!isToggle && !isRichDump) continue;
      hideChatJunkSection(el);
    }
  }

  function ensureHudShell() {
    if (typeof document === "undefined") return;
    var root = document.documentElement;
    root.classList.add("clawsum-hud-on");
    try {
      root.dataset.clawsumPage = (window.location.pathname || "/") + (window.location.search || "");
    } catch (e) {}
    paintSidebarUnique();
    var bezel = document.getElementById("clawsum-hud-bezel");
    if (bezel && !bezel.classList.contains("is-slim")) {
      bezel.remove();
      bezel = null;
    }
    if (!bezel) {
      bezel = document.createElement("div");
      bezel.id = "clawsum-hud-bezel";
      bezel.className = "is-slim";
      bezel.setAttribute("aria-hidden", "true");
      bezel.innerHTML =
        '<i class="hud-c hud-tl"></i><i class="hud-c hud-tr"></i><i class="hud-c hud-bl"></i><i class="hud-c hud-br"></i>';
      document.body.appendChild(bezel);
    }
  }

  function GaugeDial(props) {
    var val = Number(props.value);
    if (isNaN(val)) val = 0;
    var max = Number(props.max) || 100;
    var pct = max <= 0 ? 0 : Math.max(0, Math.min(1, val / max));
    var r = 34;
    var c = 2 * Math.PI * r;
    var dash = c * pct;
    var tone = props.tone || "cyan";
    return React.createElement(
      "div",
      { className: "clawsum-dial tone-" + tone },
      React.createElement(
        "svg",
        { viewBox: "0 0 88 88", className: "clawsum-dial-svg" },
        React.createElement("circle", { className: "dial-track", cx: 44, cy: 44, r: r }),
        React.createElement("circle", {
          className: "dial-arc",
          cx: 44,
          cy: 44,
          r: r,
          strokeDasharray: dash + " " + c,
          transform: "rotate(-90 44 44)",
        })
      ),
      React.createElement("div", { className: "clawsum-dial-val" }, props.value == null ? "—" : String(props.value)),
      React.createElement("div", { className: "clawsum-dial-label" }, props.label)
    );
  }

  function SparkBars(props) {
    var items = props.items || [];
    var max = 1;
    items.forEach(function (it) {
      if (Number(it.n) > max) max = Number(it.n);
    });
    return React.createElement(
      "div",
      { className: "clawsum-spark" },
      React.createElement("div", { className: "clawsum-spark-title" }, props.title || "MIX"),
      items.map(function (it, i) {
        var h = Math.max(8, Math.round((Number(it.n) / max) * 72));
        return React.createElement(
          "div",
          { key: it.label || i, className: "clawsum-spark-col tone-" + (it.tone || "cyan") },
          React.createElement("div", { className: "clawsum-spark-bar", style: { height: h + "px" } }),
          React.createElement("span", null, it.label),
          React.createElement("strong", null, it.n == null ? "—" : String(it.n))
        );
      })
    );
  }

  var FG_READY = null;
  function scriptNonce() {
    var el = document.querySelector("script[nonce]");
    return (el && (el.nonce || el.getAttribute("nonce"))) || "";
  }
  function loadForceGraph() {
    if (typeof window === "undefined") return Promise.reject(new Error("no window"));
    if (window.ForceGraph3D) return Promise.resolve(window.ForceGraph3D);
    if (FG_READY) return FG_READY;
    function inject(src) {
      return new Promise(function (resolve, reject) {
        var existing = document.querySelector('script[data-clawsum-fg="' + src + '"]');
        if (existing) {
          if (window.THREE && src.indexOf("three") >= 0) return resolve();
          if (window.ForceGraph3D && src.indexOf("force-graph") >= 0) return resolve();
          existing.addEventListener("load", resolve);
          existing.addEventListener("error", reject);
          return;
        }
        var s = document.createElement("script");
        s.src = src;
        s.async = false;
        s.dataset.clawsumFg = src;
        var nonce = scriptNonce();
        if (nonce) s.setAttribute("nonce", nonce);
        s.onload = resolve;
        s.onerror = function () { reject(new Error("script " + src)); };
        document.head.appendChild(s);
      });
    }
    function pickFg() {
      var fg = window.ForceGraph3D;
      if (fg && fg.default) fg = fg.default;
      return fg;
    }
    function chain(pair) {
      return inject(pair[0]).then(function () { return inject(pair[1]); });
    }
    var pairs = [
      [API + "/vendor/three.min.js", API + "/vendor/3d-force-graph.min.js"],
      ["https://cdn.jsdelivr.net/npm/three@0.160.1/build/three.min.js", "https://cdn.jsdelivr.net/npm/3d-force-graph@1.73.3/dist/3d-force-graph.min.js"],
      ["https://unpkg.com/three@0.160.1/build/three.min.js", "https://unpkg.com/3d-force-graph@1.73.3/dist/3d-force-graph.min.js"],
    ];
    FG_READY = chain(pairs[0])
      .catch(function () { return chain(pairs[1]); })
      .catch(function () { return chain(pairs[2]); })
      .then(function () {
        var fg = pickFg();
        if (!fg) throw new Error("ForceGraph3D missing");
        window.ForceGraph3D = fg;
        return fg;
      })
      .catch(function (err) {
        FG_READY = null;
        throw err;
      });
    return FG_READY;
  }

  function skinColors(skin) {
    if (skin === "arcade") {
      return { bg: "#020617", core: "#083344", topic: "#22d3ee", project: "#38bdf8", entity: "#67e8f9", note: "#a5f3fc", link: "rgba(34,211,238,0.35)", particle: "#22d3ee", ring: "rgba(34,211,238,0.22)" };
    }
    if (skin === "obsidian") {
      return { bg: "#09090b", core: "#18181b", topic: "#f8fafc", project: "#e2e8f0", entity: "#94a3b8", note: "#cbd5e1", link: "rgba(226,232,240,0.28)", particle: "#e8eef4", ring: "rgba(248,250,252,0.16)" };
    }
    return { bg: "#07030a", core: "#3f0d12", topic: "#e23b2a", project: "#f5c518", entity: "#fb7185", note: "#fda4af", link: "rgba(226,59,42,0.32)", particle: "#e23b2a", ring: "rgba(226,59,42,0.2)" };
  }

  function paintCanvas3D(cv, pts, edges, colors, selected, hover, nbr) {
    if (!cv || !cv.getContext) return;
    if (!cv.width) cv.width = 720;
    if (!cv.height) cv.height = 360;
    var ctx = cv.getContext("2d");
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    var w = cv.width;
    var h = cv.height;
    var grd = ctx.createRadialGradient(w * 0.5, h * 0.42, 6, w * 0.5, h * 0.55, Math.max(w, h) * 0.72);
    grd.addColorStop(0, colors.core || "#123");
    grd.addColorStop(1, colors.bg || "#020617");
    ctx.fillStyle = grd;
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "rgba(248,250,252,0.38)";
    var s;
    for (s = 0; s < 90; s++) {
      var sx = ((s * 73) % 97) / 97 * w;
      var sy = ((s * 41) % 89) / 89 * h;
      var sr = s % 7 === 0 ? 1.5 : 0.7;
      ctx.fillRect(sx, sy, sr, sr);
    }
    var cx = w * 0.5;
    var cy = h * 0.5;
    var rx = w * 0.4;
    var ry = h * 0.38;
    ctx.strokeStyle = colors.ring || "rgba(34,211,238,0.2)";
    ctx.lineWidth = 1;
    [1, 0.68, 0.38].forEach(function (sc) {
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx * sc, ry * sc, 0, 0, Math.PI * 2);
      ctx.stroke();
    });
    var byId = {};
    (pts || []).forEach(function (p) { byId[p.id] = p; });
    ctx.lineWidth = 1;
    (edges || []).slice(0, 180).forEach(function (e) {
      var a = byId[e.source];
      var b = byId[e.target];
      if (!a || !b) return;
      var hot = selected && (e.source === selected || e.target === selected);
      ctx.strokeStyle = hot ? "#fbbf24" : colors.link;
      ctx.globalAlpha = hot ? 0.85 : 0.18 + Math.max(0, (a.z + b.z + 2) / 12);
      ctx.beginPath();
      ctx.moveTo(cx + a.x * rx, cy + a.y * ry);
      ctx.lineTo(cx + b.x * rx, cy + b.y * ry);
      ctx.stroke();
    });
    ctx.globalAlpha = 1;
    var sorted = (pts || []).slice().sort(function (a, b) { return a.z - b.z; });
    sorted.forEach(function (p) {
      var x = cx + p.x * rx;
      var y = cy + p.y * ry;
      var base = p.kind === "topic" ? 8.5 : p.kind === "project" ? 6 : 4;
      var r = base * (0.72 + (p.z + 1) * 0.38);
      var col = colors[p.kind] || colors.entity;
      var glow = ctx.createRadialGradient(x - r * 0.25, y - r * 0.3, 0.4, x, y, r * 2.4);
      glow.addColorStop(0, "rgba(255,255,255,0.95)");
      glow.addColorStop(0.22, col);
      glow.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(x, y, r * 2.3, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = col;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
      var on = p.id === selected || p.id === hover || (nbr && nbr[p.id]) || p.kind === "topic" || sorted.length <= 40;
      if (on && p.label) {
        ctx.font = "600 11px ui-sans-serif, Segoe UI, sans-serif";
        ctx.fillStyle = "rgba(248,250,252,0.92)";
        ctx.fillText(String(p.label).slice(0, 22), x + r + 4, y + 4);
      }
    });
    if (!sorted.length) {
      ctx.fillStyle = "rgba(248,250,252,0.7)";
      ctx.font = "600 14px ui-sans-serif, Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("no nodes yet", w / 2, h / 2);
      ctx.textAlign = "start";
    }
  }

  function GraphStage(props) {
    var incoming = props.nodes || [];
    var incomingE = props.edges || [];
    var extraState = useState({ nodes: [], edges: [] });
    var extra = extraState[0];
    var setExtra = extraState[1];
    var rotState = useState({ x: 0.25, y: 0 });
    var rot = rotState[0];
    var setRot = rotState[1];
    var zoomState = useState(1);
    var zoom = zoomState[0];
    var setZoom = zoomState[1];
    var dragState = useState(null);
    var drag = dragState[0];
    var setDrag = dragState[1];
    var selState = useState(null);
    var selected = selState[0];
    var setSelected = selState[1];
    var spinState = useState(true);
    var spin = spinState[0];
    var setSpin = spinState[1];
    var hoverState = useState(null);
    var hover = hoverState[0];
    var setHover = hoverState[1];
    var qState = useState("");
    var q = qState[0];
    var setQ = qState[1];
    var hostState = useState(null);
    var hostEl = hostState[0];
    var setHostEl = hostState[1];
    var webglState = useState(false);
    var webglOn = webglState[0];
    var setWebglOn = webglState[1];
    var uidState = useState(function () { return "fg-" + Math.random().toString(36).slice(2, 9); });
    var uid = uidState[0];
    var fgRef = { current: null };
    var canvasOnly = props.engine === "canvas";

    useEffect(function () {
      if (!spin || drag || webglOn) return;
      var id = setInterval(function () {
        setRot(function (r) { return { x: r.x, y: r.y + 0.012 }; });
      }, 50);
      return function () { clearInterval(id); };
    }, [spin, drag]);

    var nodes = incoming.concat(extra.nodes || []);
    var seenN = {};
    nodes = nodes.filter(function (n) {
      if (!n || !n.id || seenN[n.id]) return false;
      seenN[n.id] = 1;
      return true;
    });
    var edges = incomingE.concat(extra.edges || []);
    var N = Math.max(nodes.length, 1);
    var cx0 = Math.cos(rot.x);
    var sx0 = Math.sin(rot.x);
    var cy0 = Math.cos(rot.y);
    var sy0 = Math.sin(rot.y);
    var pts = nodes.map(function (n, i) {
      var phi = Math.acos(1 - 2 * ((i + 0.5) / N));
      var theta = Math.PI * (1 + Math.sqrt(5)) * i;
      var x = Math.sin(phi) * Math.cos(theta);
      var y = Math.cos(phi);
      var z = Math.sin(phi) * Math.sin(theta);
      var x1 = x * cy0 + z * sy0;
      var z1 = -x * sy0 + z * cy0;
      var y1 = y * cx0 - z1 * sx0;
      var z2 = y * sx0 + z1 * cx0;
      return {
        id: n.id,
        label: n.label,
        facts: n.facts || [],
        degree: n.degree || 0,
        kind: n.kind || "entity",
        topic: n.topic || "",
        x: x1 * zoom,
        y: y1 * zoom,
        z: z2,
      };
    });
    var byId = {};
    pts.forEach(function (p) { byId[p.id] = p; });
    var nbr = {};
    if (selected) {
      edges.forEach(function (e) {
        if (e.source === selected) nbr[e.target] = 1;
        if (e.target === selected) nbr[e.source] = 1;
      });
    }

    function hit(evt) {
      var svg = evt.currentTarget;
      var box = svg.getBoundingClientRect();
      var mx = ((evt.clientX - box.left) / box.width) * 100;
      var my = ((evt.clientY - box.top) / box.height) * 62;
      var best = null;
      var bestD = 9;
      pts.forEach(function (p) {
        var px = 50 + p.x * 38;
        var py = 31 + p.y * 24;
        var d = (px - mx) * (px - mx) + (py - my) * (py - my);
        if (d < bestD) { bestD = d; best = p; }
      });
      return best;
    }

    function onDown(evt) {
      evt.preventDefault();
      setSpin(false);
      try { evt.currentTarget.setPointerCapture(evt.pointerId); } catch (e) {}
      setDrag({
        x: evt.clientX,
        y: evt.clientY,
        rx: rot.x,
        ry: rot.y,
        moved: false,
        hit: hit(evt),
      });
    }
    function onMove(evt) {
      if (!drag) {
        var h = hit(evt);
        setHover(h ? h.id : null);
        return;
      }
      var dx = evt.clientX - drag.x;
      var dy = evt.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
      setRot({ x: drag.rx + dy * 0.01, y: drag.ry + dx * 0.01 });
    }
    function onUp(evt) {
      if (drag && !drag.moved && drag.hit) {
        setSelected(drag.hit.id === selected ? null : drag.hit.id);
      }
      setDrag(null);
    }
    function onWheel(evt) {
      evt.preventDefault();
      setSpin(false);
      var next = zoom + (evt.deltaY > 0 ? -0.08 : 0.08);
      setZoom(Math.max(0.55, Math.min(2.2, next)));
    }

    var active = null;
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].id === selected) { active = nodes[i]; break; }
    }

    function mergeGraph(j) {
      if (!j || !j.nodes) return;
      setExtra({
        nodes: (extra.nodes || []).concat(j.nodes),
        edges: (extra.edges || []).concat(j.edges || []),
      });
    }
    function expandNode() {
      if (!active) return;
      var kind = active.kind || "";
      var url = API + "/graphify?mode=map&limit=80";
      if (kind === "topic") url += "&cluster=" + encodeURIComponent(active.label || "");
      else if (active.label) url += "&q=" + encodeURIComponent(active.label);
      else return;
      fetchJSON(url).then(mergeGraph);
    }
    function runSearch(evt) {
      if (evt) evt.preventDefault();
      var needle = (q || "").trim();
      if (!needle) return;
      setSpin(false);
      fetchJSON(API + "/graphify?mode=wide&limit=80&q=" + encodeURIComponent(needle)).then(mergeGraph);
    }

    function bindHost(el) {
      if (el && el !== hostEl) setHostEl(el);
    }

    useEffect(function () {
      var el = document.getElementById(uid);
      if (el && el !== hostEl) setHostEl(el);
    }, [uid]);

    function bindCanvas(el) {
      if (!el) return;
      paintCanvas3D(el, pts, edges, skinColors(props.skin), selected, hover, nbr);
    }

    useEffect(function () {
      if (webglOn) return;
      var cv = document.getElementById(uid + "-cv");
      paintCanvas3D(cv, pts, edges, skinColors(props.skin), selected, hover, nbr);
    });

    useEffect(function () {
      if (canvasOnly) return;
      if (!hostEl) return;
      var gone = false;
      var graph = null;
      loadForceGraph().then(function (ForceGraph3D) {
        if (gone || !hostEl) return;
        var colors = skinColors(props.skin || "hermes");
        var THREE = window.THREE;
        graph = ForceGraph3D()(hostEl)
          .backgroundColor(colors.bg)
          .showNavInfo(false)
          .nodeId("id")
          .nodeLabel(function (n) { return (n.label || n.id) + (n.kind ? " · " + n.kind : ""); })
          .nodeRelSize(5)
          .nodeVal(function (n) {
            if (n.kind === "topic") return 16;
            if (n.kind === "project") return 9;
            return 4 + Math.min(Number(n.degree) || 1, 10);
          })
          .nodeColor(function (n) { return colors[n.kind] || colors.entity; })
          .linkSource("source")
          .linkTarget("target")
          .linkColor(function () { return colors.link; })
          .linkWidth(0.55)
          .linkOpacity(0.42)
          .linkDirectionalParticles(2)
          .linkDirectionalParticleSpeed(0.004)
          .linkDirectionalParticleWidth(1.15)
          .linkDirectionalParticleColor(function () { return colors.particle; })
          .onNodeClick(function (n) {
            setSpin(false);
            setSelected(function (cur) { return cur === n.id ? null : n.id; });
          });
        try {
          if (THREE && graph.scene) {
            var scene = graph.scene();
            scene.add(new THREE.AmbientLight(0xffffff, 0.65));
            var key = new THREE.PointLight(colors.particle, 1.25, 900);
            key.position.set(60, 90, 50);
            scene.add(key);
            var fill = new THREE.PointLight(0x3b82f6, 0.45, 900);
            fill.position.set(-80, -20, 40);
            scene.add(fill);
          }
        } catch (eLite) {}
        fgRef.current = graph;
        setWebglOn(true);
      }).catch(function () {
        if (!gone) setWebglOn(false);
      });
      return function () {
        gone = true;
        try { if (graph && typeof graph._destructor === "function") graph._destructor(); } catch (eD) {}
        fgRef.current = null;
      };
    }, [hostEl, props.skin]);

    useEffect(function () {
      if (!fgRef.current) return;
      var g = fgRef.current;
      var ns = nodes.map(function (n) {
        return {
          id: n.id,
          label: n.label,
          kind: n.kind || "entity",
          degree: n.degree || 0,
          facts: n.facts || [],
          topic: n.topic || "",
        };
      });
      var ls = edges.map(function (e, i) {
        return { source: e.source, target: e.target, label: e.label || "", id: "l" + i };
      });
      try { g.graphData({ nodes: ns, links: ls }); } catch (eG) {}
    }, [webglOn, nodes.length, edges.length, extra.nodes && extra.nodes.length]);

    return React.createElement(
      "div",
      { className: "clawsum-graph-wrap skin-" + (props.skin || "hermes") },
      React.createElement(
        "div",
        {
          className: "clawsum-graph-stage is-3d is-live" + (webglOn ? " is-webgl" : "") + " skin-" + (props.skin || "hermes"),
          onPointerDown: webglOn ? undefined : onDown,
          onPointerMove: webglOn ? undefined : onMove,
          onPointerUp: webglOn ? undefined : onUp,
          onPointerLeave: webglOn ? undefined : onUp,
          onWheel: webglOn ? undefined : onWheel,
        },
        React.createElement("div", { className: "clawsum-fg-host", id: uid, ref: bindHost }),
        webglOn
          ? null
          : React.createElement("canvas", {
              id: uid + "-cv",
              className: "clawsum-graph-canvas",
              width: 720,
              height: 360,
              ref: bindCanvas,
            }),
        React.createElement(
          "form",
          { className: "clawsum-graph-search", onSubmit: runSearch },
          React.createElement("input", {
            value: q,
            onChange: function (e) { setQ(e.target.value); },
            placeholder: "expand topic…",
            onPointerDown: function (e) { e.stopPropagation(); },
          }),
          React.createElement("button", { type: "submit", onPointerDown: function (e) { e.stopPropagation(); } }, "GO")
        ),
        React.createElement(
          "div",
          { className: "clawsum-graph-hint" },
          webglOn ? "WebGL · drag orbit · scroll zoom · click node" : "3D canvas · drag orbit · scroll zoom · click node"
        )
      ),
      active
        ? React.createElement(
            "aside",
            { className: "clawsum-graph-inspector" },
            React.createElement("strong", null, active.label),
            React.createElement("div", { className: "muted" }, (active.degree || (active.facts || []).length) + " links"),
            React.createElement(
              "ul",
              null,
              (active.facts || []).slice(0, 8).map(function (f, fi) {
                return React.createElement(
                  "li",
                  { key: fi },
                  React.createElement("code", null, f.predicate),
                  " ",
                  f.other
                );
              })
            ),
            React.createElement(
              "div",
              { className: "clawsum-link-row" },
              React.createElement(
                "button",
                { type: "button", className: "clawsum-text-btn", onClick: expandNode },
                active.kind === "topic" ? "Expand topic" : "Expand neighbors"
              ),
              React.createElement(
                "button",
                { type: "button", className: "clawsum-text-btn", onClick: function () { setSelected(null); setSpin(true); } },
                "Close"
              )
            )
          )
        : null
    );
  }

  function cssVar(name) {
    if (typeof document === "undefined") return "";
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function asBg(value) {
    if (!value) return "";
    if (value.indexOf("url(") === 0) return value;
    return "url(\"" + value + "\")";
  }

  function Chip(label, key) {
    return React.createElement("span", { key: key || label, className: "clawsum-chip" }, label);
  }

  var KPI_TONES = ["cyan", "sky", "teal", "amber", "rose", "lime", "orange", "gold", "mint", "sky"];
  var GREET_LAST_KEY = "clawsum.boss.greet.last";
  var GREET_AT_KEY = "clawsum.boss.greet.at";
  var GREET_LINE_KEY = "clawsum.boss.greet.line";
  var GREET_COOLDOWN_MS = 45000;
  var BOSS_ADDRESSES = [
    "Boss", "Gerald", "Sir", "Chief", "Captain", "Commander",
    "principal", "maestro", "fearless leader", "head of the house",
  ];
  function cap(s) {
    if (!s) return s;
    return s.charAt(0).toUpperCase() + s.slice(1);
  }
  function timeOfDay() {
    var h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 17) return "Good afternoon";
    return "Good evening";
  }
  function pickBossAddress() {
    var last = "";
    try { last = localStorage.getItem(GREET_LAST_KEY) || ""; } catch (e) {}
    var pool = BOSS_ADDRESSES.filter(function (a) { return a !== last; });
    var choice = pool[Math.floor(Math.random() * pool.length)] || BOSS_ADDRESSES[0];
    try { localStorage.setItem(GREET_LAST_KEY, choice); } catch (e) {}
    return choice;
  }
  function buildBossGreeting(force) {
    var lastAt = 0;
    try { lastAt = Number(localStorage.getItem(GREET_AT_KEY) || 0); } catch (e) {}
    var now = Date.now();
    if (!force && lastAt && now - lastAt < GREET_COOLDOWN_MS) {
      try {
        var cached = localStorage.getItem(GREET_LINE_KEY);
        if (cached) return cached;
      } catch (e) {}
    }
    var a = pickBossAddress();
    var tod = timeOfDay();
    var openers = [
      tod + ", " + a + ".",
      "Welcome back, " + a + ".",
      "Standing by, " + a + ".",
      "Ready when you are, " + a + ".",
      "Online for you, " + a + ".",
      cap(a) + " — Clawsum Agent at your service.",
      "At your command, " + a + ".",
      "Briefing mode, " + a + ".",
      tod + " — " + a + ", session report is up.",
      "Unique open for you, " + a + ". Let's drive the top item.",
      a + ", Clawsum Agent online — queue loaded.",
      "Check-in, " + a + ". What should we clear first?",
      "Board is live, " + a + ".",
      "Mission face on, " + a + ".",
      "Hello again, " + a + " — not the same greeting twice.",
    ];
    var lastLine = "";
    try { lastLine = localStorage.getItem(GREET_LINE_KEY) || ""; } catch (e2) {}
    var pool = openers.filter(function (x) { return x !== lastLine; });
    var line = pool[Math.floor(Math.random() * pool.length)] || openers[0];
    try {
      localStorage.setItem(GREET_AT_KEY, String(now));
      localStorage.setItem(GREET_LINE_KEY, line);
    } catch (e3) {}
    return line;
  }
  function BossGreetingBanner() {
    var lineState = useState(function () { return buildBossGreeting(false); });
    var line = lineState[0];
    var setLine = lineState[1];
    var hudState = useState(null);
    var hud = hudState[0];
    var setHud = hudState[1];
    useEffect(function () {
      fetchJSON(API + "/hud").then(setHud).catch(function () {});
      var onVis = function () {
        if (document.visibilityState === "visible") setLine(buildBossGreeting(false));
      };
      document.addEventListener("visibilitychange", onVis);
      window.addEventListener("focus", function () { setLine(buildBossGreeting(false)); });
      return function () {
        document.removeEventListener("visibilitychange", onVis);
      };
    }, []);
    var ticker = [line].concat((hud && hud.ticker) || []);
    var track = ticker.concat(ticker).join("   ·   ");
    return React.createElement(
      "div",
      { className: "clawsum-boss-greet clawsum-marquee", role: "status", "aria-live": "polite" },
      React.createElement("span", { className: "clawsum-boss-greet-mark" }, "🫡 HUD"),
      React.createElement(
        "div",
        { className: "clawsum-marquee-window" },
        React.createElement("div", { className: "clawsum-marquee-track" }, track)
      ),
      React.createElement(
        "button",
        {
          type: "button",
          className: "clawsum-boss-greet-refresh",
          title: "New greeting",
          onClick: function () { setLine(buildBossGreeting(true)); },
        },
        "↻"
      )
    );
  }

  function LinkButtons(links) {
    if (!links) return null;
    var items = [
      { href: links.boss, label: withIcon("paperclip", "Paperclip") },
      { href: links.openclaw, label: withIcon("openclaw", "OpenClaw") },
      { href: links.grafana, label: withIcon("grafana", "Grafana") },
      { href: links.arcade, label: withIcon("arcade", "Arcade Studio") },
    ];
    return React.createElement(
      "div",
      { className: "clawsum-link-row" },
      items.filter(function (i) { return i.href; }).map(function (i) {
        return React.createElement(
          "a",
          { key: i.label, href: i.href, target: "_blank", rel: "noreferrer" },
          i.label
        );
      })
    );
  }

  function useAuthority() {
    var state = useState({ loading: true });
    var data = state[0];
    var setData = state[1];
    useEffect(function () {
      var cancel = false;
      fetchJSON(API + "/authority")
        .then(function (j) { if (!cancel) setData(Object.assign({ loading: false }, j)); })
        .catch(function (e) {
          if (!cancel) setData({ loading: false, ok: false, error: String(e), agents: [], skills: [] });
        });
      return function () { cancel = true; };
    }, []);
    return data;
  }

  function AgentsPanel() {
    var auth = useAuthority();
    var selState = useState(null);
    var selected = selState[0];
    var setSelected = selState[1];

    if (auth.loading) {
      return React.createElement("div", { className: "muted" }, "Loading agents…");
    }
    if (!auth.ok && !(auth.agents && auth.agents.length)) {
      return React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("p", null, "Authority matrix not loaded."),
        React.createElement("p", { className: "muted" }, auth.error || "Missing authority.json")
      );
    }

    var agents = auth.agents || [];
    var active = null;
    for (var i = 0; i < agents.length; i++) {
      if (agents[i].id === selected) { active = agents[i]; break; }
    }
    if (!active && agents.length) active = agents[0];

    return React.createElement(
      "div",
      { className: "clawsum-split" },
      React.createElement(
        "div",
        { className: "clawsum-list" },
        React.createElement("div", { className: "clawsum-list-title" }, "Agents (" + agents.length + ")"),
        agents.map(function (a) {
          return React.createElement(
            "button",
            {
              key: a.id,
              type: "button",
              className: "clawsum-list-item" + (active && active.id === a.id ? " active" : ""),
              onClick: function () { setSelected(a.id); },
            },
            React.createElement("strong", null, a.name || a.id),
            React.createElement("span", { className: "muted" }, a.id + " · " + (a.skills || []).length + " skills")
          );
        })
      ),
      active
        ? React.createElement(
            "div",
            { className: "clawsum-detail" },
            React.createElement("h2", null, active.name || active.id),
            React.createElement("p", { className: "muted" }, active.domains || ""),
            React.createElement(
              "div",
              { className: "clawsum-card" },
              React.createElement("strong", null, "Cells"),
              React.createElement(
                "div",
                { className: "clawsum-chip-row" },
                (active.cells || []).map(function (c) { return Chip(c, c); })
              )
            ),
            React.createElement(
              "div",
              { className: "clawsum-card" },
              React.createElement("strong", null, "Authorized skills"),
              (active.skills || []).length
                ? React.createElement(
                    "ul",
                    { className: "clawsum-plain-list" },
                    (active.skills || []).map(function (s) {
                      return React.createElement(
                        "li",
                        { key: s },
                        React.createElement("code", { className: "clawsum-skill-pill" }, s)
                      );
                    })
                  )
                : React.createElement("p", { className: "muted" }, "No skills mapped.")
            )
          )
        : null
    );
  }

  function SkillsPanel() {
    var auth = useAuthority();
    var selState = useState(null);
    var selected = selState[0];
    var setSelected = selState[1];
    var qState = useState("");
    var q = qState[0];
    var setQ = qState[1];

    if (auth.loading) {
      return React.createElement("div", { className: "muted" }, "Loading skills…");
    }
    var skills = (auth.skills || []).slice().sort(function (a, b) {
      return String(a.id).localeCompare(String(b.id));
    });
    if (q) {
      var qq = q.toLowerCase();
      skills = skills.filter(function (s) {
        return String(s.id).toLowerCase().indexOf(qq) >= 0 ||
          (s.agents || []).join(" ").toLowerCase().indexOf(qq) >= 0;
      });
    }
    var active = null;
    for (var i = 0; i < skills.length; i++) {
      if (skills[i].id === selected) { active = skills[i]; break; }
    }
    if (!active && skills.length) active = skills[0];

    var tiers = auth.tiers || {};

    return React.createElement(
      "div",
      { className: "clawsum-split" },
      React.createElement(
        "div",
        { className: "clawsum-list" },
        React.createElement("div", { className: "clawsum-list-title" }, "Skills (" + skills.length + ")"),
        React.createElement("input", {
          className: "clawsum-search",
          placeholder: "Filter skills…",
          value: q,
          onChange: function (e) { setQ(e.target.value); },
        }),
        skills.map(function (s) {
          return React.createElement(
            "button",
            {
              key: s.id,
              type: "button",
              className: "clawsum-list-item" + (active && active.id === s.id ? " active" : ""),
              onClick: function () { setSelected(s.id); },
            },
            React.createElement("strong", null, s.id),
            React.createElement(
              "span",
              { className: "muted" },
              "T" + s.tier + " · " + (s.agents || []).join(", ")
            )
          );
        })
      ),
      active
        ? React.createElement(
            "div",
            { className: "clawsum-detail" },
            React.createElement("h2", null, React.createElement("code", null, active.id)),
            React.createElement(
              "p",
              { className: "muted" },
              "Auto ≤ Tier " + active.tier +
                (tiers[String(active.tier)] ? " — " + tiers[String(active.tier)] : "")
            ),
            React.createElement(
              "div",
              { className: "clawsum-card" },
              React.createElement("strong", null, "Agents authorized"),
              React.createElement(
                "div",
                { className: "clawsum-chip-row" },
                (active.agents || []).map(function (a) { return Chip(a, a); })
              )
            ),
            React.createElement(
              "div",
              { className: "clawsum-card" },
              React.createElement("strong", null, "Cells"),
              React.createElement(
                "div",
                { className: "clawsum-chip-row" },
                (active.cells || []).map(function (c) { return Chip(c, c); })
              )
            ),
            React.createElement(
              "div",
              { className: "clawsum-card" },
              React.createElement("strong", null, "Credential prefixes"),
              React.createElement(
                "div",
                { className: "clawsum-chip-row" },
                (active.credentials || []).length
                  ? (active.credentials || []).map(function (c) { return Chip(c, c); })
                  : React.createElement("span", { className: "muted" }, "—")
              )
            )
          )
        : null
    );
  }

  function BriefPanel() {
    var state = useState({ loading: true });
    var data = state[0];
    var setData = state[1];
    useEffect(function () {
      var cancel = false;
      fetchJSON(API + "/session-startup")
        .then(function (j) {
          if (cancel) return;
          setData(Object.assign({ loading: false }, j));
          // Autoplay printed brief when Auto-Speak is on (once per browser tab session)
          try {
            if (localStorage.getItem("clawsum.autospeak") === "0") return;
            if (sessionStorage.getItem("clawsum.brief.autoplayed") === "1") return;
            if (!j || !j.ok) return;
            sessionStorage.setItem("clawsum.brief.autoplayed", "1");
            var g = "";
            try { g = localStorage.getItem("clawsum.boss.greet.line") || ""; } catch (eG) {}
            if (!g && j.greetings && j.greetings.length) {
              g = j.greetings[Math.floor(Math.random() * j.greetings.length)];
            }
            var utter =
              (g ? g + ". " : "") +
              "Last session: " + (j.last_session || "fresh start") + ". " +
              ((j.pending_approvals != null) ? (j.pending_approvals + " pending approvals. ") : "") +
              ((j.inbox_needs_boss != null) ? (j.inbox_needs_boss + " inbox items need the Boss. ") : "") +
              "Next: " + ((j.next_actions || [])[0] || "none flagged");
            setTimeout(function () {
              try {
                if (typeof window.__clawsumSpeak === "function") window.__clawsumSpeak(utter);
                else {
                  // Chat panel may mount slightly later
                  var tries = 0;
                  var wait = function () {
                    if (typeof window.__clawsumSpeak === "function") {
                      window.__clawsumSpeak(utter);
                      return;
                    }
                    tries += 1;
                    if (tries < 20) setTimeout(wait, 250);
                  };
                  wait();
                }
              } catch (eS) {}
            }, 700);
          } catch (eA) {}
        })
        .catch(function (e) {
          if (!cancel) setData({ loading: false, ok: false, error: String(e), progress: [], next_actions: [] });
        });
      return function () { cancel = true; };
    }, []);

    if (data.loading) {
      return React.createElement("div", { className: "muted" }, "Loading session briefing…");
    }
    if (!data.ok && data.error) {
      return React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("p", null, "Brief not ready."),
        React.createElement("p", { className: "muted" }, data.error)
      );
    }

    var greeting = "";
    try {
      greeting = localStorage.getItem("clawsum.boss.greet.line") || "";
    } catch (e) {}
    if (!greeting && data.greetings && data.greetings.length) {
      greeting = data.greetings[Math.floor(Math.random() * data.greetings.length)];
    }

    function taskList(rows, emptyMsg) {
      rows = rows || [];
      if (!rows.length) {
        return React.createElement("p", { className: "muted" }, emptyMsg || "none flagged");
      }
      return React.createElement(
        "ul",
        { style: { margin: "0.4rem 0 0", paddingLeft: "1.2rem" } },
        rows.map(function (t, i) {
          return React.createElement(
            "li",
            { key: t.identifier || i },
            "[" + (t.identifier || "?") + "] (" + (t.priority || "—") + "/" + (t.status || "—") + ") " +
              (t.title || "")
          );
        })
      );
    }

    return React.createElement(
      "div",
      { className: "clawsum-session-brief" },
      React.createElement(
        "div",
        { className: "clawsum-boss-greet", role: "status" },
        React.createElement("span", { className: "clawsum-boss-greet-mark" }, "🫡 SESSION BRIEF"),
        React.createElement("span", { className: "clawsum-boss-greet-line" }, greeting)
      ),
      React.createElement(
        "div",
        { className: "clawsum-grid" },
        React.createElement(
          "div",
          { className: "clawsum-card tone-amber" },
          React.createElement("div", { className: "muted" }, withIcon("approvals", "Pending approvals")),
          React.createElement("div", { className: "clawsum-kpi" }, String(data.pending_approvals || 0))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card tone-cyan" },
          React.createElement("div", { className: "muted" }, withIcon("inbox", "Inbox needs Boss")),
          React.createElement("div", { className: "clawsum-kpi" }, String(data.inbox_needs_boss || 0))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card tone-lime" },
          React.createElement("div", { className: "muted" }, withIcon("active", "Active / upcoming")),
          React.createElement(
            "div",
            { className: "clawsum-kpi" },
            String((data.active_tasks || []).length) + " / " + String((data.upcoming_tasks || []).length)
          )
        )
      ),
      React.createElement(
        "div",
        { className: "clawsum-card tone-sky" },
        React.createElement("strong", null, withIcon("last", "Last session")),
        React.createElement("p", { style: { margin: "0.45rem 0 0", whiteSpace: "pre-wrap" } }, data.last_session || "fresh start")
      ),
      React.createElement(
        "div",
        { className: "clawsum-card tone-teal" },
        React.createElement("strong", null, withIcon("progress", "Progress since last session")),
        React.createElement(
          "ul",
          { style: { margin: "0.4rem 0 0", paddingLeft: "1.2rem" } },
          (data.progress || ["not enough data"]).map(function (p, i) {
            return React.createElement("li", { key: i }, p);
          })
        )
      ),
      React.createElement(
        "div",
        { className: "clawsum-card tone-lime" },
        React.createElement("strong", null, withIcon("active", "Active tasks")),
        taskList(data.active_tasks, "none flagged — see upcoming backlog")
      ),
      React.createElement(
        "div",
        { className: "clawsum-card tone-orange" },
        React.createElement("strong", null, withIcon("upcoming", "Upcoming tasks")),
        taskList(data.upcoming_tasks, "none flagged")
      ),
      React.createElement(
        "div",
        { className: "clawsum-card tone-rose" },
        React.createElement("strong", null, withIcon("next", "Recommended next actions")),
        React.createElement(
          "ol",
          { style: { margin: "0.4rem 0 0", paddingLeft: "1.2rem" } },
          (data.next_actions || []).map(function (a, i) {
            return React.createElement("li", { key: i }, a);
          })
        ),
        React.createElement(
          "div",
          { className: "clawsum-chip-row" },
          React.createElement(
            "button",
            {
              type: "button",
              className: "clawsum-chip",
              onClick: function () {
                try {
                  sessionStorage.setItem("clawsum.pending_prompt", data.brief_prompt || "Deliver the full Session Startup Brief now.");
                  sessionStorage.setItem("clawsum.pending_autosend", "1");
                } catch (e2) {}
                window.location.href = "/chat";
              },
            },
            withIcon("chat", "Deliver in chat")
          ),
          React.createElement(
            "button",
            {
              type: "button",
              className: "clawsum-chip",
              onClick: function () {
                if (!window.speechSynthesis) return;
                var text = (greeting ? greeting + ". " : "") +
                  "Last session: " + (data.last_session || "") + ". " +
                  ((data.pending_approvals != null) ? (data.pending_approvals + " pending approvals. ") : "") +
                  ((data.inbox_needs_boss != null) ? (data.inbox_needs_boss + " inbox items need the Boss. ") : "") +
                  "Next: " + ((data.next_actions || [])[0] || "");
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
              },
            },
            withIcon("speak", "Speak brief")
          )
        ),
        LinkButtons(data.links)
      )
    );
  }

  function InboxPanel() {
    var state = useState({ loading: true });
    var data = state[0];
    var setData = state[1];
    useEffect(function () {
      var cancel = false;
      fetchJSON(API + "/inbox")
        .then(function (j) { if (!cancel) setData(Object.assign({ loading: false }, j)); })
        .catch(function (e) {
          if (!cancel) setData({ loading: false, ok: false, error: String(e), action_items: [] });
        });
      return function () { cancel = true; };
    }, []);

    if (data.loading) {
      return React.createElement("div", { className: "muted" }, "Loading inbox…");
    }
    if (!data.ok && data.error) {
      return React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("p", null, "Inbox not ready."),
        React.createElement("p", { className: "muted" }, data.hint || data.error)
      );
    }
    var items = data.action_items || [];
    var analyses = data.email_analyses || items;
    var questions = data.questions_for_boss || [];
    return React.createElement(
      "div",
      null,
      React.createElement(
        "div",
        { className: "clawsum-grid" },
        React.createElement(
          "div",
          { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Mailbox"),
          React.createElement("div", null, data.mailbox || "clawsums@gmail.com")
        ),
        React.createElement(
          "div",
          { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Action / needs Boss"),
          React.createElement("div", { className: "clawsum-kpi" }, String(items.length))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Analyses stored"),
          React.createElement("div", { className: "clawsum-kpi" }, String(data.reviews_stored || analyses.length || 0))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Active reminders"),
          React.createElement("div", { className: "clawsum-kpi" }, String(data.reminders_active || 0))
        )
      ),
      React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("strong", null, "Ask Boss"),
        React.createElement(
          "ul",
          { style: { margin: "0.5rem 0 0", paddingLeft: "1.2rem" } },
          (questions.length ? questions : ["Run gmail-inbox-review.py to queue questions."]).map(function (q, i) {
            return React.createElement("li", { key: i }, q);
          })
        )
      ),
      React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("strong", null, "Per-email analysis"),
        analyses.length
          ? React.createElement(
              "div",
              null,
              analyses.map(function (item, i) {
                return React.createElement(
                  "div",
                  {
                    key: i,
                    style: {
                      borderTop: i ? "1px solid rgba(45,212,191,0.2)" : "none",
                      paddingTop: 8,
                      marginTop: 8,
                    },
                  },
                  React.createElement(
                    "div",
                    { style: { fontWeight: 600 } },
                    "[" + (item.analysis_priority || item.review_status || "?") + "] " +
                      (item.subject || "(no subject)")
                  ),
                  React.createElement(
                    "div",
                    { className: "muted", style: { fontSize: "0.8rem" } },
                    (item.from_addr || "") +
                      " · " +
                      (item.business_slug || "—") +
                      (item.person_name ? " · " + item.person_name : "")
                  ),
                  React.createElement(
                    "p",
                    { style: { margin: "0.4rem 0" } },
                    item.analysis_intent || item.analysis_summary || "No analysis yet — run gmail-inbox-review.py"
                  ),
                  item.analysis_recommendation
                    ? React.createElement(
                        "p",
                        { className: "muted", style: { margin: 0 } },
                        "→ " + item.analysis_recommendation
                      )
                    : null
                );
              })
            )
          : React.createElement("p", { className: "muted" }, "No email analyses yet.")
      )
    );
  }

  function ArchivePanel() {
    var state = useState({ loading: true });
    var data = state[0];
    var setData = state[1];
    var openIdState = useState(null);
    var openId = openIdState[0];
    var setOpenId = openIdState[1];
    useEffect(function () {
      var cancel = false;
      fetchJSON(API + "/archive")
        .then(function (j) { if (!cancel) setData(Object.assign({ loading: false }, j)); })
        .catch(function (e) {
          if (!cancel) setData({ loading: false, ok: false, error: String(e), drive_forward: [], session_briefs: [] });
        });
      return function () { cancel = true; };
    }, []);

    if (data.loading) {
      return React.createElement("div", { className: "muted" }, "Loading archive brief…");
    }
    var drive = data.drive_forward || [];
    var questions = data.questions_for_boss || [];
    var briefs = data.session_briefs || [];
    return React.createElement(
      "div",
      null,
      React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("strong", null, "Session Startup Briefs"),
        React.createElement(
          "p",
          { className: "muted", style: { margin: "0.35rem 0 0.75rem" } },
          "Archived Hermes first-message briefs. Files: " +
            (data.session_briefs_path || "/paperclip/.hermes/session-briefs/")
        ),
        briefs.length
          ? React.createElement(
              "ul",
              { style: { margin: 0, paddingLeft: "1.2rem" } },
              briefs.map(function (b, i) {
                var id = b.id || b.filename || String(i);
                var label =
                  (b.created_at ? String(b.created_at).replace("T", " ").slice(0, 19) : "—") +
                  (b.greeting ? " — " + b.greeting : "");
                var open = openId === id;
                return React.createElement(
                  "li",
                  { key: id, style: { marginBottom: "0.5rem" } },
                  React.createElement(
                    "button",
                    {
                      type: "button",
                      className: "clawsum-linkish",
                      style: {
                        background: "none",
                        border: "none",
                        padding: 0,
                        color: "inherit",
                        textAlign: "left",
                        cursor: "pointer",
                        textDecoration: "underline",
                      },
                      onClick: function () { setOpenId(open ? null : id); },
                    },
                    label
                  ),
                  open
                    ? React.createElement(
                        "pre",
                        {
                          style: {
                            whiteSpace: "pre-wrap",
                            margin: "0.4rem 0 0",
                            fontSize: "0.85rem",
                            maxHeight: "18rem",
                            overflow: "auto",
                          },
                        },
                        b.body_md || "(empty)"
                      )
                    : null
                );
              })
            )
          : React.createElement(
              "p",
              { className: "muted" },
              "No archived session briefs yet. After the next startup brief, Hermes should write here."
            )
      ),
      (!data.ok && data.error)
        ? React.createElement(
            "div",
            { className: "clawsum-card" },
            React.createElement("p", null, "ChatGPT archive not ready."),
            React.createElement("p", { className: "muted" }, data.hint || data.error)
          )
        : null,
      React.createElement(
        "div",
        { className: "clawsum-grid" },
        React.createElement(
          "div",
          { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Personal (held private)"),
          React.createElement("div", { className: "clawsum-kpi" }, String(data.personal_conversations || 0))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Drive-forward"),
          React.createElement("div", { className: "clawsum-kpi" }, String(drive.length))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Session briefs"),
          React.createElement("div", { className: "clawsum-kpi" }, String(data.session_briefs_count != null ? data.session_briefs_count : briefs.length))
        )
      ),
      React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("strong", null, "Ask Boss next"),
        React.createElement(
          "ul",
          { style: { margin: "0.5rem 0 0", paddingLeft: "1.2rem" } },
          (questions.length ? questions : ["Classify/link archive to queue questions."]).map(function (q, i) {
            return React.createElement("li", { key: i }, q);
          })
        )
      ),
      React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("strong", null, "Related work (archive ↔ Paperclip)"),
        drive.length
          ? React.createElement(
              "ul",
              { style: { margin: "0.5rem 0 0", paddingLeft: "1.2rem" } },
              drive.map(function (item, i) {
                var link = item.paperclip_issue_identifier || "unlinked";
                var cell = item.business_slug || item.scope || "—";
                return React.createElement(
                  "li",
                  { key: i },
                  "[" + (item.work_status || "?") + "] (" + cell + ") " +
                    (item.title || "untitled") +
                    " — " + link
                );
              })
            )
          : React.createElement("p", { className: "muted" }, "No pending business archive items.")
      )
    );
  }

  function ProcessesPanel() {
    var state = useState({ loading: true });
    var data = state[0];
    var setData = state[1];
    function reload() {
      fetchJSON(API + "/processes?limit=80")
        .then(function (j) { setData(Object.assign({ loading: false }, j)); })
        .catch(function (e) {
          setData({ loading: false, ok: false, error: String(e), processes: [], kpi: {} });
        });
    }
    useEffect(function () { reload(); }, []);

    function decide(id, decision) {
      var headers = { "Content-Type": "application/json" };
      var tok = window.__HERMES_SESSION_TOKEN__;
      if (tok) headers["X-Hermes-Session-Token"] = tok;
      fetch(API + "/processes/" + id + "/decide", {
        method: "POST",
        credentials: "same-origin",
        headers: headers,
        body: JSON.stringify({ decision: decision }),
      })
        .then(function (r) { return r.json(); })
        .then(function () { reload(); })
        .catch(function () { reload(); });
    }

    if (data.loading) {
      return React.createElement("div", { className: "muted" }, "Loading Jarvis process log…");
    }
    var kpi = data.kpi || {};
    var rows = data.processes || [];
    return React.createElement(
      "div",
      { className: "clawsum-processes" },
      React.createElement(
        "div",
        { className: "clawsum-grid" },
        React.createElement(
          "div",
          { className: "clawsum-card tone-amber" },
          React.createElement("div", { className: "muted" }, withIcon("jarvis", "Awaiting Boss")),
          React.createElement("div", { className: "clawsum-kpi" }, String(kpi.awaiting_boss != null ? kpi.awaiting_boss : "—"))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card tone-lime" },
          React.createElement("div", { className: "muted" }, "Executed today"),
          React.createElement("div", { className: "clawsum-kpi" }, String(kpi.executed != null ? kpi.executed : "—"))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card tone-rose" },
          React.createElement("div", { className: "muted" }, "Failed today"),
          React.createElement("div", { className: "clawsum-kpi" }, String(kpi.failed != null ? kpi.failed : "—"))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card tone-cyan" },
          React.createElement("div", { className: "muted" }, "Today total"),
          React.createElement("div", { className: "clawsum-kpi" }, String(kpi.today_total != null ? kpi.today_total : "—"))
        )
      ),
      React.createElement(
        "p",
        { className: "muted" },
        "Batch gate: Jarvis lists every execute up front → Approve All once → runs the full batch. No drip-feed terminal approvals."
      ),
      data.ok === false
        ? React.createElement("p", { className: "muted" }, data.error || "Process log unavailable")
        : null,
      React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("strong", null, withIcon("jarvis", "Process log")),
        rows.length
          ? React.createElement(
              "ul",
              { className: "clawsum-process-list" },
              rows.map(function (p) {
                var meta = p.meta || {};
                var steps = (meta && meta.steps) || [];
                return React.createElement(
                  "li",
                  { key: p.id, className: "clawsum-process-item status-" + (p.status || "") },
                  React.createElement(
                    "div",
                    { className: "clawsum-process-head" },
                    React.createElement("strong", null, p.title || "Process"),
                    React.createElement(
                      "span",
                      { className: "clawsum-process-badge" },
                      (p.status || "?") + " · " + (p.mode || "batch_gate")
                    )
                  ),
                  p.intent
                    ? React.createElement("p", { className: "muted" }, p.intent)
                    : null,
                  steps.length
                    ? React.createElement(
                        "ol",
                        { className: "clawsum-process-steps" },
                        steps.map(function (s) {
                          return React.createElement(
                            "li",
                            { key: String(s.n) + "-" + (s.title || "") },
                            React.createElement("strong", null, s.title || ("Step " + s.n)),
                            s.detail
                              ? React.createElement("span", { className: "muted" }, " — " + s.detail)
                              : null,
                            " ",
                            React.createElement(
                              "em",
                              { className: "muted" },
                              "(" + (s.status || "pending") + ")"
                            )
                          );
                        })
                      )
                    : p.plan_md
                      ? React.createElement(
                          "pre",
                          { className: "clawsum-process-plan" },
                          String(p.plan_md).slice(0, 1200)
                        )
                      : null,
                  p.error_text
                    ? React.createElement("p", { className: "clawsum-process-err" }, p.error_text)
                    : null,
                  p.status === "proposed" || p.status === "confirmed"
                    ? React.createElement(
                        "div",
                        { className: "clawsum-chip-row" },
                        p.status === "proposed"
                          ? React.createElement(
                              "button",
                              {
                                type: "button",
                                className: "clawsum-chip clawsum-chip-primary",
                                onClick: function () { decide(p.id, "approve"); },
                              },
                              "Approve All (" + (steps.length || "plan") + ")"
                            )
                          : null,
                        React.createElement(
                          "button",
                          {
                            type: "button",
                            className: "clawsum-chip",
                            onClick: function () { decide(p.id, "reject"); },
                          },
                          "Reject"
                        ),
                        React.createElement(
                          "button",
                          {
                            type: "button",
                            className: "clawsum-chip",
                            onClick: function () { decide(p.id, "cancel"); },
                          },
                          "Cancel"
                        )
                      )
                    : null
                );
              })
            )
          : React.createElement("p", { className: "muted" }, "No Jarvis processes logged yet.")
      )
    );
  }

  function ApprovalsPanel() {
    var state = useState({ loading: true, approvals: [] });
    var data = state[0];
    var setData = state[1];
    useEffect(function () {
      var cancel = false;
      fetchJSON(API + "/approvals")
        .then(function (j) { if (!cancel) setData(Object.assign({ loading: false }, j)); })
        .catch(function (e) {
          if (!cancel) setData({ loading: false, ok: false, approvals: [], error: String(e) });
        });
      return function () { cancel = true; };
    }, []);

    if (data.loading) {
      return React.createElement("div", { className: "muted" }, "Loading approvals…");
    }
    if (!data.approvals || !data.approvals.length) {
      return React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("p", null, "No approvals yet."),
        React.createElement(
          "p",
          { className: "muted" },
          data.error || data.hint ||
            "Create one: python3 scripts/overwatch-create-approval.py --business wnn-client --action-type send_sms --summary \"Test\""
        )
      );
    }
    return React.createElement(
      "div",
      null,
      data.approvals.map(function (a) {
        var badgeClass = a.status === "pending" ? "clawsum-badge warn" : "clawsum-badge ok";
        return React.createElement(
          "div",
          { className: "clawsum-card", key: a.id },
          React.createElement(
            "div",
            { style: { display: "flex", justifyContent: "space-between", gap: 8 } },
            React.createElement("strong", null, a.action_type || "action"),
            React.createElement("span", { className: badgeClass }, a.status + " · " + (a.risk_level || ""))
          ),
          React.createElement("div", null, a.action_summary),
          React.createElement(
            "div",
            { className: "muted", style: { marginTop: 6 } },
            (a.business_name || a.business_slug || "—") +
              " · " +
              (a.agent_name || "") +
              (a.created_at ? " · " + a.created_at : "")
          )
        );
      })
    );
  }

  function HealthPanel() {
    var state = useState({ links: null });
    var data = state[0];
    var setData = state[1];
    useEffect(function () {
      fetchJSON(API + "/links")
        .then(function (j) { setData({ links: j }); })
        .catch(function () { setData({ links: null }); });
    }, []);

    var links = data.links || {};
    var embed = links.grafana_ops || links.grafana_embed || links.grafana;
    return React.createElement(
      "div",
      null,
      React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("strong", null, "Ops · Grafana"),
        React.createElement(
          "p",
          { className: "muted" },
          "Clawsum Operations strip (SSO cookie may require one Grafana visit first)."
        ),
        LinkButtons(links),
        React.createElement(
          "div",
          { className: "clawsum-link-row" },
          links.connect
            ? React.createElement("a", { href: links.connect, target: "_blank", rel: "noreferrer" }, "Connect")
            : null,
          links.login
            ? React.createElement("a", { href: links.login, target: "_blank", rel: "noreferrer" }, "Login hub")
            : null,
          links.grafana_health
            ? React.createElement("a", { href: links.grafana_health, target: "_blank", rel: "noreferrer" }, "Health dash")
            : null
        )
      ),
      embed
        ? React.createElement("iframe", {
            className: "clawsum-iframe",
            title: "Clawsum Operations",
            src: embed,
            referrerPolicy: "no-referrer",
          })
        : React.createElement("div", { className: "muted" }, "Grafana URL not configured.")
    );
  }

  function HomePanel(props) {
    var setTab = props.setTab;
    var auth = useAuthority();
    var briefState = useState(null);
    var brief = briefState[0];
    var setBrief = briefState[1];
    var inboxState = useState(null);
    var inbox = inboxState[0];
    var setInbox = inboxState[1];
    var linksState = useState(null);
    var links = linksState[0];
    var setLinks = linksState[1];
    var graphState = useState(null);
    var graph = graphState[0];
    var setGraph = graphState[1];

    useEffect(function () {
      fetchJSON(API + "/brief").then(setBrief).catch(function () {});
      fetchJSON(API + "/inbox").then(setInbox).catch(function () {});
      fetchJSON(API + "/links").then(setLinks).catch(function () {});
      fetchJSON(API + "/graphify?mode=map&limit=64").then(setGraph).catch(function () {});
    }, []);

    var needsBoss = inbox && inbox.action_items ? inbox.action_items.length : null;
    if (needsBoss == null && inbox && inbox.totals && inbox.totals.needs_boss != null) {
      needsBoss = inbox.totals.needs_boss;
    }
    var questions = (inbox && inbox.questions_for_boss) || [];
    var pending = brief && brief.pending_approvals != null ? brief.pending_approvals : null;
    var jarvisAwait = brief && brief.jarvis && brief.jarvis.awaiting_boss != null ? brief.jarvis.awaiting_boss : null;
    var jarvisFailed = brief && brief.jarvis && brief.jarvis.failed != null ? brief.jarvis.failed : null;
    var cells = brief && brief.business_cells != null ? brief.business_cells : null;
    var issues = (brief && brief.paperclip && (brief.paperclip.issues || brief.paperclip.tasks)) || {};
    var todoN = issues.todo != null ? issues.todo : (issues.backlog != null ? issues.backlog : null);
    var progN = issues.in_progress != null ? issues.in_progress : null;
    var blockedN = issues.blocked != null ? issues.blocked : null;
    var inboxErr = inbox && inbox.ok === false ? (inbox.error || inbox.detail || inbox.hint) : null;

    function tile(href, label, sub, count, onClick, icon, tone) {
      var common = {
        className: "clawsum-home-tile tone-" + (tone || "teal"),
        key: label,
      };
      var body = [
        React.createElement(
          "div",
          { className: "clawsum-home-tile-top", key: "t" },
          React.createElement("span", { className: "clawsum-ico", "aria-hidden": true }, icon || "•"),
          React.createElement("div", { className: "clawsum-home-tile-label" }, label)
        ),
        React.createElement("div", { className: "muted", key: "s" }, sub),
      ];
      if (count != null) {
        body.unshift(
          React.createElement("div", { className: "clawsum-kpi", key: "c" }, String(count))
        );
      }
      if (onClick) {
        return React.createElement(
          "button",
          Object.assign({}, common, { type: "button", onClick: onClick }),
          body
        );
      }
      if (href && /^https?:\/\//i.test(href)) {
        return React.createElement("a", Object.assign({}, common, { href: href, target: "_blank", rel: "noreferrer" }), body);
      }
      return React.createElement("a", Object.assign({}, common, { href: href }), body);
    }

    var openN = issues.open != null ? issues.open : null;
    var graphNodes = (graph && graph.nodes) || [];
    var graphEdges = (graph && graph.edges) || [];
    var arcadeG = (graph && graph.arcade) || {};
    var obsidianG = (graph && graph.obsidian) || {};

    return React.createElement(
      "div",
      { className: "clawsum-home clawsum-hud is-tight" },
      HudAscii("full"),
      React.createElement(
        "div",
        { className: "clawsum-instrument-row" },
        React.createElement(GaugeDial, { value: needsBoss, max: 40, label: "INBOX", tone: "cyan" }),
        React.createElement(GaugeDial, { value: pending, max: 20, label: "GATES", tone: "amber" }),
        React.createElement(GaugeDial, { value: auth.agent_count, max: 24, label: "CREW", tone: "lime" }),
        React.createElement(GaugeDial, { value: auth.skill_count, max: 80, label: "SKILLS", tone: "orange" }),
        React.createElement(GaugeDial, { value: graph && (graph.total_facts || graph.count), max: 5000, label: "MEMORY", tone: "violet" }),
        React.createElement(SparkBars, {
          title: "BOARD",
          items: [
            { label: "RUN", n: progN, tone: "lime" },
            { label: "HOLD", n: blockedN, tone: "rose" },
            { label: "Q", n: todoN != null ? todoN : openN, tone: "amber" },
            { label: "CELL", n: cells, tone: "sky" },
          ],
        })
      ),
      React.createElement(
        "div",
        { className: "clawsum-viz-card" },
        React.createElement(
          "div",
          { className: "clawsum-viz-head" },
          React.createElement("strong", null, "GRAPHIFY · 3D MEMORY"),
          React.createElement(
            "span",
            { className: "muted" },
            graphNodes.length
              ? graphNodes.length + " hubs · " + graphEdges.length + " links · " + ((graph && graph.total_facts) || 0) + " facts"
              : (graph && graph.error) || "spinning up vault…"
          ),
          React.createElement(
            "button",
            { type: "button", className: "clawsum-text-btn", onClick: function () { setTab("graph"); } },
            "Expand"
          )
        ),
        React.createElement(
          "div",
          { className: "clawsum-triple-graph" },
          React.createElement(
            "section",
            { className: "clawsum-graph-pane is-arcade" },
            React.createElement("header", null, "ARCADE · 3D"),
            React.createElement(GraphStage, {
              nodes: arcadeG.nodes || graphNodes,
              edges: arcadeG.edges || graphEdges,
              skin: "arcade",
              engine: "canvas",
            })
          ),
          React.createElement(
            "section",
            { className: "clawsum-graph-pane is-obsidian" },
            React.createElement("header", null, "OBSIDIAN · 3D"),
            React.createElement(GraphStage, {
              nodes: obsidianG.nodes || [],
              edges: obsidianG.edges || [],
              skin: "obsidian",
              engine: "canvas",
            })
          ),
          React.createElement(
            "section",
            { className: "clawsum-graph-pane is-hermes" },
            React.createElement("header", null, "HERMES · 3D"),
            React.createElement(GraphStage, { nodes: graphNodes, edges: graphEdges, engine: "canvas" })
          )
        )
      ),
      React.createElement(
        "div",
        { className: "clawsum-home-tiles" },
        tile(null, "Dash", "Command", null, function () { setTab("dash"); }, "📊", "navy"),
        tile(null, "Catalog", "Index", null, function () { setTab("catalog"); }, "🗂️", "star"),
        tile(null, "Brief", "Daily", null, function () { setTab("brief"); }, "📋", "gold"),
        tile(null, "Approvals", "Gates", pending, function () { setTab("approvals"); }, "✅", "crimson"),
        tile(null, "Jarvis", "Processes", jarvisAwait, function () { setTab("processes"); }, "🧠", "sky"),
        tile(null, "Archive", "ChatGPT", null, function () { setTab("archive"); }, "🗄️", "violet"),
        tile("/inbox", "Inbox", "Ask Boss", needsBoss, null, "📨", "cyan"),
        tile("/agents", "Team", "Crew", auth.agent_count, null, "👥", "violet"),
        tile("/skills", "Skills", "Toolbox", auth.skill_count, null, "🛠️", "orange"),
        tile("/chat", "Chat", "Talk", null, null, "💬", "sky"),
        tile("/cron", "Cron", "Jobs", null, null, "⏱️", "gold"),
        tile("/kanban", "Kanban", "Board", null, null, "📌", "mint"),
        tile(null, "Channels", "Live", null, function () { setTab("channels"); }, "📡", "indigo"),
        tile(null, "Ops", "Health", null, function () { setTab("health"); }, "🛰️", "sky"),
        tile(null, "Graphify", "Memory", graph && (graph.total_facts || graph.count), function () { setTab("graph"); }, "🕸️", "white"),
        tile((links && links.paperclip) || (links && links.boss) || "https://paperclip.clawsum.com", "Paperclip", "Tasks", todoN != null ? todoN : openN, null, "📎", "lobster"),
        tile((links && links.openclaw) || "https://openclaw.clawsum.com", "OpenClaw", "Gateway", null, null, "🦞", "gold"),
        tile((links && links.grafana) || "https://grafana.clawsum.com", "Grafana", "KPIs", null, null, "📈", "lime"),
        tile((links && links.arcade) || "https://arcade.clawsum.com", "Arcade", "Studio", null, null, "🔮", "navy"),
        tile((links && links.connect) || "https://connect.clawsum.com", "Connect", "Integrations", null, null, "🔌", "cyan")
      ),
      React.createElement(AskBossCard, { questions: questions, inboxErr: inboxErr, setTab: setTab }),
      LinkButtons(links)
    );
  }

  function AskBossCard(props) {
    var questions = props.questions || [];
    var qState = useState(questions[0] || "");
    var selected = qState[0];
    var setSelected = qState[1];
    var replyState = useState("");
    var reply = replyState[0];
    var setReply = replyState[1];
    var statusState = useState("");
    var status = statusState[0];
    var setStatus = statusState[1];
    useEffect(function () {
      if (!selected && questions[0]) setSelected(questions[0]);
    }, [questions]);
    function send() {
      if (!reply.trim() || !selected) {
        setStatus("Pick a question and type a reply.");
        return;
      }
      setStatus("Sending…");
      postJSON(API + "/inbox/reply", { question: selected, reply: reply.trim() })
        .then(function (j) {
          if (j && j.ok) {
            setStatus("Logged. Jarvis will treat this as answered.");
            setReply("");
          } else {
            setStatus((j && j.error) || "Could not store reply.");
          }
        })
        .catch(function (e) { setStatus(String(e)); });
    }
    return React.createElement(
      "div",
      { className: "clawsum-card clawsum-card-ask" },
      React.createElement("strong", null, "🔥 Ask Boss — reply here"),
      props.inboxErr
        ? React.createElement("p", { className: "muted" }, "Inbox not ready: " + props.inboxErr)
        : React.createElement(
            "ul",
            { style: { margin: "0.5rem 0 0", paddingLeft: "1.2rem" } },
            (questions.length ? questions.slice(0, 6) : ["Inbox is clear — or still loading."]).map(
              function (q, i) {
                return React.createElement(
                  "li",
                  { key: i },
                  React.createElement(
                    "button",
                    {
                      type: "button",
                      className: "clawsum-text-btn" + (selected === q ? " active" : ""),
                      onClick: function () { setSelected(q); },
                    },
                    q
                  )
                );
              }
            )
          ),
      React.createElement("textarea", {
        className: "clawsum-ask-reply",
        rows: 3,
        placeholder: "Type your decision or answer…",
        value: reply,
        onChange: function (e) { setReply(e.target.value); },
      }),
      React.createElement(
        "div",
        { className: "clawsum-link-row" },
        React.createElement(
          "button",
          { type: "button", className: "clawsum-text-btn", onClick: send },
          "Send reply"
        ),
        React.createElement("a", { href: "/inbox" }, "📨 Open Inbox"),
        React.createElement(
          "button",
          {
            type: "button",
            className: "clawsum-text-btn",
            onClick: function () { props.setTab("brief"); },
          },
          "📋 Open Brief"
        )
      ),
      status ? React.createElement("p", { className: "muted" }, status) : null
    );
  }

  function CronPanel() {
    var state = useState({ loading: true });
    var data = state[0];
    var setData = state[1];
    useEffect(function () {
      fetchJSON(API + "/cron").then(function (j) {
        setData(Object.assign({ loading: false }, j || {}));
      }).catch(function (e) {
        setData({ loading: false, ok: false, error: String(e), jobs: [] });
      });
    }, []);
    if (data.loading) return React.createElement("div", { className: "muted" }, "Loading scheduled jobs…");
    var jobs = data.jobs || [];
    return React.createElement(
      "div",
      { className: "clawsum-panel-wrap" },
      React.createElement("h2", null, "Cron — Clawsum host jobs"),
      React.createElement("p", { className: "muted" }, data.note || "Live Clawsum crontab, not Hermes-internal jobs."),
      jobs.length
        ? React.createElement(
            "div",
            { className: "clawsum-cron-list" },
            jobs.map(function (j) {
              return React.createElement(
                "a",
                {
                  key: j.id || j.name,
                  className: "clawsum-cron-row status-" + (j.status || "unknown"),
                  href: j.href || "/home",
                },
                React.createElement("strong", null, j.name || j.id),
                React.createElement("span", { className: "muted" }, j.schedule || ""),
                React.createElement("span", { className: "clawsum-chip" }, j.status || "unknown")
              );
            })
          )
        : React.createElement("p", { className: "muted" }, data.error || "No jobs registered yet.")
    );
  }

  function ChannelsPanel() {
    var state = useState({ loading: true });
    var data = state[0];
    var setData = state[1];
    useEffect(function () {
      fetchJSON(API + "/channels").then(function (j) {
        setData(Object.assign({ loading: false }, j || {}));
      }).catch(function (e) {
        setData({ loading: false, ok: false, error: String(e), channels: [] });
      });
    }, []);
    if (data.loading) return React.createElement("div", { className: "muted" }, "Reading OpenClaw channels…");
    var rows = data.channels || [];
    return React.createElement(
      "div",
      { className: "clawsum-panel-wrap" },
      React.createElement("h2", null, "Channels — live OpenClaw"),
      React.createElement(
        "p",
        { className: "muted" },
        (data.gateway_up ? "Gateway up. " : "Gateway not answering. ") + (data.note || "")
      ),
      React.createElement(
        "div",
        { className: "clawsum-channel-grid" },
        rows.map(function (c) {
          return React.createElement(
            "a",
            {
              key: c.id,
              className: "clawsum-channel-card status-" + (c.status || "unknown"),
              href: c.href || "https://openclaw.clawsum.com",
              target: "_blank",
              rel: "noreferrer",
            },
            React.createElement("strong", null, c.name),
            React.createElement("div", { className: "clawsum-kpi" }, c.enabled ? "LIVE" : "OFF"),
            React.createElement("div", { className: "muted" }, c.detail || "")
          );
        })
      )
    );
  }

  function Graph2D(props) {
    var nodes = props.nodes || [];
    var edges = props.edges || [];
    var title = props.title || "GRAPH";
    var N = Math.max(nodes.length, 1);
    if (!nodes.length) {
      return React.createElement(
        "div",
        { className: "clawsum-g2d is-empty" },
        React.createElement("div", { className: "clawsum-g2d-chrome" }, title),
        React.createElement("p", { className: "muted" }, "No nodes yet — snapshot or expand a topic.")
      );
    }
    return React.createElement(
      "div",
      { className: "clawsum-g2d" },
      React.createElement("div", { className: "clawsum-g2d-chrome" }, title),
      React.createElement(
        "svg",
        { viewBox: "0 0 100 62", className: "clawsum-g2d-svg", preserveAspectRatio: "xMidYMid meet" },
        React.createElement("rect", { x: 0, y: 0, width: 100, height: 62, className: "clawsum-g2d-grid" }),
        edges.slice(0, 100).map(function (e, i) {
          var ai = -1;
          var bi = -1;
          for (var n = 0; n < nodes.length; n++) {
            if (nodes[n].id === e.source) ai = n;
            if (nodes[n].id === e.target) bi = n;
          }
          if (ai < 0 || bi < 0) return null;
          var a = {
            x: 50 + Math.sin((ai / N) * Math.PI * 2) * 38,
            y: 31 + Math.cos((ai / N) * Math.PI * 2) * 22,
          };
          var b = {
            x: 50 + Math.sin((bi / N) * Math.PI * 2) * 38,
            y: 31 + Math.cos((bi / N) * Math.PI * 2) * 22,
          };
          return React.createElement("line", {
            key: "e" + i,
            x1: a.x, y1: a.y, x2: b.x, y2: b.y,
            className: "clawsum-g2d-edge",
          });
        }),
        nodes.slice(0, 72).map(function (n, i) {
          var x = 50 + Math.sin((i / N) * Math.PI * 2) * 38;
          var y = 31 + Math.cos((i / N) * Math.PI * 2) * 22;
          var kind = n.kind || "entity";
          return React.createElement(
            "g",
            { key: n.id },
            React.createElement("rect", {
              x: x - 3.2, y: y - 1.4, width: 6.4, height: 2.8, rx: 0.25,
              className: "clawsum-g2d-node kind-" + kind,
            }),
            React.createElement(
              "text",
              { x: x, y: y + 0.45, className: "clawsum-g2d-label", textAnchor: "middle" },
              String(n.label || "").slice(0, 10)
            )
          );
        })
      )
    );
  }

  function KpiStrip(props) {
    var kpis = props.kpis || [];
    var grafana = props.grafana || {};
    if (!kpis.length) return null;
    return React.createElement(
      "div",
      { className: "clawsum-kpi-strip" },
      kpis.map(function (k) {
        var v = k.value;
        return React.createElement(
          "div",
          { key: k.id, className: "clawsum-kpi-cell" + (v == null ? " is-empty" : "") },
          React.createElement("div", { className: "clawsum-kpi-val" }, v == null ? "—" : String(v)),
          React.createElement("div", { className: "clawsum-kpi-lab" }, k.label),
          React.createElement("div", { className: "muted" }, k.source === "none" ? "no SoR" : k.source)
        );
      }),
      grafana.ops
        ? React.createElement(
            "a",
            { className: "clawsum-kpi-cell is-link", href: grafana.ops, target: "_blank", rel: "noreferrer" },
            React.createElement("div", { className: "clawsum-kpi-val" }, "GRAF"),
            React.createElement("div", { className: "clawsum-kpi-lab" }, "Operations"),
            React.createElement("div", { className: "muted" }, "grafana.clawsum.com")
          )
        : null,
      grafana.health
        ? React.createElement(
            "a",
            { className: "clawsum-kpi-cell is-link", href: grafana.health, target: "_blank", rel: "noreferrer" },
            React.createElement("div", { className: "clawsum-kpi-val" }, "LIVE"),
            React.createElement("div", { className: "clawsum-kpi-lab" }, "Health"),
            React.createElement("div", { className: "muted" }, "probes")
          )
        : null
    );
  }

  function GraphPanel() {
    var state = useState({ loading: true });
    var data = state[0];
    var setData = state[1];
    useEffect(function () {
      fetchJSON(API + "/graphify?mode=map&limit=64").then(function (j) {
        setData(Object.assign({ loading: false }, j || {}));
      }).catch(function (e) {
        setData({ loading: false, ok: false, error: String(e), nodes: [], edges: [] });
      });
    }, []);
    if (data.loading) return React.createElement("div", { className: "muted" }, "Spinning up triple graph…");
    var nodes = data.nodes || [];
    var arcade = data.arcade || {};
    var obsidian = data.obsidian || {};
    return React.createElement(
      "div",
      { className: "clawsum-panel-wrap is-tight" },
      React.createElement("h2", null, "GRAPH DECK — Arcade · Obsidian · Hermes"),
      React.createElement(
        "p",
        { className: "muted" },
        data.ok === false
          ? (data.hint || data.error || "Memory graph not ready.")
          : (nodes.length + " Hermes nodes · " + ((data.edges || []).length) + " links · " + (data.total_facts || 0) + " facts. Click a TOPIC to expand. Grafana: ops + health dashboards.")
      ),
      React.createElement(KpiStrip, { kpis: data.kpis || [], grafana: data.grafana || {} }),
      React.createElement(
        "div",
        { className: "clawsum-triple-graph" },
        React.createElement(
          "section",
          { className: "clawsum-graph-pane is-arcade" },
          React.createElement("header", null, "ARCADE MEMORY · 3D HUD"),
          React.createElement("p", { className: "muted" }, (arcade.note || "Entity mirror") + " · Studio is 2D admin, this pane is our 3D."),
          React.createElement(GraphStage, { nodes: arcade.nodes || nodes, edges: arcade.edges || data.edges || [], skin: "arcade", engine: "canvas" })
        ),
        React.createElement(
          "section",
          { className: "clawsum-graph-pane is-obsidian" },
          React.createElement("header", null, "OBSIDIAN VAULT · 3D NOTES"),
          React.createElement("p", { className: "muted" }, (obsidian.note || "Vault wikilinks") + (obsidian.scanned ? " · scanned " + obsidian.scanned : "")),
          React.createElement(GraphStage, { nodes: obsidian.nodes || [], edges: obsidian.edges || [], skin: "obsidian", engine: "canvas" })
        ),
        React.createElement(
          "section",
          { className: "clawsum-graph-pane is-hermes" },
          React.createElement("header", null, "HERMES CLUSTERS · 3D TOPICS"),
          React.createElement("p", { className: "muted" }, "Topics → projects → entities. Drag / zoom / expand."),
          React.createElement(GraphStage, { nodes: nodes, edges: data.edges || [], engine: "canvas" })
        )
      )
    );
  }

  function DashPanel(props) {
    return React.createElement(
      "div",
      null,
      React.createElement(
        "p",
        { className: "muted clawsum-main-sub" },
        "Same ops KPIs as Start — fuller layout for daily command."
      ),
      React.createElement(HomePanel, { setTab: props.setTab })
    );
  }

  function CatalogPanel() {
    var state = useState({ loading: true });
    var data = state[0];
    var setData = state[1];
    var secState = useState("agents");
    var section = secState[0];
    var setSection = secState[1];
    var selState = useState(null);
    var selected = selState[0];
    var setSelected = selState[1];

    useEffect(function () {
      var cancel = false;
      fetchJSON(API + "/catalog")
        .then(function (j) {
          if (!cancel) setData(Object.assign({ loading: false }, j || {}));
        })
        .catch(function (e) {
          if (!cancel) setData({ loading: false, ok: false, error: String(e), agents: [], skills: [], projects: [], tasks: [], notes: [] });
        });
      return function () { cancel = true; };
    }, []);

    if (data.loading) {
      return React.createElement("div", { className: "muted" }, "Loading catalog…");
    }

    var lists = {
      agents: data.agents || [],
      skills: data.skills || [],
      projects: data.projects || [],
      tasks: data.tasks || [],
    };
    var items = lists[section] || [];
    var active = null;
    for (var i = 0; i < items.length; i++) {
      var id = items[i].id || items[i].identifier || items[i].title;
      if (String(id) === String(selected)) {
        active = items[i];
        break;
      }
    }
    if (!active && items.length) active = items[0];

    function pickLabel(it) {
      if (section === "skills") return it.id;
      if (section === "tasks") return (it.identifier ? it.identifier + " · " : "") + (it.title || it.id);
      return it.name || it.id || it.title;
    }

    function detailBody(it) {
      if (!it) {
        return React.createElement("p", { className: "muted" }, "Not enough data for this section.");
      }
      var blurb = it.blurb || it.domains || "Explanation not available yet.";
      var kids = [
        React.createElement("h2", { key: "h" }, pickLabel(it)),
        React.createElement("div", { key: "e", className: "clawsum-explain tone-teal" }, blurb),
      ];
      if (section === "agents") {
        kids.push(
          React.createElement("div", { key: "d", className: "clawsum-card" },
            React.createElement("strong", null, "Domains"),
            React.createElement("p", { className: "muted", style: { marginTop: "0.35rem" } }, it.domains || "—")
          ),
          React.createElement("div", { key: "c", className: "clawsum-card" },
            React.createElement("strong", null, "Cells"),
            React.createElement("div", { className: "clawsum-chip-row" },
              (it.cells || []).length ? (it.cells || []).map(function (c) { return Chip(c, c); }) : React.createElement("span", { className: "muted" }, "—"))
          ),
          React.createElement("div", { key: "s", className: "clawsum-card" },
            React.createElement("strong", null, "Skills"),
            React.createElement("div", { className: "clawsum-chip-row" },
              (it.skills || []).length ? (it.skills || []).map(function (s) { return Chip(s, s); }) : React.createElement("span", { className: "muted" }, "None mapped"))
          )
        );
      }
      if (section === "skills") {
        kids.push(
          React.createElement("div", { key: "t", className: "clawsum-card" },
            React.createElement("strong", null, "Tier"),
            React.createElement("p", { className: "muted", style: { marginTop: "0.35rem" } },
              "T" + it.tier + (data.tiers && data.tiers[String(it.tier)] ? " — " + data.tiers[String(it.tier)] : "") +
              (it.primary ? " · Primary" : " · Toolbox"))
          ),
          React.createElement("div", { key: "a", className: "clawsum-card" },
            React.createElement("strong", null, "Agents"),
            React.createElement("div", { className: "clawsum-chip-row" },
              (it.agents || []).map(function (a) { return Chip(a, a); }))
          ),
          React.createElement("div", { key: "c", className: "clawsum-card" },
            React.createElement("strong", null, "Cells / credentials"),
            React.createElement("div", { className: "clawsum-chip-row" },
              (it.cells || []).concat(it.credentials || []).map(function (c, idx) { return Chip(c, c + idx); }))
          )
        );
      }
      if (section === "projects") {
        kids.push(
          React.createElement("div", { key: "k", className: "clawsum-card" },
            React.createElement("strong", null, "Kind"),
            React.createElement("p", { className: "muted", style: { marginTop: "0.35rem" } }, it.kind || "cell")
          )
        );
      }
      if (section === "tasks") {
        kids.push(
          React.createElement("div", { key: "st", className: "clawsum-card" },
            React.createElement("strong", null, "Status / assignee"),
            React.createElement("p", { className: "muted", style: { marginTop: "0.35rem" } },
              (it.status || "—") + (it.assignee ? " · " + it.assignee : ""))
          ),
          it.href
            ? React.createElement("div", { key: "l", className: "clawsum-link-row" },
                React.createElement("a", { href: it.href, target: "_blank", rel: "noreferrer" }, "Open Paperclip"))
            : null
        );
      }
      return kids;
    }

    var sections = [
      { id: "agents", label: "Agents", tone: "violet", count: (data.agents || []).length },
      { id: "skills", label: "Skills", tone: "amber", count: (data.skills || []).length },
      { id: "projects", label: "Projects", tone: "sky", count: (data.projects || []).length },
      { id: "tasks", label: "Tasks", tone: "lime", count: (data.tasks || []).length },
    ];

    return React.createElement(
      "div",
      { className: "clawsum-catalog" },
      React.createElement(
        "p",
        { className: "muted clawsum-main-sub" },
        "Explained view of agents, skills, projects (cells), and Paperclip tasks. Empty sections say when data is missing."
      ),
      (data.notes || []).length
        ? React.createElement(
            "div",
            { className: "clawsum-card" },
            React.createElement("strong", null, "Data notes"),
            React.createElement(
              "ul",
              { style: { margin: "0.45rem 0 0", paddingLeft: "1.2rem" } },
              data.notes.map(function (n, i) {
                return React.createElement("li", { key: i, className: "muted" }, n);
              })
            )
          )
        : null,
      React.createElement(
        "div",
        { className: "clawsum-tabs", style: { marginBottom: "0.85rem" } },
        sections.map(function (s) {
          return React.createElement(
            "button",
            {
              key: s.id,
              type: "button",
              className: "clawsum-tab tone-" + s.tone + (section === s.id ? " is-active" : ""),
              onClick: function () {
                setSection(s.id);
                setSelected(null);
              },
            },
            React.createElement("span", { className: "clawsum-tab-label" }, s.label),
            React.createElement("span", { className: "clawsum-tab-sub" }, String(s.count) + " items")
          );
        })
      ),
      React.createElement(
        "div",
        { className: "clawsum-split" },
        React.createElement(
          "div",
          { className: "clawsum-list" },
          React.createElement(
            "div",
            { className: "clawsum-list-title" },
            sections.filter(function (s) { return s.id === section; })[0].label +
              " (" +
              items.length +
              ")"
          ),
          items.length
            ? items.map(function (it) {
                var id = it.id || it.identifier || it.title;
                return React.createElement(
                  "button",
                  {
                    key: String(id),
                    type: "button",
                    className:
                      "clawsum-list-item" +
                      (active && String(active.id || active.identifier || active.title) === String(id)
                        ? " active"
                        : ""),
                    onClick: function () { setSelected(id); },
                  },
                  React.createElement("strong", null, pickLabel(it)),
                  React.createElement(
                    "span",
                    { className: "muted" },
                    section === "skills"
                      ? "T" + it.tier
                      : section === "tasks"
                        ? it.status || ""
                        : (it.domains || it.kind || "").slice(0, 42)
                  )
                );
              })
            : React.createElement(
                "p",
                { className: "muted", style: { padding: "0.75rem" } },
                "Not enough data in this section."
              )
        ),
        React.createElement("div", { className: "clawsum-detail" }, detailBody(active))
      ),
      React.createElement(
        "div",
        { className: "clawsum-link-row" },
        React.createElement("a", { href: "/agents" }, "Team cell map"),
        React.createElement("a", { href: "/skills" }, "Skill heatmap"),
        React.createElement(
          "a",
          {
            href: (data.links && (data.links.paperclip || data.links.boss)) || "https://paperclip.clawsum.com",
            target: "_blank",
            rel: "noreferrer",
          },
          "Paperclip board"
        )
      )
    );
  }

  function CockpitPage() {
    var tabState = useState("home");
    var tab = tabState[0];
    var setTab = tabState[1];
    var auth = useAuthority();
    useEffect(function () {
      try {
        var params = new URLSearchParams(window.location.search || "");
        var t = params.get("tab") || params.get("view");
        var map = { start: "home", home: "home", dash: "dash", catalog: "catalog", org: "catalog", brief: "brief", archive: "archive", approvals: "approvals", processes: "processes", jarvis: "processes", health: "health", ops: "health", cron: "cron", channels: "channels", graph: "graph", graphify: "graph" };
        if (t && map[t]) setTab(map[t]);
      } catch (e) {}
    }, []);

    function go(id) {
      setTab(id);
      try {
        var u = new URL(window.location.href);
        u.pathname = "/home";
        u.searchParams.set("tab", id === "home" ? "start" : id);
        window.history.replaceState({}, "", u.toString());
      } catch (e) {}
    }

    var panels = {
      home: React.createElement(HomePanel, { setTab: go }),
      dash: React.createElement(DashPanel, { setTab: go }),
      catalog: React.createElement(CatalogPanel),
      brief: React.createElement(BriefPanel),
      archive: React.createElement(ArchivePanel),
      approvals: React.createElement(ApprovalsPanel),
      processes: React.createElement(ProcessesPanel),
      health: React.createElement(HealthPanel),
      cron: React.createElement(CronPanel),
      channels: React.createElement(ChannelsPanel),
      graph: React.createElement(GraphPanel),
    };

    var titles = {
      home: withIcon("start", "Start hub"),
      dash: withIcon("dash", "Dash"),
      catalog: withIcon("catalog", "Catalog"),
      brief: withIcon("brief", "CEO Brief"),
      archive: withIcon("archive", "Archive"),
      approvals: withIcon("approvals", "Approvals"),
      processes: withIcon("jarvis", "Jarvis Processes"),
      health: withIcon("ops", "Ops"),
      cron: withIcon("cron", "Cron"),
      channels: withIcon("channels", "Channels"),
      graph: withIcon("graph", "Graphify"),
    };

    var tabs = [
      { id: "home", label: withIcon("start", "Start"), short: "Ops KPIs + Ask Boss", tone: "cyan", kind: "tab" },
      { id: "dash", label: withIcon("dash", "Dash"), short: "Fuller KPI workspace", tone: "lime", kind: "tab" },
      { id: "catalog", label: withIcon("catalog", "Catalog"), short: "Agents · Skills · Projects · Tasks", tone: "teal", kind: "tab" },
      { id: "team", label: withIcon("team", "Team"), short: "Cell map + roles", tone: "sky", kind: "link", href: "/agents" },
      { id: "skills", label: withIcon("skills", "Skills"), short: "Authority + Toolbox", tone: "amber", kind: "link", href: "/skills" },
      { id: "inbox", label: withIcon("inbox", "Inbox"), short: "Reviews & Ask Boss", tone: "orange", kind: "link", href: "/inbox" },
      { id: "cron", label: withIcon("cron", "Cron"), short: "Scheduled jobs", tone: "amber", kind: "tab" },
      { id: "channels", label: withIcon("channels", "Channels"), short: "Discord · Telegram live", tone: "lime", kind: "tab" },
      { id: "graph", label: withIcon("graph", "Graphify"), short: "3D Obsidian memory", tone: "violet", kind: "tab" },
      { id: "health", label: withIcon("ops", "Ops"), short: "Grafana operations", tone: "sky", kind: "tab" },
      { id: "brief", label: withIcon("brief", "Brief"), short: "CEO command desk", tone: "rose", kind: "tab" },
      { id: "approvals", label: withIcon("approvals", "Approvals"), short: "Waiting on Boss", tone: "teal", kind: "tab" },
      { id: "processes", label: withIcon("jarvis", "Jarvis"), short: "Plan gate · process log", tone: "amber", kind: "tab" },
    ];

    return React.createElement(
      "div",
      { className: "clawsum-cockpit-root clawsum-company" },
      React.createElement(BossGreetingBanner),
      React.createElement(
        "header",
        { className: "clawsum-company-header" },
        React.createElement(
          "div",
          null,
          React.createElement("h1", null, titles[tab] || "Clawsum"),
          React.createElement(
            "p",
            null,
            "Chat stays in the dock below. Catalog explains agents, skills, projects, and tasks."
          )
        ),
        React.createElement(
          "nav",
          { className: "clawsum-tabs", "aria-label": "Company sections" },
          tabs.map(function (t) {
            var active = tab === t.id || (t.id === "home" && tab === "home");
            var cls = "clawsum-tab tone-" + t.tone + (active && t.kind === "tab" ? " is-active" : "");
            var kids = [
              React.createElement("span", { className: "clawsum-tab-label", key: "l" }, t.label),
              React.createElement("span", { className: "clawsum-tab-sub", key: "s" }, t.short),
            ];
            if (t.kind === "link") {
              return React.createElement("a", { key: t.id, className: cls, href: t.href, title: t.short }, kids);
            }
            return React.createElement(
              "button",
              {
                key: t.id,
                type: "button",
                className: cls,
                title: t.short,
                onClick: function () { go(t.id); },
              },
              kids
            );
          })
        )
      ),
      React.createElement("div", { className: "clawsum-company-main" }, panels[tab] || null),
      auth.agent_count
        ? React.createElement(
            "p",
            { className: "muted", style: { margin: 0, fontSize: "0.75rem" } },
            String(auth.agent_count) + " agents · " + String(auth.skill_count || 0) + " skills"
          )
        : null
    );
  }

  function isEmbeddedFrame() {
    try {
      return window.self !== window.top;
    } catch (e) {
      return true;
    }
  }

  function findComposer(doc) {
    if (!doc || !doc.querySelectorAll) return null;
    var nodes = doc.querySelectorAll(
      'textarea, [contenteditable="true"], [role="textbox"], .ProseMirror, input[type="text"], input:not([type])'
    );
    var best = null;
    var bestScore = -1;
    var i;
    for (i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.closest && el.closest("#clawsum-chat-panel, #clawsum-chat-host, #clawsum-chat-top, #clawsum-chat-dock, .clawsum-chattop, .clawsum-chatdock, .clawsum-chatpanel")) {
        continue;
      }
      if (el.disabled || el.readOnly) continue;
      var score = 0;
      try {
        var style = (doc.defaultView || window).getComputedStyle(el);
        if (style && (style.display === "none" || style.visibility === "hidden")) continue;
        var r = el.getBoundingClientRect();
        if (r.width < 2 && r.height < 2) continue;
        // Prefer composers near the bottom of the viewport (main chat input)
        score += Math.min(80, Math.max(0, r.top / 10));
        score += Math.min(40, r.width / 20);
      } catch (e) {}
      var ph = ((el.getAttribute && el.getAttribute("placeholder")) || "").toLowerCase();
      var aria = ((el.getAttribute && el.getAttribute("aria-label")) || "").toLowerCase();
      if (/message|chat|ask|prompt|type|say|write/.test(ph + " " + aria)) score += 50;
      if (el.tagName === "TEXTAREA") score += 20;
      if (el.isContentEditable || (el.getAttribute && el.getAttribute("contenteditable") === "true")) score += 25;
      if (el.classList && el.classList.contains("ProseMirror")) score += 30;
      if (score > bestScore) {
        bestScore = score;
        best = el;
      }
    }
    return best;
  }

  function clickSend(doc, input) {
    if (!doc) return false;
    var form = input && input.closest ? input.closest("form") : null;
    var container =
      (input && input.closest && (
        input.closest("[class*='composer']") ||
        input.closest("[class*='Composer']") ||
        input.closest("[class*='chat-input']") ||
        input.closest("[class*='input-area']") ||
        input.closest("[class*='prompt']") ||
        input.closest("footer") ||
        input.parentElement
      )) || null;

    var candidates = [];
    function pushBtn(b) {
      if (!b || candidates.indexOf(b) >= 0) return;
      if (b.closest && b.closest("#clawsum-chat-panel, #clawsum-chat-top, #clawsum-chat-dock, .clawsum-chattop, .clawsum-chatdock, .clawsum-chatpanel")) {
        return;
      }
      candidates.push(b);
    }

    if (form) {
      form.querySelectorAll('button[type="submit"], button, [role="button"]').forEach(pushBtn);
    }
    if (container) {
      container.querySelectorAll("button, [role='button']").forEach(pushBtn);
    }
    doc.querySelectorAll(
      'button[aria-label*="Send" i], button[title*="Send" i], [data-testid*="send" i], button[aria-label*="submit" i]'
    ).forEach(pushBtn);

    var bi;
    var buttons = doc.querySelectorAll("button, [role='button']");
    for (bi = 0; bi < buttons.length; bi++) {
      var b = buttons[bi];
      var label = (
        (b.getAttribute("aria-label") || "") +
        " " +
        (b.getAttribute("title") || "") +
        " " +
        (b.textContent || "")
      ).replace(/\s+/g, " ").trim();
      if (
        /^send$/i.test(label) ||
        /send message/i.test(label) ||
        /^▶\s*send$/i.test(label) ||
        /^submit$/i.test(label) ||
        /arrow.?up/i.test(label)
      ) {
        pushBtn(b);
      }
      // Icon-only send (common in chat UIs): svg near composer
      if (container && container.contains(b) && b.querySelector && b.querySelector("svg") && !/attach|mic|stop|cancel|clear|copy|menu/i.test(label)) {
        pushBtn(b);
      }
    }

    // Prefer enabled buttons closest to the input
    var best = null;
    var bestScore = -1;
    for (bi = 0; bi < candidates.length; bi++) {
      var cand = candidates[bi];
      if (cand.disabled) continue;
      var score = 0;
      var lab = ((cand.getAttribute("aria-label") || "") + " " + (cand.textContent || "")).toLowerCase();
      if (lab.indexOf("send") >= 0) score += 50;
      if (lab.indexOf("submit") >= 0) score += 40;
      if (container && container.contains(cand)) score += 30;
      if (cand.type === "submit") score += 20;
      if (cand.querySelector && cand.querySelector("svg")) score += 5;
      try {
        var r = cand.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) score += 10;
        if (input) {
          var ir = input.getBoundingClientRect();
          var dist = Math.abs(r.top - ir.top) + Math.abs(r.left - ir.right);
          score += Math.max(0, 40 - Math.min(40, dist / 10));
        }
      } catch (eS) {}
      if (score > bestScore) {
        bestScore = score;
        best = cand;
      }
    }

    if (best) {
      try {
        best.focus();
        best.click();
        return true;
      } catch (e) {}
    }

    if (input) {
      try {
        // Fake KeyboardEvents are often ignored by React; still try as last resort
        var optsPlain = { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true };
        var optsCtrl = { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true, cancelable: true, ctrlKey: true };
        input.dispatchEvent(new KeyboardEvent("keydown", optsPlain));
        input.dispatchEvent(new KeyboardEvent("keydown", optsCtrl));
        return false; // not confirmed — caller should check if composer cleared
      } catch (e2) {}
    }
    return false;
  }

  function fillComposer(doc, text, autoSend) {
    if (!doc) return { filled: false, sent: false };
    var win = doc.defaultView || window;
    var input = findComposer(doc);
    if (!input) return { filled: false, sent: false };
    try {
      input.focus();
      if (input.isContentEditable || (input.getAttribute && input.getAttribute("contenteditable") === "true") ||
          (input.classList && input.classList.contains("ProseMirror"))) {
        try {
          doc.execCommand("selectAll", false, null);
          doc.execCommand("insertText", false, text);
        } catch (eIns) {
          input.textContent = text;
        }
        try {
          input.dispatchEvent(new InputEvent("input", { bubbles: true, data: text, inputType: "insertText" }));
        } catch (eIE) {
          input.dispatchEvent(new Event("input", { bubbles: true }));
        }
      } else {
        var proto =
          Object.getOwnPropertyDescriptor(win.HTMLTextAreaElement.prototype, "value") ||
          Object.getOwnPropertyDescriptor(win.HTMLInputElement.prototype, "value");
        if (proto && proto.set) proto.set.call(input, text);
        else input.value = text;
        try {
          input.dispatchEvent(new InputEvent("input", { bubbles: true, data: text, inputType: "insertText" }));
        } catch (eIn) {
          input.dispatchEvent(new Event("input", { bubbles: true }));
        }
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
      input.focus();
      var sent = false;
      if (autoSend) {
        // React/state UIs often need a tick after value set before Send enables
        sent = clickSend(doc, input);
      }
      return { filled: true, sent: !!sent };
    } catch (e) {
      return { filled: false, sent: false };
    }
  }

  function drainPendingPrompt(doc, setStatus) {
    var text = "";
    var auto = false;
    try {
      text = sessionStorage.getItem("clawsum.pending_prompt") || "";
      auto = sessionStorage.getItem("clawsum.pending_autosend") === "1";
    } catch (e) {}
    if (!text) return false;

    var result = fillComposer(doc, text, false);
    if (!result.filled) return false;

    if (!auto) {
      try {
        sessionStorage.removeItem("clawsum.pending_prompt");
        sessionStorage.removeItem("clawsum.pending_autosend");
      } catch (e2) {}
      if (setStatus) setStatus("Prompt loaded in chat — press Send");
      return true;
    }

    // autoSend: retry click until it sticks (composer may enable Send after React update)
    var attempt = 0;
    var maxAttempts = 12;
    var trySend = function () {
      clickSend(doc, findComposer(doc) || null);
      // Confirm send by composer clearing (or no longer containing our prompt)
      var input = findComposer(doc);
      var stillThere = true;
      try {
        if (input) {
          var cur = (input.value != null ? input.value : input.textContent) || "";
          cur = cur.replace(/\s+/g, " ").trim();
          stillThere = !!cur && cur.indexOf(text.slice(0, Math.min(24, text.length))) >= 0;
        } else {
          stillThere = false;
        }
      } catch (e3) {}
      if (!stillThere) {
        try {
          sessionStorage.removeItem("clawsum.pending_prompt");
          sessionStorage.removeItem("clawsum.pending_autosend");
        } catch (e4) {}
        if (setStatus) setStatus("Sent to chat");
        return true;
      }
      attempt += 1;
      if (attempt < maxAttempts) {
        if (setStatus) setStatus("Sending… (" + attempt + ")");
        setTimeout(trySend, 250);
        return false;
      }
      try {
        sessionStorage.removeItem("clawsum.pending_autosend");
        sessionStorage.removeItem("clawsum.pending_prompt");
      } catch (e5) {}
      if (setStatus) setStatus("Text ready in chat — click Send");
      return true;
    };

    // Wait for React to enable Send after value set
    setTimeout(trySend, 150);
    return true;
  }

  function stripChatChrome(iframe) {
    try {
      var doc = iframe.contentDocument;
      if (!doc || !doc.head) return;
      var nested = doc.getElementById("clawsum-chat-dock") || doc.getElementById("clawsum-chat-panel") || doc.getElementById("clawsum-chat-top");
      if (nested) nested.remove();
      if (doc.getElementById("clawsum-embed-css")) return;
      var style = doc.createElement("style");
      style.id = "clawsum-embed-css";
      style.textContent =
        "html,body{height:100%!important;overflow:hidden!important;}" +
        "#clawsum-chat-dock,#clawsum-chat-top,#clawsum-chat-panel,.clawsum-sidebar,[data-clawsum-crest]{display:none!important;}" +
        "aside,nav[aria-label='Boss pages'],nav[aria-label='External systems']{display:none!important;}";
      doc.head.appendChild(style);
      doc.documentElement.classList.add("clawsum-embed-chat");
    } catch (e) {}
  }

  function setDockHeightClass(mode) {
    // retained for compatibility; chat is in-flow now (no overlay padding)
  }

  function chatFlowHost() {
    return (
      document.querySelector(".clawsum-company") ||
      document.querySelector(".clawsum-cockpit-root") ||
      document.querySelector("main") ||
      null
    );
  }

  function placeChatInFlow(panel) {
    if (!panel || !document.body) return;
    // CRITICAL: never mount inside React-managed trees (.clawsum-company, #root children).
    // React re-renders wipe those nodes; SpeechRecognition then writes to a detached textarea
    // while the visible panel shows "Listening" with an empty transcript.
    var host = document.getElementById("clawsum-chat-host");
    if (!host) {
      host = document.createElement("div");
      host.id = "clawsum-chat-host";
      host.className = "clawsum-chat-host";
      var root = document.getElementById("root");
      if (root && root.parentNode) {
        root.parentNode.insertBefore(host, root);
      } else {
        document.body.insertBefore(host, document.body.firstChild);
      }
    }
    if (!document.getElementById("clawsum-chat-host-css")) {
      var style = document.createElement("style");
      style.id = "clawsum-chat-host-css";
      style.textContent = [
        /* Keep Hermes' overflow:hidden shell, but reserve space for the chat strip */
        "html,body{height:100%!important;margin:0!important;overflow:hidden!important;}",
        "body{display:flex!important;flex-direction:column!important;height:100dvh!important;max-height:100dvh!important;}",
        "#clawsum-chat-host{flex:0 0 auto;width:100%;max-width:100%;padding:0.2rem 0.5rem 0;box-sizing:border-box;background:transparent;position:relative;z-index:70;}",
        "html[data-clawsum-page^='/chat'] #clawsum-chat-host{padding:0.15rem 0.4rem 0;}",
        "#root{flex:1 1 auto!important;min-height:0!important;height:auto!important;overflow:hidden!important;position:relative!important;}",
        /* Hermes root is h-dvh — force it to fill remaining #root, not the full viewport */
        "#root > div{height:100%!important;max-height:100%!important;min-height:0!important;}",
        "#root .h-dvh,#root .max-h-dvh{height:100%!important;max-height:100%!important;}",
        /* Main content must scroll (Hermes sets overflow-hidden when embedded-chat flag is on) */
        "#root main{overflow-y:auto!important;overflow-x:hidden!important;min-height:0!important;overscroll-behavior:contain;}",
        /* Fixed left/right rails: offset below chat host */
        "#root .fixed.top-0{top:var(--clawsum-chat-h,0px)!important;height:calc(100dvh - var(--clawsum-chat-h,0px))!important;max-height:calc(100dvh - var(--clawsum-chat-h,0px))!important;}",
      ].join("");
      document.head.appendChild(style);
    }
    function syncChatHostHeight() {
      try {
        var hh = host.offsetHeight || 0;
        document.documentElement.style.setProperty("--clawsum-chat-h", hh + "px");
      } catch (eH) {}
    }
    syncChatHostHeight();
    if (!host._clawsumRo && typeof ResizeObserver !== "undefined") {
      try {
        host._clawsumRo = new ResizeObserver(function () { syncChatHostHeight(); });
        host._clawsumRo.observe(host);
      } catch (eRo) {}
    }
    if (panel.parentNode !== host) {
      host.appendChild(panel);
    }
    syncChatHostHeight();
  }

  function placeInlineGreeting(text) {
    text = String(text || "").trim();
    if (!text || !document.body) return null;
    var bubble = document.getElementById("clawsum-inline-greeting");
    if (!bubble) {
      bubble = document.createElement("div");
      bubble.id = "clawsum-inline-greeting";
      bubble.className = "clawsum-inline-greeting";
      bubble.setAttribute("role", "status");
      bubble.setAttribute("aria-live", "polite");
      bubble.innerHTML =
        '<div class="clawsum-inline-greeting-inner">' +
        '<div class="clawsum-inline-greeting-meta">Jarvis</div>' +
        '<div class="clawsum-inline-greeting-text" data-inline-greet></div>' +
        '<button type="button" class="clawsum-inline-greeting-speak" data-inline-speak>🔊 Speak</button>' +
        "</div>";
    }
    var textEl = bubble.querySelector("[data-inline-greet]");
    if (textEl) textEl.textContent = text;
    var composer = findComposer(document);
    var anchor = null;
    if (composer && composer.closest) {
      anchor =
        composer.closest("form") ||
        composer.closest("[class*='composer' i]") ||
        composer.closest("[class*='Composer']") ||
        composer.closest("[class*='chat-input' i]") ||
        composer.closest("[class*='input-area' i]") ||
        composer.closest("footer") ||
        composer.parentElement;
    }
    if (anchor && anchor.parentNode) {
      if (bubble.parentNode !== anchor.parentNode || bubble.nextSibling !== anchor) {
        anchor.parentNode.insertBefore(bubble, anchor);
      }
    } else {
      var host = document.getElementById("clawsum-chat-host");
      if (host) host.appendChild(bubble);
      else document.body.appendChild(bubble);
    }
    if (!bubble._clawsumSpeakBound) {
      bubble._clawsumSpeakBound = true;
      var btn = bubble.querySelector("[data-inline-speak]");
      if (btn) {
        btn.addEventListener("click", function () {
          var line = (textEl && textEl.textContent) || text;
          try {
            if (typeof window.__clawsumSpeak === "function") window.__clawsumSpeak(line);
          } catch (eSpeak) {}
        });
      }
    }
    if (!document.getElementById("clawsum-inline-greeting-css")) {
      var style = document.createElement("style");
      style.id = "clawsum-inline-greeting-css";
      style.textContent = [
        "#clawsum-inline-greeting{width:100%;max-width:48rem;margin:0 auto 0.55rem;padding:0 0.75rem;box-sizing:border-box;position:relative;z-index:65;}",
        ".clawsum-inline-greeting-inner{display:flex;flex-wrap:wrap;align-items:flex-start;gap:0.45rem 0.7rem;padding:0.7rem 0.85rem;border:1px solid rgba(34,211,238,0.35);border-radius:0.75rem;background:rgba(8,47,73,0.72);color:#f8fafc;}",
        ".clawsum-inline-greeting-meta{flex:0 0 auto;font:700 0.68rem/1 ui-monospace,Menlo,Consolas,monospace;letter-spacing:0.12em;text-transform:uppercase;color:#22d3ee;margin-top:0.2rem;}",
        ".clawsum-inline-greeting-text{flex:1 1 14rem;min-width:0;font-size:0.98rem;line-height:1.4;font-weight:600;white-space:normal;}",
        ".clawsum-inline-greeting-speak{flex:0 0 auto;border:1px solid rgba(56,189,248,0.45);background:rgba(14,116,144,0.35);color:#ecfeff;border-radius:0.4rem;padding:0.3rem 0.55rem;cursor:pointer;font-size:0.78rem;}",
      ].join("");
      document.head.appendChild(style);
    }
    return bubble;
  }

  function pickRotatingGreeting(pool) {
    var list = pool && pool.length ? pool : null;
    if (!list) return buildBossGreeting(true);
    var last = "";
    try { last = localStorage.getItem(GREET_LINE_KEY) || ""; } catch (e) {}
    var choices = list.filter(function (g) { return g !== last; });
    var line = choices[Math.floor(Math.random() * choices.length)] || list[0];
    try {
      localStorage.setItem(GREET_LINE_KEY, line);
      localStorage.setItem(GREET_AT_KEY, String(Date.now()));
    } catch (e2) {}
    return line;
  }

  var ACK_LINE_KEY = "clawsum.boss.ack.line";
  var DEFAULT_ACK_POOL = [
    "On it, Boss.",
    "Acknowledged — checking now.",
    "Got it, Gerald. Working.",
    "Understood, Chief. One moment.",
    "Copy that, Captain.",
    "Yes Sir — on it.",
    "Heard. Pulling that up.",
    "Right away, Boss.",
    "Locked in — starting.",
    "Roger that. Standing by with results shortly.",
    "Affirmative. Digging in.",
    "I'm on it, Commander.",
  ];
  var cachedAckPool = null;

  function pickRotatingAck(pool) {
    var list = (pool && pool.length) ? pool : (cachedAckPool && cachedAckPool.length ? cachedAckPool : DEFAULT_ACK_POOL);
    var last = "";
    try { last = localStorage.getItem(ACK_LINE_KEY) || ""; } catch (e) {}
    var choices = list.filter(function (g) { return g !== last; });
    var line = choices[Math.floor(Math.random() * choices.length)] || list[0];
    try { localStorage.setItem(ACK_LINE_KEY, line); } catch (e2) {}
    return line;
  }

  var DEFAULT_CHAT_SUGGESTIONS = [
    { label: "📋 Startup brief", text: "Deliver the full Session Startup Brief now, in this exact order: (1) unique respectful Boss greeting from the rotating pool, (2) last session summary, (3) progress since last session, (4) active tasks, (5) upcoming tasks, (6) recommended Next actions from all live data. Archive the brief after. Do not invent work." },
    { label: "🔥 What's on fire?", text: "What's on fire right now? Rank by urgency and say the single best Next." },
    { label: "📨 Inbox triage", text: "Triage clawsums@gmail.com — list needs_boss items with recommended replies." },
    { label: "✅ Approvals", text: "List pending ops.approvals and ask me for decide/reject on the top one." },
    { label: "🏁 Wrap session", text: "Wrap up this session: rewrite LAST_SESSION.md and confirm tomorrow's #1 Next." },
  ];

  function ensureChatDock() {
    if (typeof document === "undefined" || !document.body) return;
    if (isEmbeddedFrame()) return;

    var path = "";
    try { path = window.location.pathname || ""; } catch (e) {}
    var onChatPage = path === "/chat" || path.indexOf("/chat/") === 0;

    ["clawsum-chat-top", "clawsum-chat-dock"].forEach(function (id) {
      var old = document.getElementById(id);
      if (old) old.remove();
    });

    var existing = document.getElementById("clawsum-chat-panel");
    if (existing) {
      existing.classList.toggle("is-chatpage", onChatPage);
      ensureChatAscii(existing);
      placeChatInFlow(existing);
      stripHermesColorBanner();
      if (onChatPage && !document._clawsumBannerObs) {
        try {
          var existTimer = 0;
          document._clawsumBannerObs = new MutationObserver(function () {
            if (existTimer) return;
            existTimer = setTimeout(function () {
              existTimer = 0;
              stripHermesColorBanner();
            }, 80);
          });
          document._clawsumBannerObs.observe(document.getElementById("root") || document.body, {
            childList: true,
            subtree: true,
          });
        } catch (eExist) {}
      }
      return;
    }

    var panel = document.createElement("section");
    panel.id = "clawsum-chat-panel";
    panel.className = "clawsum-chatpanel" + (onChatPage ? " is-chatpage" : "");
    panel.setAttribute("aria-label", "Clawsum Agent chat");
    panel.innerHTML =
      '<div class="clawsum-chatpanel-head">' +
      (onChatPage ? "" : clawsumAsciiHtml()) +
      '<span class="clawsum-chatpanel-mark">⚡ CLAWSUM CHAT · escalate → frontier</span>' +
      (onChatPage ? "" : '<a class="clawsum-chatpanel-link" href="/chat">↗ Full chat</a>') +
      "</div>" +
      '<div class="clawsum-chatpanel-greetline" role="status" aria-live="polite">' +
      '<span class="clawsum-chatpanel-greet-label">Jarvis</span>' +
      '<span class="clawsum-chatpanel-greet" data-greet>Loading greeting…</span>' +
      '<button type="button" class="clawsum-chatdock-speak" data-speak-greet title="Speak greeting">🔊 Speak greeting</button>' +
      "</div>" +
      '<div class="clawsum-chatpanel-prompts" data-prompts></div>' +
      '<div class="clawsum-chatpanel-voice">' +
      '<button type="button" class="clawsum-toggle" data-listen-toggle aria-pressed="false">Live Listen: Off</button>' +
      '<button type="button" class="clawsum-toggle" data-autospeak-toggle aria-pressed="true">Auto-Speak: On</button>' +
      '<button type="button" class="clawsum-toggle" data-autosend-toggle aria-pressed="true" title="When Live Listen is on, send after 2s of silence">Auto-Send: On</button>' +
      '<button type="button" class="clawsum-chatdock-speak" data-speak-brief>🔊 Speak brief now</button>' +
      '<span class="clawsum-chatpanel-status" data-voice-status>Voice idle</span>' +
      "</div>" +
      '<div class="clawsum-chatpanel-microw">' +
      '<label class="clawsum-mic-label">Mic <select class="clawsum-mic-select" data-mic-device><option value="">Default</option></select></label>' +
      '<div class="clawsum-mic-meter" title="Mic input level"><div class="clawsum-mic-level" data-mic-level></div></div>' +
      '<span class="clawsum-mic-level-label" data-mic-label>level —</span>' +
      "</div>" +
      '<p class="clawsum-chatpanel-hint" data-voice-hint>Live Listen or type below → <strong>Send</strong>. Auto-Send (when Listen is on) fires after <strong>2s silence</strong>.</p>' +
      '<textarea class="clawsum-chatpanel-transcript" data-transcript rows="2" placeholder="Type here or use Live Listen…"></textarea>' +
      '<div class="clawsum-chatpanel-actions">' +
      '<button type="button" class="clawsum-btn-primary" data-done-send>▶ Send</button>' +
      '<button type="button" class="clawsum-btn-ghost" data-clear-tx>Clear</button>' +
      "</div>" +
      '<details class="clawsum-chatpanel-brief">' +
      "<summary>📋 Session briefing (greeting + board pulse)</summary>" +
      '<p class="clawsum-chatdock-last" data-last></p>' +
      '<ul class="clawsum-chatdock-report" data-report></ul>' +
      '<ol class="clawsum-chatdock-next" data-next></ol>' +
      "</details>" +
      (onChatPage
        ? ""
        : '<div class="clawsum-chatpanel-agentlink"><a class="clawsum-chatpanel-link" href="/chat">💬 Open Agent chat</a></div>');

    placeChatInFlow(panel);
    stripHermesColorBanner();
    if (onChatPage && !document._clawsumBannerObs) {
      try {
        var bannerTimer = 0;
        document._clawsumBannerObs = new MutationObserver(function () {
          if (bannerTimer) return;
          bannerTimer = setTimeout(function () {
            bannerTimer = 0;
            stripHermesColorBanner();
          }, 80);
        });
        document._clawsumBannerObs.observe(document.getElementById("root") || document.body, {
          childList: true,
          subtree: true,
        });
      } catch (eObs) {}
    }

    var greetEl = panel.querySelector("[data-greet]");
    var lastEl = panel.querySelector("[data-last]");
    var reportEl = panel.querySelector("[data-report]");
    var nextEl = panel.querySelector("[data-next]");
    var promptsEl = panel.querySelector("[data-prompts]");
    var inputEl = panel.querySelector("[data-input]"); // legacy; may be null after single-box UI
    var sendBtn = panel.querySelector("[data-send]");
    var transcriptEl = panel.querySelector("[data-transcript]");
    var listenToggle = panel.querySelector("[data-listen-toggle]");
    var autoSpeakToggle = panel.querySelector("[data-autospeak-toggle]");
    var autoSendToggle = panel.querySelector("[data-autosend-toggle]");
    var speakBriefBtn = panel.querySelector("[data-speak-brief]");
    var speakGreetBtn = panel.querySelector("[data-speak-greet]");
    var doneSendBtn = panel.querySelector("[data-done-send]");
    var clearBtn = panel.querySelector("[data-clear-tx]");
    var voiceStatus = panel.querySelector("[data-voice-status]");
    var voiceHint = panel.querySelector("[data-voice-hint]");
    var micDeviceEl = panel.querySelector("[data-mic-device]");
    var micLevelEl = panel.querySelector("[data-mic-level]");
    var micLabelEl = panel.querySelector("[data-mic-label]");
    var latestBrief = null;
    var cachedGreetingPool = [];
    var currentGreeting = "";
    var listenOn = false;
    var autoSpeakOn = true; // default on — greeting brief autoplays when loaded
    var autoSendOn = true; // default on — send after 2s silence while Live Listen is on
    var silenceAutoSendMs = 2000;
    var silenceTimer = null;
    var autoSendInFlight = false;
    var committed = "";
    var mediaStream = null;
    var mediaRecorder = null;
    var recordChunks = [];
    var audioCtx = null;
    var analyser = null;
    var meterRaf = 0;
    var segmentTimer = null;
    var transcribeBusy = false;
    var pendingStops = 0;
    var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    var recognition = null;
    var chromeRestartTimer = null;
    var chromeWatchdog = null;
    var sttEngine = null; // "chrome" | "whisper"
    var chromeHadResult = false;
    var noSpeechStreak = 0;
    var peakLevel = 0;
    var whisperArmed = false;
    var speakAudio = null;
    var speakObjectUrl = null;
    var spokenReplyFingerprints = {};
    var waitingForReplySpeak = false;
    var pendingSpeakText = "";
    var pendingSpeakBound = false;

    function clearSilenceAutoSend() {
      if (silenceTimer) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
      }
    }

    function isSpeakPlaying() {
      try {
        return !!(speakAudio && !speakAudio.paused && !speakAudio.ended);
      } catch (eSp) {
        return false;
      }
    }

    function noteSpeechActivity() {
      clearSilenceAutoSend();
      if (!listenOn || !autoSendOn || autoSendInFlight) return;
      if (isSpeakPlaying()) return;
      silenceTimer = setTimeout(trySilenceAutoSend, silenceAutoSendMs);
    }

    function trySilenceAutoSend() {
      silenceTimer = null;
      if (!listenOn || !autoSendOn || autoSendInFlight) return;
      if (isSpeakPlaying()) {
        silenceTimer = setTimeout(trySilenceAutoSend, 400);
        return;
      }
      var text = readComposeText();
      if (!text) return;
      if (transcribeBusy) {
        silenceTimer = setTimeout(trySilenceAutoSend, 300);
        return;
      }
      autoSendInFlight = true;
      setVoiceStatus("2s silence — auto-sending…");
      voiceLog("autosend_silence", "chars=" + text.length);

      var finishSend = function () {
        text = readComposeText() || text;
        committed = "";
        setTranscript("");
        clearSilenceAutoSend();
        if (text) sendToChat(text, true);
        autoSendInFlight = false;
        if (listenOn) {
          setVoiceStatus("Sent — listening for next…");
          if ((whisperArmed || sttEngine === "whisper") && mediaStream) {
            try { startSegmentRecorder(); } catch (eSeg) {}
          }
        }
      };

      if (whisperArmed || sttEngine === "whisper") {
        stopSegmentRecorder(true).then(function () {
          var wait = 0;
          var poll = function () {
            if (!transcribeBusy || wait > 40) {
              finishSend();
              return;
            }
            wait += 1;
            setTimeout(poll, 250);
          };
          poll();
        });
      } else {
        finishSend();
      }
    }

    function setVoiceStatus(msg) {
      if (voiceStatus) voiceStatus.textContent = msg;
      try {
        var toast = document.getElementById("clawsum-voice-toast");
        if (!toast) {
          toast = document.createElement("div");
          toast.id = "clawsum-voice-toast";
          toast.className = "clawsum-voice-toast";
          toast.setAttribute("role", "status");
          document.body.appendChild(toast);
        }
        toast.textContent = msg;
        toast.className = "clawsum-voice-toast is-on" + (/denied|blocked|error|unavailable|busy|network|fail/i.test(msg) ? " is-err" : "");
        clearTimeout(setVoiceStatus._t);
        setVoiceStatus._t = setTimeout(function () { toast.classList.remove("is-on"); }, 4500);
      } catch (eT) {}
    }

    function voiceLog(event, detail) {
      try {
        var headers = { "Content-Type": "application/json" };
        var tok = window.__HERMES_SESSION_TOKEN__;
        if (tok) headers["X-Hermes-Session-Token"] = tok;
        fetch(API + "/voice-debug", {
          method: "POST",
          credentials: "same-origin",
          headers: headers,
          body: JSON.stringify({
            event: event,
            detail: detail || "",
            transcript_len: transcriptEl && transcriptEl.value ? transcriptEl.value.length : 0,
            listen_on: !!listenOn,
            secure: !!window.isSecureContext,
            speech_rec: !!SpeechRec,
          }),
        }).catch(function () {});
      } catch (eL) {}
    }

    function queueSpeakUnlock(text, reason) {
      pendingSpeakText = String(text || "").trim();
      if (!pendingSpeakText) return;
      voiceLog("tts_blocked", reason || "blocked");
      setVoiceStatus("Audio blocked by browser — click once to enable Jarvis");
      if (pendingSpeakBound) return;
      pendingSpeakBound = true;
      var resumeSpeak = function () {
        document.removeEventListener("pointerdown", resumeSpeak, true);
        document.removeEventListener("keydown", resumeSpeak, true);
        pendingSpeakBound = false;
        var queued = pendingSpeakText;
        pendingSpeakText = "";
        if (!queued) return;
        setTimeout(function () { speakBrowserFallback(queued); }, 0);
      };
      document.addEventListener("pointerdown", resumeSpeak, true);
      document.addEventListener("keydown", resumeSpeak, true);
    }

    function setTranscript(text) {
      if (transcriptEl) transcriptEl.value = text || "";
      if (inputEl && text) inputEl.value = text;
    }

    function readComposeText() {
      return (
        ((transcriptEl && transcriptEl.value) || (inputEl && inputEl.value) || "")
      ).trim();
    }

    function renderSuggestions(items) {
      if (!promptsEl) return;
      promptsEl.innerHTML = "";
      (items || DEFAULT_CHAT_SUGGESTIONS).forEach(function (s) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "clawsum-chip";
        b.textContent = s.label || s.text;
        b.title = s.text;
        b.addEventListener("click", function () {
          setTranscript(s.text);
          sendToChat(s.text, true);
        });
        promptsEl.appendChild(b);
      });
    }
    renderSuggestions(DEFAULT_CHAT_SUGGESTIONS);

    function sendToChat(text, autoSend) {
      text = (text || "").trim();
      if (!text) {
        setVoiceStatus("Nothing to send");
        return;
      }
      // Boss codeword: escalate → force OpenRouter top/frontier model this turn
      if (/(^|[^\w])escalate([^\w]|$)/i.test(text) && !/CODEWORD escalate/i.test(text)) {
        text =
          "[CODEWORD escalate — switch to OpenRouter top/frontier model for this turn. " +
          "Say you escalated in one short clause, then answer.]\n\n" + text;
      }
      try {
        sessionStorage.setItem("clawsum.pending_prompt", text);
        sessionStorage.setItem("clawsum.pending_autosend", autoSend ? "1" : "0");
      } catch (e) {}
      // Instant approved ack on screen + TTS before any agent tools/reply
      var ackLine = pickRotatingAck(cachedAckPool);
      if (greetEl) greetEl.textContent = ackLine;
      if (autoSpeakOn) speakText(ackLine);
      setVoiceStatus("Ack spoken — waiting for Clawsum…");
      if (onChatPage) {
        var tries = 0;
        var tick = function () {
          if (drainPendingPrompt(document, setVoiceStatus)) {
            waitingForReplySpeak = !!autoSpeakOn;
            return;
          }
          tries += 1;
          if (tries < 30) setTimeout(tick, 350);
          else setVoiceStatus("Could not find chat composer");
        };
        tick();
        return;
      }
      window.location.href = "/chat";
    }

    function getSpeakPlayer() {
      var el = document.getElementById("clawsum-speak-audio");
      if (!el) {
        el = document.createElement("audio");
        el.id = "clawsum-speak-audio";
        el.setAttribute("playsinline", "true");
        el.setAttribute("preload", "auto");
        el.controls = true;
        el.style.cssText =
          "position:fixed;right:12px;bottom:12px;z-index:99999;width:240px;max-width:46vw;" +
          "height:36px;opacity:0.95;background:#0f172a;border-radius:8px;";
        document.body.appendChild(el);
      }
      try {
        el.muted = false;
        el.volume = 1;
      } catch (eVol) {}
      return el;
    }

    function stopSpeakAudio() {
      try {
        if (speakAudio) {
          speakAudio.pause();
          speakAudio.removeAttribute("src");
          speakAudio.load();
        }
      } catch (eS) {}
      speakAudio = null;
      if (speakObjectUrl) {
        try { URL.revokeObjectURL(speakObjectUrl); } catch (eR) {}
        speakObjectUrl = null;
      }
      try {
        if (window.speechSynthesis) window.speechSynthesis.cancel();
      } catch (eC) {}
    }

    function speakBrowserFallback(text) {
      if (!window.speechSynthesis) {
        setVoiceStatus("TTS unavailable");
        return;
      }
      warmVoices();
      try { window.speechSynthesis.cancel(); } catch (eC) {}
      setTimeout(function () {
        var utter = new SpeechSynthesisUtterance(text);
        utter.rate = 1.02;
        try {
          var voices = window.speechSynthesis.getVoices() || [];
          var voice = voices.find(function (v) { return /^en/i.test(v.lang); }) || voices[0];
          if (voice) utter.voice = voice;
        } catch (eV) {}
        utter.onend = function () { setVoiceStatus(listenOn ? "Listening…" : "Voice idle"); };
        utter.onerror = function () { setVoiceStatus("Browser speak failed"); };
        window.speechSynthesis.speak(utter);
        setVoiceStatus("Speaking (browser)…");
      }, 40);
    }

    function speakText(text) {
      text = String(text || "")
        .replace(/[#*_`>|]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
      if (!text) return;
      stopSpeakAudio();

      // Instant path: pre-generated ElevenLabs MP3 from session-startup voice.cache
      var cachedUrl = null;
      try {
        if (window.__clawsumVoiceCache && window.__clawsumVoiceCache[text]) {
          cachedUrl = window.__clawsumVoiceCache[text];
        }
      } catch (eC) {}
      if (cachedUrl) {
        setVoiceStatus("Speaking (cached Jarvis)…");
        voiceLog("tts_cache", "url=" + cachedUrl);
        fetch(cachedUrl, { headers: authHeaders({}), credentials: "same-origin" })
          .then(function (r) {
            var ctype = (r.headers.get("content-type") || "").toLowerCase();
            if (!r.ok) throw new Error("cache http " + r.status);
            return r.blob().then(function (blob) {
              if (ctype.indexOf("audio") < 0 && ctype.indexOf("octet-stream") < 0 && blob.size < 500) {
                throw new Error("cache not audio");
              }
              return blob;
            });
          })
          .then(function (blob) {
            speakObjectUrl = URL.createObjectURL(blob);
            speakAudio = getSpeakPlayer();
            speakAudio.onended = function () {
              setVoiceStatus(listenOn ? "Listening…" : "Voice idle");
            };
            speakAudio.onerror = function () {
              setVoiceStatus("Cache play failed — synthesizing…");
              speakTextLive(text);
            };
            speakAudio.src = speakObjectUrl;
            return speakAudio.play().catch(function (err) {
              var msg = String(err && err.message || err || "");
              if (/notallowed|user gesture|gesture|interact/i.test(msg)) {
                queueSpeakUnlock(text, msg);
                return;
              }
              throw err;
            });
          })
          .catch(function () { speakTextLive(text); });
        return;
      }
      speakTextLive(text);
    }

    function speakTextLive(text) {
      setVoiceStatus("Synthesizing Jarvis voice…");
      voiceLog("tts_request", "chars=" + text.length);
      fetch(API + "/tts", {
        method: "POST",
        credentials: "same-origin",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ text: text.slice(0, 2500) }),
      })
        .then(function (r) {
          var ctype = (r.headers.get("content-type") || "").toLowerCase();
          if (!r.ok) {
            return r.text().then(function (t) {
              throw new Error((t || ("HTTP " + r.status)).slice(0, 220));
            });
          }
          var provider = r.headers.get("X-Clawsum-TTS-Provider") || "tts";
          return r.blob().then(function (blob) {
            // Some proxies strip Content-Type; accept binary audio by size/magic.
            if (ctype.indexOf("audio") < 0 && ctype.indexOf("octet-stream") < 0 && blob.size < 500) {
              throw new Error("not audio (" + (ctype || "no-type") + ", " + blob.size + " bytes)");
            }
            return { blob: blob, provider: provider };
          });
        })
        .then(function (pack) {
          speakObjectUrl = URL.createObjectURL(pack.blob);
          speakAudio = getSpeakPlayer();
          speakAudio.onended = function () {
            setVoiceStatus(listenOn ? "Listening…" : "Voice idle");
          };
          speakAudio.onerror = function () {
            setVoiceStatus("Audio playback failed — trying browser voice");
            speakBrowserFallback(text);
          };
          speakAudio.src = speakObjectUrl;
          return speakAudio.play()
            .then(function () {
              setVoiceStatus(
                pack.provider === "elevenlabs" || pack.provider === "cache"
                  ? "Speaking (Jarvis / " + pack.provider + ")…"
                  : "Speaking (" + pack.provider + ")…"
              );
              voiceLog("tts_play", "provider=" + pack.provider + " bytes=" + pack.blob.size);
            })
            .catch(function (err) {
              var msg = String(err && err.message || err || "");
              if (/notallowed|user gesture|gesture|interact/i.test(msg)) {
                queueSpeakUnlock(text, msg);
                return;
              }
              throw err;
            });
        })
        .catch(function (err) {
          voiceLog("tts_fail", String(err && err.message || err).slice(0, 200));
          setVoiceStatus("TTS failed — browser fallback");
          speakBrowserFallback(text);
        });
    }

    function stripForSpeak(raw) {
      return String(raw || "")
        .replace(/```[\s\S]*?```/g, " ")
        .replace(/[#*_`>|]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    }

    function findLatestAssistantText() {
      var root = document.getElementById("root") || document.body;
      if (!root) return "";
      var candidates = root.querySelectorAll(
        '[data-role="assistant"], [data-message-role="assistant"], [data-author="assistant"], .assistant, .message-assistant, [class*="assistant"]'
      );
      var best = "";
      var i;
      for (i = 0; i < candidates.length; i++) {
        var el = candidates[i];
        if (el.closest && el.closest("#clawsum-chat-host, #clawsum-chat-panel, .clawsum-chatpanel")) continue;
        var t = stripForSpeak(el.innerText || el.textContent || "");
        if (t.length > best.length) best = t;
      }
      if (best.length >= 40) return best;
      // Fallback: last large prose block in main
      var blocks = root.querySelectorAll("main article, main .prose, main [class*='markdown'], main [class*='message']");
      for (i = 0; i < blocks.length; i++) {
        var b = blocks[i];
        if (b.closest && b.closest("#clawsum-chat-host, .clawsum-chatpanel")) continue;
        var bt = stripForSpeak(b.innerText || b.textContent || "");
        if (bt.length > best.length && bt.length > 80) best = bt;
      }
      return best;
    }

    function maybeSpeakNewReply() {
      if (!autoSpeakOn) return;
      var text = findLatestAssistantText();
      if (!text || text.length < 24) return;
      var fp = text.slice(0, 160);
      if (spokenReplyFingerprints[fp]) return;
      // Debounce while agent is still streaming
      if (maybeSpeakNewReply._timer) clearTimeout(maybeSpeakNewReply._timer);
      maybeSpeakNewReply._last = text;
      maybeSpeakNewReply._timer = setTimeout(function () {
        if (!autoSpeakOn) return;
        var stable = findLatestAssistantText();
        if (!stable || stable !== maybeSpeakNewReply._last) return;
        var f2 = stable.slice(0, 160);
        if (spokenReplyFingerprints[f2]) return;
        spokenReplyFingerprints[f2] = 1;
        waitingForReplySpeak = false;
        setVoiceStatus("Speaking reply…");
        speakText(stable.slice(0, 1800));
      }, 900);
    }

    function watchChatReplies() {
      var root = document.getElementById("root");
      if (!root || typeof MutationObserver === "undefined") return;
      var obs = new MutationObserver(function () {
        maybeSpeakNewReply();
      });
      try {
        obs.observe(root, { childList: true, subtree: true, characterData: true });
      } catch (eO) {}
    }
    watchChatReplies();

    function warmVoices() {
      try {
        if (!window.speechSynthesis) return;
        window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = function () {
          try { window.speechSynthesis.getVoices(); } catch (e) {}
        };
      } catch (e2) {}
    }
    warmVoices();

    // Expose for Brief tab / other panels
    try { window.__clawsumSpeak = speakText; } catch (eEx) {}


    function stopMeter() {
      if (meterRaf) {
        cancelAnimationFrame(meterRaf);
        meterRaf = 0;
      }
      if (micLevelEl) micLevelEl.style.width = "0%";
      if (micLabelEl) micLabelEl.textContent = "level —";
      try {
        if (audioCtx && audioCtx.state !== "closed") audioCtx.close();
      } catch (eC) {}
      audioCtx = null;
      analyser = null;
    }

    function startMeter(stream) {
      stopMeter();
      try {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        var src = audioCtx.createMediaStreamSource(stream);
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        src.connect(analyser);
        var data = new Uint8Array(analyser.frequencyBinCount);
        var tick = function () {
          if (!analyser || !listenOn) return;
          analyser.getByteTimeDomainData(data);
          var sum = 0;
          var i;
          for (i = 0; i < data.length; i++) {
            var v = (data[i] - 128) / 128;
            sum += v * v;
          }
          var rms = Math.sqrt(sum / data.length);
          var pct = Math.min(100, Math.round(rms * 340));
          if (pct > peakLevel) peakLevel = pct;
          if (micLevelEl) micLevelEl.style.width = pct + "%";
          if (micLabelEl) {
            micLabelEl.textContent = pct < 3 ? "silent / check mic" : ("level " + pct + "%");
          }
          // Treat sustained mic energy as speech so silence auto-send resets while talking
          if (pct >= 6 && !isSpeakPlaying()) noteSpeechActivity();
          meterRaf = requestAnimationFrame(tick);
        };
        meterRaf = requestAnimationFrame(tick);
      } catch (eM) {
        voiceLog("meter_fail", String(eM && eM.message || eM));
      }
    }

    function pickMime() {
      var types = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
        "audio/ogg;codecs=opus",
      ];
      if (!window.MediaRecorder || !MediaRecorder.isTypeSupported) return "";
      var i;
      for (i = 0; i < types.length; i++) {
        if (MediaRecorder.isTypeSupported(types[i])) return types[i];
      }
      return "";
    }

    function authHeaders(extra) {
      var headers = extra || {};
      var tok = window.__HERMES_SESSION_TOKEN__;
      if (tok) headers["X-Hermes-Session-Token"] = tok;
      return headers;
    }

    function appendTranscript(piece) {
      piece = (piece || "").replace(/\s+/g, " ").trim();
      if (!piece) return;
      committed = (committed ? committed + " " : "") + piece;
      committed = committed.replace(/\s+/g, " ").trim();
      applyTranscript(committed, sttEngine === "whisper" ? "whisper" : "chrome");
    }

    function uploadWhisper(blob) {
      if (!whisperArmed && sttEngine !== "whisper") {
        voiceLog("whisper_skip_chrome_ok", "bytes=" + (blob && blob.size));
        return Promise.resolve("");
      }
      if (!blob || blob.size < 800) {
        voiceLog("whisper_skip_tiny", "bytes=" + (blob && blob.size));
        return Promise.resolve("");
      }
      transcribeBusy = true;
      setVoiceStatus("Whisper backup… (" + Math.round(blob.size / 1024) + " KB)");
      voiceLog("whisper_upload", "bytes=" + blob.size);
      var fd = new FormData();
      var ext = (blob.type || "").indexOf("mp4") >= 0 ? "m4a" : "webm";
      fd.append("file", blob, "listen." + ext);
      return fetch(API + "/transcribe", {
        method: "POST",
        credentials: "same-origin",
        headers: authHeaders({}),
        body: fd,
      })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          transcribeBusy = false;
          if (!res.ok || !res.j || !res.j.ok) {
            var err = (res.j && (res.j.error || res.j.detail)) || "transcribe failed";
            setVoiceStatus("Whisper error: " + String(err).slice(0, 120));
            voiceLog("whisper_fail", String(err).slice(0, 200));
            return "";
          }
          var text = (res.j.text || "").trim();
          voiceLog("whisper_ok", "chars=" + text.length);
          if (text) {
            appendTranscript(text);
            noteSpeechActivity();
          }
          else setVoiceStatus(listenOn ? "Listening… (Whisper: no speech in chunk)" : "No speech detected");
          return text;
        })
        .catch(function (err) {
          transcribeBusy = false;
          setVoiceStatus("Whisper network error");
          voiceLog("whisper_net", String(err && err.message || err));
          return "";
        });
    }

    function stopSegmentRecorder(flush) {
      if (segmentTimer) {
        clearTimeout(segmentTimer);
        segmentTimer = null;
      }
      return new Promise(function (resolve) {
        if (!mediaRecorder || mediaRecorder.state === "inactive") {
          resolve();
          return;
        }
        pendingStops += 1;
        var rec = mediaRecorder;
        rec.onstop = function () {
          pendingStops = Math.max(0, pendingStops - 1);
          var mime = rec.mimeType || pickMime() || "audio/webm";
          var blob = new Blob(recordChunks, { type: mime });
          recordChunks = [];
          mediaRecorder = null;
          if (flush && (whisperArmed || sttEngine === "whisper")) {
            uploadWhisper(blob).then(function () { resolve(); });
          } else {
            resolve(blob);
          }
        };
        try { rec.stop(); } catch (eS) {
          pendingStops = Math.max(0, pendingStops - 1);
          resolve();
        }
      });
    }

    function startSegmentRecorder() {
      if (!listenOn || !mediaStream || !whisperArmed) return;
      if (!window.MediaRecorder) {
        setVoiceStatus("MediaRecorder unavailable — use Chrome/Edge");
        return;
      }
      recordChunks = [];
      var mime = pickMime();
      try {
        mediaRecorder = mime
          ? new MediaRecorder(mediaStream, { mimeType: mime })
          : new MediaRecorder(mediaStream);
      } catch (eR) {
        setVoiceStatus("Recorder failed: " + String(eR && eR.message || eR));
        voiceLog("recorder_fail", String(eR && eR.message || eR));
        return;
      }
      mediaRecorder.ondataavailable = function (ev) {
        if (ev.data && ev.data.size) recordChunks.push(ev.data);
      };
      mediaRecorder.onerror = function (ev) {
        voiceLog("recorder_error", String(ev && ev.error || "err"));
      };
      try {
        mediaRecorder.start();
        voiceLog("segment_start", mime || "default");
      } catch (eStart) {
        voiceLog("segment_start_fail", String(eStart && eStart.message || eStart));
        return;
      }
      segmentTimer = setTimeout(function () {
        if (!listenOn || !whisperArmed) return;
        stopSegmentRecorder(false).then(function (blob) {
          if (!listenOn || !whisperArmed) return;
          var p = blob ? uploadWhisper(blob) : Promise.resolve();
          p.finally(function () {
            if (listenOn && whisperArmed) startSegmentRecorder();
          });
        });
      }, 2000);
    }

    function releaseStream() {
      if (mediaStream) {
        try {
          mediaStream.getTracks().forEach(function (t) { t.stop(); });
        } catch (eT) {}
      }
      mediaStream = null;
    }

    function populateMicDevices() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices || !micDeviceEl) return;
      navigator.mediaDevices.enumerateDevices().then(function (devs) {
        var cur = micDeviceEl.value || "";
        var mics = devs.filter(function (d) { return d.kind === "audioinput"; });
        micDeviceEl.innerHTML = '<option value="">Default mic</option>';
        mics.forEach(function (d, i) {
          var opt = document.createElement("option");
          opt.value = d.deviceId;
          opt.textContent = d.label || ("Microphone " + (i + 1));
          micDeviceEl.appendChild(opt);
        });
        if (cur) micDeviceEl.value = cur;
        else if (micDeviceEl._want) {
          micDeviceEl.value = micDeviceEl._want;
          delete micDeviceEl._want;
        }
        voiceLog("devices", "mics=" + mics.length);
      }).catch(function () {});
    }

    function stopChromeRecognition() {
      if (chromeRestartTimer) {
        clearTimeout(chromeRestartTimer);
        chromeRestartTimer = null;
      }
      if (chromeWatchdog) {
        clearTimeout(chromeWatchdog);
        chromeWatchdog = null;
      }
      if (recognition) {
        try {
          recognition.onend = null;
          recognition.onresult = null;
          recognition.onerror = null;
          recognition.onstart = null;
          recognition.onaudiostart = null;
          recognition.onspeechstart = null;
          recognition.stop();
        } catch (eS) {}
      }
      recognition = null;
    }

    function markChromeBroken(reason) {
      // Session-only: retry Chrome next page load / new tab after user fixes OS settings
      try { sessionStorage.setItem("clawsum.chrome_stt_skip", "1"); } catch (e) {}
      try { localStorage.removeItem("clawsum.chrome_stt_broken"); } catch (e2) {}
      voiceLog("chrome_skip_session", reason || "");
    }

    function chromeSttLikelyBroken() {
      try {
        // Migrate away from permanent flag (settings fix would stay stuck on Whisper)
        if (localStorage.getItem("clawsum.chrome_stt_broken") === "1") {
          localStorage.removeItem("clawsum.chrome_stt_broken");
        }
        return sessionStorage.getItem("clawsum.chrome_stt_skip") === "1";
      } catch (e) {
        return false;
      }
    }

    function clearChromeBroken() {
      try { sessionStorage.removeItem("clawsum.chrome_stt_skip"); } catch (e) {}
      try { localStorage.removeItem("clawsum.chrome_stt_broken"); } catch (e2) {}
    }

    function armWhisperBackup(reason) {
      if (whisperArmed) return;
      whisperArmed = true;
      sttEngine = "whisper";
      voiceLog("whisper_armed", reason || "");
      if (!chromeHadResult) markChromeBroken(reason || "no_result");
      stopChromeRecognition();
      setVoiceStatus("Using Whisper backup (Chrome quiet this session)");
      if (voiceHint) {
        voiceHint.innerHTML = "<strong>Whisper backup</strong> for this tab. Reload the page to try Chrome again after mic settings changes.";
      }
      var go = function () {
        if (listenOn && mediaStream) startSegmentRecorder();
      };
      if (mediaStream) {
        go();
        return;
      }
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setVoiceStatus("Whisper needs mic access");
        return;
      }
      var constraints = {
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      };
      if (micDeviceEl && micDeviceEl.value) {
        constraints.audio.deviceId = { exact: micDeviceEl.value };
      }
      navigator.mediaDevices.getUserMedia(constraints)
        .then(function (stream) {
          if (!listenOn) {
            try { stream.getTracks().forEach(function (t) { t.stop(); }); } catch (e) {}
            return;
          }
          mediaStream = stream;
          populateMicDevices();
          startMeter(stream);
          go();
        })
        .catch(function (err) {
          setVoiceStatus("Whisper mic error: " + ((err && err.name) || "failed"));
          voiceLog("whisper_gum_fail", String(err && err.name || err));
        });
    }

    function startChromeRecognition() {
      if (!SpeechRec || !listenOn) {
        if (!SpeechRec) armWhisperBackup("no_speech_rec");
        return;
      }
      // Chrome STT opens its own capture — release any held GUM tracks so it is not silenced
      if (mediaStream) {
        stopMeter();
        releaseStream();
      }
      stopChromeRecognition();
      recognition = new SpeechRec();
      // continuous:false + restart is more reliable than continuous:true on some Chrome builds
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognition.lang = "en-US";
      sttEngine = "chrome";

      recognition.onstart = function () {
        voiceLog("chrome_onstart");
        setVoiceStatus("Trying Chrome speech…");
        if (chromeWatchdog) clearTimeout(chromeWatchdog);
        chromeWatchdog = setTimeout(function () {
          if (!listenOn || chromeHadResult || whisperArmed) return;
          armWhisperBackup("watchdog_no_chrome");
        }, 2500);
      };

      recognition.onaudiostart = function () { voiceLog("chrome_onaudiostart"); };
      recognition.onspeechstart = function () {
        voiceLog("chrome_onspeechstart");
        setVoiceStatus("Chrome hearing you…");
        noteSpeechActivity();
      };
      recognition.onspeechend = function () {
        voiceLog("chrome_onspeechend");
        noteSpeechActivity();
      };

      recognition.onerror = function (ev) {
        var err = (ev && ev.error) || "error";
        voiceLog("chrome_onerror", err);
        if (err === "aborted") return;
        if (err === "no-speech") {
          noSpeechStreak += 1;
          if (!chromeHadResult && noSpeechStreak >= 1) {
            armWhisperBackup("no_speech");
          }
          return;
        }
        var map = {
          "not-allowed": "Mic blocked — allow microphone for boss.clawsum.com",
          network: "Chrome speech network error — using Whisper",
          "audio-capture": "No microphone found",
          "service-not-allowed": "Chrome speech blocked by browser policy",
        };
        setVoiceStatus(map[err] || ("Chrome mic: " + err));
        if (err === "network" || err === "service-not-allowed") {
          armWhisperBackup("chrome_" + err);
        }
        if (err === "not-allowed" || err === "audio-capture") {
          stopListening();
        }
      };

      recognition.onresult = function (ev) {
        chromeHadResult = true;
        noSpeechStreak = 0;
        sttEngine = "chrome";
        clearChromeBroken();
        if (chromeWatchdog) {
          clearTimeout(chromeWatchdog);
          chromeWatchdog = null;
        }
        whisperArmed = false;
        if (segmentTimer || mediaRecorder) {
          stopSegmentRecorder(false);
        }
        var interim = "";
        var i;
        for (i = ev.resultIndex; i < ev.results.length; i++) {
          var piece = (ev.results[i][0] && ev.results[i][0].transcript) || "";
          if (ev.results[i].isFinal) {
            committed += (committed && !/\s$/.test(committed) ? " " : "") + piece;
          } else {
            interim += piece;
          }
        }
        var live = (committed + (interim ? " " + interim : "")).replace(/\s+/g, " ").trim();
        voiceLog("chrome_onresult", "len=" + live.length + " interim=" + !!interim);
        applyTranscript(live, "chrome");
        if (live) noteSpeechActivity();
      };

      recognition.onend = function () {
        voiceLog("chrome_onend", "listenOn=" + listenOn + " had=" + chromeHadResult + " whisper=" + whisperArmed);
        if (!listenOn || whisperArmed) return;
        chromeRestartTimer = setTimeout(function () {
          if (!listenOn || whisperArmed || !recognition) return;
          try {
            recognition.start();
            voiceLog("chrome_restart");
          } catch (eR) {
            voiceLog("chrome_restart_fail", String(eR && eR.message || eR));
            if (!chromeHadResult) armWhisperBackup("chrome_restart_fail");
          }
        }, 250);
      };

      try {
        recognition.start();
        voiceLog("chrome_start");
      } catch (eStart) {
        voiceLog("chrome_start_fail", String(eStart && eStart.message || eStart));
        armWhisperBackup("chrome_start_fail");
      }
    }

    function stopListening() {
      listenOn = false;
      whisperArmed = false;
      sttEngine = null;
      clearSilenceAutoSend();
      autoSendInFlight = false;
      stopChromeRecognition();
      if (segmentTimer) {
        clearTimeout(segmentTimer);
        segmentTimer = null;
      }
      try {
        if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
      } catch (eS) {}
      mediaRecorder = null;
      recordChunks = [];
      stopMeter();
      releaseStream();
      if (panel) panel.classList.remove("is-listening");
      if (transcriptEl) transcriptEl.classList.remove("is-listening");
      if (listenToggle) {
        listenToggle.setAttribute("aria-pressed", "false");
        listenToggle.textContent = "Live Listen: Off";
        listenToggle.classList.remove("is-on");
      }
    }

    function applyTranscript(live, engine) {
      setTranscript(live);
      if (transcriptEl) {
        try {
          transcriptEl.focus();
          transcriptEl.scrollTop = transcriptEl.scrollHeight;
        } catch (eF) {}
      }
      var tag = engine === "whisper" ? "Whisper" : "Chrome";
      if (autoSendOn && listenOn) {
        setVoiceStatus(tag + " live — auto-send after 2s silence");
      } else {
        setVoiceStatus(tag + " live — keep talking or Send");
      }
    }

    function startListening() {
      if (!window.isSecureContext) {
        setVoiceStatus("Mic needs HTTPS (open https://boss.clawsum.com)");
        voiceLog("insecure_context");
        return;
      }
      chromeHadResult = false;
      noSpeechStreak = 0;
      peakLevel = 0;
      whisperArmed = false;
      sttEngine = null;
      committed = (transcriptEl && transcriptEl.value) || committed || "";

      if (panel) panel.classList.add("is-listening");
      if (transcriptEl) {
        transcriptEl.classList.add("is-listening");
        if (!transcriptEl.value) transcriptEl.placeholder = "Listening… speak now";
      }

      // Logs show Chrome opens mic (onaudiostart) but never onspeechstart/onresult on this PC.
      // After one failure, skip straight to Whisper so we don't burn ~3s every time.
      if (chromeSttLikelyBroken() || !SpeechRec) {
        if (voiceHint) {
          voiceHint.innerHTML = "<strong>Whisper</strong> (Chrome Web Speech unavailable here). ~2s chunks. Use mic picker if level is flat.";
        }
        setVoiceStatus("Listening via Whisper…");
        voiceLog("skip_chrome", chromeSttLikelyBroken() ? "remembered_broken" : "no_speech_rec");
        armWhisperBackup(SpeechRec ? "skip_remembered_broken" : "no_speech_rec");
        return;
      }

      if (voiceHint) {
        voiceHint.innerHTML = "<strong>Trying Chrome</strong> once. If it stays quiet, Whisper starts automatically and we remember to skip Chrome next time.";
      }
      setVoiceStatus("Trying Chrome speech…");
      startChromeRecognition();
    }

    if (micDeviceEl) {
      micDeviceEl.addEventListener("change", function () {
        try { localStorage.setItem("clawsum.mic_device", micDeviceEl.value || ""); } catch (eD) {}
        if (listenOn) {
          stopListening();
          listenOn = true;
          if (listenToggle) {
            listenToggle.setAttribute("aria-pressed", "true");
            listenToggle.textContent = "Live Listen: On";
            listenToggle.classList.add("is-on");
          }
          startListening();
        }
      });
      try {
        var savedMic = localStorage.getItem("clawsum.mic_device") || "";
        if (savedMic) {
          micDeviceEl._want = savedMic;
        }
      } catch (eS) {}
    }

    if (listenToggle) {
      listenToggle.addEventListener("click", function () {
        if (listenOn) {
          var finishing = (whisperArmed || sttEngine === "whisper")
            ? stopSegmentRecorder(true)
            : Promise.resolve();
          finishing.then(function () {
            stopListening();
            setVoiceStatus("Listen off — edit transcript, then Done — Send");
            if (voiceHint) {
              voiceHint.innerHTML = "Live Listen is off. Edit the transcript if needed, then click <strong>Done — Send</strong>.";
            }
          });
          return;
        }
        listenOn = true;
        listenToggle.setAttribute("aria-pressed", "true");
        listenToggle.textContent = "Live Listen: On";
        listenToggle.classList.add("is-on");
        setVoiceStatus("Starting mic — allow permission if asked");
        voiceLog("listen_toggle_on");
        startListening();
      });
    }

    if (autoSpeakToggle) {
      autoSpeakToggle.addEventListener("click", function () {
        autoSpeakOn = !autoSpeakOn;
        autoSpeakToggle.setAttribute("aria-pressed", autoSpeakOn ? "true" : "false");
        autoSpeakToggle.textContent = autoSpeakOn ? "Auto-Speak: On" : "Auto-Speak: Off";
        autoSpeakToggle.classList.toggle("is-on", autoSpeakOn);
        setVoiceStatus(autoSpeakOn ? "Auto-Speak on — briefs will be read aloud" : "Auto-Speak off");
        try { localStorage.setItem("clawsum.autospeak", autoSpeakOn ? "1" : "0"); } catch (eA) {}
      });
      try {
        var savedSpeak = localStorage.getItem("clawsum.autospeak");
        // Default ON when unset; only Off if user explicitly chose 0
        autoSpeakOn = savedSpeak !== "0";
        autoSpeakToggle.setAttribute("aria-pressed", autoSpeakOn ? "true" : "false");
        autoSpeakToggle.textContent = autoSpeakOn ? "Auto-Speak: On" : "Auto-Speak: Off";
        autoSpeakToggle.classList.toggle("is-on", autoSpeakOn);
      } catch (eB) {}
    }

    if (autoSendToggle) {
      autoSendToggle.addEventListener("click", function () {
        autoSendOn = !autoSendOn;
        autoSendToggle.setAttribute("aria-pressed", autoSendOn ? "true" : "false");
        autoSendToggle.textContent = autoSendOn ? "Auto-Send: On" : "Auto-Send: Off";
        autoSendToggle.classList.toggle("is-on", autoSendOn);
        clearSilenceAutoSend();
        if (!autoSendOn) {
          setVoiceStatus("Auto-Send off — use Send when ready");
        } else {
          setVoiceStatus("Auto-Send on — sends after 2s silence while listening");
          if (listenOn && readComposeText()) noteSpeechActivity();
        }
        try { localStorage.setItem("clawsum.autosend", autoSendOn ? "1" : "0"); } catch (eAs) {}
      });
      try {
        var savedSend = localStorage.getItem("clawsum.autosend");
        autoSendOn = savedSend !== "0";
        autoSendToggle.setAttribute("aria-pressed", autoSendOn ? "true" : "false");
        autoSendToggle.textContent = autoSendOn ? "Auto-Send: On" : "Auto-Send: Off";
        autoSendToggle.classList.toggle("is-on", autoSendOn);
      } catch (eAs2) {}
    }

    function briefSpeakScript(brief, greetLine) {
      var parts = [];
      if (greetLine) parts.push(greetLine);
      else if (greetEl && greetEl.textContent) parts.push(greetEl.textContent);
      brief = brief || latestBrief;
      if (brief) {
        parts.push("Last session: " + (brief.last_session || "fresh start"));
        (brief.progress || []).slice(0, 3).forEach(function (p) { parts.push(p); });
        var approvals = brief.pending_approvals;
        if (approvals != null) parts.push(String(approvals) + " pending approvals.");
        var inbox = brief.inbox_needs_boss;
        if (inbox != null) parts.push(String(inbox) + " inbox items need the Boss.");
        (brief.next_actions || []).slice(0, 3).forEach(function (a, i) {
          parts.push(String(i + 1) + ". " + a);
        });
      } else if (lastEl && lastEl.textContent) parts.push(lastEl.textContent);
      if (!parts.length) parts.push("Clawsum is online. Brief still loading.");
      return parts.join(". ");
    }

    function maybeAutoplayBrief(brief) {
      if (!autoSpeakOn) return;
      try {
        if (sessionStorage.getItem("clawsum.brief.autoplayed") === "1") return;
        sessionStorage.setItem("clawsum.brief.autoplayed", "1");
      } catch (eAp) {}
      setTimeout(function () {
        speakText(briefSpeakScript(brief));
        setVoiceStatus("Speaking greeting brief…");
      }, 600);
    }

    if (doneSendBtn) {
      doneSendBtn.addEventListener("click", function () {
        var finish = function () {
          var text = readComposeText();
          if (!text) {
            setVoiceStatus("Nothing to send — type or use Live Listen first");
            return;
          }
          setVoiceStatus("Sending…");
          sendToChat(text, true);
          committed = "";
        };
        if (listenOn) {
          if (whisperArmed || sttEngine === "whisper") {
            setVoiceStatus("Finishing Whisper chunk…");
            stopSegmentRecorder(true).then(function () {
              stopListening();
              var wait = 0;
              var poll = function () {
                if (!transcribeBusy || wait > 40) {
                  finish();
                  return;
                }
                wait += 1;
                setTimeout(poll, 250);
              };
              poll();
            });
          } else {
            stopListening();
            finish();
          }
        } else {
          finish();
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        committed = "";
        setTranscript("");
        setVoiceStatus("Cleared");
      });
    }

    if (transcriptEl) {
      transcriptEl.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
          ev.preventDefault();
          if (doneSendBtn) doneSendBtn.click();
        }
      });
    }

    if (speakGreetBtn) {
      speakGreetBtn.addEventListener("click", function () {
        try {
          if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          if (audioCtx && audioCtx.state === "suspended") audioCtx.resume();
        } catch (eUnlock) {}
        var g = currentGreeting || (greetEl && greetEl.textContent) || "";
        if (!g || /loading greeting/i.test(g)) {
          if (cachedGreetingPool.length) {
            g = pickRotatingGreeting(cachedGreetingPool);
            currentGreeting = g;
            if (greetEl) greetEl.textContent = g;
          }
        }
        if (!g) {
          setVoiceStatus("No greeting loaded yet — wait a second and try again");
          return;
        }
        try { sessionStorage.removeItem("clawsum.greet.spoken"); } catch (eClear) {}
        setVoiceStatus("Speaking greeting…");
        speakText(g);
      });
    }

    if (speakBriefBtn) {
      speakBriefBtn.addEventListener("click", function () {
        var g = currentGreeting || (greetEl && greetEl.textContent) || "";
        if (g && !/loading greeting/i.test(g)) {
          // Always speak greeting first on explicit click (user gesture unlocks audio)
          speakText(g);
        }
        if (latestBrief) {
          setTimeout(function () { speakText(briefSpeakScript(latestBrief)); }, g ? 1200 : 0);
        } else {
          setVoiceStatus("Loading brief…");
          fetchJSON(API + "/session-startup").then(function (j) {
            if (j && j.ok) latestBrief = j;
            speakText(briefSpeakScript(latestBrief));
          }).catch(function () { speakText(briefSpeakScript(null)); });
        }
      });
    }

    if (onChatPage) {
      var bootTries = 0;
      var bootTick = function () {
        if (drainPendingPrompt(document, setVoiceStatus)) return;
        bootTries += 1;
        if (bootTries < 30) setTimeout(bootTick, 350);
      };
      setTimeout(bootTick, 500);
    }

    var isNewSession = false;
    try {
      if (!sessionStorage.getItem("clawsum.dock.session")) {
        sessionStorage.setItem("clawsum.dock.session", String(Date.now()));
        isNewSession = true;
      }
    } catch (e) { isNewSession = true; }

    var line = buildBossGreeting(true);
    currentGreeting = line;
    if (greetEl) greetEl.textContent = line;
    placeInlineGreeting(line);
    setVoiceStatus("Voice idle — click Speak on the greeting above the chat box");
    populateMicDevices();
    // Clear old permanent "Chrome broken" flag so fixed mic settings take effect
    clearChromeBroken();
    try { sessionStorage.removeItem("clawsum.greet.spoken"); } catch (eClearGreet) {}
    if (voiceHint) {
      voiceHint.innerHTML = "Greeting sits above the chat cursor. Click <strong>Speak</strong> there, or <strong>Speak greeting</strong>. Auto-Speak reads replies aloud.";
    }

    // Keep the greeting glued above the composer if Hermes re-renders the chat shell
    try {
      var greetPlaceTimer = 0;
      var greetPlaceObs = new MutationObserver(function () {
        if (greetPlaceTimer) return;
        greetPlaceTimer = setTimeout(function () {
          greetPlaceTimer = 0;
          if (currentGreeting) placeInlineGreeting(currentGreeting);
        }, 250);
      });
      greetPlaceObs.observe(document.getElementById("root") || document.body, { childList: true, subtree: true });
    } catch (ePlace) {}

    fetchJSON(API + "/session-startup")
      .then(function (j) {
        if (!j || !j.ok) {
          setVoiceStatus("Greeting API failed — using local greeting");
          return;
        }
        latestBrief = j;
        if (j.acks && j.acks.length) cachedAckPool = j.acks;
        if (j.greetings && j.greetings.length) cachedGreetingPool = j.greetings;
        try {
          window.__clawsumVoiceCache = window.__clawsumVoiceCache || {};
          var vc = (j.voice && j.voice.cache) || [];
          vc.forEach(function (row) {
            if (row && row.text && row.url) window.__clawsumVoiceCache[row.text] = row.url;
          });
          voiceLog("voice_cache_ready", "entries=" + vc.length);
        } catch (eVc) {}
        // Always show an approved greeting (not only on brand-new tab sessions)
        if (cachedGreetingPool.length) {
          var g = pickRotatingGreeting(cachedGreetingPool);
          currentGreeting = g;
          if (greetEl) greetEl.textContent = g;
          placeInlineGreeting(g);
          try { spokenReplyFingerprints[g.slice(0, 160)] = 1; } catch (eFp) {}
          if (autoSpeakOn) {
            // Attempt autoplay; browser may require the Speak greeting click
            speakText(g);
          }
        }
        if (lastEl) lastEl.textContent = "Last session: " + (j.last_session || "fresh start / not enough data");
        if (reportEl) {
          reportEl.innerHTML = "";
          (j.progress || j.report || []).slice(0, 6).forEach(function (line2) {
            var li = document.createElement("li");
            li.textContent = line2;
            reportEl.appendChild(li);
          });
        }
        if (nextEl) {
          nextEl.innerHTML = "";
          (j.next_actions || []).slice(0, 5).forEach(function (a) {
            var li = document.createElement("li");
            li.textContent = a;
            nextEl.appendChild(li);
          });
        }
        if (j.suggestions && j.suggestions.length) renderSuggestions(j.suggestions);
        maybeAutoplayBrief(j);
      })
      .catch(function () {
        if (lastEl) lastEl.textContent = "Last session: not enough live data yet.";
      });
  }

  function forceStartHome() {
    if (typeof window === "undefined" || typeof sessionStorage === "undefined") return;
    if (isEmbeddedFrame()) return;
    try {
      var params = new URLSearchParams(window.location.search || "");
      if (params.get("noredirect") === "1") {
        sessionStorage.setItem("clawsum.stay", "1");
        return;
      }
      if (sessionStorage.getItem("clawsum.stay") === "1") return;
      var path = window.location.pathname || "/";
      if (path === "/" || path === "/sessions" || path === "/index.html") {
        window.location.replace("/home");
      }
    } catch (e) {}
  }

  function SidebarSlot() {
    var auth = useAuthority();
    var briefState = useState(null);
    var brief = briefState[0];
    var setBrief = briefState[1];
    var linksState = useState(null);
    var extLinks = linksState[0];
    var setExtLinks = linksState[1];
    useEffect(function () {
      fetchJSON(API + "/brief").then(setBrief).catch(function () {});
      fetchJSON(API + "/links").then(setExtLinks).catch(function () {});
      forceStartHome();
      ensureChatDock();
      var tries = 0;
      var rid = setInterval(function () {
        forceStartHome();
        ensureChatDock();
        tries += 1;
        if (tries > 20) clearInterval(rid);
      }, 500);
      // Keep dock alive across SPA navigations
      var keep = setInterval(function () { ensureChatDock(); paintSidebarUnique(); }, 2500);
      ensureChatDock();
      var tick = function () {
        if (typeof document === "undefined") return;
        if (/Hermes/i.test(document.title || "")) {
          document.title = (document.title || "")
            .replace(/Hermes Agent/gi, "Clawsum Agent")
            .replace(/Hermes(?!\.clawsum)/gi, "Clawsum");
        }
        if (!/Clawsum Agent/i.test(document.title || "")) {
          document.title = "Clawsum Agent";
        }
      };
      tick();
      var id = setInterval(tick, 3000);
      return function () {
        clearInterval(id);
        clearInterval(rid);
        clearInterval(keep);
      };
    }, []);
    var L = extLinks || {};
    var path = "";
    var tab = "";
    try {
      path = window.location.pathname || "";
      tab = new URLSearchParams(window.location.search || "").get("tab") || "";
    } catch (e) {}
    if (!tab && (path === "/home" || path === "/")) tab = "start";

    function isActive(l) {
      if (l.ext) return false;
      if (l.matchTab) {
        if (path.indexOf("/home") < 0 && path !== "/") return false;
        if (l.matchTab === "start") return !tab || tab === "start" || tab === "home";
        return tab === l.matchTab;
      }
      if (l.matchPath) return path === l.matchPath || path.indexOf(l.matchPath) === 0;
      return false;
    }

    var links = [
      { href: "/home", label: withIcon("start", "Start"), matchTab: "start", group: "pages", tone: "lobster" },
      { href: "/home?tab=dash", label: withIcon("dash", "Dash"), matchTab: "dash", group: "pages", tone: "navy" },
      { href: "/home?tab=catalog", label: withIcon("catalog", "Catalog"), matchTab: "catalog", group: "pages", tone: "star" },
      { href: "/home?tab=brief", label: withIcon("brief", "Brief"), matchTab: "brief", group: "pages", tone: "gold" },
      { href: "/home?tab=approvals", label: withIcon("approvals", "Approvals"), matchTab: "approvals", group: "pages", tone: "crimson", count: brief && brief.pending_approvals },
      { href: "/home?tab=processes", label: withIcon("jarvis", "Jarvis"), matchTab: "processes", group: "pages", tone: "sky", count: brief && brief.jarvis && brief.jarvis.awaiting_boss },
      { href: "/home?tab=archive", label: withIcon("archive", "Archive"), matchTab: "archive", group: "pages", tone: "violet" },
      { href: "/home?tab=health", label: withIcon("ops", "Ops"), matchTab: "health", group: "pages", tone: "orange" },
      { href: "/chat", label: withIcon("chat", "Chat"), matchPath: "/chat", group: "pages", tone: "cyan" },
      { href: "/agents", label: withIcon("team", "Team"), matchPath: "/agents", group: "pages", tone: "teal", count: auth.agent_count },
      { href: "/skills", label: withIcon("skills", "Skills"), matchPath: "/skills", group: "pages", tone: "pink", count: auth.skill_count },
      { href: "/inbox", label: withIcon("inbox", "Inbox"), matchPath: "/inbox", group: "pages", tone: "indigo" },
      { href: "/cron", label: withIcon("cron", "Cron"), matchPath: "/cron", group: "pages", tone: "mint" },
      { href: "/kanban", label: withIcon("todo", "Kanban"), matchPath: "/kanban", group: "pages", tone: "amber" },
      { href: "/home?tab=channels", label: withIcon("channels", "Channels"), matchTab: "channels", group: "pages", tone: "rose" },
      { href: "/home?tab=graph", label: withIcon("graph", "Graphify"), matchTab: "graph", group: "pages", tone: "white" },
      { href: L.paperclip || L.boss || "https://paperclip.clawsum.com", label: withIcon("paperclip", "Paperclip"), ext: true, group: "ext", tone: "lobster" },
      { href: L.connect || "https://connect.clawsum.com", label: withIcon("connect", "Connect"), ext: true, group: "ext", tone: "cyan" },
      { href: L.openclaw || "https://openclaw.clawsum.com", label: withIcon("openclaw", "OpenClaw"), ext: true, group: "ext", tone: "gold" },
      { href: L.grafana || "https://grafana.clawsum.com", label: withIcon("grafana", "Grafana"), ext: true, group: "ext", tone: "lime" },
      { href: L.arcade || "https://arcade.clawsum.com", label: withIcon("arcade", "Arcade Studio"), ext: true, group: "ext", tone: "white" },
      { href: L.login || "https://login.clawsum.com", label: withIcon("login", "Login hub"), ext: true, group: "ext", tone: "navy" },
    ];
    return React.createElement(
      "div",
      { className: "clawsum-sidebar" },
      React.createElement(
        "a",
        {
          href: "/home",
          className: "clawsum-sidebar-brand",
        },
        React.createElement("div", { className: "clawsum-sidebar-brand-mark" }, "⚡ Clawsum"),
        React.createElement("div", { className: "clawsum-sidebar-brand-sub" }, "Pages")
      ),
      React.createElement("div", { className: "clawsum-sidebar-section" }, "🧭 Boss pages"),
      React.createElement(
        "nav",
        { className: "clawsum-sidebar-nav", "aria-label": "Boss pages" },
        links
          .filter(function (l) { return l.group === "pages"; })
          .map(function (l, idx) {
            return React.createElement(
              "a",
              {
                key: l.href + l.label,
                href: l.href,
                className: "clawsum-sidebar-btn tone-" + (l.tone || "lobster") + (isActive(l) ? " is-active" : ""),
              },
              React.createElement("span", { className: "clawsum-sidebar-btn-num" }, String(idx + 1)),
              React.createElement("span", { className: "clawsum-sidebar-btn-label" }, l.label),
              l.count != null && l.count !== ""
                ? React.createElement("span", { className: "clawsum-nav-count" }, String(l.count))
                : null
            );
          })
      ),
      React.createElement("div", { className: "clawsum-sidebar-section" }, "🔌 Systems"),
      React.createElement(
        "nav",
        { className: "clawsum-sidebar-nav", "aria-label": "External systems" },
        links
          .filter(function (l) { return l.group === "ext"; })
          .map(function (l) {
            return React.createElement(
              "a",
              {
                key: l.href + l.label,
                href: l.href,
                className: "clawsum-sidebar-btn is-ext tone-" + (l.tone || "navy"),
                target: "_blank",
                rel: "noreferrer",
              },
              React.createElement("span", { className: "clawsum-sidebar-btn-label" }, l.label)
            );
          })
      )
    );
  }

  function HeaderCrestSlot() {
    useEffect(function () {
      if (typeof document === "undefined") return;
      document.title = "Clawsum Agent";
      ensureHudShell();
      ensureChatDock();
      var keepChat = setInterval(function () {
        ensureHudShell();
        ensureChatDock();
      }, 2000);
      if (!document.getElementById("clawsum-crest-css")) {
        var style = document.createElement("style");
        style.id = "clawsum-crest-css";
        style.textContent = [
          'a[data-clawsum-crest="1"]{display:inline-flex;align-items:center;gap:0.65rem;',
          "max-height:2.75rem;overflow:hidden;min-width:0;flex:0 1 auto;}",
          'a[data-clawsum-crest="1"] .clawsum-crest-mark{width:2.55rem;height:2.55rem;flex:0 0 auto;',
          "background-size:contain;background-position:center;background-repeat:no-repeat;}",
          'a[data-clawsum-crest="1"] .clawsum-crest-label{font-size:1.15rem;font-weight:700;',
          "letter-spacing:0.015em;line-height:1.1;white-space:nowrap;overflow:hidden;",
          "text-overflow:ellipsis;max-width:14rem;}",
          '[data-clawsum-dup-brand="1"]{display:none!important;visibility:hidden!important;',
          "width:0!important;height:0!important;max-width:0!important;overflow:hidden!important;",
          "margin:0!important;padding:0!important;border:0!important;}",
        ].join("");
        document.head.appendChild(style);
      }
      var brandRe = /^(Clawsum(\s+Agent)?|Hermes(\s+Agent)?)$/i;
      var tick = function () {
        var crest = document.querySelector('a[data-clawsum-crest="1"]');
        if (!crest) return;
        var header =
          crest.closest("header") ||
          crest.closest('[class*="Header"]') ||
          crest.closest('[class*="header"]') ||
          crest.parentElement;
        if (!header) return;
        var nodes = header.querySelectorAll("a, span, div, p, h1, h2, button, label, img");
        Array.prototype.forEach.call(nodes, function (el) {
          if (el === crest || crest.contains(el)) return;
          if (el.querySelector && el.querySelector('[data-clawsum-crest="1"]')) return;
          if (el.tagName === "IMG") {
            var alt = (el.getAttribute("alt") || "").trim();
            if (brandRe.test(alt) || /clawsum|hermes/i.test(alt)) {
              (el.closest("a") || el).setAttribute("data-clawsum-dup-brand", "1");
            }
            return;
          }
          // Prefer leaf labels (little/no nested structure)
          if (el.children && el.children.length > 2) return;
          var t = (el.textContent || "").replace(/\s+/g, " ").trim();
          if (!t || t.length > 28) return;
          if (brandRe.test(t)) {
            el.setAttribute("data-clawsum-dup-brand", "1");
          }
        });
      };
      tick();
      var id = setInterval(tick, 600);
      return function () {
        clearInterval(id);
        clearInterval(keepChat);
      };
    }, []);
    var crest = cssVar("--theme-asset-crest");
    var logo = cssVar("--theme-asset-logo");
    // Prefer mark for icon+word combo; fall back to logo
    var src = crest || logo;
    var inner = src
      ? React.createElement("div", {
          className: "clawsum-crest-mark",
          style: { backgroundImage: asBg(src) },
          "aria-hidden": true,
        })
      : React.createElement(
          "span",
          {
            className: "clawsum-crest-label",
            style: { color: "#2dd4bf", fontSize: "1.15rem" },
          },
          "CS"
        );
    return React.createElement(
      "a",
      {
        href: "/home",
        "data-clawsum-crest": "1",
        style: {
          paddingLeft: 10,
          paddingRight: 10,
          textDecoration: "none",
          color: "inherit",
          cursor: "pointer",
        },
        title: "Clawsum Agent",
        "aria-label": "Clawsum Agent — Home",
      },
      inner,
      React.createElement("span", { className: "clawsum-crest-label" }, "Clawsum Agent")
    );
  }

  function FooterTaglineSlot() {
    return React.createElement(
      "span",
      {
        style: {
          fontFamily: "var(--theme-font-display, sans-serif)",
          fontSize: "0.6rem",
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          opacity: 0.7,
        },
      },
      "Clawsum talks · Paperclip manages · OpenClaw acts"
    );
  }

  PLUGINS.register(NAME, CockpitPage);
  if (PLUGINS.registerSlot) {
    PLUGINS.registerSlot(NAME, "sidebar", SidebarSlot);
    PLUGINS.registerSlot(NAME, "header-left", HeaderCrestSlot);
    PLUGINS.registerSlot(NAME, "footer-right", FooterTaglineSlot);
    PLUGINS.registerSlot(NAME, "cron:top", CronPanel);
    PLUGINS.registerSlot(NAME, "skills:top", function SkillsTop() {
      return React.createElement(
        "div",
        { className: "clawsum-card tone-orange", style: { margin: "0.75rem 0" } },
        React.createElement("strong", null, "Clawsum skills are live on this page (HUD 1.4.1)."),
        React.createElement("p", { className: "muted" }, "If the list below is Hermes-empty, scroll this card — or open /skills.")
      );
    });
  }
  // Boot chat chrome even if slots mount late
  try {
    if (typeof document !== "undefined") {
      var bootChat = function () { try { ensureHudShell(); ensureChatDock(); } catch (e) {} };
      if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bootChat);
      else bootChat();
      setTimeout(bootChat, 400);
      setTimeout(bootChat, 1200);
    }
  } catch (eBoot) {}
})();
