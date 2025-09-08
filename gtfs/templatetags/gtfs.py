from django import template
from .. import models

register = template.Library()

@register.filter(name="shape_points_js")
def shape_points_js(shape: models.Shape):
    out = "["
    for p in shape.points.all():
        out += f"[{p.lat},{p.lon}],"
    out += "]"
    return out