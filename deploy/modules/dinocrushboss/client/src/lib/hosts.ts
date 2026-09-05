/** Host split: promo dinocrushboss.com · login.dinocrushboss.com · game.dinocrushboss.com */

export type PublicUrls = {
  loginUrl: string;
  gameUrl: string;
  promoUrl: string;
};

const DEFAULTS: PublicUrls = {
  loginUrl: "/login",
  gameUrl: "/",
  promoUrl: "https://dinocrushboss.com",
};

export function loginSurface(): boolean {
  const host = window.location.hostname;
  if (host.startsWith("login.")) return true;
  const path = window.location.pathname.replace(/\/$/, "") || "/";
  return path === "/login";
}

export function gameSurface(): boolean {
  return !loginSurface();
}

export async function loadPublicUrls(): Promise<PublicUrls> {
  try {
    const res = await fetch("/api/config", { credentials: "include" });
    if (!res.ok) return DEFAULTS;
    const data = (await res.json()) as Partial<PublicUrls>;
    return {
      loginUrl: data.loginUrl || DEFAULTS.loginUrl,
      gameUrl: data.gameUrl || DEFAULTS.gameUrl,
      promoUrl: data.promoUrl || DEFAULTS.promoUrl,
    };
  } catch {
    return DEFAULTS;
  }
}

export function go(url: string): void {
  if (!url || url === window.location.href) return;
  window.location.href = url;
}

export function withGuest(url: string): string {
  try {
    const u = new URL(url, window.location.origin);
    u.searchParams.set("guest", "1");
    return u.href;
  } catch {
    return `${url}${url.includes("?") ? "&" : "?"}guest=1`;
  }
}
