from seqr.utils.logging_utils import SeqrLogger

logger = SeqrLogger(__name__)


def associate_groups(backend, response, user, details, *args, **kwargs):
    """
    Example on how to add groups from IDP as auth groups.
    """
    if user:
        logger.info('Associating groups to user {}'.format(user.email), user)
        # user.groups.clear()
        # for idp_group in details.get('idp_groups', []):
        #     db_group, _ = Group.objects.get_or_create(name=idp_group)
        #     user.groups.add(db_group)
    else:
        logger.warning('Skipping associating groups as user was not given.')
