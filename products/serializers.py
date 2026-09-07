from rest_framework import serializers

from .models import Category, Product


def validate_immutable_code(instance, initial_data) -> None:
    if instance is None:
        return

    if "code" not in initial_data:
        return

    if initial_data["code"] != instance.code:
        raise serializers.ValidationError({"code": "Code cannot be modified."})
        
def validate_unknown_fields(
    fields: dict, initial_data: dict, is_bulk: bool = False
) -> None:
    if is_bulk and "code" not in initial_data:
        raise serializers.ValidationError({"code": "This field is required."})

    unknown_fields = set(initial_data.keys()) - set(fields.keys())

    if unknown_fields:
        raise serializers.ValidationError(
            {
                "unknown_fields": (
                    f"Fields not allowed: {', '.join(sorted(unknown_fields))}"
                )
            }
        )

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            "code",
            "name",
            "is_active",
        )
        
    def to_internal_value(self, data):
        validate_unknown_fields(self.fields, data)

        return super().to_internal_value(data)

    def validate(self, attrs):
        validate_immutable_code(self.instance, self.initial_data)

        return attrs
        
        
class ProductSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Category.objects.all(),
    )
    
    class Meta:
        model = Product
        fields = (
            "code",
            "name",
            "description",
            "price",
            "stock",
            "is_active",
            "category",
        )
        
    def to_internal_value(self, data):
        validate_unknown_fields(self.fields, data)

        return super().to_internal_value(data)

    def validate(self, attrs):
        validate_immutable_code(self.instance, self.initial_data)

        return attrs