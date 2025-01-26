from django import template

register = template.Library()


@register.filter(name="proto_has_field")
def proto_has_field(msg, field_name: str) -> bool:
    return msg.HasField(field_name)