"""uni_ticket_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
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
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path, include

from djangosaml2 import views

urlpatterns = [
    path('gestione/', admin.site.urls),

    # Login/Logou URLs
    # for local auth
    # disable these for SAML2 auth or others
    path('{}/'.format(settings.LOGIN_URL), auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('{}/'.format(settings.LOGOUT_URL), auth_views.LogoutView.as_view(template_name='logout.html', next_page='../'), name='logout'),
]

import uni_ticket.urls
urlpatterns += path('', include(uni_ticket.urls, namespace='uni_ticket')),

if settings.DEBUG:
    # STATICS FILE SERVE
    from django.views.static import serve
    urlpatterns.append(
        path('{}/<path>'.format(settings.STATIC_URL[1:-1]),
            serve,
            {'document_root': settings.STATIC_ROOT,
             'show_indexes' : True})
    )

if 'nested_admin' in settings.INSTALLED_APPS:
    import nested_admin.views
    urlpatterns += path('nested_admin/', include('nested_admin.urls')),

if 'saml2_sp' in settings.INSTALLED_APPS:
    import saml2_sp.urls
    saml2_url_prefix = 'saml2'

    urlpatterns += path('', include((saml2_sp.urls, 'sp',))),
    urlpatterns += path('{}/login/'.format(saml2_url_prefix),
                        views.login, name='saml2_login'),
    urlpatterns += path('{}/acs/'.format(saml2_url_prefix),
                        views.assertion_consumer_service, name='saml2_acs'),
    urlpatterns += path('{}/logout/'.format(saml2_url_prefix),
                        views.logout, name='saml2_logout'),
    urlpatterns += path('{}/ls/'.format(saml2_url_prefix),
                        views.logout_service, name='saml2_ls'),
    urlpatterns += path('{}/ls/post/'.format(saml2_url_prefix),
                        views.logout_service_post, name='saml2_ls_post'),
    urlpatterns += path('{}/metadata/'.format(saml2_url_prefix),
                        views.metadata, name='saml2_metadata'),

    # system local
    urlpatterns += path('logout/', LogoutView.as_view(),
                        {'next_page': settings.LOGOUT_REDIRECT_URL},
                        name='logout'),


if 'djangosaml2' in settings.INSTALLED_APPS:
    import djangosaml2.urls
    urlpatterns += path('', include((djangosaml2.urls, 'djangosaml2',))),
