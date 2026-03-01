from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('device', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='device',
            name='device_type',
        ),
    ]
