# Generated by Django 3.2.11 on 2022-03-15 19:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('matchmaker', '0003_auto_20201123_2111'),
    ]

    operations = [
        migrations.AlterField(
            model_name='matchmakersubmission',
            name='individual',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='seqr.individual'),
        ),
    ]
