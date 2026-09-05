import { pgSchema, text, serial, integer, boolean, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

/** Isolated from Clawsum public/ops tables. Applied by postgres-init/29-ops-dinocrushboss.sql */
export const dinocrushSchema = pgSchema("dinocrush");

export const users = dinocrushSchema.table("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

/** Extra emails that open the same save (play@dinocrushboss.com, typo aliases). */
export const userAliases = dinocrushSchema.table("user_aliases", {
  alias: text("alias").primaryKey(),
  userId: integer("user_id")
    .notNull()
    .references(() => users.id),
});

export const gameProgress = dinocrushSchema.table("game_progress", {
  id: serial("id").primaryKey(),
  userId: integer("user_id")
    .notNull()
    .references(() => users.id),
  currentLevel: integer("current_level").default(1).notNull(),
  highestLevel: integer("highest_level").default(1).notNull(),
  totalScore: integer("total_score").default(0).notNull(),
  totalStars: integer("total_stars").default(0).notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const levelScores = dinocrushSchema.table("level_scores", {
  id: serial("id").primaryKey(),
  userId: integer("user_id")
    .notNull()
    .references(() => users.id),
  level: integer("level").notNull(),
  highScore: integer("high_score").default(0).notNull(),
  stars: integer("stars").default(0).notNull(),
  completed: boolean("completed").default(false).notNull(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
export type GameProgress = typeof gameProgress.$inferSelect;
export type LevelScore = typeof levelScores.$inferSelect;
