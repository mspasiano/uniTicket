import datetime
import inspect
import locale
import os
import pytz

from django import template
from django.utils import timezone
from django.utils.translation import gettext as _

from django_form_builder import dynamic_fields
from uni_ticket.models import (Ticket,
                               TicketAssignment,
                               TicketCategoryCondition,
                               TicketCategoryModule)
from uni_ticket.settings import (CONTEXT_SIMPLE_USER,
                                 MANAGEMENT_URL_PREFIX)
from uni_ticket.utils import (download_file,
                              format_slugged_name,
                              get_path_allegato,
                              get_user_type,
                              office_is_eliminabile,
                              user_manage_something)

register = template.Library()

@register.simple_tag
def not_a_simple_user(user):
    return user_manage_something(user)

@register.filter
def filename(value):
    if os.path.exists(value.path):
        return os.path.basename(value.file.name)
    return _("Risorsa non più disponibile")

# @register.filter
# def status(ticket):
    # if ticket.is_closed:
        # v = '<span class="text-danger"><b>{}</b>'.format(_('Chiuso'))
    # elif ticket.is_taken:
        # v = '<span class="text-success"><b>{}</b>'.format(_('Aperto'))
    # else:
        # v = '<span class="text-warning"><b>{}</b>'.format(_('Da prendere in carico'))
    # return v

@register.filter
def no_slugged(value):
    return format_slugged_name(value)

@register.simple_tag
def year_list():
    return range(2019, timezone.localdate().year+1)

@register.simple_tag
def current_date():
    locale.setlocale(locale.LC_ALL, 'it_IT.UTF-8')
    tz_IT = pytz.timezone('Europe/Rome')
    now = datetime.datetime.now(tz_IT)
    return now.strftime('%A, %d %B %Y')

@register.simple_tag
def ticket_in_category(category):
    result = 0
    office = category.organizational_office
    tickets = TicketAssignment.get_ticket_in_office_list(office_list=[office,])
    return len(tickets)

@register.simple_tag
def conditions_in_category(category):
    conditions = TicketCategoryCondition.objects.filter(category=category,
                                                        is_active=True).count()
    return conditions

@register.simple_tag
def simple_user_context_name():
    return CONTEXT_SIMPLE_USER

@register.simple_tag
def get_usertype(user, structure, label_value_tuple=False):
    label = get_user_type(user, structure)
    value = MANAGEMENT_URL_PREFIX[label]
    if label_value_tuple: return (label, value)
    return value

@register.simple_tag
def get_label_from_form(form, field_name):
    field = form.fields.get(field_name)
    if field: return field.label
    return False

@register.filter
def get_dyn_field_name(value):
    for m in inspect.getmembers(dynamic_fields, inspect.isclass):
        if m[0]==value: return getattr(m[1], 'field_type')
    return value

@register.simple_tag
def get_unread_replies(ticket, want_structure=True):
    replies = ticket.get_unread_replies(want_structure)
    return replies
