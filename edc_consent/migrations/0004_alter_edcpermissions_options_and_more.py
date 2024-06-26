# Generated by Django 4.2.7 on 2023-12-04 22:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("edc_consent", "0003_edcpermissions_locale_created_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="edcpermissions",
            options={
                "default_manager_name": "objects",
                "default_permissions": (
                    "add",
                    "change",
                    "delete",
                    "view",
                    "export",
                    "import",
                ),
                "verbose_name": "Edc Permissions",
                "verbose_name_plural": "Edc Permissions",
            },
        ),
        migrations.AddIndex(
            model_name="edcpermissions",
            index=models.Index(
                fields=["modified", "created"], name="edc_consent_modifie_851b6a_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="edcpermissions",
            index=models.Index(
                fields=["user_modified", "user_created"],
                name="edc_consent_user_mo_27c64b_idx",
            ),
        ),
    ]
