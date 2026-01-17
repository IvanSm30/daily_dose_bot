import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from database import AsyncSessionLocal
from models.models import WaterLog, FoodLog, WorkoutLog


async def generate_water_graph(telegram_id: int) -> BytesIO | None:
    async with AsyncSessionLocal() as session:
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        result = await session.execute(
            select(
                func.date(WaterLog.logged_at).label("date"),
                func.sum(WaterLog.quantity).label("total"),
            )
            .where(WaterLog.telegram_id == telegram_id)
            .where(WaterLog.logged_at >= week_ago)
            .group_by(func.date(WaterLog.logged_at))
            .order_by("date")
        )
        data = result.fetchall()

        if not data:
            return None

        dates = [row.date for row in data]
        amounts = [row.total for row in data]

        from utils import get_user_profile

        user = await get_user_profile(telegram_id)
        water_goal = user.water_goal if user else 2000

        plt.figure(figsize=(10, 5))
        plt.plot(dates, amounts, marker="o", label="Выпито", color="#1E88E5")
        plt.axhline(
            y=water_goal,
            color="#43A047",
            linestyle="--",
            label=f"Цель ({water_goal} мл)",
        )
        plt.title("💧 Прогресс по воде (последние 7 дней)")
        plt.xlabel("Дата")
        plt.ylabel("Миллилитры")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)
        return buf


async def generate_calories_graph(telegram_id: int) -> BytesIO | None:
    async with AsyncSessionLocal() as session:
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        food_result = await session.execute(
            select(
                func.date(FoodLog.logged_at).label("date"),
                func.sum(FoodLog.calories).label("total"),
            )
            .where(FoodLog.telegram_id == telegram_id)
            .where(FoodLog.logged_at >= week_ago)
            .group_by(func.date(FoodLog.logged_at))
            .order_by("date")
        )
        food_data = {row.date: row.total for row in food_result.fetchall()}

        workout_result = await session.execute(
            select(
                func.date(WorkoutLog.logged_at).label("date"),
                func.sum(WorkoutLog.calories_burned).label("total"),
            )
            .where(WorkoutLog.telegram_id == telegram_id)
            .where(WorkoutLog.logged_at >= week_ago)
            .group_by(func.date(WorkoutLog.logged_at))
            .order_by("date")
        )
        workout_data = {row.date: row.total for row in workout_result.fetchall()}

        if not food_data and not workout_data:
            return None

        all_dates = sorted(set(food_data.keys()) | set(workout_data.keys()))
        consumed = [food_data.get(d, 0) for d in all_dates]
        burned = [workout_data.get(d, 0) for d in all_dates]

        from utils import get_user_profile

        user = await get_user_profile(telegram_id)
        calorie_goal = user.calorie_goal if user else 2000

        plt.figure(figsize=(10, 5))
        plt.plot(all_dates, consumed, marker="o", label="Потреблено", color="#FB8C00")
        plt.plot(all_dates, burned, marker="s", label="Сожжено", color="#E53935")
        plt.axhline(
            y=calorie_goal,
            color="#43A047",
            linestyle="--",
            label=f"Цель ({calorie_goal} ккал)",
        )
        plt.title("🔥 Калории: потребление vs расход (последние 7 дней)")
        plt.xlabel("Дата")
        plt.ylabel("Калории")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)
        return buf
