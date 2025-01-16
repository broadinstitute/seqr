import logging
from slacker import Slacker

from settings import SLACK_TOKEN, BASE_URL
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from notifications.signals import notify

BASE_EMAIL_TEMPLATE = 'Dear seqr user,\n\n{}\n\nAll the best,\nThe seqr team'
EMAIL_MESSAGE_TEMPLATE = 'This is to notify you that data for {notification} has been loaded in seqr project {project_link}'

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
    email_content = f"""
    Hi there {user.get_full_name()}--

    {referrer.get_full_name() or referrer.email} has added you as a collaborator in seqr.

    Please click this link to set up your account:
    {BASE_URL}login/set_password/{user.password}

    Thanks!
    """
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


def send_project_notification(project, notification, subject, email_template=None, slack_channel=None, slack_detail=None):
    users = project.subscribers.user_set.all()
    notify.send(project, recipient=users, verb=f'Loaded {notification}')

    url = f'{BASE_URL}project/{project.guid}/project_page'

    email = (email_template or EMAIL_MESSAGE_TEMPLATE).format(
        notification=notification,
        project_link=f'<a href={url}>{project.name}</a>',
    )
    email_kwargs = dict(
        email_body=BASE_EMAIL_TEMPLATE.format(email),
        to=list(users.values_list('email', flat=True)),
        subject=subject,
    )
    try:
        send_html_email(**email_kwargs, process_message=_set_bulk_notification_stream)
    except Exception as e:
        logger.error(f'Error sending project email for {project.guid}: {e}', extra={'detail': email_kwargs})

    if slack_channel:
        slack_message = f'{notification} are loaded in <{url}|{project.name}>'
        if slack_detail:
            slack_message += f'\n```{slack_detail}```'
        safe_post_to_slack(slack_channel, slack_message)

    return url


def _set_bulk_notification_stream(message):
    set_email_message_stream(message, 'seqr-notifications')
    # Use batch API: emails are all sent with a single request and each recipient sees only their own email address
    message.merge_data = {}


def set_email_message_stream(message, stream):
    message.esp_extra = {
        'MessageStream': stream,
    }
