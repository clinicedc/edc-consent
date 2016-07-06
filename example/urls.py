from django.contrib import admin
from django.conf.urls import include, url

from example.views import HomeView


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^edc/', include('edc_base.urls')),
    url(r'^', HomeView.as_view(), name='home_url'),
]
