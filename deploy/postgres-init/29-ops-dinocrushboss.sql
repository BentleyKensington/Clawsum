-- DinoCrushBoss player accounts (dinocrushboss.com).
-- Apply: psql -U clawsum -d clawsum -f postgres-init/29-ops-dinocrushboss.sql
-- Isolated schema so game users never collide with Clawsum ops/public tables.
CREATE SCHEMA IF NOT EXISTS dinocrush;

CREATE TABLE IF NOT EXISTS dinocrush.users (
  id SERIAL PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dinocrush.game_progress (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES dinocrush.users(id) ON DELETE CASCADE,
  current_level INTEGER NOT NULL DEFAULT 1,
  highest_level INTEGER NOT NULL DEFAULT 1,
  total_score INTEGER NOT NULL DEFAULT 0,
  total_stars INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS dinocrush.level_scores (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES dinocrush.users(id) ON DELETE CASCADE,
  level INTEGER NOT NULL,
  high_score INTEGER NOT NULL DEFAULT 0,
  stars INTEGER NOT NULL DEFAULT 0,
  completed BOOLEAN NOT NULL DEFAULT false,
  UNIQUE (user_id, level)
);

CREATE INDEX IF NOT EXISTS idx_dinocrush_progress_user ON dinocrush.game_progress (user_id);
CREATE INDEX IF NOT EXISTS idx_dinocrush_scores_user ON dinocrush.level_scores (user_id, level);

COMMENT ON SCHEMA dinocrush IS 'DinoCrushBoss game accounts + progress. Kid lane. No commerce.';
COMMENT ON TABLE dinocrush.users IS 'Play accounts (username only — no email). Guest play does not write here.';

-- Telemetry app row lives in ops (26-ops-dinocrush.sql).
DO $$
BEGIN
  IF to_regclass('ops.game_apps') IS NULL THEN
    RETURN;
  END IF;

  IF to_regclass('ops.game_versions') IS NOT NULL THEN
    INSERT INTO ops.game_versions (app_id, version, channel, notes, released_at)
    SELECT a.id, '1.0.0', 'dev', 'Vendored from github.com/aaaredrover/DinoCrush2 as DinoCrushBoss', now()
    FROM ops.game_apps a
    WHERE a.slug = 'dinocrush'
      AND NOT EXISTS (
        SELECT 1 FROM ops.game_versions v
        WHERE v.app_id = a.id AND v.version = '1.0.0' AND v.channel = 'dev'
      );
  END IF;

  IF to_regclass('ops.game_dev_items') IS NOT NULL THEN
    UPDATE ops.game_dev_items d
  SET status = 'shipped',
      notes = CASE
        WHEN d.notes IS NULL OR d.notes = '' THEN 'DinoCrush2 vendored to modules/dinocrushboss (2026-09-04).'
        WHEN d.notes LIKE '%modules/dinocrushboss%' THEN d.notes
        ELSE d.notes || ' — DinoCrush2 vendored to modules/dinocrushboss (2026-09-04).'
      END,
      updated_at = now()
  FROM ops.game_apps a
  WHERE d.app_id = a.id
    AND a.slug = 'dinocrush'
    AND d.title IN (
      'First playable slice (one screen, one action, one reward)',
      'Public site dinocrushboss.com (download / play / support)'
    )
    AND d.status <> 'shipped';
  END IF;
END $$;
