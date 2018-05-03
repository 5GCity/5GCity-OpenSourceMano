from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from projecthandler.models import Project
from sf_user.models import CustomUser


@login_required
def home(request):
    user = CustomUser.objects.get(id=request.user.id)
    projects = Project.objects.filter(owner=user).select_subclasses()
    result = {
        'projects': len(projects) if projects else 0,
    }
    return render(request, 'home.html', result)


def forbidden(request):
    return render(request, 'forbidden.html')



