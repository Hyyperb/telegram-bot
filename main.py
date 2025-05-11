import logging
import random
from telegram import ForceReply, Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import pandas as pd
import numpy as np

# import re
import json
import requests
from math import ceil
from math import floor
import hashlib
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from urllib.parse import urlencode
import io

from board_notifier import board_reminder_message
from status_notifier import send_message
from blox import notify_stock
import facts
import exam
import anime_meme
import os

if not os.path.exists("config.json"):
    raise FileNotFoundError("No config file found. exiting...")

CONFIG = json.loads(open("config.json").read())

# df = pd.read_csv("https://gist.githubusercontent.com/GoodmanSciences/c2dd862cd38f21b0ad36b8f96b4bf1ee/raw/1d92663004489a5b6926e944c1b3d9ec5c40900e/Periodic%2520Table%2520of%2520Elements.csv")
df = pd.read_csv("periodic_table.csv")

SERVERS = CONFIG["servers"]

progbar_width = 25  # for /ship

MONTHS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]

MONTHS_SHORT = list(map(lambda x: x[:3], MONTHS))

PREF_TZ_HRS, PREF_TZ_MINS = map(int, CONFIG["timezone"].split(":"))
PREF_TZ = timezone(timedelta(hours=PREF_TZ_HRS, minutes=PREF_TZ_MINS))


def split_args(x):
    return zip(x[::2], x[::-2][::-1])


df["Symbol"] = df["Symbol"].str.lower()


def to_element(raw_text):
    raw_text = raw_text.lower()
    # left to right
    text = raw_text + "_"
    res1 = []
    skip_next = False
    weight1 = 0

    for i in range(len(raw_text)):
        if skip_next:
            skip_next = 0
            continue

        s1 = text[i]
        s2 = text[i + 1]
        if s1 + s2 in list(df["Symbol"]):
            skip_next = True
            name = df["Element"][
                df.index[df["Symbol"] == (s1 + s2)].tolist()[0]
            ]
            res1.append(name)
        elif s1 in list(df["Symbol"]):
            name = df["Element"][df.index[df["Symbol"] == s1].tolist()[0]]
            res1.append(name)
        else:
            res1.append(s1)
            weight1 -= 1

    text = "_" + raw_text
    res2 = []
    weight2 = 0

    for i in range(len(raw_text))[::-1]:
        if skip_next:
            skip_next = 0
            continue

        s1 = text[i]
        s2 = text[i + 1]

        if s1 + s2 in list(df["Symbol"]):
            skip_next = True
            name = df["Element"][
                df.index[df["Symbol"] == (s1 + s2)].tolist()[0]
            ]
            res2.append(name)
        elif s2 in list(df["Symbol"]):
            name = df["Element"][df.index[df["Symbol"] == s2].tolist()[0]]
            res2.append(name)
        else:
            res2.append(s2)
            weight2 -= 1

    if weight1 > weight2:
        return "\n".join(res1)
    else:
        return "\n".join(res2[::-1])


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def nextexam(update, content):
    MESSAGES = CONFIG["next exam messages"]

    dt, exam_name = exam.time_till_next_exam()

    format = {
        "name": exam_name,
        "days": abs(dt.days),
        "hours": round(dt.seconds / 3600) + dt.days * 24,
        "seconds": dt.seconds,
    }

    if dt.days < 0:
        msg = MESSAGES["past exam"]
    elif dt.days > 5:
        msg = MESSAGES["more than 5 days"]
    elif dt.total_seconds() > 3600:
        msg = MESSAGES["within 5 days"]
    else:
        msg = MESSAGES["within an hour"]

    for stub in format:
        msg = msg.replace(f"{stub}", format[stub])

    await update.message.reply_text(msg)


