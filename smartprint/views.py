from django.shortcuts import render

def home(request):
    return render(request, 'smartprint/home.html')

def user_panel(request):
    return render(request, 'smartprint/user_panel.html')