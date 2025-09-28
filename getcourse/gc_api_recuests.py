import base64


example_users = {
    "user": {
        "email": "email",
        "phone": "телефон",
        "first_name": "имя",
        "last_name": "фамилия",
        "city": "город",
        "country": "страна",
        "group_name": [  # для добавления пользователя в группы
            "Группа1",  # простое добавление в групп
            [
                "Группа2",
                "2018-08-01 21:21",
            ],  # добавление в группу с указанием произвольного момента
            ["Группа4", "2018-08-02"],
        ],
        "addfields": {
            "Доп.поле1": "значение",
            "Доп.поле2": "значение",
        },  # для добавления дополнительных полей пользователя
    },
    "system": {
        "refresh_if_exists": 0,  # обновлять ли существующего пользователя 1/0 да/нет
        "partner_email": "email партнера (для пользователя)*",
    },
    "session": {
        "utm_source": "",
        "utm_medium": "",
        "utm_content": "",
        "utm_campaign": "",
        "utm_group": "",
        "gcpc": "",
        "gcao": "",
    },
}


example_payment = {
    "user": {
        # как в импорте пользователя
    },
    "system": {
        "refresh_if_exists": 0,  # обновлять ли существующего пользователя 1/0 да/нет
        "partner_email": "email партнера (для пользователя)*",
        "multiple_offers": 0,  # добавлять несколько предложений в заказ 1/0
        "return_payment_link": 0,  # возвращать ссылку на оплату 1/0
        "return_deal_number": 0,  # возвращать номер заказа 1/0
    },
    "session": {
        # как в импорте пользователя
    },
    "deal": {
        "deal_number": "номер заказа",
        "offer_code": "уникальный код предложения",
        "offer_id": "ID предложения",
        "product_title": "наименование предложения",
        "product_description": "описание продукта",
        "quantity": 1,  # количество
        "deal_cost": "сумма заказа",
        "deal_status": "код статуса заказа",
        "deal_is_paid": "нет",  # оплачен да/нет 1/0
        "manager_email": "email менеджера",
        "deal_created_at": "дата заказа",
        "deal_finished_at": "дата оплаты/завершения заказа",
        "deal_comment": "комментарий",
        "payment_type": "тип платежа из списка",
        "payment_status": "статус платежа из списка",
        "partner_email": "email партнера (для заказа)",
        "addfields": {
            "Доп.поле1": "значение",
            "Доп.поле2": "значение",
        },  # для добавления дополнительных полей заказа
        "deal_currency": "код валюты заказа",  # например, "EUR", параметр не является обязательным, если он не используется в запросе - валютой заказа будут рубли (RUB)
        "funnel_id": "ID доски продаж",
        "funnel_stage_id": "ID этапа на доске продаж",
    },
}


async def create_user_req(email, phone, name):
    create_user_request = {
        "user": {
            "email": email,
            "phone": phone,
            "first_name": name,
        },
        "system": {
            "refresh_if_exists": 1,  # обновлять ли существующего пользователя 1/0 да/нет
        },
    }

    encoded = base64.b64encode(str(create_user_request).encode("utf-8"))
    base64_string = encoded.decode("utf-8")

    return base64_string


async def create_payment_req_auto(email, offer_code, offer_id):
    create_payment_request = {
        "user": {
            "email": email,
        },
        "system": {
            "return_payment_link": 1,  # возвращать ссылку на оплату 1/0
            "return_deal_number": 1,  # возвращать номер заказа 1/0
        },
        "deal": {
            "offer_code": offer_code,  # уникальный код предложения
            "offer_id": offer_id,  # ID предложения
            "deal_status": "new",  # код статуса заказа (new)
            "addfields": {
                "Бот_подписка": "Да",  # пример доп. поля
            },
        },
    }
    print(offer_code, offer_id)
    encoded = base64.b64encode(str(create_payment_request).encode("utf-8"))
    base64_string = encoded.decode("utf-8")

    return base64_string


async def create_payment_req_no_auto(email, offer_code, offer_id):
    create_payment_request = {
        "user": {
            "email": email,
        },
        "system": {
            "return_payment_link": 1,  # возвращать ссылку на оплату 1/0
            "return_deal_number": 1,  # возвращать номер заказа 1/0
        },
        "deal": {
            "offer_code": offer_code,  # уникальный код предложения
            "offer_id": offer_id,  # ID предложения
            "deal_status": "new",  # код статуса заказа (new)
            "addfields": {
                "Бот_подписка": "Нет",  # пример доп. поля
            },
        },
    }
    print(offer_code, offer_id)
    encoded = base64.b64encode(str(create_payment_request).encode("utf-8"))
    base64_string = encoded.decode("utf-8")

    return base64_string



async def create_promo_req(email, offer_code, offer_id):
    create_payment_request = {
        "user": {
            "email": email,
        },
        "system": {
            "return_payment_link": 0,  # возвращать ссылку на оплату 1/0
            "return_deal_number": 0,  # возвращать номер заказа 1/0
        },
        "deal": {
            "offer_code": offer_code,  # уникальный код предложения
            "offer_id": offer_id,  # ID предложения
            "deal_status": "payed",  # код статуса заказа (new)
        },
    }

    encoded = base64.b64encode(str(create_payment_request).encode("utf-8"))
    base64_string = encoded.decode("utf-8")

    return base64_string
