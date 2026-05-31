from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.users.models import User
from apps.users.services.avatar import process_avatar


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

    first_name = forms.CharField()
    last_name = forms.CharField()
    username = forms.CharField()
    email = forms.CharField()
    password1 = forms.CharField()
    password2 = forms.CharField()


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
