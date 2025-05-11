# About

A multipurpose private telegram bot for developed specifically for that one telegram group chat.

# Features

- fetching weather
- fetching minecraft server status (api wrapper with added aternos servers support and notification when server is started)
- fetching blox fruits stocks
- fetching exams data (self hosted data)
- calculations and simulations for JEE
- fetch anime image with motivational text
- other fun & utility commands

# Complete Setup

- Get a telegram bot api key from @BotFather
- Create a jsonbin.io bucket
- Optionally add cron jobs for blox.py exam.py status_notifier.py board_notifier.py as preferred
- Edit config.json and configure everything.
- Generate commands list with gencommands.sh and add it botfather
- Run main.py to start the bot
- use /chatid to get the group chat id and add it to config.json
