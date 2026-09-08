from django.db.models import QuerySet
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from products.utils.filters import apply_filters

from ..models import Product
from ..serializers import ProductSerializer, serializers


# Pagiantion
class PaginationProduct(PageNumberPagination):
    page_query_param = "page"
    page_size_query_param = "page_size"
    max_page_size = 200

    def paginate_queryset(
        self,
        queryset,
        request: Request,
        view=None,
    ):
        if "page" not in request.query_params:
            raise serializers.ValidationError(
                {"page": "This query parameter is required."}
            )

        if "page_size" not in request.query_params:
            raise serializers.ValidationError(
                {"page_size": "This query parameter is required."}
            )

        return super().paginate_queryset(
            queryset=queryset,
            request=request,
            view=view,
        )


# Products Views
@extend_schema_view(
    get=extend_schema(
        responses={200: ProductSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                default=1,
                description="Page number.",
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                default=20,
                description="Number of products per page.",
            ),
            OpenApiParameter(
                name="name",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter products by name. Partial match.",
            ),
            OpenApiParameter(
                name="is_active",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter products by active. Exact match.",
            ),
            OpenApiParameter(
                name="code",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter products by code.",
            ),
            OpenApiParameter(
                name="description",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter products by description. Partial match.",
            ),
            OpenApiParameter(
                name="min_stock",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Minimum product stock.",
            ),
            OpenApiParameter(
                name="max_stock",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Maximum product stock.",
            ),
            OpenApiParameter(
                name="min_price",
                type=float,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Minimum product price.",
            ),
            OpenApiParameter(
                name="max_price",
                type=float,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Maximum product price.",
            ),
            OpenApiParameter(
                name="category_code",
                type={"type": "array", "items": {"type": "string"}},
                location=OpenApiParameter.QUERY,
                required=False,
                description="Maximum product price.",
            ),
        ],
    ),
    post=extend_schema(
        responses={
            201: ProductSerializer,
            400: OpenApiResponse(description="Invalid category format."),
        }
    ),
)
class ProductsListView(ListCreateAPIView[Product]):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = PaginationProduct

    def get_queryset(self) -> QuerySet[Product]:
        filter_config = {
            "name": {
                "lookup": "icontains",
            },
            "code": {
                "lookup": "icontains",
            },
            "is_active": {"lookup": "exact"},
            "min_stock": {
                "field": "stock",
                "lookup": "gte",
            },
            "max_stock": {
                "field": "stock",
                "lookup": "lte",
            },
            "description": {"lookup": "icontains"},
            "min_price": {
                "field": "price",
                "lookup": "gte",
            },
            "max_price": {
                "field": "price",
                "lookup": "lte",
            },
            "category_code": {
                "lookup": "foreign_key",
            },
        }

        queryset = apply_filters(
            model=Product, config=filter_config, filters=self.request.query_params
        )

        category_code = self.request.query_params.getlist("category_code")

        if category_code:
            queryset = queryset.filter(category__code__in=category_code)

        return queryset


@extend_schema_view(
    get=extend_schema(
        responses={
            200: ProductSerializer,
            404: OpenApiResponse(description="Product code not found."),
        }
    ),
    patch=extend_schema(
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(description="Invalid product format."),
            404: OpenApiResponse(description="Product code not found."),
        },
    ),
    delete=extend_schema(
        responses={
            204: OpenApiResponse(description="Successfull code deleted."),
            404: OpenApiResponse(description="Product code not found."),
        }
    ),
)
class ProductsDetailView(RetrieveUpdateDestroyAPIView[Product]):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    lookup_field = "code"
    lookup_url_kwarg = "code_param"

    http_method_names = (
        "get",
        "patch",
        "delete",
        "head",
        "options",
    )


