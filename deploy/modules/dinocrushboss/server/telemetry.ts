import { pool } from "./db";

const APP_SLUG = "dinocrush";
const VERSION = process.env.GAME_VERSION || "1.0.0";

async function appId(): Promise<string | null> {
  try {
    const r = await pool.query("SELECT id FROM ops.game_apps WHERE slug = $1", [APP_SLUG]);
    return r.rows[0]?.id ?? null;
  } catch {
    return null;
  }
}

export async function touchPlayer(remoteId: string, displayName: string, platform: string): Promise<void> {
  const id = await appId();
  if (!id) return;
  try {
    await pool.query(
      `INSERT INTO ops.game_players (app_id, remote_id, display_name, platform, last_seen_at)
       VALUES ($1, $2, $3, $4, now())
       ON CONFLICT (app_id, remote_id) DO UPDATE
         SET display_name = EXCLUDED.display_name,
             last_seen_at = now()`,
      [id, remoteId, displayName, platform],
    );
  } catch (err) {
    console.error("telemetry touchPlayer", err);
  }
}

export async function recordSession(opts: {
  remoteId?: string;
  platform: string;
  durationS?: number;
  metadata: Record<string, unknown>;
}): Promise<void> {
  const id = await appId();
  if (!id) return;
  try {
    let playerId: string | null = null;
    if (opts.remoteId) {
      const p = await pool.query(
        `SELECT id FROM ops.game_players WHERE app_id = $1 AND remote_id = $2`,
        [id, opts.remoteId],
      );
      playerId = p.rows[0]?.id ?? null;
    }
    await pool.query(
      `INSERT INTO ops.game_sessions (app_id, player_id, version, platform, duration_s, metadata)
       VALUES ($1, $2, $3, $4, $5, $6::jsonb)`,
      [id, playerId, VERSION, opts.platform, opts.durationS ?? null, JSON.stringify(opts.metadata)],
    );
  } catch (err) {
    console.error("telemetry recordSession", err);
  }
}

export async function recordError(opts: {
  fingerprint: string;
  message: string;
  stack?: string;
  platform: string;
}): Promise<void> {
  const id = await appId();
  if (!id) return;
  try {
    await pool.query(
      `INSERT INTO ops.game_errors (app_id, version, platform, fingerprint, message, stack)
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT (app_id, fingerprint) DO UPDATE
         SET count = ops.game_errors.count + 1,
             last_seen_at = now(),
             message = EXCLUDED.message`,
      [id, VERSION, opts.platform, opts.fingerprint.slice(0, 200), opts.message.slice(0, 500), opts.stack ?? null],
    );
  } catch (err) {
    console.error("telemetry recordError", err);
  }
}
