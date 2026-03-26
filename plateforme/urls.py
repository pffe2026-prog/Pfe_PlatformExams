"""
URL configuration for plateforme project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import re

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.views import serve as staticfiles_serve
from django.http import HttpResponse
from django.urls import include, path, re_path


def accueil(request):
    return HttpResponse("Bienvenue sur la plateforme.")

urlpatterns = [
    path("", include("ui.urls")),
    path("admin/", admin.site.urls),
    path("api/", include("gestion.urls")),
    path("accounts/", include("allauth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_STATIC_INSECURE:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, insecure=True)
    static_prefix = settings.STATIC_URL.lstrip("/")
    if not static_prefix.endswith("/"):
        static_prefix += "/"
    urlpatterns += [
        re_path(
            rf"^{re.escape(static_prefix)}(?P<path>.*)$",
            staticfiles_serve,
            {"insecure": True},
        ),
    ]
