from django import forms
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Layout, Submit, Field, Fieldset
from django.core.exceptions import ValidationError


class TicketUploadForm(forms.Form):
    ticket = forms.FileField(
        label="Your ticket",
        error_messages={
            "required": "Please upload a ticket image or PDF",
        }
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Upload"))


class EOSLoginForm(forms.Form):
    username = forms.CharField(label="Email/Username", required=True)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Login"))

class DoBField(Field):
    template = "main/date_input.html"

class DBAboForm(forms.Form):
    subscription_number = forms.CharField(label="Subscription Number", required=True)
    surname = forms.CharField(label="Surname", required=False)
    date_of_birth = forms.DateField(
        label="Date of Birth", required=False, widget=forms.widgets.SelectDateWidget()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "subscription_number",
            Fieldset(
                "surname",
                DoBField("date_of_birth"),
                legend="One of surname or date of birth must be provided",
            ),
            Submit("submit", "Add")
        )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("date_of_birth") and not cleaned_data.get("surname"):
            raise ValidationError({
                "surname": "Either a surname or a date of birth must be given",
                "date_of_birth": "Either a surname or a date of birth must be given",
            })
        return cleaned_data


class SNCBTicketForm(forms.Form):
    pnr = forms.CharField(label="Booking Reference", required=True)
    email = forms.EmailField(label="Email", required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Add"))


class DBTicketForm(forms.Form):
    booking_number = forms.CharField(label="Booking number", required=True)
    surname = forms.CharField(label="Surname", required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Add"))