class ProductBulkView(APIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @extend_schema(
        request=ProductSerializer(many=True),
        responses={
            201: ProductSerializer(many=True),
            400: None,
        },
    )
    def post(self, request: Request) -> Response:
        serializers = ProductSerializer(data=request.data, many=True)

        serializers.is_valid(raise_exception=True)

        validated_data = (Product(**product) for product in serializers.validated_data)

        created_data = Product.objects.bulk_create(validated_data)

        response = ProductSerializer(instance=created_data, many=True)

        return Response(data=response.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=ProductSerializer(many=True),
        responses={
            200: ProductSerializer(many=True),
            400: ProductSerializer(many=True),
        },
    )
    def patch(self, request: Request) -> Response:
        # Obtenemos la lista de productos enviada en el body.
        data_product: list[dict] = request.data

        # Separamos los códigos de los campos que realmente serán actualizados.
        codes: list[str] = []
        products_without_codes: list[dict] = []

        for index, product in enumerate(data_product):
            # `code` es obligatorio porque lo utilizaremos para encontrar
            # la instancia existente del producto en la base de datos.
            if "code" not in product:
                raise serializers.ValidationError(
                    {index: {"code": "This field is required."}}
                )

            # Guardamos el código para posteriormente buscar los productos.
            codes.append(product["code"])

            # Creamos una copia sin `code`, ya que este campo solo identifica
            # el producto y no debe formar parte de los campos a actualizar.
            copy_product = product.copy()
            copy_product.pop("code")

            products_without_codes.append(copy_product)

        # Obtenemos las instancias existentes de Product.
        # bulk_update necesita instancias con PK, no los diccionarios del request.
        queryset = Product.objects.filter(code__in=codes)

        # Creamos un diccionario code -> Product para encontrar cada instancia
        # independientemente del orden en que el QuerySet haya sido retornado.
        products_by_code: dict[str, Product] = {
            product.code: product for product in queryset
        }

        # Verificamos que todos los códigos enviados correspondan
        # a productos existentes.
        for index, code in enumerate(codes):
            if code not in products_by_code:
                raise serializers.ValidationError(
                    {index: {"code": f"Product with code '{code}' does not exist."}}
                )

        # Validamos únicamente los campos que serán modificados.
        # `partial=True` permite que cada producto contenga solo algunos campos.
        serializer = ProductSerializer(
            data=products_without_codes,
            many=True,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        # Aquí almacenaremos las instancias modificadas y el conjunto
        # de campos que bulk_update deberá actualizar.
        products_to_update: list[Product] = []
        fields_to_update: set[str] = set()

        # Relacionamos cada código con sus datos ya validados.
        for code, validated_data in zip(codes, serializer.validated_data):
            # Recuperamos la instancia real correspondiente al código.
            product_instance = products_by_code[code]

            # Aplicamos dinámicamente cada campo validado sobre la instancia.
            for field, value in validated_data.items():
                setattr(product_instance, field, value)

                # Registramos el campo para indicárselo posteriormente a bulk_update.
                fields_to_update.add(field)

            products_to_update.append(product_instance)

        # Ejecutamos una única operación de actualización masiva.
        if fields_to_update:
            Product.objects.bulk_update(
                products_to_update,
                fields=list(fields_to_update),
            )

        # Serializamos las instancias ya actualizadas para devolverlas al cliente.
        response_serializer = ProductSerializer(
            products_to_update,
            many=True,
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="codes",
                type={"type": "array", "items": {"type": "string"}},
                location=OpenApiParameter.QUERY,
                required=True,
                description="Category codes to delete.",
            ),
        ],
    )
    def delete(self, request: Request) -> Response:
        product_codes = request.query_params.getlist("codes")

        queryset = Product.objects.filter(code__in=product_codes)

        queryset_codes = set(queryset.values_list("code", flat=True))

        queryparam_codes = set(product_codes)

        missing_codes = queryparam_codes - queryset_codes

        if missing_codes:
            raise serializers.ValidationError(
                {"codes": f"Users not found: {', '.join(sorted(missing_codes))}"}
            )

        queryset.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
