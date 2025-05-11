from urllib.parse import urlencode
from urllib.request import urlretrieve
import requests
import json

CONFIG = json.loads(open("config.json").read())

API = f"https://api.telegram.org/bot{CONFIG['TELEGRAM_API_KEY']}/sendMessage?"

SERVER_IP = CONFIG["servers"][0]

status_message = {
    True: "The server is online",
    False: "The server have gone offline",
}


def send_message(chat_id, text):
    qstr = urlencode(
        {
            "parse_mode": "HTML",
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    )

    url = API + qstr
    response = urlretrieve(url)
    return response


def notify_group(msg):
    return send_message(CONFIG["TELEGRAM_GROUP_ID"], msg)


def get_server_status(server_ip):
    api_url = "https://api.mcstatus.io/v2/status/java/"
    print(f"getting server status for {server_ip}")
    return json.loads(requests.get(api_url + server_ip).text)


if __name__ == "__main__":
    status = get_server_status(SERVER_IP)
    if status["online"] and status["version"]["protocol"] > 0:
        ping = True
    else:
        ping = False

    try:
        with open(".status") as f:
            past_ping = bool(int(f.read()[0]))
    except (ValueError, IndexError):
        past_ping = False  # workaround

    if ping != past_ping:
        notify_group(status_message[ping])
        print(status)

        with open(".status", "w") as f:
            f.write(str(int(ping)))
