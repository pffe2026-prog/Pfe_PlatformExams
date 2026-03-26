from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestion", "0003_examen_pdf_examen"),
    ]

    operations = [
        migrations.AlterField(
            model_name="soumission",
            name="url_depot_git",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name="soumission",
            name="hash_commit",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="soumission",
            name="code_source",
            field=models.TextField(blank=True),
        ),
    ]
