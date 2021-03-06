# Generated by Django 2.0.1 on 2018-01-24 18:51

from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import kuro.web.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Experiment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.CharField(max_length=100)),
                ('identifier', models.CharField(max_length=200)),
                ('hyper_parameters', jsonfield.fields.JSONField(default=dict)),
                ('n_trials', models.IntegerField(default=1)),
            ],
        ),
        migrations.CreateModel(
            name='Metric',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('mode', models.CharField(choices=[('max', 'max'), ('min', 'min')], max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metric', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='web.Metric')),
            ],
        ),
        migrations.CreateModel(
            name='ResultValue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step', models.IntegerField(default=0)),
                ('value', models.FloatField()),
                ('result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='result_values', to='web.Result')),
            ],
            options={
                'ordering': ('result', 'step'),
            },
        ),
        migrations.CreateModel(
            name='Trial',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('complete', models.BooleanField(default=False)),
                ('experiment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trials', to='web.Experiment')),
            ],
            options={
                'ordering': ('id',),
            },
        ),
        migrations.CreateModel(
            name='Worker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('active', models.BooleanField(default=False)),
                ('cpu_brand', models.CharField(default='', max_length=200)),
                ('memory', models.FloatField(default=0)),
                ('gpus', jsonfield.fields.JSONField(default=kuro.web.models.gpus_default)),
            ],
        ),
        migrations.AddField(
            model_name='trial',
            name='worker',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web.Worker'),
        ),
        migrations.AddField(
            model_name='result',
            name='trial',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='web.Trial'),
        ),
        migrations.AddField(
            model_name='experiment',
            name='metrics',
            field=models.ManyToManyField(blank=True, to='web.Metric'),
        ),
        migrations.AlterUniqueTogether(
            name='resultvalue',
            unique_together={('result', 'step')},
        ),
        migrations.AlterUniqueTogether(
            name='experiment',
            unique_together={('group', 'identifier', 'hyper_parameters')},
        ),
    ]
