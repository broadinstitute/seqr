from slacker import Slacker
from settings import SLACK_TOKEN


def post_to_slack(channel, message):
    if not SLACK_TOKEN:
        return None

    slack = Slacker(SLACK_TOKEN)
    response = slack.chat.post_message(
        channel, message, as_user=False, icon_emoji=":beaker:", username="Beaker (engineering-minion)",
    )
    return response.raw
