import { users, userAliases, gameProgress, levelScores, type User, type InsertUser, type GameProgress, type LevelScore } from "../shared/schema";
import { db } from "./db";
import { eq, and, sql } from "drizzle-orm";

export interface IStorage {
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  addAlias(userId: number, alias: string): Promise<void>;
  getGameProgress(userId: number): Promise<GameProgress | undefined>;
  createGameProgress(userId: number): Promise<GameProgress>;
  updateGameProgress(userId: number, data: Partial<GameProgress>): Promise<GameProgress | undefined>;
  getLevelScores(userId: number): Promise<LevelScore[]>;
  getLevelScore(userId: number, level: number): Promise<LevelScore | undefined>;
  saveLevelScore(userId: number, level: number, score: number, stars: number): Promise<LevelScore>;
}

function key(value: string): string {
  return value.trim().toLowerCase();
}

export class DatabaseStorage implements IStorage {
  async getUser(id: number): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const login = key(username);
    const [direct] = await db
      .select()
      .from(users)
      .where(sql`lower(${users.username}) = ${login}`);
    if (direct) return direct;
    const [aliased] = await db
      .select({ user: users })
      .from(userAliases)
      .innerJoin(users, eq(userAliases.userId, users.id))
      .where(sql`lower(${userAliases.alias}) = ${login}`);
    return aliased?.user;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const [user] = await db
      .insert(users)
      .values({ ...insertUser, username: key(insertUser.username) })
      .returning();
    return user;
  }

  async addAlias(userId: number, alias: string): Promise<void> {
    const a = key(alias);
    if (!a) return;
    await db.insert(userAliases).values({ alias: a, userId }).onConflictDoNothing();
  }

  async getGameProgress(userId: number): Promise<GameProgress | undefined> {
    const [progress] = await db.select().from(gameProgress).where(eq(gameProgress.userId, userId));
    return progress;
  }

  async createGameProgress(userId: number): Promise<GameProgress> {
    const existing = await this.getGameProgress(userId);
    if (existing) return existing;
    const [progress] = await db.insert(gameProgress).values({ userId }).returning();
    return progress;
  }

  async updateGameProgress(userId: number, data: Partial<GameProgress>): Promise<GameProgress | undefined> {
    const [progress] = await db
      .update(gameProgress)
      .set({ ...data, updatedAt: new Date() })
      .where(eq(gameProgress.userId, userId))
      .returning();
    return progress;
  }

  async getLevelScores(userId: number): Promise<LevelScore[]> {
    return db.select().from(levelScores).where(eq(levelScores.userId, userId));
  }

  async getLevelScore(userId: number, level: number): Promise<LevelScore | undefined> {
    const [score] = await db
      .select()
      .from(levelScores)
      .where(and(eq(levelScores.userId, userId), eq(levelScores.level, level)));
    return score;
  }

  async saveLevelScore(userId: number, level: number, score: number, stars: number): Promise<LevelScore> {
    const existing = await this.getLevelScore(userId, level);

    if (existing) {
      const [updated] = await db
        .update(levelScores)
        .set({
          highScore: Math.max(existing.highScore, score),
          stars: Math.max(existing.stars, stars),
          completed: true,
        })
        .where(and(eq(levelScores.userId, userId), eq(levelScores.level, level)))
        .returning();
      return updated;
    }
    const [newScore] = await db
      .insert(levelScores)
      .values({ userId, level, highScore: score, stars, completed: true })
      .returning();
    return newScore;
  }
}

export const storage = new DatabaseStorage();
