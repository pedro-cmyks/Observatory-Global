-- Data lifecycle configuration table
CREATE TABLE IF NOT EXISTS data_lifecycle_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default configuration
INSERT INTO data_lifecycle_config (key, value, description) VALUES
    ('raw_retention_days', '90', 'Days to keep raw signals before deletion'),
    ('aggregate_retention_days', '730', 'Days to keep hourly aggregates (2 years)'),
    ('country_normalization_enabled', 'false', 'Normalize by source count in global view'),
    ('retention_policy_active', 'false', 'Whether retention deletion is active (SAFETY FLAG)')
ON CONFLICT (key) DO NOTHING;

-- Helper function to get config value
CREATE OR REPLACE FUNCTION get_lifecycle_config(config_key TEXT, default_value TEXT DEFAULT NULL)
RETURNS TEXT AS $$
BEGIN
    RETURN COALESCE(
        (SELECT value FROM data_lifecycle_config WHERE key = config_key),
        default_value
    );
END;
$$ LANGUAGE plpgsql;
