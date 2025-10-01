from aiogram import Router
from . import commands, for_admin, other, user, chat_admin


def get_routers() -> list[Router]:
    return [
        for_admin.router,
        commands.router,
        other.router,
        user.router,
        chat_admin.router,
    ]
