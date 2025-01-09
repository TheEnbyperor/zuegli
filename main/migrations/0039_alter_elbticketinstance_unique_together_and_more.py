from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0038_alter_elbticketinstance_unique_together_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='elbticketinstance',
            name='pnr',
        ),
        migrations.RemoveField(
            model_name='elbticketinstance',
            name='sequence_number',
        ),
        migrations.RemoveField(
            model_name='uicticketinstance',
            name='reference',
        ),
        migrations.RemoveField(
            model_name='vdvticketinstance',
            name='ticket_number',
        ),
        migrations.AlterField(
            model_name='elbticketinstance',
            name='barcode_hash',
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name='sncfticketinstance',
            name='barcode_hash',
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name='ssbticketinstance',
            name='barcode_hash',
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name='uicticketinstance',
            name='barcode_hash',
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name='vdvticketinstance',
            name='barcode_hash',
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
