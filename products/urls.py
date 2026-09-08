from django.urls import URLPattern, URLResolver, path

from .views.category import CategoryBulkView, CategoryDetailView, CategoryListView
from .views.products import ProductBulkView, ProductsDetailView, ProductsListView

urlpatterns: list[URLPattern | URLResolver] = [
    path("categories", CategoryListView.as_view(), name="categories-list"),
    path("products", ProductsListView.as_view(), name="products-list"),
    path("categories/bulk/", CategoryBulkView.as_view(), name="categories-bulk"),
    path("products/bulk/", ProductBulkView.as_view(), name="products-bulk"),
    path(
        "categories/<str:code_param>/",
        CategoryDetailView.as_view(),
        name="categories-detail",
    ),
    path(
        "products/<str:code_param>/",
        ProductsDetailView.as_view(),
        name="products-detail",
    ),
]
