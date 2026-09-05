import pg from "pg";
import { drizzle } from "drizzle-orm/node-postgres";
import * as schema from "../shared/schema";

const { Pool } = pg;

function databaseUrl(): string {
  if (process.env.DATABASE_URL?.trim()) {
    return process.env.DATABASE_URL.trim();
  }
  const user = process.env.POSTGRES_USER || "clawsum";
  const pass = encodeURIComponent(process.env.POSTGRES_PASSWORD || "");
  const host = process.env.POSTGRES_HOST || "127.0.0.1";
  const port = process.env.POSTGRES_PORT || "5432";
  const dbname = process.env.POSTGRES_DB || "clawsum";
  return `postgresql://${user}:${pass}@${host}:${port}/${dbname}`;
}

const url = databaseUrl();
if (!url.includes("@")) {
  throw new Error("DATABASE_URL or POSTGRES_* must be set");
}

export const pool = new Pool({
  connectionString: url,
  max: 8,
});

export const db = drizzle(pool, { schema });
