import logging
from slacker import Slacker
from settings import SLACK_TOKEN, BASE_URL
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


def send_load_data_email(project, base_url, data):
    email_content = """
    Data from AnVIL workspace {namespace}/{name} needs to be loaded to seqr project <a href="{base_url}/project/{guid}/project_page">{project_name}</a> (guid: {guid})

    The sample IDs to load are attached.    
    """.format(
        namespace=project.workspace_namespace,
        name=project.workspace_name,
        base_url=base_url,
        guid=project.guid,
        project_name=project.name,
    )
    mail = EmailMessage(
        subject='AnVIL data loading request',
        body=email_content,
        to=[dm.email for dm in User.objects.filter(is_staff=True)])
    mail.attach('{}_sample_ids.tsv'.format(project.guid), data)
    mail.send()
