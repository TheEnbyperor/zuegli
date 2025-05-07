from django import template
from .. import flexi_ticket

register = template.Library()


@register.filter(name="ft_station")
def station(station_id: str, brand: str):
    return flexi_ticket.ticket_data.get_station(station_id, brand)


@register.filter(name="ft_ticket_product")
def ticket_product(product_id: str, brand: str):
    return flexi_ticket.ticket_data.get_ticket_product(product_id, brand)