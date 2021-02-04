import logging
from slacker import Slacker
from settings import SLACK_TOKEN, BASE_URL, DEFAULT_FROM_EMAIL
from django.core.mail import EmailMessage
from django.contrib.auth.models import User

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


def send_load_data_email(user, guid, namespace, name, individual_ids):
    for data_manager in User.objects.filter(is_staff = True):
        email_content = """
        Hi there {full_name}--
    
        Collaborator project manager {user_name}/email{email} has created a new project with a GUID:
          {guid}
        from an AnVIL workspace {namespace}/{name}.

        The new project is ready for loading. The created individual IDs are in attached file.
    
        Thanks!
        """.format(
            full_name = data_manager.get_full_name(),
            user_name = user.get_full_name(),
            email = user.email,
            guid = guid,
            namespace = namespace,
            name = name,
        )
        mail = EmailMessage('Requesting loading AnVIL workspace data', email_content, DEFAULT_FROM_EMAIL, [data_manager.email])
        mail.attach('individual IDs', str(individual_ids), 'text/plain')
        mail.send()
