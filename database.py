import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.pool = None
        self.conn = None

    async def connect(self):
        self.conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        await self.create_table()

    async def create_table(self):
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS orders(
                id SERIAL PRIMARY KEY,
                address TEXT NOT NULL,
                contacts TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                worker_id BIGINT,
                worker_name TEXT
            )
        ''')

    async def add_order(self, address, contacts, time):
        return await self.conn.fetchval(
            "INSERT INTO orders(address, contacts, time) VALUES($1, $2, $3) RETURNING id",
            address, contacts, time
        )

    async def assign_order(self, order_id, worker_id, worker_name):
        await self.conn.execute(
            "UPDATE orders SET status='assigned', worker_id=$1, worker_name=$2 WHERE id=$3",
            worker_id, worker_name, order_id
        )

    async def get_open_orders(self):
        return await self.conn.fetch("SELECT * FROM orders WHERE status='open'")
