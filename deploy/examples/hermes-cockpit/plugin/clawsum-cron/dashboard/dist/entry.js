/* register: Cron — replaces Hermes empty /cron */
(function () {
  "use strict";
  var SDK = window.__HERMES_PLUGIN_SDK__;
  var PLUGINS = window.__HERMES_PLUGINS__;
  var P = window.__CLAWSUM_PANELS__;
  if (!SDK || !PLUGINS || !P) return;
  var React = SDK.React;
  var useEffect = SDK.hooks.useEffect;
  function Page() {
    useEffect(function () { P.rebrandDom(); }, []);
    return React.createElement("div", { className: "clawsum-cockpit-root" }, React.createElement(P.CronPanel));
  }
  PLUGINS.register("clawsum-cron", Page);
})();
