import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import formset_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from django_form_builder.utils import (get_as_dict,
                                       get_labeled_errors,
                                       get_POST_as_json,
                                       set_as_dict)
from organizational_area.models import (OrganizationalStructure,
                                        OrganizationalStructureOffice,)
from uni_ticket.decorators import *
from uni_ticket.forms import *
from uni_ticket.models import *
from uni_ticket.settings import *
from uni_ticket.utils import *


@login_required
def ticket_new_preload(request, struttura_slug=None):
    """
    Choose the OrganizationalStructure and the category of the ticket

    :type structure_slug: String

    :param structure_slug: slug of structure

    :return: render
    """
    if Ticket.number_limit_reached_by_user(request.user):
        messages.add_message(request, messages.ERROR,
                             _("Hai raggiunto il limite massimo giornaliero"
                               " di ticket: {}".format(MAX_DAILY_TICKET_PER_USER)))
        return redirect(reverse('uni_ticket:user_dashboard'))

    strutture = OrganizationalStructure.objects.filter(is_active=True)
    categorie = None
    template = "user/new_ticket_preload.html"
    title = _("Apri un nuovo ticket")
    sub_title = _("Seleziona la struttura")
    if struttura_slug:
        struttura = get_object_or_404(OrganizationalStructure,
                                      slug=struttura_slug,
                                      is_active=True)
        categorie = TicketCategory.objects.filter(organizational_structure=struttura.pk,
                                                  is_active=True)
        # User roles
        is_employee = user_is_employee(request.user)
        is_user = user_is_in_organization(request.user)

        if is_employee and is_user:
            categorie = categorie.filter(Q(allow_employee=True) |
                                         Q(allow_user=True) |
                                         Q(allow_guest=True))
        elif is_employee:
            categorie = categorie.filter(Q(allow_employee=True) |
                                         Q(allow_guest=True))
        elif is_user:
            categorie = categorie.filter(Q(allow_user=True) |
                                         Q(allow_guest=True))
        else:
            categorie = categorie.filter(allow_guest=True)

        sub_title = _("Seleziona la Categoria")
    d = {'categorie': categorie,
         'struttura_slug': struttura_slug,
         'strutture': strutture,
         'sub_title': sub_title,
         'title': title,}
    return render(request, template, d)

