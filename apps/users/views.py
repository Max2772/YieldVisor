from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView
from apps.users.forms import UserLoginForm, UserRegistrationForm, ProfileForm
from apps.users.services.profile_page import build_profile_page_context


class UserLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = UserLoginForm
    success_url = reverse_lazy('user:profile')

    def get_success_url(self):
        redirect_page = self.request.POST.get('next', None)
        if redirect_page and redirect_page != reverse('user:logout'):
            return redirect_page
        return self.success_url

    def form_valid(self, form):
        user = form.get_user()
        auth.login(self.request, user)

        messages.success(self.request, f"{user.username}, Вы вошли в аккаунт")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Login'
        return context


class UserRegistrationView(CreateView):
    template_name = 'users/registration.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('user:profile')

    def form_valid(self, form):
        user = form.instance

        form.save()
        auth.login(self.request, user)

        messages.success(self.request, f"{user.username}, Вы успешно зарегестрированы и вошли в аккаунт")
        return HttpResponseRedirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Registration'
        return context

class UserProfileView(LoginRequiredMixin, UpdateView):
    template_name = 'users/profile.html'
    form_class = ProfileForm
    success_url = reverse_lazy('user:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def post(self, request, *args, **kwargs):
        if request.POST.get("section") == "password":
            return self._change_password(request)
        return super().post(request, *args, **kwargs)

    def _change_password(self, request):
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            auth.update_session_auth_hash(request, form.user)
            messages.success(request, "Пароль успешно обновлен")
            return redirect(self.success_url)

        messages.error(request, "Не удалось обновить пароль")
        context = self.get_context_data(password_form=form)
        return self.render_to_response(context)

    def form_valid(self, form):
        messages.success(self.request, "Профиль успешно обновлен")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Не удалось сохранить профиль")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_profile_page_context(self.request.user))
        context.setdefault("password_form", PasswordChangeForm(user=self.request.user))
        context['title'] = 'Profile'
        return context

@login_required
def logout(request):
    username = request.user.username
    auth.logout(request)
    messages.success(request, f"{username}, Вы вышли из аккаунта")
    return redirect(reverse('main:main'))
