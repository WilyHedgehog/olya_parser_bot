from aiogram import Router
from . import add_mailing, for_admin, other, user


def get_routers() -> list[Router]:
    return [
        for_admin.router,
        add_mailing.router,
        other.router,
        user.router,
    ]
