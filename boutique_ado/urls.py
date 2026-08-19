"""boutique_ado URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('home.urls')),
    path('products/', include('products.urls')),
    path('bag/', include('bag.urls')),
    path('checkout/', include('checkout.urls')),
    path('profile/', include('profiles.urls')),
    path("privacy-policy/", views.privacy_policy, name="privacy_policy"),
    path(
        "terms-and-conditions/",
        views.terms_conditions,
        name="terms_conditions",
    ),
    path(
        "delivery-policy/",
        views.delivery_policy,
        name="delivery_policy",
    ),
    path(
        "refunds/",
        views.refund_policy,
        name="refund_policy",
    ),
    path(
        "whatsapp/webhook/",
        views.whatsapp_webhook,
        name="whatsapp_webhook",
    ),
    path("faq/", views.faq, name="faq"),
    path(
        "about/",
        views.about,
        name="about",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
handler404 = 'boutique_ado.views.handler404'
