def create_model_instance(model_class, validated_data, *, relation_id_fields=None):
    relation_id_fields = relation_id_fields or ()
    payload = validated_data.copy()
    relation_values = {field_name: payload.pop(field_name, None) for field_name in relation_id_fields}
    return model_class.objects.create(**relation_values, **payload)


def update_model_instance(instance, validated_data, *, relation_id_fields=None):
    relation_id_fields = relation_id_fields or ()
    payload = validated_data.copy()
    relation_values = {field_name: payload.pop(field_name, None) for field_name in relation_id_fields}

    for field_name, value in payload.items():
        setattr(instance, field_name, value)
    for field_name, value in relation_values.items():
        setattr(instance, field_name, value)

    instance.save()
    return instance
