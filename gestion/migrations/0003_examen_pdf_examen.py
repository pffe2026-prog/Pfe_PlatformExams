from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestion", "0002_examen_tests_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="examen",
            name="pdf_examen",
            field=models.FileField(blank=True, null=True, upload_to="examens/pdfs/"),
        ),
    ]
