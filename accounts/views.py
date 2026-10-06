from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from accounts.forms import RegisterForm

def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)     #fill form with submitted data
        if form.is_valid():                        # run all validation rules
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account has been created successfully.')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})