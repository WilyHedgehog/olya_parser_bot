from aiogram import Router
from . import add_mailing, for_admin, other, user


def get_routers() -> list[Router]:
    return [
        add_mailing.router,
        other.router,
        for_admin.router,
        user.router,
    ]
