from bs4 import BeautifulSoup
from status_notifier import notify_group
import requests
import sys
import json

CONFIG = json.loads(open("config.json").read())

MYTHICAL = [
    "Gravity",
    "Mammoth",
    "T-rex",
    "Dough",
    "Shadow",
    "Venom",
    "Control",
    "Spirit",
    "Dragon",
    "Leopard",
    "Kitsune",
    # "Meme",
    # "Soul",
    # "Door",
    # "Revive",
    # "Kilo"
]
LEGENDARY = [
    "Quake",
    "Buddha",
    "Love",
    "Spider",
    "Sound",
    "Phoenix",
    "Portal",
    "Rumble",
    "Pain",
    "Blizzard",
]


def get_fruit_soup():
    source = requests.get("https://fruityblox.com/stock").text
    soup = BeautifulSoup(source, features="html")
    return soup


# div.grid:nth-child(3) > div:nth-child(1) > div:nth-child(3) > div:nth-child(1) > div:nth-child(2) > h3:nth-child(1)
# div.grid:nth-child(3) > div:nth-child(1) > div:nth-child(3) > div:nth-child(1)


def get_fruits_stock(soup):
    # fruits = list(soup.select(".grid > div:nth-child(1)")[0].children)[2:]
    fruits_name = list(
        map(
            lambda x: x.string,
            soup.select(
                "div.grid:nth-child(3) > div:nth-child(1) > div > div > div > h3"
            ),
        )
    )
    # fruits_name = [
    #     fruit.select("div:nth-child(1) > div:nth-child(2) > h3:nth-child(1)")[0].string
    #     for fruit in fruits
    # ]

    fruits_price = list(
        map(
            lambda x: x.text,
            soup.select(
                "div.grid:nth-child(3) > div:nth-child(1) > div > div > p:nth-child(3)"
            ),
        )
    )

    # fruits_price = [
    #     fruit.select("div:nth-child(1) > p:nth-child(3)")[0].text for fruit in fruits
    # ]

    print(fruits_name, fruits_price, sep="\n\n=================\n\n")

    return dict(zip(fruits_name, fruits_price))


# mirage advance fruit shop stock
def get_mirage_stock(soup):
    # fruits = soup.select(".grid > div:nth-child(3) > a > div:nth-child(1)")
    # fruits_name = list(
    #     map(lambda fruit: fruit.select("p:nth-child(2)")[0].text, fruits)
    # )
    # fruits_price = list(
    #     map(lambda fruit: fruit.select("p:nth-child(3)")[0].text, fruits)
    # )
    # div.grid:nth-child(3) > div:nth-child(2) > div:nth-child(3) > div:nth-child(1) > div:nth-child(2) > h3:nth-child(1)
    fruits_name = list(
        map(
            lambda x: x.string,
            soup.select(
                "div.grid:nth-child(3) > div:nth-child(2) > div > div > div > h3"
            ),
        )
    )
    fruits_price = list(
        map(
            lambda x: x.text,
            soup.select(
                "div.grid:nth-child(3) > div:nth-child(2) > div > div > p:nth-child(3)"
            ),
        )
    )

    print(fruits_name, fruits_price, sep="\n")

    return dict(zip(fruits_name, fruits_price))


def notify_stock(normal=True, mirage=False, send=True, filter=[]):
    soup = get_fruit_soup()
    stock = {}
    mirage_stock = {}
    msg = ""

    filter = list(map(lambda x: x.title(), filter))

    if normal:
        stock = get_fruits_stock(soup)
        print("sending [normal]:", stock)
    if mirage:
        mirage_stock = get_mirage_stock(soup)
        print("sending [mirage]:", mirage_stock)

    if not not filter:
        if filtered_fruit_in_stock(stock, mirage_stock, filter):
            msg = "Currently available good fruits:"
    else:
        msg = "Currently available blox fruit stock:"

    # stock["KITSUNE"] = "test"

    if normal and (filtered_fruit_in_stock(stock, [], filter) or not filter):
        msg += "\n\n<b>Normal market:</b>" if mirage else ""
        for name, price in stock.items():
            if fruit_in_filters(name, filter) or not filter:
                msg += f'\n<a href="https://blox-fruits.fandom.com/wiki/{
                    name.title()
                }">{name}</a>: {price}'

    if mirage and (
        filtered_fruit_in_stock([], mirage_stock, filter) or not filter
    ):
        msg += "\n\n<b>Mirage market:</b>"
        for name, price in mirage_stock.items():
            if fruit_in_filters(name, filter) or not filter:
                msg += f'\n<a href="https://blox-fruits.fandom.com/wiki/{
                    name.title()
                }">{name}</a>: {price}'

    print(msg)
    if send:
        data_path, response = notify_group(msg)
        data = json.loads(open(data_path).read())
        try:
            if data["ok"]:
                message_id = data["result"]["message_id"]
        except KeyError:
            notify_group("error: failed to fetch data")

        # if mythical_fruit_in_stock(stock, mirage_stock):
        #     pin_message(message_id)
        #     notify_group("Mythical fruit in stock!")


def mythical_fruit_in_stock(stock, mirage_stock) -> bool:
    return x_fruit_in_y(stock, mirage_stock, MYTHICAL)


def legendary_fruit_in_stock(stock, mirage_stock) -> bool:
    return x_fruit_in_y(stock, mirage_stock, LEGENDARY)


def x_fruit_in_y(x1, x2, y) -> bool:
    for fruit in y:
        if fruit.title() in x1 or fruit.title() in x2:
            return True
    return False


def filtered_fruit_in_stock(stock, mirage_stock, filter):
    yeah = False
    yeah |= (
        mythical_fruit_in_stock(stock, mirage_stock)
        if "Mythical" in filter
        else False
    )
    yeah |= (
        legendary_fruit_in_stock(stock, mirage_stock)
        if "Legendary" in filter
        else False
    )
    yeah |= x_fruit_in_y(stock, mirage_stock, filter)

    return bool(yeah)


def fruit_in_filters(fruit, filter) -> bool:
    fruit = fruit.title()
    # Note: 'and' precedence is higher than 'or'
    if (
        fruit in MYTHICAL
        and "Mythical" in filter
        or fruit in LEGENDARY
        and "Legendary" in filter
        or fruit in filter
    ):
        return True
    else:
        return False


def the_filter_that_the_fruit_belongs_to(fruit, filter=[]) -> str | None:
    if fruit in MYTHICAL:
        return "Mythical"
    elif fruit in LEGENDARY:
        return "Legendary"
    elif fruit in filter:
        return "Custom filter"
    else:
        return None


def pin_message(message_id):
    requests.get(
        f"https://api.telegram.org/bot{
            CONFIG['TELEGRAM_API_KEY']
        }/pinChatMessage",
        params={
            "chat_id": CONFIG["TELEGRAM_GROUP_ID"],
            "message_id": message_id,
        },
    )


if __name__ == "__main__":
    send = True if "send" in sys.argv else False
    mirage = "mirage" in sys.argv
    normal = True if "normal" in sys.argv else False if mirage else True
    filter = (
        sys.argv[sys.argv.index("filter") + 1 :] if "filter" in sys.argv else []
    )
    notify_stock(normal, mirage, send, filter)