async def examtopic(update, context):
    index = 1
    for arg in context.args:
        try:
            index = int(arg)
            context.args.pop(context.args.index(arg))
            break
        except ValueError:
            continue

    next_exam = exam.get_next_exam_data(index)
    exam_name = next_exam["name"]
    topics = next_exam["topics"]
    msg_parts = []
    exam_type = ""

    exam_type_table = CONFIG["exam types"]

    for entry in exam_type_table:
        if exam_name.startswith(entry):
            exam_type = exam_type_table[entry]

    for subject in topics:
        if context.args:
            if subject.lower() not in context.args:
                continue
        msg_parts.append(f"\n<b>{subject.title()}</b>:")
        for chapter in topics[subject]:
            if ":" not in chapter:
                chapter_title = chapter[chapter.find(" ") + 1:]
            else:
                chapter_title = chapter
            search_term = chapter_title + " " + exam_type
            ch_search_url = "https://google.com/search?" + urlencode(
                {"q": search_term}
            )
            msg_parts.append(f'• <a href="{ch_search_url}">{chapter}</a>')
        # msg_parts.append("\n")

    if msg_parts:
        msg = f"<b>{exam_name}</b>\n"
        msg += next_exam["date"] + "\n"
        msg += "\n".join(msg_parts)
    else:
        msg = "No subject found for the next exam"

    print(msg)

    await update.message.reply_text(msg, parse_mode="HTML")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        rf"Hello, {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(" ".join(context.args))


async def pong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("got pinged")
    await update.message.reply_text("pong")


async def elementify(update, context):
    try:
        text = " ".join(context.args)
        elements = to_element(text)
        await update.effective_message.reply_text(elements)

    except (IndexError, ValueError):
        user = update.message.from_user["username"]
        await update.effective_message.reply_text(f"Try /elementify {user}")


async def examsim(update, context):
    try:
        attempts = int(context.args[0])
        accuracy = int(context.args[1])
    except:
        await update.effective_message.reply_text(
            "Try /jee {attempts} {accuracy} [n exams]\n ex:- /jee 75 25"
        )
    try:
        n = int(context.args[2])
    except:
        n = 1
    # stddev = int(context.args[3])
    if n > 100000:
        await update.effective_message.reply_text(
            "choose n value less than 10000"
        )
    if not 0 <= accuracy <= 100:
        await update.effective_message.reply_text(
            "choose accuracy b/w 0 and 100"
        )

    score = 0
    n_record = n if n < 20 else 20
    tests = [0 for i in range(n_record)]
    accuracy = accuracy

    for exam in range(n_record):
        for question in range(attempts):
            que = 4 if random.randint(1, 100) <= accuracy else -1
            tests[exam] += que
            score += que
        tests[exam] = str(tests[exam])

    if n > 20:
        for exam in range(n - 20):
            for question in range(attempts):
                score += 4 if random.randint(1, 100) <= accuracy else -1

    score /= n
    nl = "\n    "  # To remove in 3.12

    await update.effective_message.reply_text(f"""
attempts: {attempts} ques
accuracy: {accuracy}%
n(tests): {n}
tests:
    {nl.join(tests)}{rf"{nl}running {n - 20} more tests...." if n > 20 else ""}
result:
    avg score: {score}
j   percentage: {score / 3}
    """)


async def weather(update, context):
    city = CONFIG["city"]
    response = requests.get(f"https://wttr.in/{city}?0&T&Q&m")
    await update.message.reply_text(
        f"```\n{response.text}\n```", parse_mode="markdown"
    )


def get_server_status(server_ip):
    api_url = "https://api.mcstatus.io/v2/status/java/"
    print(f"getting server status for {server_ip}")
    return json.loads(requests.get(api_url + server_ip).text)


def is_server_online(status):
    if status["online"] and status["version"]["protocol"] > -1:
        player_list_is_available = not not len(status["players"]["list"])
        msg = f"Server online with {status['players']['online']} players"
        if player_list_is_available:
            msg += ":\n"
            for player in status["players"]["list"]:
                msg += f"● {player['name_clean']}\n"
        return msg
    else:
        return "Server offline."


def fusion(x, y):
    return x[: ceil(len(x) / 2)] + y[floor(len(y) / 2):]


def compat(x: str, y: str, seed_phase=0):
    mean = 50
    stddev = 21.5 * (2**0.5)

    xy_hash = int(hashlib.md5((x + y).encode()).hexdigest()[-7:], 16)
    yx_hash = int(hashlib.md5((y + x).encode()).hexdigest()[-7:], 16)

    np.random.seed(xy_hash + seed_phase)
    rand1 = np.random.normal(mean, stddev)
    np.random.seed(yx_hash + seed_phase)
    rand2 = np.random.normal(mean, stddev)

    score = (rand1 + rand2) / 2
    if score > 100:
        score = 100
    elif score < 0:
        score = 0

    return round(score)