@login_required
def ticket_add_new(request, struttura_slug, categoria_slug):
    """
    Create the ticket

    :type structure_slug: String
    :type categoria_slug: String

    :param structure_slug: slug of structure
    :param categoria_slug: slug of category

    :return: render
    """
    if Ticket.number_limit_reached_by_user(request.user):
        messages.add_message(request, messages.ERROR,
                             _("Hai raggiunto il limite massimo giornaliero"
                               " di ticket: {}".format(MAX_DAILY_TICKET_PER_USER)))
        return redirect(reverse('uni_ticket:user_dashboard'))

    struttura = get_object_or_404(OrganizationalStructure,
                                  slug=struttura_slug,
                                  is_active=True)
    categoria = get_object_or_404(TicketCategory,
                                  slug=categoria_slug,
                                  is_active=True)

    if not categoria.allowed_to_user(request.user):
        return custom_message(request, _("Permesso negato a questa tipologia di utente."),
                              struttura.slug)

    title = _("Apri un nuovo ticket")
    template = 'user/ticket_add_new.html'
    sub_title = _("Compila i campi richiesti")
    modulo = get_object_or_404(TicketCategoryModule,
                               ticket_category=categoria,
                               is_active=True)
    form = modulo.get_form(show_conditions=True)
    clausole_categoria = categoria.get_conditions()
    d={'categoria': categoria,
       'conditions': clausole_categoria,
       'form': form,
       'struttura': struttura,
       'sub_title': sub_title,
       'title': title}
    if request.POST:
        form = modulo.get_form(data=request.POST,
                               files=request.FILES,
                               show_conditions=True)
        d['form'] = form

        if form.is_valid():
            fields_to_pop = [TICKET_CONDITIONS_FIELD_ID,
                             TICKET_SUBJECT_ID,
                             TICKET_DESCRIPTION_ID]
            json_data = get_POST_as_json(request=request,
                                         fields_to_pop=fields_to_pop)
            # make a UUID based on the host ID and current time
            code = uuid_code()
            subject = request.POST.get(TICKET_SUBJECT_ID)
            description = request.POST.get(TICKET_DESCRIPTION_ID)
            ticket = Ticket(code=code,
                            subject=subject,
                            description=description,
                            modulo_compilato=json_data,
                            created_by=request.user,
                            input_module=modulo)
            ticket.save()

            # salvataggio degli allegati nella cartella relativa
            json_dict = json.loads(ticket.modulo_compilato)
            json_stored = get_as_dict(compiled_module_json=json_dict)
            if request.FILES:
                json_stored["allegati"] = {}
                path_allegati = get_path_allegato(ticket)
                for key, value in request.FILES.items():
                    salva_file(request.FILES.get(key),
                               path_allegati,
                               request.FILES.get(key)._name)
                    value = request.FILES.get(key)._name
                    json_stored["allegati"]["{}".format(key)]="{}".format(value)
                set_as_dict(ticket, json_stored)
            office = categoria.organizational_office or struttura.get_default_office()
            if not office:
                messages.add_message(request, messages.ERROR,
                                     _("Nessun ufficio di default impostato"))
                return redirect(reverse('uni_ticket:user_dashboard'))

            ticket_assignment = TicketAssignment(ticket=ticket,
                                                 office=office,
                                                 assigned_by=request.user)
            ticket_assignment.save()
            ticket_detail_url = reverse('uni_ticket:ticket_detail', args=[code])

            # Send mail to ticket owner
            mail_params = {'hostname': settings.HOSTNAME,
                           'user': request.user,
                           'status': _('submitted'),
                           'ticket': ticket
                          }
            m_subject = _('{} - ticket {} submitted'.format(settings.HOSTNAME,
                                                            ticket))
            send_custom_mail(subject = m_subject,
                             body=NEW_TICKET_UPDATE.format(**mail_params),
                             recipient=request.user)
            # END Send mail to ticket owner

            messages.add_message(request, messages.SUCCESS,
                                 _("Ticket creato con successo "
                                   "con il codice <b>{}</b>").format(code))
            return redirect('uni_ticket:ticket_detail',
                            ticket_id=ticket.code)
        else:
            for k,v in get_labeled_errors(form).items():
                messages.add_message(request, messages.ERROR,
                                     "<b>{}</b>: {}".format(k, strip_tags(v)))
    return render(request, template, d)

@login_required
def dashboard(request):
    """
    Dashboard of user, with tickets list

    :return: render
    """
    # Ci pensa datatables a popolare la tabella
    title =_("Dashboard")
    sub_title = _("Livello utente semplice")
    template = "user/dashboard.html"
    tickets = Ticket.objects.filter(created_by=request.user)
    non_gestiti = tickets.filter(is_taken=False,
                                 is_closed=False)
    aperti = tickets.filter(is_taken=True, is_closed=False)
    chiusi = tickets.filter(is_closed=True)

    messages = 0
    for ticket in tickets:
        messages += ticket.get_unread_replies(want_structure=True)

    d = {'ticket_messages': messages,
         'priority_levels': PRIORITY_LEVELS,
         'sub_title': sub_title,
         'ticket_aperti': aperti,
         'ticket_chiusi': chiusi,
         'ticket_non_gestiti': non_gestiti,
         'title': title,}
    return render(request, template, d)

