from aiogram.fsm.state import State, StatesGroup


class ProfileStates(StatesGroup):
    weight = State()
    height = State()
    age = State()
    city = State()
    gender = State()
    activity_minutes = State()
    calorie_goal = State()
    water_goal = State()


class WaterStates(StatesGroup):
    quantity = State()


class FoodStates(StatesGroup):
    name = State()
    weight = State()


class WorkoutStates(StatesGroup):
    kind = State()
    calories_burned = State()
    duration = State()
