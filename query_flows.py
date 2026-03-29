import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://observatory:changeme@localhost:5432/observatory')
    rows = await conn.fetch("""
        SELECT * FROM signals_v2 
        WHERE array_length(themes, 1) > 0 
        LIMIT 5;
    """)
    print("Found signals:", len(rows))
    await conn.close()
asyncio.run(run())
