from aiogram import Router
from . import commands, for_admin, other, user


def get_routers() -> list[Router]:
    return [
        for_admin.router,
        commands.router,
        other.router,
        user.router,]