async def serverstatus(update, context):
    if len(context.args):
        if context.args[0] == "-l":
            msg = "\n".join(SERVERS)

        elif context.args[0] == "-h":
            msg = f"usage examples:\n\t/serverstatus\n\t/serverstatus {
                SERVERS[0]
            }\n\t/serverstatus -u hypixel.net\n\t/serverstatus -l"

        elif context.args[0] in SERVERS:
            ip = SERVERS[context.args[0]]
            msg = is_server_online(get_server_status(ip))

        else:
            ip = context.args[0]
            msg = is_server_online(get_server_status(ip))

    else:
        ip = SERVERS[0]
        msg = is_server_online(get_server_status(ip))

    await update.message.reply_text(msg)


async def targetscore(update, context):
    if not context.args:
        await update.message.reply_text("usage: /targetscore {desired score}")
        return
    msg = "You need one of the following pair of stats to achieve your target:\n\n"
    msg += "accuracy | attempts"
    for i in range(6):
        accuracy = i * 10 + 50
        score = int(context.args[0])
        attempts = round(score / (5 * accuracy / 100 - 1), 2)
        if not i == 0:
            msg += "\n---------+----------\n"
        else:
            msg += "\n====================\n"
        msg += f"{accuracy}{'%':<6} | {attempts:>8}"

    await update.message.reply_text(f"```\n{msg}\n```", parse_mode="markdown")


async def ship(update, context):
    if len(context.args) < 3 or "x" not in context.args:
        await update.message.reply_text(
            "Usage: /ship {someone} x {someone else}"
        )
    else:
        x, y = " ".join(context.args).lower().split(" x ")
        xy = fusion(x, y)
        score = compat(x, y, seed_phase=818)
        prog = int(score / 100 * progbar_width)
        msg = f"{x} x {y} = {xy}\n"
        msg += f"Compatibility: {score}%\n"
        msg += f"|{'#' * prog}{' ' * (progbar_width - prog)}|"

        await update.message.reply_text(
            f"```\n{msg}\n```", parse_mode="markdown"
        )


async def perlin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nlines = 60
    x = 20
    msg = ""
    cell = "#"
    depth = 2

    for i in range(nlines):
        x += round(np.random.normal(0, depth))
        msg += cell * x
        msg += "\n"

    await update.message.reply_text(msg)


async def attempts(update, context):
    if not context.args:
        await update.message.reply_text(
            "usage: /attempts {no. of questions attempted}"
        )
        return
    msg = "You'll score the percentage next to your corresponding accuracy:\n\n"
    msg += "accuracy | score"
    for i in range(6):
        accuracy = i * 10 + 50
        attempts = int(context.args[0])
        score = attempts * accuracy * 0.05 - attempts
        if not i == 0:
            msg += "\n---------+----------\n"
        else:
            msg += "\n====================\n"
        msg += f"{accuracy}{'%':<6} | {score:>8}"

    await update.message.reply_text(f"```\n{msg}\n```", parse_mode="markdown")


def random_element(fr=1, to=118):
    if fr > to:
        fr, to = to, fr
    # print(f"random element b/w {fr} and {to}")
    element = {}

    element["atomic_number"] = random.randint(fr, to)
    element["symbol"] = df["Symbol"][
        df.index[df["AtomicNumber"] == element["atomic_number"]].tolist()[0]
    ].title()
    element["name"] = df["Element"][
        df.index[df["AtomicNumber"] == element["atomic_number"]].tolist()[0]
    ]

    return element


def full_element_quiz(fr=1, to=118, show_answer=True):
    element = random_element(fr, to)
    msg = f"Whats the element at {element['atomic_number']}"
    if show_answer:
        msg += f"\nAnswer:\- ||{element['name']} \({element['symbol']}\)||"
    return msg


def short_element_quiz(fr=1, to=118, show_answer=True):
    element = random_element(fr, to)
    return f"Atomic No\. {element['atomic_number']}" + (
        f":\- ||{element['name']} \({element['symbol']}\)||\n"
        if show_answer
        else ""
    )


async def elementquiz(update, context):
    msg = ""
    fr = 1
    to = 118
    count = 1
    show_answer = True

    if len(context.args):
        for arg, value in split_args(context.args):
            if arg == "-h":
                msg += "Usage: /elementquiz -f {from} -t {to} -c {count} -a [true|false]\n"
                count = 0
            elif arg == "-f":
                fr = int(value)
            elif arg == "-t":
                to = int(value)
            elif arg == "-c":
                count = int(value)
            elif arg == "-a":
                show_answer = False if value == "false" else True
            else:
                msg += f"invalid argument: /{arg} {value}"

        for i in range(count):
            msg += short_element_quiz(fr, to, show_answer)

    else:
        msg = full_element_quiz()

    await update.message.reply_text(f"{msg}", parse_mode="MarkdownV2")


