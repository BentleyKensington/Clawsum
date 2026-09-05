-- DinoCrushBoss login aliases (same save, extra emails).
-- Apply: psql -U clawsum -d clawsum -f postgres-init/30-ops-dinocrushboss-login.sql
CREATE SCHEMA IF NOT EXISTS dinocrush;

CREATE TABLE IF NOT EXISTS dinocrush.user_aliases (
  alias TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES dinocrush.users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dinocrush_aliases_user ON dinocrush.user_aliases (user_id);

COMMENT ON TABLE dinocrush.user_aliases IS 'Extra emails for one save. play@dinocrushboss.com and dincrushboss@gmail.com map to dinocrushboss@gmail.com.';
