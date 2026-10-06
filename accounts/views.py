from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)  # fill form with submitted data
        if form.is_valid():                # run all validation rules
            user = form.save()             # saves user, password gets hashed
            login(request, user)           # log in straight away
            messages.success(request, f'Welcome, {user.username}! Your account has been created.')
            return redirect('home')
    else:
        form = RegisterForm()              # empty form on first visit

    return render(request, 'accounts/register.html', {'form': form})


@login_required  # not logged in? Django sends the visitor to the login page
def profile(request):
    if request.method == 'POST':
        # instance=request.user means "edit the logged-in user's own record"
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)  # pre-filled with current data

    return render(request, 'accounts/profile.html', {'form': form})