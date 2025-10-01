import aiohttp
from config.config import load_config
from getcourse.gc_api_recuests import (
    create_promo_req,
    create_payment_req_auto,
    create_payment_req_no_auto,
)
import logging

config = load_config()
GETCOURSE_ACCOUNT = config.getcourse.gc_name
GETCOURSE_API_KEY = config.getcourse.api_key
PAY_PRODUCT_ID = config.getcourse.product_id
GETCOURSE_GROUP_ID = config.getcourse.group_id

logging = logging.getLogger(__name__)

BASE_URL = f"https://{GETCOURSE_ACCOUNT}.getcourse.ru/pl/api"


async def create_user(base64_string):
    url = f"{BASE_URL}/users"

    payload = {
        "action": "add",
        "key": GETCOURSE_API_KEY,
        "params": base64_string,  # здесь уже должен быть base64
    }

    headers = {"Accept": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers) as resp:
            return await resp.json()


async def gc_request_no_payment_link(email, offer_code, offer_id):
    base64_string = await create_promo_req(
        email=email, offer_code=offer_code, offer_id=offer_id
    )
    #print(base64_string)
    url = f"{BASE_URL}/deals"

    payload = {
        "action": "add",
        "key": GETCOURSE_API_KEY,
        "params": base64_string,  # здесь уже должен быть base64
    }

    headers = {"Accept": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers) as resp:
            await resp.json()


async def gc_request_auto_payment_link(email, offer_code, offer_id):
    base64_string = await create_payment_req_auto(
        email=email, offer_code=offer_code, offer_id=offer_id
    )
    #print(base64_string)
    url = f"{BASE_URL}/deals"

    payload = {
        "action": "add",
        "key": GETCOURSE_API_KEY,
        "params": base64_string,  # здесь уже должен быть base64
    }

    headers = {"Accept": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers) as resp:
            data = await resp.json()
            print(data)
            if data:
                return data.get("result", {}).get("payment_link")
            else:
                logging.error("No data received from create_payment_link")
                return None


async def gc_request_no_auto_payment_link(email, offer_code, offer_id):
    base64_string = await create_payment_req_no_auto(
        email=email, offer_code=offer_code, offer_id=offer_id
    )
    #print(base64_string)
    url = f"{BASE_URL}/deals"

    payload = {
        "action": "add",
        "key": GETCOURSE_API_KEY,
        "params": base64_string,  # здесь уже должен быть base64
    }

    headers = {"Accept": "application/json"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers) as resp:
            data = await resp.json()
            print(data)
            if data:
                return data.get("result", {}).get("payment_link")
            else:
                logging.error("No data received from create_payment_link")
                return None