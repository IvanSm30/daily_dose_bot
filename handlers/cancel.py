from aiogram import Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

router = Router()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer(
            "❌ Действие отменено.", reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer("Нечего отменять.")
