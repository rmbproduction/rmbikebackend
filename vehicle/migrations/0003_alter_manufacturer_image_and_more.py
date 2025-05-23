# Generated by Django 5.2 on 2025-05-10 19:49

import cloudinary.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("vehicle", "0002_alter_uservehicle_manufacturer_name_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="manufacturer",
            name="image",
            field=cloudinary.models.CloudinaryField(
                blank=True, max_length=255, null=True, verbose_name="image"
            ),
        ),
        migrations.AlterField(
            model_name="uservehicle",
            name="vehicle_image",
            field=cloudinary.models.CloudinaryField(
                blank=True, max_length=255, null=True, verbose_name="vehicle_image"
            ),
        ),
        migrations.AlterField(
            model_name="vehicleimage",
            name="image",
            field=cloudinary.models.CloudinaryField(
                max_length=255, verbose_name="image"
            ),
        ),
        migrations.AlterField(
            model_name="vehiclemodel",
            name="image",
            field=cloudinary.models.CloudinaryField(
                blank=True, max_length=255, null=True, verbose_name="image"
            ),
        ),
        migrations.AlterField(
            model_name="vehiclemodel",
            name="image_back",
            field=cloudinary.models.CloudinaryField(
                blank=True, max_length=255, null=True, verbose_name="image_back"
            ),
        ),
        migrations.AlterField(
            model_name="vehiclemodel",
            name="image_front",
            field=cloudinary.models.CloudinaryField(
                blank=True, max_length=255, null=True, verbose_name="image_front"
            ),
        ),
        migrations.AlterField(
            model_name="vehiclemodel",
            name="image_side",
            field=cloudinary.models.CloudinaryField(
                blank=True, max_length=255, null=True, verbose_name="image_side"
            ),
        ),
        migrations.AlterField(
            model_name="vehiclemodel",
            name="thumbnail",
            field=cloudinary.models.CloudinaryField(
                blank=True, max_length=255, null=True, verbose_name="thumbnail"
            ),
        ),
        migrations.AlterField(
            model_name="vehicletype",
            name="image",
            field=cloudinary.models.CloudinaryField(
                blank=True, max_length=255, null=True, verbose_name="image"
            ),
        ),
    ]
