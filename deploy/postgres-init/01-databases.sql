-- Separate databases for GHL and Real Estate (isolated data planes)
-- Other domains use the default 'clawsum' database with per-domain schemas.

CREATE DATABASE realestate;
CREATE DATABASE ghl;

-- Grants for app user (created by POSTGRES_USER in compose)
GRANT ALL PRIVILEGES ON DATABASE realestate TO clawsum;
GRANT ALL PRIVILEGES ON DATABASE ghl TO clawsum;
