from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.db.repo import repo
from bot.formatters import render_track_html
from bot.keyboards import tracks_keyboard

router = Router(name="mytracks")


@router.message(Command("mytracks"))
async def cmd_mytracks(message: Message) -> None:
    user_id = await repo.get_or_create_user(message.from_user.id, message.from_user.username)
    tracks = await repo.list_user_tracks(user_id)
    if not tracks:
        await message.answer("Список отслеживаемых товаров пуст. Добавьте через /track <url> <порог>.")
        return
    text = "\n\n".join(render_track_html(t) for t in tracks)
    await message.answer(text, parse_mode="HTML", reply_markup=tracks_keyboard(tracks))


@router.callback_query(F.data.startswith("u:"))
async def cb_untrack(callback: CallbackQuery) -> None:
    track_id = int(callback.data.split(":")[1])
    user_id = await repo.get_or_create_user(callback.from_user.id, callback.from_user.username)
    removed = await repo.remove_track(track_id, user_id)
    if removed:
        await callback.answer("Удалено.", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
    else:
        await callback.answer("Не удалось удалить.", show_alert=True)
