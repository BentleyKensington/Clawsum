import { create } from "zustand";

interface User {
  id: number;
  email: string;
  username: string;
}

interface GameProgress {
  currentLevel: number;
  highestLevel: number;
  totalScore: number;
  totalStars: number;
}

interface LevelScore {
  level: number;
  highScore: number;
  stars: number;
  completed: boolean;
}

interface AuthState {
  user: User | null;
  isGuest: boolean;
  progress: GameProgress | null;
  levelScores: LevelScore[];
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  signup: (email: string, password: string) => Promise<boolean>;
  playAsGuest: () => void;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  saveLevelProgress: (level: number, score: number, stars: number) => Promise<void>;
  clearError: () => void;
}

const GUEST_KEY = "dinocrushboss.guest";
const GUEST_USER: User = { id: 0, email: "Guest", username: "guest" };
const EMPTY_PROGRESS: GameProgress = {
  currentLevel: 1,
  highestLevel: 1,
  totalScore: 0,
  totalStars: 0,
};

type GuestSave = {
  progress: GameProgress;
  levelScores: LevelScore[];
};

function asUser(data: { user?: { id: number; email?: string; username?: string } } | null): User | null {
  const u = data?.user;
  if (!u) return null;
  const email = u.email || u.username || "";
  return { id: u.id, email, username: email };
}

function readGuest(): GuestSave | null {
  try {
    const raw = localStorage.getItem(GUEST_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<GuestSave>;
    return {
      progress: parsed.progress || EMPTY_PROGRESS,
      levelScores: parsed.levelScores || [],
    };
  } catch {
    return null;
  }
}

function writeGuest(save: GuestSave): void {
  localStorage.setItem(GUEST_KEY, JSON.stringify(save));
}

function clearGuest(): void {
  localStorage.removeItem(GUEST_KEY);
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  isGuest: false,
  progress: null,
  levelScores: [],
  isLoading: true,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) {
        set({ error: data.error, isLoading: false });
        return false;
      }
      clearGuest();
      set({
        user: asUser(data),
        isGuest: false,
        progress: data.progress,
        levelScores: data.levelScores || [],
        isLoading: false,
      });
      return true;
    } catch {
      set({ error: "Failed to connect to server", isLoading: false });
      return false;
    }
  },

  signup: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch("/api/auth/signup", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) {
        set({ error: data.error, isLoading: false });
        return false;
      }
      clearGuest();
      set({
        user: asUser(data),
        isGuest: false,
        progress: { currentLevel: 1, highestLevel: 1, totalScore: 0, totalStars: 0 },
        levelScores: [],
        isLoading: false,
      });
      return true;
    } catch {
      set({ error: "Failed to connect to server", isLoading: false });
      return false;
    }
  },

  playAsGuest: () => {
    const existing = readGuest();
    const save = existing || { progress: EMPTY_PROGRESS, levelScores: [] };
    writeGuest(save);
    set({
      user: GUEST_USER,
      isGuest: true,
      progress: save.progress,
      levelScores: save.levelScores,
      isLoading: false,
      error: null,
    });
  },

  logout: async () => {
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    } catch (error) {
      console.error("Logout error:", error);
    }
    clearGuest();
    set({ user: null, isGuest: false, progress: null, levelScores: [] });
  },

  checkAuth: async () => {
    set({ isLoading: true });
    try {
      const response = await fetch("/api/auth/me", { credentials: "include" });
      if (response.ok) {
        const data = await response.json();
        clearGuest();
        set({
          user: asUser(data),
          isGuest: false,
          progress: data.progress,
          levelScores: data.levelScores || [],
          isLoading: false,
        });
        return;
      }
    } catch {
      /* fall through to guest */
    }
    const guest = readGuest();
    if (guest) {
      set({
        user: GUEST_USER,
        isGuest: true,
        progress: guest.progress,
        levelScores: guest.levelScores,
        isLoading: false,
      });
      return;
    }
    set({ user: null, isGuest: false, isLoading: false });
  },

  saveLevelProgress: async (level: number, score: number, stars: number) => {
    const { user, isGuest, progress, levelScores } = get();
    if (!user) return;

    const nextScores = (() => {
      const existingScore = levelScores.find((ls) => ls.level === level);
      if (existingScore) {
        return levelScores.map((ls) =>
          ls.level === level
            ? { ...ls, highScore: Math.max(ls.highScore, score), stars: Math.max(ls.stars, stars) }
            : ls,
        );
      }
      return [...levelScores, { level, highScore: score, stars, completed: true }];
    })();

    let nextProgress = progress;
    if (progress && level >= progress.highestLevel) {
      nextProgress = {
        ...progress,
        highestLevel: level + 1,
        currentLevel: level + 1,
        totalScore: progress.totalScore + score,
        totalStars: progress.totalStars + stars,
      };
    } else if (progress) {
      nextProgress = { ...progress, totalScore: progress.totalScore + score };
    }

    if (isGuest || user.id === 0) {
      const save = { progress: nextProgress || EMPTY_PROGRESS, levelScores: nextScores };
      writeGuest(save);
      set(save);
      return;
    }

    try {
      const response = await fetch("/api/progress/save-level", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level, score, stars }),
      });
      if (response.ok) {
        set({ levelScores: nextScores, progress: nextProgress });
      }
    } catch (error) {
      console.error("Failed to save progress:", error);
    }
  },

  clearError: () => set({ error: null }),
}));
