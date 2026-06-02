from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.users.models import User
from apps.users.services.antispam import verify_turnstile
from apps.users.services.avatar import process_avatar
from apps.users.validators import (
    validate_registration_display_name,
    validate_registration_email,
    validate_registration_username,
)


class UserLoginForm(AuthenticationForm):
    class Meta:
        model = User
        fields = ['username', 'password']

    username = forms.CharField()
    password = forms.CharField()

    error_messages = {
        "invalid_login": "Invalid login or password"
    }


class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'username',
            'email',
            'password1',
            'password2',
        )

    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50, required=False)
    username = forms.CharField(max_length=32)
    email = forms.EmailField()
    password1 = forms.CharField()
    password2 = forms.CharField()

    def clean_username(self):
        username = self.cleaned_data["username"]
        validate_registration_username(username)
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        validate_registration_email(email)
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует.")
        return email

    def clean_first_name(self):
        value = self.cleaned_data["first_name"].strip()
        validate_registration_display_name(value, field_label="Имя")
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get("last_name", "").strip()
        if value:
            validate_registration_display_name(value, field_label="Фамилия")
        return value

    def clean(self):
        cleaned = super().clean()
        request = getattr(self, "request", None)
        if request is None:
            return cleaned
        token = self.data.get("cf-turnstile-response")
        ok, message = verify_turnstile(request, token)
        if not ok:
            raise forms.ValidationError(message)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'image',
            'first_name',
            'last_name',
            'username',
            'email',
        )

    image = forms.ImageField(required=False)

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image
        try:
            return process_avatar(image)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc

    def save(self, commit=True):
        user = super().save(commit=False)
        new_image = self.cleaned_data.get("image")
        if new_image and "image" in self.changed_data:
            if user.pk and user.image:
                user.image.delete(save=False)
            user.image.save(new_image.name, new_image, save=False)
        if commit:
            user.save()
        return user
