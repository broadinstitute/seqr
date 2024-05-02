import logging
from slacker import Slacker
from settings import SLACK_TOKEN, BASE_URL
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from notifications.signals import notify

from seqr.views.utils.terra_api_utils import google_auth_enabled

logger = logging.getLogger(__name__)


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
    if google_auth_enabled():
        setup_message = 'You can now log into seqr using your Google account:\n    {}login/google-oauth2'.format(BASE_URL)
    else:
        setup_message = 'Please click this link to set up your account:\n    {}login/set_password/{}'.format(
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


def send_html_email(email_body, process_message=None, **kwargs):
    email_message = EmailMultiAlternatives(
        body=strip_tags(email_body),
        **kwargs,
    )
    email_message.attach_alternative(email_body.replace('\n', '<br />'), 'text/html')
    if process_message:
        process_message(email_message)
    email_message.send()


def send_project_notification(project, notification, email_body, subject):
    users = project.subscribers.user_set.all()
    notify.send(project, recipient=users, verb=notification)
    send_html_email(
        email_body,
        to=list(users.values_list('email', flat=True)),
        subject=subject,
        process_message=_set_bulk_notification_stream,
    )


def _set_bulk_notification_stream(message):
    message.esp_extra = {
        'MessageStream': 'seqr-notifications',
    }
    # Use batch API: emails are all sent with a single request and each recipient sees only their own email address
    message.merge_data = {}

