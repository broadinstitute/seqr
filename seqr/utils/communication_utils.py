import logging
from slacker import Slacker
from settings import SLACK_TOKEN, BASE_URL
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from seqr.views.utils.terra_api_utils import anvil_enabled

logger = logging.getLogger(__name__)

ANVIL_UI_URL = 'https://anvil.terra.bio/'


def safe_post_to_slack(channel, message):
    try:
        _post_to_slack(channel, message)
    except Exception as e:
        logger.error('Slack error: {}: Original message in channel ({}) - {}'.format(e, channel, message))


def _post_to_slack(channel, message):
    if not SLACK_TOKEN:
        logger.info(message)
        return None

    slack = Slacker(SLACK_TOKEN)
    response = slack.chat.post_message(
        channel, message, as_user=False, icon_emoji=":beaker:", username="Beaker (engineering-minion)",
    )
    return response.raw


def send_welcome_email(user, referrer):
    if anvil_enabled():
        setup_message = 'Please make sure this account is registered in AnVIL by signing in to {} and registering.'.format(
            ANVIL_UI_URL
        )
        setup_message += ' Once you are registered in AnVIL, you will be able to access seqr at {}'.format(BASE_URL)
    else:
        setup_message = 'Please click this link to set up your account:\n    {}users/set_password/{}'.format(
            BASE_URL, user.password)

    email_content = """
    Hi there {full_name}--

    {referrer} has added you as a collaborator in seqr.

    {setup_message}

    Thanks!
    """.format(
        full_name=user.get_full_name(),
        referrer=referrer.get_full_name() or referrer.email,
        setup_message=setup_message,
    )
    user.email_user('Set up your seqr account', email_content, fail_silently=False)


def send_html_email(email_body, **kwargs):
    email_message = EmailMultiAlternatives(
        body=strip_tags(email_body),
        **kwargs,
    )
    email_message.attach_alternative(email_body, 'text/html')
    email_message.send()
