from django.db import migrations

from seqr.utils.logging_utils import SeqrLogger

logger = SeqrLogger(__name__)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('oauth2_provider', '0004_auto_20200902_2022'),
    ]

    def update_username_match_email(apps, schema_editor):
        """
        oauth2_provider associates user access tokens (oauth2_provider_accesstoken) using username field and the
        username from MCRI Okta is email so we bulk set usernames to match their emails.
        """
        User = apps.get_model('auth', 'User')
        db_alias = schema_editor.connection.alias
        real_users = User.objects.using(db_alias).exclude(username__in=['AnonymousUser', ''])

        for user in real_users:
            logger.info('Updating user, username={}, email={}'.format(user.username, user.email), user=None)
            user.username = user.email
            user.save()

    operations = [
        # Okta tokens are very long!
        # Since this is only increasing column length, it is probably the simplest approach even though this creates
        # a mismatch between the Django model and DB table.
        migrations.RunSQL("ALTER TABLE oauth2_provider_accesstoken ALTER COLUMN token TYPE varchar(2048)"),
        migrations.RunSQL("ALTER TABLE oauth2_provider_refreshtoken ALTER COLUMN token TYPE varchar(2048)"),

        migrations.RunPython(update_username_match_email, reverse_code=migrations.RunPython.noop),
    ]