def solve_compatibility_layer(x: list, msg: str):
    output_buffer = " ".join(list(map(lambda x: str(x), x)))

    xstr = "".join(list(map(lambda i: str(i), x)))

    if len(xstr) == 2:
        return (int(xstr), msg + "\n" + output_buffer)

    y = []

    for i in range(int(len(x) / 2)):
        y.append(x[i] + x[-i - 1])

    if len(x) % 2:
        y.append(x[int(len(x) / 2)])

    # y = list("".join(list(map(lambda x:str(x),x))))

    return solve_compatibility_layer(y, msg + "\n" + output_buffer)


# different from compat(), this one is based on the popular manual shipping algorithm


async def compatibility(update, context):
    if len(context.args) < 3 or "x" not in context.args:
        await update.message.reply_text(
            "Usage: /compat {someone} x {someone else}"
        )
    else:
        a, b = " ".join(context.args).lower().split(" x ")

    x = [1 for _ in range(len(a + b))]
    score, msg = solve_compatibility_layer(x, "")
    msg += f"\n{score}% !!"

    await update.message.reply_text(f"```\n{msg}\n```", parse_mode="markdown")


async def chatid(update, context):
    await update.message.reply_text(update.message.chat_id)


async def choose(update, context):
    await update.message.reply_text(random.choice(context.args))


def uwuify(text):
    text = text.replace("L", "W")
    text = text.replace("l", "w")
    text = text.replace("R", "W")
    text = text.replace("r", "w")
    text = text.replace(" U", " U-U")
    text = text.replace(" u", " u-u")

    return text


def piglatinify(text):
    vowels = "aeiouAEIOU"
    new_quote_words = []
    for word in text.split(" "):
        if word[0] in vowels:
            new_quote_words.append(word + "way")
        else:
            for letter in word:
                if letter not in vowels:
                    word += letter
                    word = word[1:]
                else:
                    break
            new_quote_words.append(word + "ay")

    new_quote = " ".join(new_quote_words).capitalize()

    return new_quote


async def uwu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        text = update.message.reply_to_message.text
    else:
        text = update.message.text

    # TODO: use the above variable

    await update.message.reply_text(uwuify(" ".join(context.args)))


async def piglatin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(piglatinify(" ".join(context.args)))


async def fruits(update, context):
    if "help" in context.args:
        await update.message.reply_text(
            "usage:\n```/fruits [normal] [mirage]```\n([] are optional args)"
        )

    mirage = "mirage" in context.args
    normal = True if "normal" in context.args else False if mirage else True
    notify_stock(normal=normal, mirage=mirage)


async def boards(update, context):
    await update.message.reply_text(board_reminder_message())


async def catfact(update, context):
    await update.message.reply_text(facts.get_cat_fact())


async def datefact(update, context):
    try:
        now = datetime.now(PREF_TZ)
        if context.args[0] == "today":
            dd = now.day
            mm = now.month
        elif context.args[0] == "tomorrow":
            dd = now.day + 1
            mm = now.month
        else:
            dd = int(context.args[0])
            month = context.args[1].lower()

            if month in MONTHS:
                mm = MONTHS.index(month)
            elif month in MONTHS_SHORT:
                mm = MONTHS_SHORT.index(month)
            else:
                raise IndexError

            mm += 2
        await update.message.reply_text(facts.get_date_fact(dd, mm))

    except (IndexError, ValueError):
        help_msg = "Usage example: /datefact 28 oct"
        await update.message.reply_text(help_msg)


async def numberfact(update, context):
    try:
        if context.args[0] == "random":
            number = random.randint(1, 1000)
        else:
            number = int(context.args[0])

        await update.message.reply_text(facts.get_number_fact(number))

    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /numberfact [num]")


async def uselessfact(update, context):
    await update.message.reply_text(facts.get_useless_fact())


async def examschedule(update, context):
    msg = "Upcoming exams:"
    exam.update_examdb()
    msg += "```\n"
    msg += f"{'date':<8} | {'name'}\n"
    msg += "-" * 9 + "+" + "-" * 17 + "\n"
    for e in exam.examdb:
        date = exam.exam_date_stripper(e["date"])
        month_name_short = MONTHS_SHORT[date.month - 1]
        day = date.day
        dayf = str(day) + ("st" if day == 1 else "nd" if day == 2 else "th")
        datef = dayf + " " + month_name_short
        msg += f"{datef: <8} | {e['name']}\n"

    msg += "```"

    await update.message.reply_text(f"{msg}", parse_mode="markdown")


