# scripts/seed-data.py
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.database import AsyncSessionLocal
from app.models.user import Goal
from sqlalchemy import select

async def seed_data():
    """Seed initial data"""
    print("Seeding initial data...")

    async with AsyncSessionLocal() as db:
        try:
            # Check if goals already exist
            stmt = select(Goal)
            result = await db.execute(stmt)
            existing_goals = result.scalars().all()

            if existing_goals:
                print("Goals already seeded, skipping...")
                return

            # Create default goals
            goals_data = [
                {"name": "weight_loss", "description": "Perder peso de forma saudável", "category": "fitness"},
                {"name": "muscle_gain", "description": "Ganhar massa muscular", "category": "fitness"},
                {"name": "maintenance", "description": "Manter peso atual", "category": "fitness"},
                {"name": "improve_health", "description": "Melhorar saúde geral", "category": "health"},
                {"name": "increase_strength", "description": "Aumentar força", "category": "fitness"},
                {"name": "improve_endurance", "description": "Melhorar resistência", "category": "fitness"}
            ]

            for goal_data in goals_data:
                goal = Goal(**goal_data)
                db.add(goal)

            await db.commit()
            print("Goals seeded successfully")

        except Exception as e:
            print(f"Error seeding data: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(seed_data())