@login_required
@is_the_owner
@ticket_is_not_taken
def ticket_edit(request, ticket_id):
    """
    Edit ticket details while it is unassigned
    Note: formset validation is in widget (._fill_body method)

    :type ticket_id: String

    :param ticket_id: ticket code

    :return: render
    """
    ticket = get_object_or_404(Ticket, code=ticket_id)
    categoria = ticket.input_module.ticket_category
    title = _("Modifica ticket")
    sub_title = ticket
    allegati = ticket.get_allegati_dict()
    path_allegati = get_path_allegato(ticket)
    form = ticket.compiled_form(files=None, remove_filefields=allegati)
    form_allegati = ticket.compiled_form(files=None,
                                         remove_filefields=False,
                                         remove_datafields=True)
    template = "user/ticket_edit.html"
    d = {'allegati': allegati,
         'categoria': categoria,
         'form': form,
         'form_allegati': form_allegati,
         'path_allegati': path_allegati,
         'sub_title': sub_title,
         'ticket': ticket,
         'title': title,}
    if request.method == 'POST':
        fields_to_pop = [TICKET_CONDITIONS_FIELD_ID]
        json_post = get_POST_as_json(request=request,
                                     fields_to_pop=fields_to_pop)
        json_response=json.loads(json_post)
        # Costruisco il form con il json dei dati inviati e tutti gli allegati
        # json_response["allegati"]=allegati
        # rimuovo solo gli allegati che sono stati già inseriti
        modulo = ticket.get_form_module()
        form = modulo.get_form(data=json_response,
                               files=request.FILES,
                               remove_filefields=allegati)

        d['form'] = form

        if form.is_valid():
            if request.FILES:
                json_response["allegati"] = allegati
                path_allegati = get_path_allegato(ticket)
                for key, value in request.FILES.items():
                    # form.validate_attachment(request.FILES.get(key))
                    salva_file(request.FILES.get(key),
                               path_allegati,
                               request.FILES.get(key)._name)
                    nome_allegato = request.FILES.get(key)._name
                    json_response["allegati"]["{}".format(key)] = "{}".format(nome_allegato)
            elif allegati:
                # Se non ho aggiornato i miei allegati lasciandoli invariati rispetto
                # all'inserimento precedente
                json_response["allegati"] = allegati
            # salva il modulo
            ticket.save_data(request.POST.get(TICKET_SUBJECT_ID),
                             request.POST.get(TICKET_DESCRIPTION_ID),
                             json_response)
            # data di modifica
            ticket.update_history(user=request.user,
                                  note=_("Modifica ticket"))
            # Allega il messaggio al redirect
            messages.add_message(request, messages.SUCCESS,
                                 _("Modifica effettuata con successo"))
            return redirect('uni_ticket:ticket_edit', ticket_id=ticket_id)
        else:
            for k,v in get_labeled_errors(form).items():
                messages.add_message(request, messages.ERROR,
                                     "<b>{}</b>: {}".format(k, strip_tags(v)))

    return render(request, template, d)

@login_required
@is_the_owner
@ticket_is_not_taken
def delete_my_attachment(request, ticket_id, attachment):
    """
    Delete ticket attachment while it is unassigned
    Note: it must be called by a dialogbox with user confirmation

    :type ticket_id: String
    :type attachment: String

    :param ticket_id: ticket code
    :param attachment: attachment name

    :return: redirect
    """
    ticket = get_object_or_404(Ticket, code=ticket_id)
    json_dict = json.loads(ticket.modulo_compilato)
    ticket_details = get_as_dict(compiled_module_json=json_dict)
    nome_file = ticket_details["allegati"]["{}".format(attachment)]

    # Rimuove il riferimento all'allegato dalla base dati
    del ticket_details["allegati"]["{}".format(attachment)]
    path_allegato = get_path_allegato(ticket)

    # Rimuove l'allegato dal disco
    elimina_file(file_name=nome_file,
                 path=path_allegato)
    set_as_dict(ticket, ticket_details)
    allegati = ticket.get_allegati_dict(ticket_dict=ticket_details)
    ticket.update_history(user=request.user,
                          note=_("Elimina allegato"))

    messages.add_message(request, messages.SUCCESS,
                         _("Allegato eliminato correttamente"))
    return redirect('uni_ticket:ticket_edit', ticket_id=ticket_id)

