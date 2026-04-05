import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record', '0001_initial'),
        ('datamining', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PigMLData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('record_code', models.CharField(max_length=120, unique=True)),
                ('batch_code', models.CharField(max_length=120)),
                ('pen_code', models.CharField(max_length=120)),
                ('sample_date', models.DateTimeField()),
                ('pig_age_days', models.IntegerField()),
                ('avg_weight', models.FloatField()),
                ('total_feed_quantity', models.FloatField(default=0)),
                ('feeding_count', models.IntegerField(default=0)),
                ('avg_feeding_interval_hours', models.FloatField(default=0)),
                ('pen_capacity', models.IntegerField()),
                ('pen_status', models.CharField(max_length=120)),
                ('growth_stage', models.CharField(max_length=120)),
                ('feed_type_mode', models.CharField(blank=True, max_length=20)),
                ('device_code', models.CharField(blank=True, max_length=120)),
                ('window_days', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'record',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='pig_ml_data',
                        to='record.record',
                    ),
                ),
            ],
            options={
                'ordering': ['sample_date', 'record_code'],
            },
        ),
        migrations.DeleteModel(
            name='Datamining',
        ),
    ]
