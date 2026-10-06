from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from  django.contrib.auth.models import User

class BootstrapFormMixin:
    """
    Mixin to add Bootstrap classes to form fields.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class RegisterForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'email')

    def clean_email(self):
        # Django does not enforce unique emails by default, so we need to check for duplicates manually.
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass

class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        # exclude(pk=...) lets you keep your OWN email without an error
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('This email is already used by another account.')
        return email