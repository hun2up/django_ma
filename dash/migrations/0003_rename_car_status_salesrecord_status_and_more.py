from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dash', '0002_salesrecord_car_liability_salesrecord_car_optional_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='salesrecord',
            old_name='car_status',
            new_name='status',
        ),
        migrations.RenameField(
            model_name='salesrecord',
            old_name='main_premium',
            new_name='insured',
        ),
        migrations.AlterField(
            model_name='salesrecord',
            name='product_code',
            field=models.CharField(blank=True, max_length=60, null=True, verbose_name='상품코드'),
        ),
        migrations.AlterField(
            model_name='salesrecord',
            name='product_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='상품명'),
        ),
    ]
