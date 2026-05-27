import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("history", "0003_portfolio_cascade"),
    ]

    operations = [
        migrations.AlterField(
            model_name="history",
            name="portfolio",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="history",
                to="portfolio.portfolio",
            ),
        ),
    ]
