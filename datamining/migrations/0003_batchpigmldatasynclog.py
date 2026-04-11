import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('batch', '0004_alter_pigbatches_batch_code_and_more'),
        ('datamining', '0002_replace_datamining_with_pigmldata'),
    ]

    operations = [
        migrations.CreateModel(
            name='BatchPigMLSyncLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_code', models.CharField(db_index=True, max_length=120)),
                ('source_sample_date', models.DateTimeField()),
                ('old_age', models.IntegerField()),
                ('new_age', models.IntegerField()),
                ('old_avg_weight', models.FloatField()),
                ('new_avg_weight', models.FloatField()),
                ('old_growth_stage_code', models.CharField(blank=True, max_length=120)),
                ('new_growth_stage_code', models.CharField(max_length=120)),
                ('synced_at', models.DateTimeField(auto_now_add=True)),
                (
                    'batch',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='pig_ml_sync_logs',
                        to='batch.pigbatches',
                    ),
                ),
            ],
            options={
                'ordering': ['-synced_at', 'batch_code'],
            },
        ),
        migrations.AddConstraint(
            model_name='batchpigmlsynclog',
            constraint=models.UniqueConstraint(
                fields=('batch', 'source_sample_date'),
                name='unique_batch_sync_log_per_sample_date',
            ),
        ),
    ]
