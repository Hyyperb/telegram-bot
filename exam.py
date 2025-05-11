import requests
import json
from datetime import datetime, timezone, timedelta

CONFIG = json.loads(open("config.json").read())
examdb = []
PREF_TZ_HRS, PREF_TZ_MINS = map(int, CONFIG["timezone"].split(":"))
PREF_TZ = timezone(timedelta(hours=PREF_TZ_HRS, minutes=PREF_TZ_MINS))
headers = {
    "Content-Type": "application/json",
    "X-Access-Key": "",
}


def update_examdb():
    global examdb
    if not len(examdb):
        examdb = json.loads(
            requests.get(
                f"https://api.jsonbin.io/v3/b/{CONFIG['JSONBIN_BUCKET_ID']}",
                headers=headers,
            ).text
        )["record"]["exams"]


def exam_date_stripper(date_str: str) -> datetime:
    format = "%Y-%m-%d %H:%M"
    return datetime.strptime(date_str, format).replace(tzinfo=PREF_TZ)


def get_next_exam_data(index=1):
    update_examdb()
    # it is assumed that the entries are sorted by dates
    now = datetime.now(PREF_TZ)
    for exam in examdb:
        exam_date = exam_date_stripper(exam["date"])
        if exam_date > now:
            if index == 1:
                return exam
            else:
                index -= 1
    else:
        raise IndexError("No exam found")


def time_till_next_exam():
    next_exam = get_next_exam_data()
    exam_date = exam_date_stripper(next_exam["date"])
    now = datetime.now(PREF_TZ)
    dt = exam_date.astimezone(PREF_TZ) - now
    exam_name = next_exam["name"]
    print(now, exam_date.astimezone(PREF_TZ), dt)
    return dt, exam_name
