import logging
from slacker import Slacker
import requests

from reference_data.management.commands.utils.download_utils import download_gcs_file_as_bytes
from settings import SLACK_TOKEN, BASE_URL
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from notifications.signals import notify


BASE_EMAIL_TEMPLATE = 'Dear seqr user,\n\n{}\n\nAll the best,\nThe seqr team'

SLACK_GET_UPLOAD_URL = 'https://slack.com/api/files.getUploadURLExternal'
SLACK_COMPLETE_UPLOAD = 'https://slack.com/api/files.completeUploadExternal'

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

def safe_upload_gcs_file_to_slack(channel_id, gcs_file_path, uploaded_filename, message):
    try:
        _upload_gcs_file_to_slack(channel_id, gcs_file_path, uploaded_filename, message)
    except Exception as e:
        logger.error('Slack error: {}: Original message in channel ({}) - {}'.format(e, channel_id, message))


def _upload_gcs_file_to_slack(channel_id, gcs_file_path, uploaded_filename, message):
    file_content = download_gcs_file_as_bytes(gcs_file_path)

    # https://api.slack-gov.com/messaging/files#uploading_files
    # Note: slackbot needs files:read and files:write scopes
    # Step 1: Create the file upload URL
    headers = {"Authorization": f'Bearer {SLACK_TOKEN}'}
    upload_url_resp = requests.get(
        SLACK_GET_UPLOAD_URL,
        headers=headers,
        params={
            "length": len(file_content),
            "filename": uploaded_filename
        }
    )
    upload_url = upload_url_resp.json().get('upload_url')
    file_id = upload_url_resp.json().get('file_id')

    # Step 2: Post the contents of the file to the upload URL
    requests.post(
        upload_url,
        headers=headers,
        data=file_content
    )

    # Step 3: Finalize the upload
    complete_upload_res = requests.post(
        SLACK_COMPLETE_UPLOAD,
        headers=headers,
        json={
            "files": [{"id": file_id}],
            "channel_id": channel_id,
            "initial_comment": message,
        }
    )
    return complete_upload_res.raw

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


def send_project_notification(project, notification, email, subject):
    users = project.subscribers.user_set.all()
    notify.send(project, recipient=users, verb=notification)
    email_kwargs = dict(
        email_body=BASE_EMAIL_TEMPLATE.format(email),
        to=list(users.values_list('email', flat=True)),
        subject=subject,
        process_message=_set_bulk_notification_stream,
    )
    try:
        send_html_email(**email_kwargs)
    except Exception as e:
        logger.error(f'Error sending project email for {project.guid}: {e}', extra={'detail': email_kwargs})


def _set_bulk_notification_stream(message):
    set_email_message_stream(message, 'seqr-notifications')
    # Use batch API: emails are all sent with a single request and each recipient sees only their own email address
    message.merge_data = {}


def set_email_message_stream(message, stream):
    message.esp_extra = {
        'MessageStream': stream,
    }

