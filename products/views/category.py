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

from ..models import Category
from ..serializers import CategorySerializer, serializers


# Pagiantion
class Pagination(PageNumberPagination):
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


# Categories Views
@extend_schema_view(
    get=extend_schema(
        responses={
            200: CategorySerializer(many=True),
        },
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
                description="Filter categories by name. Partial match.",
            ),
            OpenApiParameter(
                name="is_valid",
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter categories by email. Exact match.",
            ),
            OpenApiParameter(
                name="code",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filter categories by code.",
            ),
        ],
    ),
    post=extend_schema(
        request=CategorySerializer,
        responses={
            201: CategorySerializer,
            400: OpenApiResponse(description="Invalid category format."),
        },
    ),
)
class CategoryListView(ListCreateAPIView[Category]):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = Pagination

    def get_queryset(self) -> QuerySet[Category]:
        filter_config = {
            "name": {
                "lookup": "icontains",
            },
            "code": {
                "lookup": "icontains",
            },
            "is_active": {"lookup": "exact"},
        }

        return apply_filters(
            model=Category,
            filters=self.request.query_params,
            config=filter_config,
        )


@extend_schema_view(
    get=extend_schema(
        responses={
            200: CategorySerializer,
            404: OpenApiResponse(description="Category code not found."),
        }
    ),
    patch=extend_schema(
        request=CategorySerializer,
        responses={
            200: CategorySerializer,
            400: OpenApiResponse(description="Invalid category format."),
            404: OpenApiResponse(description="Category code not found."),
        },
    ),
    delete=extend_schema(
        responses={
            204: OpenApiResponse(description="Successfull code deleted."),
            404: OpenApiResponse(description="Category code not found."),
        }
    ),
)
class CategoryDetailView(RetrieveUpdateDestroyAPIView[Category]):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    lookup_field = "code"
    lookup_url_kwarg = "code_param"

    http_method_names = (
        "get",
        "patch",
        "delete",
        "head",
        "options",
    )


@extend_schema(
    request=CategorySerializer(many=True),
    responses={
        201: CategorySerializer(many=True),
        400: OpenApiResponse(description="Invalid category format."),
    },
)
class CategoryBulkView(APIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @extend_schema(
        request=CategorySerializer(many=True), responses=CategorySerializer(many=True)
    )
    def post(self, request: Request) -> Response:
        serializer = CategorySerializer(data=request.data, many=True)

        serializer.is_valid(raise_exception=True)

        categories = (Category(**category) for category in serializer.validated_data)

        created_categories = Category.objects.bulk_create(categories)

        response_serializer = CategorySerializer(
            instance=created_categories,
            many=True,
        )

        return Response(data=response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=CategorySerializer(many=True),
        responses={
            200: CategorySerializer(many=True),
            400: OpenApiResponse(description="Invalid category data"),
            404: OpenApiResponse(description="Category not found"),
        },
    )
    def patch(self, request: Request) -> Response:
        request_data: list[dict] = request.data

        codes: list[str] = []
        categories_without_codes: list[dict] = []

        for index, category_data in enumerate(request_data):
            if "code" not in category_data:
                raise serializers.ValidationError(
                    {index: {"code": "This field is required."}}
                )

            codes.append(category_data["code"])

            category_without_code = category_data.copy()
            category_without_code.pop("code")

            categories_without_codes.append(category_without_code)

        serialized = CategorySerializer(
            data=categories_without_codes,
            many=True,
            partial=True,
        )

        serialized.is_valid(raise_exception=True)

        query_data = Category.objects.filter(code__in=codes)

        categories_by_code: dict[str, Category] = {}

        for category in query_data:
            categories_by_code[category.code] = category

        for index, category_data in enumerate(request_data):
            code = category_data["code"]

            if code not in categories_by_code:
                raise serializers.ValidationError(
                    {index: {"code": f"Category with code '{code}' does not exist."}}
                )

        categories_to_update: list[Category] = []

        for code, update_data in zip(
            codes,
            serialized.validated_data,
        ):
            category = categories_by_code[code]

            for field, value in update_data.items():
                setattr(category, field, value)

            categories_to_update.append(category)

        Category.objects.bulk_update(
            categories_to_update,
            fields=[
                "name",
                "is_active",
            ],
        )

        response_serializer = CategorySerializer(
            instance=categories_to_update,
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
        responses=None,
    )
    def delete(self, request: Request) -> Response:
        category_codes = request.query_params.getlist("codes")

        queryset = Category.objects.filter(code__in=category_codes)

        existing_codes = set(queryset.values_list("code", flat=True))

        requested_codes = set(category_codes)

        missing_codes = requested_codes - existing_codes

        if missing_codes:
            raise serializers.ValidationError(
                {"codes": f"Users not found: {', '.join(sorted(missing_codes))}"}
            )

        queryset.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )