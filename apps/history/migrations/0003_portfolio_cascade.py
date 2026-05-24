import django.db.models.deletion
from django.db import migrations, models


def delete_history_without_portfolio(apps, schema_editor):
    History = apps.get_model("history", "History")
    History.objects.filter(portfolio_id__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("history", "0002_alter_history_table"),
        ("portfolio", "0002_alter_portfolio_table"),
    ]

    operations = [
        migrations.RunPython(delete_history_without_portfolio, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="history",
            name="portfolio",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="history",
                to="portfolio.portfolio",
            ),
        ),
    ]
