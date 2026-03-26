from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gestion", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="examen",
            name="url_tests_git",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="examen",
            name="hash_tests",
            field=models.CharField(blank=True, max_length=40),
        ),
    ]
