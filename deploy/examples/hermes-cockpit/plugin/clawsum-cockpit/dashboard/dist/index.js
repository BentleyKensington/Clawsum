/**
 * Clawsum CEO Cockpit — Hermes dashboard plugin
 *
 * - Visible tab /clawsum: Brief | Inbox | Archive | Approvals | Health
 * - Slots: sidebar HUD, header crest, footer tagline
 * - Data: /api/plugins/clawsum-cockpit/{brief,inbox,archive,approvals,links,crm}
 */
(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  var PLUGINS = window.__HERMES_PLUGINS__;
  if (!SDK || !PLUGINS) return;

  var React = SDK.React;
  var useState = SDK.hooks.useState;
  var useEffect = SDK.hooks.useEffect;
  var fetchJSON = SDK.fetchJSON || function (url) {
    return fetch(url).then(function (r) { return r.json(); });
  };

  var API = "/api/plugins/clawsum-cockpit";
  var NAME = "clawsum-cockpit";

  function cssVar(name) {
    if (typeof document === "undefined") return "";
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function asBg(value) {
    if (!value) return "";
    if (value.indexOf("url(") === 0) return value;
    return "url(\"" + value + "\")";
  }

  function LinkButtons(links) {
    if (!links) return null;
    var items = [
      { href: links.boss, label: "Boss UI" },
      { href: links.openclaw, label: "OpenClaw" },
      { href: links.grafana, label: "Grafana" },
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

  function BriefPanel() {
    var state = useState({ loading: true });
    var data = state[0];
    var setData = state[1];
    useEffect(function () {
      var cancel = false;
      fetchJSON(API + "/brief")
        .then(function (j) { if (!cancel) setData(Object.assign({ loading: false }, j)); })
        .catch(function (e) {
          if (!cancel) setData({ loading: false, ok: false, error: String(e), priorities: [] });
        });
      return function () { cancel = true; };
    }, []);

    if (data.loading) {
      return React.createElement("div", { className: "muted" }, "Loading brief…");
    }

    var priorities = data.priorities || [];
    return React.createElement(
      "div",
      null,
      React.createElement(
        "div",
        { className: "clawsum-grid" },
        React.createElement(
          "div",
          { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Pending approvals"),
          React.createElement("div", { className: "clawsum-kpi" }, String(data.pending_approvals || 0))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Business cells"),
          React.createElement("div", { className: "clawsum-kpi" }, String(data.business_cells || 0))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Data source"),
          React.createElement("div", null, data.source || (data.ok ? "ok" : "error"))
        )
      ),
      React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("strong", null, "Priorities"),
        React.createElement(
          "ul",
          { style: { margin: "0.5rem 0 0", paddingLeft: "1.2rem" } },
          priorities.map(function (p, i) {
            return React.createElement("li", { key: i }, p);
          })
        ),
        data.warning
          ? React.createElement("p", { className: "muted" }, data.warning)
          : null,
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
    useEffect(function () {
      var cancel = false;
      fetchJSON(API + "/archive")
        .then(function (j) { if (!cancel) setData(Object.assign({ loading: false }, j)); })
        .catch(function (e) {
          if (!cancel) setData({ loading: false, ok: false, error: String(e), drive_forward: [] });
        });
      return function () { cancel = true; };
    }, []);

    if (data.loading) {
      return React.createElement("div", { className: "muted" }, "Loading archive brief…");
    }
    if (!data.ok && data.error) {
      return React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("p", null, "Archive not ready."),
        React.createElement("p", { className: "muted" }, data.hint || data.error)
      );
    }
    var drive = data.drive_forward || [];
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
          React.createElement("div", { className: "muted" }, "Personal (held private)"),
          React.createElement("div", { className: "clawsum-kpi" }, String(data.personal_conversations || 0))
        ),
        React.createElement(
          "div",
          { className: "clawsum-card" },
          React.createElement("div", { className: "muted" }, "Drive-forward"),
          React.createElement("div", { className: "clawsum-kpi" }, String(drive.length))
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

    var embed = data.links && (data.links.grafana_embed || data.links.grafana);
    return React.createElement(
      "div",
      null,
      React.createElement(
        "div",
        { className: "clawsum-card" },
        React.createElement("strong", null, "Server health"),
        React.createElement(
          "p",
          { className: "muted" },
          "Grafana embed below (set CLAWSUM_GRAFANA_EMBED_URL to a kiosk dashboard). If the frame is blank, open Grafana in a new tab — Traefik auth / X-Frame may block embeds."
        ),
        LinkButtons(data.links)
      ),
      embed
        ? React.createElement("iframe", {
            className: "clawsum-iframe",
            title: "Grafana",
            src: embed,
            referrerPolicy: "no-referrer",
          })
        : React.createElement("div", { className: "muted" }, "Grafana URL not configured.")
    );
  }

  function CockpitPage() {
    var tabState = useState("brief");
    var tab = tabState[0];
    var setTab = tabState[1];
    var tabs = [
      { id: "brief", label: "CEO Brief" },
      { id: "inbox", label: "Inbox" },
      { id: "archive", label: "Archive" },
      { id: "approvals", label: "Approvals" },
      { id: "health", label: "Health" },
    ];
    return React.createElement(
      "div",
      { className: "clawsum-cockpit-root" },
      React.createElement("h1", null, "Clawsum Command"),
      React.createElement(
        "div",
        { className: "muted" },
        "JARVIS face · Paperclip manages · OpenClaw acts · Gerald approves"
      ),
      React.createElement(
        "div",
        { className: "clawsum-tabs" },
        tabs.map(function (t) {
          return React.createElement(
            "button",
            {
              key: t.id,
              type: "button",
              className: tab === t.id ? "active" : "",
              onClick: function () { setTab(t.id); },
            },
            t.label
          );
        })
      ),
      tab === "brief" ? React.createElement(BriefPanel) : null,
      tab === "inbox" ? React.createElement(InboxPanel) : null,
      tab === "archive" ? React.createElement(ArchivePanel) : null,
      tab === "approvals" ? React.createElement(ApprovalsPanel) : null,
      tab === "health" ? React.createElement(HealthPanel) : null
    );
  }

  function SidebarSlot() {
    var state = useState(null);
    var brief = state[0];
    var setBrief = state[1];
    useEffect(function () {
      fetchJSON(API + "/brief")
        .then(setBrief)
        .catch(function () {});
    }, []);
    var hero = cssVar("--theme-asset-hero");
    var pending = brief && brief.pending_approvals != null ? brief.pending_approvals : "—";
    var cells = brief && brief.business_cells != null ? brief.business_cells : "—";
    return React.createElement(
      "div",
      { className: "clawsum-sidebar" },
      React.createElement(
        "div",
        { style: { borderBottom: "1px solid rgba(45,212,191,0.3)", paddingBottom: 8 } },
        React.createElement("div", { style: { opacity: 0.55 } }, "overwatch"),
        React.createElement("div", { style: { fontWeight: 700, fontSize: "0.85rem" } }, "Clawsum"),
        React.createElement("div", { style: { opacity: 0.55, fontSize: "0.6rem" } }, "CEO Command")
      ),
      hero
        ? React.createElement("div", {
            style: {
              width: "100%",
              aspectRatio: "3 / 4",
              backgroundImage: asBg(hero),
              backgroundSize: "contain",
              backgroundPosition: "center",
              backgroundRepeat: "no-repeat",
              opacity: 0.9,
            },
            "aria-hidden": true,
          })
        : null,
      React.createElement(
        "div",
        { className: "clawsum-card", style: { padding: "0.6rem" } },
        React.createElement("div", { style: { opacity: 0.55 } }, "Approvals"),
        React.createElement("div", { className: "clawsum-kpi", style: { fontSize: "1.2rem" } }, String(pending))
      ),
      React.createElement(
        "div",
        { className: "clawsum-card", style: { padding: "0.6rem" } },
        React.createElement("div", { style: { opacity: 0.55 } }, "Cells"),
        React.createElement("div", { className: "clawsum-kpi", style: { fontSize: "1.2rem" } }, String(cells))
      ),
      React.createElement(
        "a",
        {
          href: "/clawsum",
          style: { color: "#38bdf8", textAlign: "center", textDecoration: "none" },
        },
        "Open cockpit →"
      )
    );
  }

  function HeaderCrestSlot() {
    var crest = cssVar("--theme-asset-crest");
    var logo = cssVar("--theme-asset-logo");
    var src = crest || logo;
    var inner = src
      ? React.createElement("div", {
          style: {
            width: 28,
            height: 28,
            backgroundImage: asBg(src),
            backgroundSize: "contain",
            backgroundPosition: "center",
            backgroundRepeat: "no-repeat",
          },
          "aria-hidden": true,
        })
      : React.createElement(
          "span",
          { style: { fontWeight: 700, fontSize: "0.75rem", letterSpacing: "0.08em", color: "#2dd4bf" } },
          "CS"
        );
    return React.createElement(
      "div",
      {
        style: {
          display: "flex",
          alignItems: "center",
          gap: 8,
          paddingLeft: 12,
          paddingRight: 8,
        },
        title: "Clawsum Command",
      },
      inner,
      React.createElement(
        "span",
        {
          style: {
            fontFamily: "var(--theme-font-display, sans-serif)",
            fontSize: "0.7rem",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            opacity: 0.85,
          },
        },
        "Clawsum"
      )
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
      "Hermes talks · Paperclip manages · OpenClaw acts"
    );
  }

  PLUGINS.register(NAME, CockpitPage);
  if (PLUGINS.registerSlot) {
    PLUGINS.registerSlot(NAME, "sidebar", SidebarSlot);
    PLUGINS.registerSlot(NAME, "header-left", HeaderCrestSlot);
    PLUGINS.registerSlot(NAME, "footer-right", FooterTaglineSlot);
  }
})();
