import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.db import connection

from products.models import Category, Product


class Command(BaseCommand):
    help = "Seed categories and products"

    def handle(self, *args, **options):
        confirmation = input("This will delete all users. Continue? (Y/n): ")

        if confirmation.lower() not in ("y", ""):
            print("Seed cancelled.")
            return

        file_path_categories = (
            Path(__file__).resolve().parents[2]
            / "management"
            / "seeds"
            / "categories.json"
        )
        file_path_products = (
            Path(__file__).resolve().parents[2]
            / "management"
            / "seeds"
            / "products.json"
        )

        with file_path_categories.open("r", encoding="utf-8") as file:
            data_categories = json.load(file)
        with file_path_products.open("r", encoding="utf-8") as file:
            data_products = json.load(file)

        products = [Product(**products) for products in data_products]
        categories = [Category(**categories) for categories in data_categories]

        Product.objects.all().delete()
        Category.objects.all().delete()

        sequence_sql = connection.ops.sequence_reset_sql(
            no_style(),
            [Product, Category],
        )
        
        with connection.cursor() as cursor:
            for sql in sequence_sql:
                cursor.execute(sql)
         
        Category.objects.bulk_create(categories)       
        Product.objects.bulk_create(products)
        
        print("Successfull finish seed insertions")
