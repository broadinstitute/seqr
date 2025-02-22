from django.db import migrations


def update_urls(apps, schema_editor):
    PaLocusList = apps.get_model('panelapp', 'PaLocusList')

    # Replace the old domain with the new domain in the url field
    for entry in PaLocusList.objects.filter(url__startswith='https://panelapp.agha.umccr.org'):
        entry.url = entry.url.replace('https://panelapp.agha.umccr.org', 'https://panelapp-aus.org')
        entry.save()


class Migration(migrations.Migration):
    dependencies = [
        ('panelapp', '0002_auto_20210915_1049'),
    ]

    operations = [
        migrations.RunPython(update_urls),
    ]