@login_required
@is_the_owner
@ticket_is_not_taken
def ticket_delete(request, ticket_id):
    """
    Delete ticket while it is unassigned
    Note: it must be called by a dialogbox with user confirmation

    :type ticket_id: String

    :param ticket_id: ticket code

    :return: redirect
    """
    ticket = get_object_or_404(Ticket, code=ticket_id)
    code = ticket.code
    json_dict = json.loads(ticket.modulo_compilato)
    ticket_details = get_as_dict(compiled_module_json=json_dict)
    if "allegati" in ticket_details:
        elimina_directory(ticket_id)

    ticket_assignment = TicketAssignment.objects.filter(ticket=ticket).first()
    ticket_assignment.delete()

    ticket_history = TicketHistory.objects.filter(ticket=ticket)
    for event in ticket_history:
        event.delete()

    # Send mail to ticket owner
    mail_params = {'hostname': settings.HOSTNAME,
                   'user': request.user,
                   'status': _('deleted'),
                   'ticket': ticket
                  }
    m_subject = _('{} - ticket {} deleted'.format(settings.HOSTNAME,
                                                  ticket))
    send_custom_mail(subject=m_subject,
                     body=NEW_TICKET_UPDATE.format(**mail_params),
                     recipient=request.user)
    # END Send mail to ticket owner

    ticket.delete()
    messages.add_message(request, messages.SUCCESS,
                         _("Ticket {} eliminato correttamente".format(code)))
    return redirect('uni_ticket:user_unassigned_ticket')

@login_required
def ticket_detail(request, ticket_id, template='user/ticket_detail.html'):
    """
    Shows ticket details

    :type ticket_id: String
    :type template: String

    :param ticket_id: ticket code
    :param attachment: template to user (can change if specified)

    :return: render
    """
    ticket = get_object_or_404(Ticket, code=ticket_id)
    json_dict = json.loads(ticket.modulo_compilato)
    ticket_details = get_as_dict(compiled_module_json=json_dict,
                                 allegati=False,
                                 formset_management=False)
    allegati = ticket.get_allegati_dict()
    path_allegati = get_path_allegato(ticket)
    ticket_form = ticket.input_module.get_form(files=allegati,
                                               remove_filefields=False)
    priority = ticket.get_priority()
    ticket_history = TicketHistory.objects.filter(ticket=ticket)
    ticket_replies = TicketReply.objects.filter(ticket=ticket)
    ticket_task = Task.objects.filter(ticket=ticket)
    ticket_dependences = ticket.get_dependences()
    title = _("Dettaglio ticket")
    sub_title = ticket
    assigned_to = []
    ticket_assignments = TicketAssignment.objects.filter(ticket=ticket)

    d={'allegati': allegati,
       'dependences': ticket_dependences,
       'details': ticket_details,
       'path_allegati': path_allegati,
       'priority': priority,
       'sub_title': sub_title,
       'ticket': ticket,
       'ticket_assignments': ticket_assignments,
       'ticket_form': ticket_form,
       'ticket_history': ticket_history,
       'ticket_task': ticket_task,
       'title': title,}
    template = template
    return render(request, template, d)

@login_required
def ticket_url(request):
    """
    Fake URL to build datatables ticket details link on click (href)
    """
    return custom_message(request, _("Permesso negato"))

