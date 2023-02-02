# Generated by Django 3.2.16 on 2022-10-31 20:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reference_data', '0020_clingen'),
    ]

    operations = [
        migrations.AddField(
            model_name='transcriptinfo',
            name='is_mane_select',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='RefseqTranscript',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('refseq_id', models.CharField(max_length=20)),
                ('transcript', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='reference_data.transcriptinfo')),
            ],
        ),
    ]
