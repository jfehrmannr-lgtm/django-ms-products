from typing import Any

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Model, QuerySet
from django.http import QueryDict
from rest_framework import serializers

RESERVED_QUERY_PARAMS = {
    "page",
    "page_size",
}


def parse_filter_value(field: Any, value: str) -> Any:
    internal_type = field.get_internal_type()

    if internal_type == "BooleanField":
        return serializers.BooleanField().run_validation(value)

    if internal_type in {
        "IntegerField",
        "PositiveIntegerField",
        "PositiveSmallIntegerField",
        "BigIntegerField",
    }:
        return serializers.IntegerField().run_validation(value)

    if internal_type == "DecimalField":
        return serializers.DecimalField(
            max_digits=field.max_digits,
            decimal_places=field.decimal_places,
        ).run_validation(value)

    return value


def apply_filters(
    model: type[Model],
    filters: QueryDict,
    config: dict[str, dict[str, str]],
) -> QuerySet:
    queryset = model.objects.all()

    for key in filters:
        value = filters.get(key)

        if key in RESERVED_QUERY_PARAMS:
            continue

        if value is None:
            continue

        if key in config:
            filter_config = config[key]
            

            field_name = filter_config.get(
                "field",
                key,
            )

            lookup = filter_config.get(
                "lookup",
                "exact",
            )
            
            if lookup == "foreign_key":
                continue
        else:
            field_name = key
            lookup = "exact"

        if field_name == "id":
            raise serializers.ValidationError(
                {
                    key: "Filter not allowed.",
                }
            )

        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            raise serializers.ValidationError(
                {
                    key: "Filter not allowed.",
                }
            )

        parsed_value = parse_filter_value(
            field,
            value,
        )

        lookup_key = f"{field_name}__{lookup}"

        queryset = queryset.filter(
            **{
                lookup_key: parsed_value,
            }
        )

    return queryset
