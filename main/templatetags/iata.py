from django import template
from .. import iata

register = template.Library()

@register.filter(name="iata_airline")
def get_iata_airline_code(value):
    if not value:
        return None
    if v := iata.codes.get_iata_airline(value):
        return v
    if v := iata.codes.get_icao_airline(value):
        return v

@register.filter(name="iata_airport")
def get_iata_airport_code(value):
    if not value:
        return None
    return iata.codes.get_iata_airport(value)
