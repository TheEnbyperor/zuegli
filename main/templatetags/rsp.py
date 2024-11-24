from django import template
from .. import rsp

register = template.Library()


@register.filter(name="rsp_ticket_type")
def rsp_ticket_type(type_code: str):
    return rsp.ticket_data.get_ticket_type(type_code)


@register.filter(name="rsp_ticket_restriction")
def rsp_ticket_restriction(type_code: str):
    return rsp.ticket_data.get_ticket_restriction(type_code)


@register.filter(name="rsp_station_nlc")
def rsp_station_nlc(nlc: str):
    return rsp.ticket_data.get_station_by_nlc(nlc)


@register.filter(name="rsp_station_crs")
def rsp_station_crs(nlc: str):
    return rsp.ticket_data.get_station_by_crs(nlc)


@register.filter(name="rsp_discount")
def rsp_discount(discount: int):
    return rsp.ticket_data.get_discount_by_id(discount)


@register.filter(name="rsp_route")
def rsp_route(route: int):
    return rsp.ticket_data.get_route_by_id(route)


@register.filter(name="rsp_toc")
def rsp_toc(toc: str):
    return rsp.ticket_data.get_toc_by_id(toc)