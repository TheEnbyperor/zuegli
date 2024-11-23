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