@login_required
@is_the_owner
def ticket_message(request, ticket_id):
    """
    Ticket messages page

    :param ticket_id: String

    :type ticket_id: ticket code

    :return: render
    """
    ticket = get_object_or_404(Ticket, code=ticket_id)
    title = _("Messaggi")
    sub_title = ticket
    # Conversazione utente-operatori
    ticket_replies = TicketReply.objects.filter(ticket=ticket)
    form = ReplyForm()
    if ticket.is_open():
        agent_replies = ticket_replies.exclude(owner=ticket.created_by,
                                               structure=None).filter(read_by=None)
        for reply in agent_replies:
            reply.read_by = request.user
            reply.read_date = timezone.now()
            reply.save(update_fields = ['read_by', 'read_date'])

    if request.method == 'POST':
        if not ticket.is_open():
            return custom_message(request, _("Il ticket non è modificabile"))
        form = ReplyForm(request.POST, request.FILES)
        if form.is_valid():
            ticket_reply = TicketReply()
            ticket_reply.subject = request.POST.get('subject')
            ticket_reply.text = request.POST.get('text')
            ticket_reply.attachment = request.FILES.get('attachment')
            ticket_reply.ticket = ticket
            ticket_reply.owner = request.user
            ticket_reply.save()

            # Send mail to ticket owner
            mail_params = {'hostname': settings.HOSTNAME,
                           'status': _('submitted'),
                           'ticket': ticket,
                           'user': request.user
                          }
            m_subject = _('{} - ticket {} message submitted'.format(settings.HOSTNAME,
                                                                    ticket))
            send_custom_mail(subject=m_subject,
                             body=USER_TICKET_MESSAGE.format(**mail_params),
                             recipient=request.user)
            # END Send mail to ticket owner

            messages.add_message(request, messages.SUCCESS,
                                 _("Messaggio inviato con successo"))
            return redirect('uni_ticket:ticket_message',
                            ticket_id=ticket_id)
        else:
            for k,v in get_labeled_errors(form).items():
                messages.add_message(request, messages.ERROR,
                                     "<b>{}</b>: {}".format(k, strip_tags(v)))
    d={'form': form,
       'sub_title': sub_title,
       'ticket': ticket,
       'ticket_replies': ticket_replies,
       'title': title,}
    template='user/ticket_assistance.html'
    return render(request, template, d)

@login_required
@is_the_owner
def task_detail(request, ticket_id, task_id):
    """
    Task details page

    :param ticket_id: String
    :param task_id: String

    :type ticket_id: ticket code
    :type task_id: task code

    :return: render
    """
    ticket = get_object_or_404(Ticket, code=ticket_id)
    task = get_object_or_404(Task, code=task_id, ticket=ticket)
    title = _("Dettaglio task")
    d={'sub_title': task,
       'task': task,
       'title': title}
    template = "task_detail.html"
    return render(request, template, d)

@login_required
@is_the_owner
def ticket_close(request, ticket_id):
    """
    Ticket closing by owner user

    :param ticket_id: String

    :type ticket_id: ticket code

    :return: render
    """
    ticket = get_object_or_404(Ticket, code=ticket_id)
    # Se il ticket non è chiudibile (per dipendenze attive)
    if ticket.is_closed:
        return custom_message(request, _("Il ticket è già chiuso!"))
    title = _('Chiusura del ticket')
    sub_title = ticket
    form = ChiusuraForm()
    if request.method=='POST':
        form = ChiusuraForm(request.POST)
        if form.is_valid():
            motivazione = request.POST.get('note')
            ticket.is_closed = True
            ticket.motivazione_chiusura = motivazione
            ticket.data_chiusura = timezone.now()
            ticket.save(update_fields = ['is_closed',
                                         'motivazione_chiusura',
                                         'data_chiusura'])
            ticket.update_history(user = request.user,
                                  note = _("Chiusura ticket: {}".format(motivazione)))
            messages.add_message(request, messages.SUCCESS,
                                 _("Ticket {} chiuso correttamente".format(ticket)))
            return redirect('uni_ticket:ticket_detail', ticket.code)
        else:
            for k,v in get_labeled_errors(form).items():
                messages.add_message(request, messages.ERROR,
                                     "<b>{}</b>: {}".format(k, strip_tags(v)))

    template = "user/ticket_close.html"
    d = {'form': form,
         'sub_title': sub_title,
         'ticket': ticket,
         'title': title,}
    return render(request, template, d)
