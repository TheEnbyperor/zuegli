from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Layout, Submit, Field, Fieldset
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import SetPasswordForm as _SetPasswordForm


class LoginForm(forms.Form):
    username = forms.CharField(label=_("Email"), required=True)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Login")))


class AccountEditForm(forms.Form):
    first_name = forms.CharField(max_length=255, required=True)
    last_name = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Save")))


class AlternateExpansionForm(forms.Form):
    first_name = forms.CharField(max_length=255, required=False)
    last_name = forms.CharField(max_length=255, required=False)
    email = forms.EmailField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Save")))


class SetPasswordForm(_SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Save")))


class TicketEditForm(forms.Form):
    name = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Save")))


class TicketUploadForm(forms.Form):
    ticket = forms.FileField(
        label=_("Your ticket"),
        error_messages={
            "required": _("Please upload a ticket image or PDF"),
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Upload")))


class EOSLoginForm(forms.Form):
    username = forms.CharField(label=_("Email/Username"), required=True)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Login")))


class RaileasyLoginForm(forms.Form):
    email = forms.EmailField(label=_("Email"), required=True)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Login")))


class DoBField(Field):
    template = "main/date_input.html"


class DBAboForm(forms.Form):
    subscription_number = forms.CharField(label=_("Subscription Number"), required=True)
    surname = forms.CharField(label=_("Surname"), required=False)
    date_of_birth = forms.DateField(
        label=_("Date of Birth"), required=False, widget=forms.widgets.SelectDateWidget()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "subscription_number",
            Fieldset(
                "surname",
                DoBField("date_of_birth"),
                legend=_("One of surname or date of birth must be provided"),
            ),
            Submit("submit", _("Add"))
        )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("date_of_birth") and not cleaned_data.get("surname"):
            raise ValidationError({
                "surname": _("Either a surname or a date of birth must be given"),
                "date_of_birth": _("Either a surname or a date of birth must be given"),
            })
        return cleaned_data


class SNCBTicketForm(forms.Form):
    pnr = forms.CharField(label=_("Booking Reference"), required=True)
    email = forms.EmailField(label=_("Email"), required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Add")))


class DBTicketForm(forms.Form):
    booking_number = forms.CharField(label=_("Booking number"), required=True)
    surname = forms.CharField(label=_("Surname"), required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", _("Add")))