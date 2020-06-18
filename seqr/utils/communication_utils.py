from __future__ import unicode_literals

import logging
from slacker import Slacker
from settings import SLACK_TOKEN, BASE_URL

logger = logging.getLogger(__name__)


def post_to_slack(channel, message):
    if not SLACK_TOKEN:
        logger.info(message)
        return None

    slack = Slacker(SLACK_TOKEN)
    response = slack.chat.post_message(
        channel, message, as_user=False, icon_emoji=":beaker:", username="Beaker (engineering-minion)",
    )
    return response.raw


def send_welcome_email(user, referrer):
    email_content = """
    Hi there {full_name}--

    {referrer} has added you as a collaborator in seqr.

    Please click this link to set up your account:
    {base_url}users/set_password/{password_token}

    Thanks!
    """.format(
        full_name=user.get_full_name(),
        referrer=referrer.get_full_name() or referrer.email,
        base_url=BASE_URL,
        password_token=user.password,
    )
    user.email_user('Set up your seqr account', email_content, fail_silently=False)
