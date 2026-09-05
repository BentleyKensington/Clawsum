import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { recordError, recordSession, touchPlayer } from "./telemetry";
import bcrypt from "bcryptjs";
import session from "express-session";
import crypto from "crypto";

declare module "express-session" {
  interface SessionData {
    userId: number;
  }
}

const sessionSecret = process.env.SESSION_SECRET || crypto.randomBytes(32).toString("hex");
const isProduction = process.env.NODE_ENV === "production";
const cookieSecure =
  process.env.COOKIE_SECURE === "1"
    ? true
    : process.env.COOKIE_SECURE === "0"
      ? false
      : isProduction;
const cookieDomain = process.env.COOKIE_DOMAIN?.trim() || undefined;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function publicUrls() {
  const prod = process.env.NODE_ENV === "production";
  return {
    loginUrl: process.env.PUBLIC_LOGIN_URL || (prod ? "https://login.dinocrushboss.com" : "/login"),
    gameUrl: process.env.PUBLIC_GAME_URL || (prod ? "https://game.dinocrushboss.com" : "/"),
    promoUrl: process.env.PUBLIC_PROMO_URL || "https://dinocrushboss.com",
  };
}

function emailFrom(body: unknown): string | null {
  const rec = body && typeof body === "object" ? (body as Record<string, unknown>) : {};
  const raw = String(rec.email || rec.username || "").trim().toLowerCase();
  if (!EMAIL_RE.test(raw) || raw.length > 120) return null;
  return raw;
}

function publicUser(user: { id: number; username: string }) {
  return { id: user.id, email: user.username, username: user.username };
}

function platformOf(req: Request): string {
  const raw = String(req.headers["user-agent"] || "web");
  if (/android/i.test(raw)) return "android";
  if (/iphone|ipad|ipod/i.test(raw)) return "ios";
  return "web";
}

