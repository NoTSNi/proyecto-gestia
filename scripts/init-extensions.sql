-- GESTIA PostgreSQL Extensions Initialization
-- Runs automatically on container startup via docker-entrypoint-initdb.d

-- Vector embeddings (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Trigram search for fuzzy matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Full text search configuration for Spanish
-- CREATE EXTENSION IF NOT EXISTS pg_search; -- Optional, for advanced FTS

-- Create schemas if needed
-- CREATE SCHEMA IF NOT EXISTS gestia;
-- SET search_path TO gestia, public;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Grant permissions to gestia user
GRANT ALL ON SCHEMA public TO gestia;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gestia;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gestia;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO gestia;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO gestia;