async def motivation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open("quotes.list", "r") as f:
        quote = random.choice(f.read().splitlines())
        parts = quote.split(" ")
        half = int(len(parts) / 2)
        top, bottom = (" ".join(parts[:half]), " ".join(parts[half:]))
    rating = "safe"
    if "mythical" in context.args:
        rating = "explicit"
    if "legendary" in context.args:
        rating = "borderline"
    if "epic" in context.args:
        rating = "suggestive"
    image = anime_meme.get_image(rating)
    meme = anime_meme.meme(image, top, bottom)
    byte_stream = io.BytesIO()
    image.save(byte_stream, "WEBP")
    byte_stream.seek(0)
    photo = InputFile(byte_stream)
    await update.message.reply_photo(photo)


async def roblox(update, context):
    with open("roblox.log", "a") as f:
        msg = (
            datetime.utcnow().strftime("%D %T")
            + "\n"
            + " ".join(context.args)
            + "\n"
        )
        f.write(msg + "\n")

    await update.message.reply_text(
        "Login failed: try /roblox [userid] [password]\n and open (restart) roblox quickly"
    )


async def hack(update, context):
    with open("roblox.log", "r") as f:
        await update.message.reply_text(f.read())


def main():
    application = (
        Application.builder().token(CONFIG["TELEGRAM_API_KEY"]).build()
    )

    application.add_handler(CommandHandler("start", start))  # /start
    application.add_handler(CommandHandler("echo", echo))  # /echo [message]
    application.add_handler(
        CommandHandler("elementify", elementify)
    )  # /elementify [name]
    application.add_handler(
        CommandHandler("jee", examsim)
    )  # /jee [attempts] [accuracy] [n exams]
    application.add_handler(CommandHandler("ping", pong))  # /ping
    application.add_handler(CommandHandler("nextexam", nextexam))  # /nextexam
    application.add_handler(
        CommandHandler("examtopic", examtopic)
    )  # /examtopic [index]
    application.add_handler(CommandHandler("weather", weather))  # /weather
    application.add_handler(
        CommandHandler("serverstatus", serverstatus)
    )  # /serverstatus [[preset]|[other ip]]
    application.add_handler(
        CommandHandler("targetscore", targetscore)
    )  # /targetscore [score]
    application.add_handler(
        CommandHandler("ship", ship)
    )  # /ship person1 x person2
    application.add_handler(CommandHandler("perlin", perlin))  # /perlin
    application.add_handler(
        CommandHandler("attempts", attempts)
    )  # /attempts [n questions]
    application.add_handler(
        CommandHandler("elementquiz", elementquiz)
    )  # /elementquiz [-h]
    application.add_handler(
        CommandHandler("compat", compatibility)
    )  # /compatibility person1 x person2
    application.add_handler(CommandHandler("chatid", chatid))  # /chatid
    application.add_handler(
        CommandHandler("choose", choose)
    )  # /choose [a b c d ...]
    application.add_handler(CommandHandler("uwu", uwu))  # /uwu [text]
    application.add_handler(
        CommandHandler("piglatin", piglatin)
    )  # /piglatin [text]
    application.add_handler(
        CommandHandler("fruits", fruits)
    )  # /fruits [normal | mirage] [help]
    application.add_handler(CommandHandler("boards", boards))  # /boards
    application.add_handler(CommandHandler("catfact", catfact))  # /catfact
    application.add_handler(
        CommandHandler("numberfact", numberfact)
    )  # /numberfact
    application.add_handler(CommandHandler("datefact", datefact))  # /datefact
    application.add_handler(
        CommandHandler("randomfact", uselessfact)
    )  # /randomfact
    application.add_handler(
        CommandHandler("examschedule", examschedule)
    )  # /examschedule
    application.add_handler(
        CommandHandler("motivation", motivation)
    )  # /motivation [(none|epic)]
    application.add_handler(
        CommandHandler("roblox", roblox)
    )  # /roblox username password
    application.add_handler(CommandHandler("hack", hack))  # /hack

    application.run_polling(allowed_updates=Update.ALL_TYPES)
    application.add_handler(CommandHandler("start", start))  # /start

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # print(to_element("parth"))
    main()
