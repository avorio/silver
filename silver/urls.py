"""URLs for the silver app."""

from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
    url(r'^docs/', include('rest_framework_swagger.urls')),
    url(r'', include('silver.api.urls', namespace='silver_api'))
)
