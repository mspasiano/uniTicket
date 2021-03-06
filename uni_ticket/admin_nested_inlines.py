import nested_admin

from django import forms
from django.contrib import admin
from django.urls import reverse

from .models import *


# Ticket Category Module Input List
class TicketCategoryInputListModelForm(forms.ModelForm):

    class Meta:
        model = TicketCategoryInputList
        fields = ('__all__')


class TicketCategoryInputListNestedInline(nested_admin.NestedTabularInline):
    model = TicketCategoryInputList
    form = TicketCategoryInputListModelForm
    sortable_field_name = "ordinamento"
    extra = 0
    classes = ['collapse',]


# Ticket Category Module Form
class TicketCategoryModuleModelForm(forms.ModelForm):

    class Meta:
        model = TicketCategoryModule
        fields = ('__all__')


class TicketCategoryModuleNestedInline(nested_admin.NestedTabularInline):
    model = TicketCategoryModule
    form = TicketCategoryModuleModelForm
    #sortable_field_name = "name"
    extra = 0
    inlines = [TicketCategoryInputListNestedInline,]


# Ticket Attachment
# class TicketAttachmentModelForm(forms.ModelForm):

    # class Meta:
        # model = TicketAttachment
        # fields = ('__all__')


# class TicketAttachmentNestedInline(nested_admin.NestedTabularInline):
    # model = TicketAttachment
    # form = TicketAttachmentModelForm
    # extra = 0


# Ticket Assignment
class TicketAssignmentModelForm(forms.ModelForm):

    class Meta:
        model = TicketAssignment
        fields = ('__all__')


class TicketAssignmentNestedInline(nested_admin.NestedTabularInline):
    model = TicketAssignment
    form = TicketAssignmentModelForm
    extra = 0


# Ticket History
class TicketHistoryModelForm(forms.ModelForm):

    class Meta:
        model = TicketHistory
        fields = ('__all__')


class TicketHistoryNestedInline(nested_admin.NestedTabularInline):
    model = TicketHistory
    form = TicketHistoryModelForm
    extra = 0


# Ticket Reply
class TicketReplyModelForm(forms.ModelForm):
    class Meta:
        model = TicketReply
        fields = ('__all__')


class TicketReplyNestedInline(nested_admin.NestedTabularInline):
    model = TicketReply
    form = TicketReplyModelForm
    extra = 0


# Ticket dependency from other Ticket
class Ticket2TicketModelForm(forms.ModelForm):
    class Meta:
        model = Ticket2Ticket
        fields = ('__all__')


class Ticket2TicketNestedInline(nested_admin.NestedTabularInline):
    model = Ticket2Ticket
    form = Ticket2TicketModelForm
    extra = 0
    fk_name = 'slave_ticket'
