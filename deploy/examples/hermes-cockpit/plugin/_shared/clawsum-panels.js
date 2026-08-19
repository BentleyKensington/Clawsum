/**
 * Shared Clawsum panels — loaded by inbox/agents/skills/cockpit plugins.
 * Exposes window.__CLAWSUM_PANELS__
 */
(function () {
  "use strict";
  var SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;
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
  var API = "/api/plugins/clawsum-cockpit";

  function Chip(label, key) {
    return React.createElement("span", { key: key || label, className: "clawsum-chip" }, label);
  }

  function HudAscii(kind) {
    var slim = kind === "chat" || kind === "slim";
    return React.createElement(
      "pre",
      { className: "clawsum-ascii-art" + (slim ? " is-slim" : ""), "aria-hidden": true },
      slim
        ? "╔═ COMMS LINK ════ CLAWSUM ════ LIVE HUD ═╗\n║  JARVIS CHANNEL · GPT / OPENROUTER / OR  ║\n╚════ SAY  escalate  FOR FRONTIER MODEL ═══╝"
        : "╔══════════════════════════════════════════════════════════╗\n║  ⚡  C L A W S U M   ·   C E O   C O C K P I T  ⚡       ║\n║  ⟨CYN⟩ ⟨AMB⟩ ⟨LIM⟩ ⟨ROS⟩ ⟨VIO⟩ ⟨GLD⟩ ⟨TEL⟩ ⟨SKY⟩     ║\n╚════ 5TH-GEN COMMAND DECK · TILES ARE LIVE LINKS ═════════╝"
    );
  }

  var AGENT_EXPLAIN = {
    admin: "Command liaison — briefs, inbox triage, approvals queue, reminders. First stop when Boss needs the desk cleared.",
    hermes: "Proactive Clawsum Agent — drives follow-through, archive questions, and session briefs. Boss-authorized actions only.",
    paperclip: "Task router and board hygiene — keeps Paperclip issues moving, flags blocked work, syncs priorities.",
    coding: "Platform engineer — VPS, Hermes cockpit, OpenClaw config, deploy hygiene for Clawsum cells.",
    data: "Data plane — Postgres reports, ETL, ArcadeDB, inbox analytics feeds.",
    ghl: "GoHighLevel CRM ops for WNN — pipelines, re-engage sequences, lead hygiene (overlay skills included).",
    realestate: "Deals + storm/roofing intel cells — research support, not auto-send.",
    comms: "Outbound draft writer — every send stays Tier 2 (Boss approval).",
    research: "Cross-cell competitive and brief research — read-heavy, cite sources.",
    planning: "Priorities and cell planning — Techtasia + platform roadmap hygiene.",
    media: "Studio render/publish — video factory; publish stays Tier 2.",
    pentest: "Defensive security — scans and reports; no exploits.",
    legal: "Contracts, terms, privilege — draft/review only; file/sign Tier 3.",
    content: "Repurpose longform into shorts, threads, posts. Publish via Social.",
    ads: "PPC / paid media — budgets and ads; spend Tier 2.",
    bookkeeper: "Books, invoices, receipts — ledger hygiene; pay/wire Tier 3.",
    seo: "SEO/AEO/GEO, Search Console, GMB, knowledge panel.",
    funnel: "Offers, landing pages, CRO.",
    calendar: "Scheduling across cells — holds and invites; send Tier 2.",
    social: "Post, schedule, reply — public voice; post/reply Tier 2.",
    "llm-lab": "Model bake-offs — tests and compares LLMs; no silent spend.",
  };
  var SKILL_EXPLAIN = {
    "ceo-daily-brief": "Builds the morning ops brief from Paperclip + inbox signals. Read-only; posts only when asked.",
    "hermes-proactive-drive": "Session startup brief + every-reply Next guidance. Keeps Gerald moving without nagging.",
    "overwatch-approvals": "Surfaces Tier-gated waits and approval queue health across cells.",
    "paperclip-task-routing": "Creates/updates Paperclip tasks from briefs and Ask Boss items.",
    "resume-policy-gate": "Blocks risky resume/auto-continue unless policy allows.",
    "gmail-inbox-review": "Per-email analysis for clawsums@ — needs_boss, drafts, reminders.",
    "gmail-sync-triage": "Sync + coarse triage into Postgres / Paperclip.",
    "people-places-crm": "People/places CRM lookups across cells.",
    "reminders-boss-nudge": "Scheduled Boss nudges (Telegram when wired).",
    "chatgpt-archive": "Search prior ChatGPT/archive conversations for context.",
    "cell-isolation-check": "Ensures cell boundaries — no cross-tenant credential bleed.",
    "ghl-lead-ops": "GHL lead pipeline ops for WNN.",
    "ghl-reengage": "Re-engage dormant GHL contacts (draft-first).",
    "vocalitic-health": "Vocalitic / local AI health checks.",
    "roofing-storm-intel": "Storm/roofing intel research — advisory, not claims.",
    "real-estate-pipeline": "RE deal pipeline notes and ArcadeDB hooks.",
    "commerce-fastbuy": "AcceptAI / FastBuy commerce lane drafts.",
    "techtasia-planning": "Techtasia priorities and planning board.",
    "personal-admin": "Gerald personal-admin lane (mail, calendar hygiene).",
    "hardware-local-ai": "Local hardware / AI box status.",
    "research-brief": "Competitive / market research briefs with citations.",
    "credential-hygiene": "Credential inventory and rotation reminders.",
    "draft-comms-approval-gated": "Outbound drafts only — send requires Boss.",
    "telegram-ops-notify": "Ops alerts to Telegram when configured.",
    "data-scraper": "In-house scraper — Data tool, not its own agent.",
    "data-osint": "OSINT + global monitoring; extract public details.",
    "data-chat-extract": "Pull durable facts from chat/archive into memory.",
    "graphify-obsidian": "Graphify / 3D Obsidian memory visualizer.",
    "agent-daily-review": "Each agent reviews memory/tasks; feeds morning brief.",
    "hermes-daily-alert": "Hermes daily sweep — money, leverage, must-know.",
    "legal-review": "Contract/terms review. File/sign = Tier 3.",
    "content-repurpose": "Longform → clips, threads, posts.",
    "ppc-ads-ops": "PPC campaigns. Spend = Tier 2.",
    "bookkeeper-ledger": "Invoices, receipts, books. Pay/wire = Tier 3.",
    "seo-aeo-geo": "GSC, GMB, knowledge panel, AEO/GEO.",
    "funnel-builder": "Offers, landing pages, CRO.",
    "calendar-ops": "Holds and scheduling. Invite send = Tier 2.",
    "social-posting": "Schedule posts and reply to comments.",
    "llm-compare": "Bake-off models; write scorecard.",
    "cockpit-hud": "CEO cockpit HUD — gauges, marquee, live tiles.",
  };

  function ExplainBox(text, tone) {
    if (!text) return null;
    return React.createElement(
      "div",
      { className: "clawsum-explain tone-" + (tone || "teal") },
      text
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
    var viewState = useState("cells");
    var view = viewState[0];
    var setView = viewState[1];
    if (auth.loading) return React.createElement("div", { className: "muted" }, "Loading agents…");
    if (!auth.ok && !(auth.agents && auth.agents.length)) {
      return React.createElement("div", { className: "clawsum-card" },
        React.createElement("p", null, "Authority matrix not loaded."),
        React.createElement("p", { className: "muted" }, auth.error || "Missing authority.json"));
    }
    var agents = auth.agents || [];
    var active = null;
    for (var i = 0; i < agents.length; i++) {
      if (agents[i].id === selected) { active = agents[i]; break; }
    }
    if (!active && agents.length) active = agents[0];
    var cells = {};
    agents.forEach(function (a) {
      (a.cells || []).forEach(function (cell) {
        if (!cells[cell]) cells[cell] = [];
        cells[cell].push(a);
      });
    });
    return React.createElement("div", { className: "clawsum-panel-wrap is-tight" },
      React.createElement("div", { className: "clawsum-title-row" },
        React.createElement("div", null,
          React.createElement("h1", null, "Team"),
          React.createElement("div", { className: "muted" }, agents.length + " core agents · organized by operating cell")
        ),
        React.createElement("div", { className: "clawsum-view-toggle" },
          React.createElement("button", {
            type: "button", className: view === "cells" ? "active" : "",
            onClick: function () { setView("cells"); },
          }, "Cell map"),
          React.createElement("button", {
            type: "button", className: view === "details" ? "active" : "",
            onClick: function () { setView("details"); },
          }, "Details")
        )
      ),
      view === "cells" ? React.createElement("div", { className: "clawsum-cell-map" },
        Object.keys(cells).sort(function (a, b) {
          if (a === "clawsum-platform") return -1;
          if (b === "clawsum-platform") return 1;
          if (a === "*") return 1;
          if (b === "*") return -1;
          return a.localeCompare(b);
        }).map(function (cell) {
          return React.createElement("section", { className: "clawsum-cell-card", key: cell },
            React.createElement("div", { className: "clawsum-cell-head" },
              React.createElement("strong", null, cell === "*" ? "Cross-cell / read-only" : cell),
              React.createElement("span", null, cells[cell].length + " agents")
            ),
            React.createElement("div", { className: "clawsum-agent-nodes" },
              cells[cell].map(function (a) {
                var tones = ["cyan", "violet", "amber", "lime", "rose", "orange", "teal", "sky", "gold", "pink", "indigo", "mint"];
                var ti = cells[cell].indexOf(a);
                return React.createElement("button", {
                  type: "button", key: a.id,
                  className: "clawsum-agent-node tone-" + tones[Math.max(ti, 0) % tones.length] + (selected === a.id ? " active" : ""),
                  onClick: function () { setSelected(a.id); setView("details"); },
                  title: a.domains || "",
                },
                  React.createElement("span", { className: "clawsum-agent-avatar" },
                    String(a.name || a.id).replace(/^Clawsum\s*/i, "").slice(0, 2).toUpperCase()),
                  React.createElement("span", null,
                    React.createElement("strong", null, a.name || a.id),
                    React.createElement("small", null, (a.skills || []).length + " skills")
                  )
                );
              })
            )
          );
        })
      ) : React.createElement("div", { className: "clawsum-split" },
        React.createElement("div", { className: "clawsum-list" },
          React.createElement("div", { className: "clawsum-list-title" }, "Agents (" + agents.length + ")"),
          agents.map(function (a) {
            return React.createElement("button", {
              key: a.id, type: "button",
              className: "clawsum-list-item" + (active && active.id === a.id ? " active" : ""),
              onClick: function () { setSelected(a.id); },
            },
              React.createElement("strong", null, a.name || a.id),
              React.createElement("span", { className: "muted" }, a.id + " · " + (a.skills || []).length + " skills")
            );
          })
        ),
        active ? React.createElement("div", { className: "clawsum-detail" },
          React.createElement("h2", null, active.name || active.id),
          React.createElement("p", { className: "muted" }, active.domains || ""),
          ExplainBox(active.blurb || AGENT_EXPLAIN[active.id] || "Specialist agent in the Clawsum org chart.", "violet"),
          React.createElement("div", { className: "clawsum-card" },
            React.createElement("strong", null, "What this agent is for"),
            React.createElement("p", { className: "muted", style: { marginTop: "0.4rem" } },
              active.blurb || AGENT_EXPLAIN[active.id] ||
                "Owns the domains above. Skills listed below are the only tools it may run without expanding authority.")
          ),
          React.createElement("div", { className: "clawsum-card" },
            React.createElement("strong", null, "Cells"),
            React.createElement("div", { className: "clawsum-chip-row" },
              (active.cells || []).map(function (c) { return Chip(c, c); }))
          ),
          React.createElement("div", { className: "clawsum-card" },
            React.createElement("strong", null, "Authorized skills"),
            (active.skills || []).length
              ? React.createElement("ul", { className: "clawsum-plain-list" },
                  (active.skills || []).map(function (s) {
                    return React.createElement("li", { key: s },
                      React.createElement("code", { className: "clawsum-skill-pill" }, s),
                      SKILL_EXPLAIN[s]
                        ? React.createElement("div", { className: "muted", style: { fontSize: "0.78rem", margin: "0.2rem 0 0.45rem" } }, SKILL_EXPLAIN[s])
                        : null);
                  }))
              : React.createElement("p", { className: "muted" }, "No skills mapped.")
          )
        ) : null
      )
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
    var viewState = useState("matrix");
    var view = viewState[0];
    var setView = viewState[1];
    var toolboxState = useState(false);
    var toolboxOpen = toolboxState[0];
    var setToolboxOpen = toolboxState[1];
    if (auth.loading) return React.createElement("div", { className: "muted" }, "Loading skills…");
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
    var allAgents = auth.agents || [];
    var primaryIds = auth.primary_skills || [
      "ceo-daily-brief", "overwatch-approvals", "gmail-inbox-review",
      "paperclip-task-routing", "hermes-proactive-drive", "research-brief", "credential-hygiene",
    ];
    var primarySet = {};
    primaryIds.forEach(function (id) { primarySet[id] = true; });
    var primarySkills = skills.filter(function (s) { return primarySet[s.id]; });
    var toolboxSkills = skills.filter(function (s) { return !primarySet[s.id]; });

    function skillButton(s) {
      return React.createElement("button", {
        key: s.id, type: "button",
        className: "clawsum-list-item" + (active && active.id === s.id ? " active" : ""),
        onClick: function () { setSelected(s.id); },
      },
        React.createElement("strong", null, s.id),
        React.createElement("span", { className: "muted" }, "T" + s.tier + " · " + (s.agents || []).join(", "))
      );
    }

    return React.createElement("div", { className: "clawsum-panel-wrap clawsum-wide-panel" },
      React.createElement("div", { className: "clawsum-title-row" },
        React.createElement("div", null,
          React.createElement("h1", null, "Skill authority"),
          React.createElement("div", { className: "muted" }, skills.length + " skills · agent access and autonomous risk tier")
        ),
        React.createElement("div", { className: "clawsum-view-toggle" },
          React.createElement("button", {
            type: "button", className: view === "matrix" ? "active" : "",
            onClick: function () { setView("matrix"); },
          }, "Heatmap"),
          React.createElement("button", {
            type: "button", className: view === "details" ? "active" : "",
            onClick: function () { setView("details"); },
          }, "Details")
        )
      ),
      view === "matrix" ? React.createElement("div", null,
        React.createElement("div", { className: "clawsum-tier-legend" },
          React.createElement("span", { className: "tier-0" }, "T0 Read"),
          React.createElement("span", { className: "tier-1" }, "T1 Draft/write"),
          React.createElement("span", { className: "tier-2" }, "T2 Boss approval"),
          React.createElement("span", { className: "tier-3" }, "T3 Human only")
        ),
        React.createElement("div", { className: "clawsum-matrix-wrap" },
          React.createElement("table", { className: "clawsum-authority-matrix" },
            React.createElement("thead", null,
              React.createElement("tr", null,
                React.createElement("th", null, "Skill"),
                React.createElement("th", null, "Tier"),
                allAgents.map(function (a) {
                  return React.createElement("th", { key: a.id, title: a.name || a.id },
                    React.createElement("span", null, a.id));
                })
              )
            ),
            React.createElement("tbody", null,
              skills.map(function (s) {
                var allowed = s.agents || [];
                return React.createElement("tr", {
                  key: s.id, onClick: function () { setSelected(s.id); setView("details"); },
                },
                  React.createElement("th", null,
                    (primarySet[s.id] ? "★ " : "") + s.id),
                  React.createElement("td", null,
                    React.createElement("span", { className: "clawsum-tier-dot tier-" + s.tier }, "T" + s.tier)),
                  allAgents.map(function (a) {
                    var on = allowed.indexOf(a.id) >= 0;
                    return React.createElement("td", {
                      key: a.id, className: on ? "allowed tier-bg-" + s.tier : "not-allowed",
                      title: on ? (a.name + " may run " + s.id) : "Not authorized",
                    }, on ? "●" : "·");
                  })
                );
              })
            )
          )
        )
      ) : React.createElement("div", { className: "clawsum-split" },
        React.createElement("div", { className: "clawsum-list" },
          React.createElement("div", { className: "clawsum-list-title" }, "Primary (" + primarySkills.length + ")"),
          React.createElement("input", {
            className: "clawsum-search", placeholder: "Filter skills…", value: q,
            onChange: function (e) { setQ(e.target.value); },
          }),
          primarySkills.map(skillButton),
          React.createElement("button", {
            type: "button",
            className: "clawsum-list-item",
            onClick: function () { setToolboxOpen(!toolboxOpen); },
            style: { marginTop: "0.4rem" },
          },
            React.createElement("strong", null, (toolboxOpen ? "▾ " : "▸ ") + "Toolbox"),
            React.createElement("span", { className: "muted" }, toolboxSkills.length + " more skills")
          ),
          toolboxOpen ? toolboxSkills.map(skillButton) : null
        ),
        active ? React.createElement("div", { className: "clawsum-detail" },
          React.createElement("h2", null, React.createElement("code", null, active.id)),
          React.createElement("p", { className: "muted" },
            "Auto ≤ Tier " + active.tier +
              (tiers[String(active.tier)] ? " — " + tiers[String(active.tier)] : "") +
              (primarySet[active.id] ? " · Primary" : " · Toolbox")),
          ExplainBox(
            active.blurb || SKILL_EXPLAIN[active.id] ||
              "Skill in the authority matrix. Tier gates what can run without Boss approval.",
            primarySet[active.id] ? "amber" : "sky"
          ),
          React.createElement("div", { className: "clawsum-card" },
            React.createElement("strong", null, "How to use it"),
            React.createElement("p", { className: "muted", style: { marginTop: "0.4rem" } },
              "Ask Clawsum Agent or the owning agent to run this skill. Higher tiers stop at draft/approval. " +
              "Primary skills stay visible; Toolbox skills are still authorized when listed.")
          ),
          React.createElement("div", { className: "clawsum-card" },
            React.createElement("strong", null, "Agents authorized"),
            React.createElement("div", { className: "clawsum-chip-row" },
              (active.agents || []).map(function (a) { return Chip(a, a); }))
          ),
          React.createElement("div", { className: "clawsum-card" },
            React.createElement("strong", null, "Cells"),
            React.createElement("div", { className: "clawsum-chip-row" },
              (active.cells || []).map(function (c) { return Chip(c, c); }))
          ),
          React.createElement("div", { className: "clawsum-card" },
            React.createElement("strong", null, "Credential prefixes"),
            React.createElement("div", { className: "clawsum-chip-row" },
              (active.credentials || []).length
                ? (active.credentials || []).map(function (c) { return Chip(c, c); })
                : React.createElement("span", { className: "muted" }, "—"))
          )
        ) : null
      )
    );
  }

  function InboxPanel() {
    var state = useState({ loading: true, items: [], offset: 0, view: "all" });
    var data = state[0];
    var setData = state[1];
    var openState = useState({});
    var openMap = openState[0];
    var setOpenMap = openState[1];
    var taskOpenState = useState({});
    var taskOpen = taskOpenState[0];
    var setTaskOpen = taskOpenState[1];

    function load(view, offset, append) {
      var q = "?limit=200&offset=" + (offset || 0) + "&view=" + encodeURIComponent(view || "all");
      setData(function (prev) {
        return Object.assign({}, prev, { loading: !append, error: null });
      });
      fetchJSON(API + "/inbox" + q)
        .then(function (j) {
          setData(function (prev) {
            var prevItems = append ? (prev.items || prev.email_analyses || []) : [];
            var nextItems = (j.email_analyses || []).slice();
            var merged = append ? prevItems.concat(nextItems) : nextItems;
            return Object.assign({ loading: false }, j, {
              items: merged,
              email_analyses: merged,
              offset: (offset || 0) + nextItems.length,
              view: view || "all",
            });
          });
        })
        .catch(function (e) {
          setData({ loading: false, ok: false, error: String(e), items: [], action_items: [] });
        });
    }

    useEffect(function () {
      load("all", 0, false);
    }, []);

    function toggle(id) {
      setOpenMap(function (m) {
        var next = Object.assign({}, m);
        next[id] = !next[id];
        return next;
      });
    }
    function toggleTask(id) {
      setTaskOpen(function (m) {
        var next = Object.assign({}, m);
        next[id] = !next[id];
        return next;
      });
    }

    if (data.loading && !(data.items && data.items.length)) {
      return React.createElement("div", { className: "muted" }, "Loading inbox…");
    }
    if (!data.ok && data.error) {
      return React.createElement("div", { className: "clawsum-panel-wrap is-tight" },
        React.createElement("h1", null, "Inbox"),
        React.createElement("div", { className: "clawsum-card" },
          React.createElement("p", null, "Inbox not ready."),
          React.createElement("p", { className: "muted" }, data.hint || data.error)));
    }

    var analyses = data.items || data.email_analyses || [];
    var questions = data.questions_for_boss || [];
    var tasks = data.open_tasks || [];
    var needsBoss = (data.by_review && data.by_review.needs_boss) || 0;
    var views = [
      { id: "all", label: "All analyzed" },
      { id: "needs_boss", label: "Needs Boss" },
      { id: "action", label: "Action" },
      { id: "inbox", label: "Inbox flag" },
    ];

    return React.createElement("div", { className: "clawsum-panel-wrap is-tight" },
      React.createElement("h1", null, "Inbox"),
      React.createElement("div", { className: "muted clawsum-main-sub" },
        (data.mailbox || "clawsums@gmail.com") +
          " · showing " + analyses.length + " of " + (data.match_total != null ? data.match_total : "?") +
          " · mailbox total " + (data.inbox_total != null ? data.inbox_total : "—")),
      React.createElement("div", { className: "clawsum-grid" },
        React.createElement("div", { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Needs Boss (all)"),
          React.createElement("div", { className: "clawsum-kpi" }, String(needsBoss))),
        React.createElement("div", { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Reviews stored"),
          React.createElement("div", { className: "clawsum-kpi" }, String(data.reviews_stored || 0))),
        React.createElement("div", { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Open tasks"),
          React.createElement("div", { className: "clawsum-kpi" }, String(tasks.length))),
        React.createElement("div", { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Active reminders"),
          React.createElement("div", { className: "clawsum-kpi" }, String(data.reminders_active || 0)))
      ),
      React.createElement("div", { className: "clawsum-link-row", style: { marginBottom: "0.75rem" } },
        views.map(function (v) {
          return React.createElement("button", {
            key: v.id,
            type: "button",
            className: "clawsum-text-btn" + (data.view === v.id ? " active" : ""),
            onClick: function () { load(v.id, 0, false); },
          }, v.label);
        })
      ),
      React.createElement(AskBossReply, { questions: questions }),
      React.createElement("div", { className: "clawsum-card" },
        React.createElement("strong", null, "Emails — expand for full body + narrative"),
        analyses.length
          ? React.createElement("div", null, analyses.map(function (item, i) {
              var key = String(item.gmail_id || item.id || i);
              var open = !!openMap[key];
              var aj = item.analysis_json || {};
              var value = aj.take || aj.value_assessment || aj.value || null;
              var fit = aj.project_fit || null;
              var vsHave = aj.vs_what_we_have || null;
              var imgNotes = aj.image_notes || null;
              var suggestions = aj.suggested_actions || aj.suggestions || aj.actions || [];
              var research = aj.research_notes || aj.repo_notes || aj.research || null;
              var body = item.body_text || item.snippet || "";
              var report = item.analysis_report || item.review_report || "";
              return React.createElement("div", {
                key: key,
                className: "clawsum-expand-item",
                style: { borderTop: i ? "1px solid rgba(45,212,191,0.2)" : "none", paddingTop: 10, marginTop: 10 },
              },
                React.createElement("button", {
                  type: "button",
                  className: "clawsum-expand-toggle",
                  onClick: function () { toggle(key); },
                  style: {
                    display: "block", width: "100%", textAlign: "left", background: "transparent",
                    border: "none", color: "inherit", cursor: "pointer", padding: 0, font: "inherit",
                  },
                },
                  React.createElement("div", { style: { fontWeight: 650 } },
                    (open ? "▾ " : "▸ ") +
                      "[" + (item.analysis_priority || item.review_priority || item.review_status || "?") + "] " +
                      (item.subject || "(no subject)")),
                  React.createElement("div", { className: "muted", style: { fontSize: "0.8rem" } },
                    (item.from_addr || "") + " · " + (item.business_slug || "—") +
                      (aj.owner_agent ? " · " + aj.owner_agent : "") +
                      (aj.adopt_verdict ? " · " + aj.adopt_verdict : "") +
                      (item.person_name ? " · " + item.person_name : "") +
                      (item.received_at ? " · " + String(item.received_at).slice(0, 16) : ""))
                ),
                React.createElement("p", { style: { margin: "0.35rem 0 0" } },
                  item.analysis_summary || item.analysis_intent || "No analysis yet"),
                item.analysis_recommendation
                  ? React.createElement("p", { className: "muted", style: { margin: "0.25rem 0 0" } },
                      "→ " + item.analysis_recommendation)
                  : null,
                open ? React.createElement("div", { className: "clawsum-expand-body", style: { marginTop: "0.75rem" } },
                  value
                    ? React.createElement("div", { className: "clawsum-card", style: { marginBottom: "0.5rem" } },
                        React.createElement("strong", null, "My take"),
                        React.createElement("p", { style: { margin: "0.4rem 0 0", whiteSpace: "pre-wrap" } }, String(value)))
                    : null,
                  fit
                    ? React.createElement("div", { className: "clawsum-card", style: { marginBottom: "0.5rem" } },
                        React.createElement("strong", null, "Does this apply"),
                        React.createElement("p", { style: { margin: "0.4rem 0 0", whiteSpace: "pre-wrap" } }, String(fit)))
                    : null,
                  vsHave
                    ? React.createElement("div", { className: "clawsum-card", style: { marginBottom: "0.5rem" } },
                        React.createElement("strong", null, "Compared to what we have"),
                        React.createElement("p", { style: { margin: "0.4rem 0 0", whiteSpace: "pre-wrap" } }, String(vsHave)))
                    : null,
                  imgNotes
                    ? React.createElement("div", { className: "clawsum-card", style: { marginBottom: "0.5rem" } },
                        React.createElement("strong", null, "Images"),
                        React.createElement("p", { style: { margin: "0.4rem 0 0", whiteSpace: "pre-wrap" } }, String(imgNotes)))
                    : null,
                  suggestions && suggestions.length
                    ? React.createElement("div", { className: "clawsum-card", style: { marginBottom: "0.5rem" } },
                        React.createElement("strong", null, "Suggested actions"),
                        React.createElement("ul", { style: { margin: "0.4rem 0 0", paddingLeft: "1.2rem" } },
                          suggestions.map(function (s, si) {
                            return React.createElement("li", { key: si }, typeof s === "string" ? s : JSON.stringify(s));
                          })))
                    : null,
                  research
                    ? React.createElement("div", { className: "clawsum-card", style: { marginBottom: "0.5rem" } },
                        React.createElement("strong", null, "Research"),
                        React.createElement("p", { style: { margin: "0.4rem 0 0", whiteSpace: "pre-wrap" } }, String(research)))
                    : null,
                  React.createElement("div", { className: "clawsum-card", style: { marginBottom: "0.5rem" } },
                    React.createElement("strong", null, "Original message"),
                    React.createElement("pre", {
                      style: {
                        margin: "0.5rem 0 0", whiteSpace: "pre-wrap", wordBreak: "break-word",
                        fontSize: "0.82rem", maxHeight: "28rem", overflow: "auto",
                        color: "#e8eef4", background: "rgba(0,0,0,0.25)", padding: "0.75rem",
                        borderRadius: "0.35rem",
                      },
                    }, body || "(no body text synced — HTML/attachments not stored yet)")),
                  report
                    ? React.createElement("div", { className: "clawsum-card" },
                        React.createElement("strong", null, "Full analysis narrative"),
                        React.createElement("pre", {
                          style: {
                            margin: "0.5rem 0 0", whiteSpace: "pre-wrap", wordBreak: "break-word",
                            fontSize: "0.82rem", maxHeight: "32rem", overflow: "auto",
                            color: "#e8eef4", background: "rgba(0,0,0,0.25)", padding: "0.75rem",
                            borderRadius: "0.35rem",
                          },
                        }, report))
                    : React.createElement("p", { className: "muted" },
                        "No deep narrative yet — run gmail-inbox-deep-review.py")
                ) : null
              );
            }))
          : React.createElement("p", { className: "muted" }, "No email analyses in this view."),
        data.has_more
          ? React.createElement("button", {
              type: "button",
              className: "clawsum-text-btn",
              style: { marginTop: "0.75rem" },
              onClick: function () { load(data.view || "all", data.offset || analyses.length, true); },
            }, "Load more (" + ((data.match_total || 0) - analyses.length) + " remaining)")
          : null
      ),
      React.createElement("div", { className: "clawsum-card" },
        React.createElement("strong", null, "Open tasks (from mail / CRM)"),
        tasks.length
          ? React.createElement("div", null, tasks.map(function (t, i) {
              var tid = String(t.id || i);
              var open = !!taskOpen[tid];
              return React.createElement("div", {
                key: tid,
                style: { borderTop: i ? "1px solid rgba(45,212,191,0.2)" : "none", paddingTop: 8, marginTop: 8 },
              },
                React.createElement("button", {
                  type: "button",
                  onClick: function () { toggleTask(tid); },
                  style: {
                    display: "block", width: "100%", textAlign: "left", background: "transparent",
                    border: "none", color: "inherit", cursor: "pointer", padding: 0, font: "inherit",
                  },
                },
                  React.createElement("div", { style: { fontWeight: 600 } },
                    (open ? "▾ " : "▸ ") + "[" + (t.priority || "?") + "] " + (t.title || "(untitled)")),
                  React.createElement("div", { className: "muted", style: { fontSize: "0.8rem" } },
                    (t.status || "") + " · " + (t.source || "—") + " · " + (t.business_slug || "—") +
                      (t.email_subject ? " · email: " + t.email_subject : ""))
                ),
                open ? React.createElement("pre", {
                  style: {
                    margin: "0.5rem 0 0", whiteSpace: "pre-wrap", wordBreak: "break-word",
                    fontSize: "0.82rem", color: "#e8eef4", background: "rgba(0,0,0,0.25)",
                    padding: "0.75rem", borderRadius: "0.35rem",
                  },
                }, t.description || "(no task description)") : null
              );
            }))
          : React.createElement("p", { className: "muted" }, "No open local tasks.")
      )
    );
  }

  function AskBossReply(props) {
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
    function send() {
      if (!reply.trim() || !selected) {
        setStatus("Pick a question and type a reply.");
        return;
      }
      setStatus("Sending…");
      var headers = { "Content-Type": "application/json" };
      var tok = typeof window !== "undefined" && window.__HERMES_SESSION_TOKEN__;
      if (tok) headers["X-Hermes-Session-Token"] = tok;
      fetch(API + "/inbox/reply", {
        method: "POST",
        credentials: "same-origin",
        headers: headers,
        body: JSON.stringify({ question: selected, reply: reply.trim() }),
      })
        .then(function (r) { return r.json(); })
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
    return React.createElement("div", { className: "clawsum-card clawsum-card-ask" },
      React.createElement("strong", null, "Ask Boss — reply here"),
      React.createElement("ul", { style: { margin: "0.5rem 0 0", paddingLeft: "1.2rem" } },
        (questions.length ? questions : ["Run deep review to queue questions."]).map(function (q, i) {
          return React.createElement("li", { key: i },
            React.createElement("button", {
              type: "button",
              className: "clawsum-text-btn" + (selected === q ? " active" : ""),
              onClick: function () { setSelected(q); },
            }, q));
        })),
      React.createElement("textarea", {
        className: "clawsum-ask-reply",
        rows: 3,
        placeholder: "Type your decision or answer…",
        value: reply,
        onChange: function (e) { setReply(e.target.value); },
      }),
      React.createElement("div", { className: "clawsum-link-row" },
        React.createElement("button", { type: "button", className: "clawsum-text-btn", onClick: send }, "Send reply")),
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
    var tones = ["cyan", "amber", "lime", "rose", "violet", "orange", "teal", "sky", "gold", "pink", "indigo"];
    return React.createElement(
      "div",
      { className: "clawsum-panel-wrap is-tight" },
      React.createElement("h1", null, "Cron — live Clawsum jobs"),
      React.createElement("p", { className: "muted" }, data.note || "Host crontab, not Hermes-internal scheduler."),
      jobs.length
        ? React.createElement(
            "div",
            { className: "clawsum-cron-list" },
            jobs.map(function (j, i) {
              return React.createElement(
                "a",
                {
                  key: j.id || j.name,
                  className: "clawsum-cron-row status-" + (j.status || "unknown") + " tone-" + tones[i % tones.length],
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

  function KanbanPanel() {
    var state = useState({ loading: true });
    var data = state[0];
    var setData = state[1];
    useEffect(function () {
      fetchJSON(API + "/kanban").then(function (j) {
        setData(Object.assign({ loading: false }, j || {}));
      }).catch(function (e) {
        setData({ loading: false, ok: false, error: String(e), columns: [] });
      });
    }, []);
    if (data.loading) return React.createElement("div", { className: "muted" }, "Loading Paperclip board…");
    var cols = data.columns || [];
    var boardHref = (data.links && (data.links.paperclip || data.links.boss)) || "https://paperclip.clawsum.com";
    return React.createElement(
      "div",
      { className: "clawsum-panel-wrap is-tight" },
      React.createElement("h1", null, "Kanban — live Paperclip"),
      React.createElement(
        "p",
        { className: "muted" },
        (data.total != null ? data.total + " open cards · " : "") +
          "Hermes kanban.db is unused. This is the real board."
      ),
      data.error
        ? React.createElement("p", { className: "muted" }, data.error)
        : null,
      React.createElement(
        "div",
        { className: "clawsum-kanban" },
        cols.map(function (col) {
          return React.createElement(
            "section",
            { key: col.id, className: "clawsum-kanban-col tone-" + (col.tone || "teal") },
            React.createElement(
              "header",
              null,
              React.createElement("strong", null, col.label),
              React.createElement("span", { className: "clawsum-nav-count" }, String((col.cards || []).length))
            ),
            (col.cards || []).length
              ? (col.cards || []).map(function (card, i) {
                  return React.createElement(
                    "a",
                    {
                      key: card.id || i,
                      className: "clawsum-kanban-card tone-" + (col.tone || "teal"),
                      href: card.href || boardHref,
                      target: "_blank",
                      rel: "noreferrer",
                    },
                    React.createElement("strong", null, card.title || card.id),
                    React.createElement("span", { className: "muted" }, card.assignee || card.status || "")
                  );
                })
              : React.createElement("p", { className: "muted" }, "Empty column")
          );
        })
      ),
      React.createElement("a", { href: boardHref, target: "_blank", rel: "noreferrer" }, "Open Paperclip →")
    );
  }

  function rebrandDom() {
    if (typeof document === "undefined") return;
    document.title = (document.title || "").replace(/Hermes Agent/gi, "Clawsum").replace(/Hermes/gi, "Clawsum");
    var walk = function (node) {
      if (!node) return;
      if (node.nodeType === 3) {
        var v = node.nodeValue;
        if (v && /Hermes/i.test(v)) {
          node.nodeValue = v.replace(/Hermes Agent/gi, "Clawsum").replace(/Hermes/gi, "Clawsum");
        }
        return;
      }
      if (node.nodeType === 1) {
        var tag = (node.tagName || "").toLowerCase();
        if (tag === "script" || tag === "style") return;
        for (var i = 0; i < node.childNodes.length; i++) walk(node.childNodes[i]);
      }
    };
    walk(document.body);
  }

  window.__CLAWSUM_PANELS__ = {
    AgentsPanel: AgentsPanel,
    SkillsPanel: SkillsPanel,
    InboxPanel: InboxPanel,
    CronPanel: CronPanel,
    KanbanPanel: KanbanPanel,
    useAuthority: useAuthority,
    rebrandDom: rebrandDom,
    API: API,
  };
})();
