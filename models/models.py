from sqlalchemy import (
    BigInteger,
    Column,
    Integer,
    String,
    DateTime,
    func,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True, autoincrement=False)
    weight = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    age = Column(Integer, nullable=False)
    city = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    activity_minutes = Column(Integer, nullable=False)
    calorie_goal = Column(Integer, nullable=False)
    water_goal = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WaterLog(Base):
    __tablename__ = "water_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())


class FoodLog(Base):
    __tablename__ = "food_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    name = Column(String, nullable=False)
    weight = Column(Integer, nullable=False)
    calories = Column(Integer, nullable=False)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    kind = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())
    calories_burned = Column(Integer, nullable=False)
