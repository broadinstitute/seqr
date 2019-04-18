from django.core.management.base import BaseCommand
from django.db.models import F
from xbrowse_server.base.models import UserProfile


class Command(BaseCommand):

    def handle(self, *args, **options):
        count = 0
        errors = []
        for profile in UserProfile.objects.exclude(display_name='').exclude(display_name=F('user__email')).prefetch_related('user'):
            split_name = profile.display_name.split()
            profile.user.first_name = split_name[0]
            profile.user.last_name = ' '.join(split_name[1:])
            try:
                profile.user.save()
            except Exception as e:
                errors.append('Display name: {}, email: {} ({})'.format(profile.display_name, profile.user.email, e))
            count += 1
        print('Update {} users'.format(count))
        if errors:
            print('Unable to migrate the following users:')
            for error in errors:
                print(error)

