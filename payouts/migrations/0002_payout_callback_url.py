from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payouts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payout',
            name='callback_url',
            field=models.URLField(blank=True, max_length=255),
        ),
    ]
