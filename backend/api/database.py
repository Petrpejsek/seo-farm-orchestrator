from prisma import Prisma
import asyncio

# Globální instance Prisma clienta
prisma = Prisma()

async def connect_database():
    """Připojí se k databázi"""
    if not prisma.is_connected():
        await prisma.connect()

async def disconnect_database():
    """Odpojí se od databáze"""
    if prisma.is_connected():
        await prisma.disconnect()

async def get_prisma_client():
    """Vrátí připojený Prisma client"""
    await connect_database()
    return prisma