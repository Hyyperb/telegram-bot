from datetime import datetime, timedelta
from status_notifier import notify_group
import json
import exam
# from facts import get_number_fact


CONFIG = json.loads(open("config.json").read())


def days_left():
    board_date = datetime(*CONFIG["boards_date"].split("-"))
    today = datetime.today()
    dt = board_date - today

    return dt.days + 1


def board_reminder_message(days=None):
    if days is None:
        days = days_left()
    syllabus_total_days = (31 * 11) + (30 * 7) + 15
    # syllabus_progress = (syllabus_total_days - (days - 72)
    #                     ) / syllabus_total_days * 100
    try:
        next_exam_dt, next_exam_name = exam.time_till_next_exam()
    except IndexError:
        next_exam_dt = timedelta(0)
        next_exam_name = "[exam not found]"

    msg = f"{days - 14} days till january last week\n"
    msg += f"{days + 1} days left for boards\n"
    msg += f"{next_exam_name} in {next_exam_dt.days} days\n"
    # msg += f"{round(syllabus_progress, 2)}% course complete"
    return msg


if __name__ == "__main__":
    days = days_left()
    message = board_reminder_message(days)
    notify_group(message)
    print(message)
    # notify_group(f"Random fact about {days}:\n" + get_number_fact(days - 42))