export async function registerRoutes(app: Express): Promise<Server> {
  app.use(
    session({
      name: "dinocrushboss.sid",
      secret: sessionSecret,
      resave: false,
      saveUninitialized: false,
      cookie: {
        secure: cookieSecure,
        httpOnly: true,
        sameSite: "lax",
        domain: cookieDomain,
        maxAge: 7 * 24 * 60 * 60 * 1000,
      },
    }),
  );

  app.get("/api/health", (_req: Request, res: Response) => {
    res.json({
      ok: true,
      service: "dinocrushboss",
      game: "Dino Crush",
      version: process.env.GAME_VERSION || "1.0.0",
    });
  });

  app.get("/api/config", (_req: Request, res: Response) => {
    res.json(publicUrls());
  });

  app.post("/api/auth/signup", async (req: Request, res: Response) => {
    try {
      const email = emailFrom(req.body);
      const { password } = req.body as { password?: string };

      if (!email) {
        return res.status(400).json({ error: "A real email is required to save progress" });
      }
      if (typeof password !== "string" || password.length < 6) {
        return res.status(400).json({ error: "Password must be at least 6 characters" });
      }

      const existingUser = await storage.getUserByUsername(email);
      if (existingUser) {
        return res.status(400).json({ error: "That email already has a save" });
      }

      const hashedPassword = await bcrypt.hash(password, 10);
      const user = await storage.createUser({ username: email, password: hashedPassword });

      await storage.createGameProgress(user.id);

      req.session.userId = user.id;
      void touchPlayer(`user:${user.id}`, email, platformOf(req));

      res.json({
        user: publicUser(user),
        message: "Save created",
      });
    } catch (error) {
      console.error("Signup error:", error);
      res.status(500).json({ error: "Failed to create account" });
    }
  });

  app.post("/api/auth/login", async (req: Request, res: Response) => {
    try {
      const email = emailFrom(req.body);
      const { password } = req.body as { password?: string };

      if (!email || typeof password !== "string") {
        return res.status(400).json({ error: "Email and password are required" });
      }

      const user = await storage.getUserByUsername(email);
      if (!user) {
        return res.status(401).json({ error: "Invalid email or password" });
      }

      const validPassword = await bcrypt.compare(password, user.password);
      if (!validPassword) {
        return res.status(401).json({ error: "Invalid email or password" });
      }

      req.session.userId = user.id;

      const progress = await storage.getGameProgress(user.id);
      const levelScores = await storage.getLevelScores(user.id);
      void touchPlayer(`user:${user.id}`, user.username, platformOf(req));

      res.json({
        user: publicUser(user),
        progress,
        levelScores,
        message: "Logged in successfully",
      });
    } catch (error) {
      console.error("Login error:", error);
      res.status(500).json({ error: "Failed to log in" });
    }
  });

  app.post("/api/auth/logout", (req: Request, res: Response) => {
    req.session.destroy((err) => {
      if (err) {
        return res.status(500).json({ error: "Failed to log out" });
      }
      res.json({ message: "Logged out successfully" });
    });
  });

  app.get("/api/auth/me", async (req: Request, res: Response) => {
    try {
      if (!req.session.userId) {
        return res.status(401).json({ error: "Not logged in" });
      }

      const user = await storage.getUser(req.session.userId);
      if (!user) {
        return res.status(401).json({ error: "User not found" });
      }

      const progress = await storage.getGameProgress(user.id);
      const levelScores = await storage.getLevelScores(user.id);

      res.json({
        user: publicUser(user),
        progress,
        levelScores,
      });
    } catch (error) {
      console.error("Get user error:", error);
      res.status(500).json({ error: "Failed to get user data" });
    }
  });

  app.post("/api/progress/save-level", async (req: Request, res: Response) => {
    try {
      if (!req.session.userId) {
        return res.status(401).json({ error: "Not logged in" });
      }

      const { level, score, stars } = req.body;

      if (typeof level !== "number" || typeof score !== "number" || typeof stars !== "number") {
        return res.status(400).json({ error: "Invalid data" });
      }

      const levelScore = await storage.saveLevelScore(req.session.userId, level, score, stars);

      const progress = await storage.getGameProgress(req.session.userId);
      if (progress && level >= progress.highestLevel) {
        await storage.updateGameProgress(req.session.userId, {
          highestLevel: level + 1,
          currentLevel: level + 1,
          totalScore: progress.totalScore + score,
          totalStars: progress.totalStars + stars,
        });
      } else if (progress) {
        await storage.updateGameProgress(req.session.userId, {
          totalScore: progress.totalScore + score,
        });
      }

      const user = await storage.getUser(req.session.userId);
      const remoteId = `user:${req.session.userId}`;
      if (user) {
        void touchPlayer(remoteId, user.username, platformOf(req));
      }
      void recordSession({
        remoteId,
        platform: platformOf(req),
        metadata: { level, score, stars, username: user?.username },
      });

      res.json({ levelScore, message: "Progress saved" });
    } catch (error) {
      console.error("Save progress error:", error);
      res.status(500).json({ error: "Failed to save progress" });
    }
  });

  app.get("/api/progress", async (req: Request, res: Response) => {
    try {
      if (!req.session.userId) {
        return res.status(401).json({ error: "Not logged in" });
      }

      const progress = await storage.getGameProgress(req.session.userId);
      const levelScores = await storage.getLevelScores(req.session.userId);

      res.json({ progress, levelScores });
    } catch (error) {
      console.error("Get progress error:", error);
      res.status(500).json({ error: "Failed to get progress" });
    }
  });

  app.post("/api/ingest/error", async (req: Request, res: Response) => {
    const message = String(req.body?.message || "error");
    const fingerprint = String(req.body?.fingerprint || message);
    void recordError({
      fingerprint,
      message,
      stack: req.body?.stack ? String(req.body.stack) : undefined,
      platform: String(req.body?.platform || platformOf(req)),
    });
    res.json({ ok: true });
  });

  const httpServer = createServer(app);

  return httpServer;
}
