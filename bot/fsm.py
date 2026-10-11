from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_query = State()
    results = State()


class TrackStates(StatesGroup):
    waiting_url = State()
    waiting_threshold = State()


class CategoryStates(StatesGroup):
    browsing = State()
