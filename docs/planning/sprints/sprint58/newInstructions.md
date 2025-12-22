The two newly introduced tables, definition_groups and group_memberships, serve as a structured foundation for managing stock universes in your PostgreSQL database. The definition_groups table defines high-level categories such as ETFs, themes, sectors, segments, or custom groupings, storing essential attributes including name, type, metadata, liquidity filters, and environment-specific details to ensure data segregation across development stages. Complementing this, the group_memberships table establishes many-to-many relationships by linking individual stock symbols to these groups, optionally incorporating weights and additional metadata for refined analysis. Together, these tables enable efficient operations such as retrieving unique stock lists for data subscriptions, associating metadata during imports or displays, and aggregating transaction data by group, thereby enhancing reliability and query performance over the previous cache-based approach.


Instructions for Creating New Tables and Porting the Cache Maintenance Script
1. Creating the New Tables in the PostgreSQL Database
Execute the following SQL statements in your PostgreSQL database to create the two new tables. These statements include necessary constraints for data integrity and assume the use of a standard PostgreSQL setup. Run them sequentially in a database management tool such as pgAdmin or via a SQL client.
SQL-- Create the definition_groups table
CREATE TABLE IF NOT EXISTS public.definition_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('ETF', 'THEME', 'SECTOR', 'SEGMENT', 'CUSTOM')),
    description TEXT,
    metadata JSONB,
    liquidity_filter JSONB,
    environment VARCHAR(10) NOT NULL CHECK (environment IN ('DEFAULT', 'TEST', 'UAT', 'PROD')),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_update TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_group UNIQUE (name, type, environment)
);

-- Create the group_memberships table
CREATE TABLE IF NOT EXISTS public.group_memberships (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES public.definition_groups(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    weight NUMERIC(5,4),
    metadata JSONB,
    added_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_membership UNIQUE (group_id, symbol)
);
After execution, verify the tables by querying the system catalog (e.g., SELECT * FROM pg_tables WHERE tablename IN ('definition_groups', 'group_memberships');).
2. Porting the "scripts\cache_maintenance" Load to the New Tables
Adapt the existing scripts\cache_maintenance script (assumed to be a Python script or similar that loads data into the original cache_entries table) to populate the new definition_groups and group_memberships tables. Focus on the basic structural changes below; detailed implementation specifics (e.g., data sources, error handling) are available in the separate location.

Update Data Loading Logic:
Replace insertions into cache_entries with insertions into definition_groups for group-level data (e.g., ETFs, themes). Map fields such as type, name, environment, metadata, liquidity_filter, and timestamps accordingly.
For each group inserted into definition_groups, retrieve the generated id (e.g., via RETURNING id in SQL or cursor.lastrowid in Python).
Parse and insert stock memberships (previously in value JSONB) into group_memberships, linking via the group_id. Include symbol, optional weight, and metadata as applicable.

Basic Python Snippet Outline (assuming psycopg2 or similar library):Pythonimport psycopg2  # Or your preferred PostgreSQL driver

# Connect to database (use your connection details)
conn = psycopg2.connect("dbname=your_db user=your_user password=your_pass")
cur = conn.cursor()

# Example: Insert a group and get ID
cur.execute("""
    INSERT INTO definition_groups (name, type, environment, metadata, liquidity_filter)
    VALUES (%s, %s, %s, %s, %s) RETURNING id;
""", ('SPY', 'ETF', 'PROD', '{"source": "massive.com"}', '{"min_volume": 1000000}'))
group_id = cur.fetchone()[0]

# Insert memberships for the group
stocks = [('AAPL', 0.06), ('MSFT', 0.05)]  # Example list from parsed data
for symbol, weight in stocks:
    cur.execute("""
        INSERT INTO group_memberships (group_id, symbol, weight)
        VALUES (%s, %s, %s);
    """, (group_id, symbol, weight))

conn.commit()
cur.close()
conn.close()
Migration Considerations:
Query existing cache_entries data and transform it (e.g., extract JSONB value for stock lists) before inserting into the new tables.
Update any dependent queries in the script to reference the new schema.
Test in a non-production environment (e.g., 'TEST') to ensure data consistency.


This provides the foundational steps; refine based on the detailed specifications in the other location.