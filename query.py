import asyncio
import asyncpg
import json

async def run():
    conn = await asyncpg.connect('postgresql://observatory:changeme@localhost:5432/observatory')
    rows = await conn.fetch("""
        WITH theme_counts AS (
            SELECT 
                country_code,
                unnest(themes) as theme,
                COUNT(*) as cnt
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '2160 hours'
            AND themes IS NOT NULL AND array_length(themes, 1) > 0
            GROUP BY country_code, theme
            HAVING COUNT(*) >= 2
        )
        SELECT * FROM theme_counts LIMIT 5;
    """)
    print("row count:", len(rows))
    for r in rows:
        print(dict(r))
    await conn.close()

asyncio.run(run())
