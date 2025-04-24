from django.urls import path
from . import views

urlpatterns = [
    path('', views.passes.index, name='index'),
    path('ticket/<str:pk>/', views.passes.view_ticket, name='ticket'),
    path('ticket/<str:pk>/delete/', views.passes.delete_ticket, name='delete_ticket'),
    path('ticket/<str:pk>/pkpass/', views.passes.ticket_pkpass, name='ticket_pkpass'),
    path('ticket/<str:pk>/ics/', views.ical.download_ics, name='ticket_ics'),
    path('ticket/<str:pk>/pass_photo_banner.png', views.passes.pass_photo_banner, name='ticket_pass_photo_banner'),

    path('vdv_smartcard/', views.vdv.read_smartcard, name='vdv_read'),
    path('vdv_smartcard/<str:pk>/', views.vdv.view_smartcard, name='vdv_smartcard'),

    path('api/apple/v1/log', views.apple_api.log),
    path('api/apple/v1/devices/<str:device_id>/registrations/<str:pass_type_id>', views.apple_api.pass_status),
    path('api/apple/v1/devices/<str:device_id>/registrations/<str:pass_type_id>/<str:serial_number>', views.apple_api.registration),
    path('api/apple/v1/passes/<str:pass_type_id>/<str:serial_number>', views.apple_api.pass_document),

    path('api/upload', views.api.upload_aztec),
    path('api/upload_image', views.api.upload_aztec_img),

    path('account/', views.account.index, name='account'),

    path('account/db/add_ticket/', views.db.db_add_ticket, name='db_add_ticket'),
    path('account/db_abo/', views.db_abo.view_db_abo, name='db_abo'),
    path('account/db_abo/new/', views.db_abo.new_abo, name='new_db_abo'),
    path('account/db_abo/abo/<abo_id>/delete/', views.db_abo.delete_abo, name='delete_db_abo'),

    path('account/avv/', views.avv.avv_account, name='avv_account'),
    path('account/db/', views.db.db_account, name='db_account'),
    path('account/saarvv/', views.saarvv.saarvv_account, name='saarvv_account'),
    path('account/sbahn_berlin/', views.sbahn_berlin.sbahn_berlin_account, name='sbahn_berlin_account'),

    path('account/db_login/', views.db.db_login, name='db_login'),
    path('account/bahnbonus_login/', views.db.bahnbonus_login, name='bahnbonus_login'),
    path('account/avv_login/', views.avv.avv_login, name='avv_login'),
    path('account/vestische_login/', views.vrr.vestische_login, name='vestische_login'),
    path('account/nrway_login/', views.vrr.nrway_login, name='nrway_login'),
    path('account/saarvv_login/', views.saarvv.saarvv_login, name='saarvv_login'),
    path('account/sbahn_berlin_login/', views.sbahn_berlin.sbahn_berlin_login, name='sbahn_berlin_login'),

    path('account/oauth/<str:provider>/login', views.oauth.oauth_login_start, name='oauth_login_start'),
    path('account/oauth/<str:provider>/logout', views.oauth.oauth_logout, name='oauth_logout'),
    path('account/oauth_callback', views.oauth.oauth_login_callback, name='oauth_login_callback'),

    path('account/sncb/add_ticket/', views.sncb.sncb_add_ticket, name='sncb_add_ticket'),

    path('calendar/<str:account_token>.ics', views.ical.account_calendar, name='account_calendar'),

    path('nfc', views.nfc.nfc_index, name='nfc_app'),

    path('metrics', views.metrics.metrics, name='metrics'),

    path('robots.txt', views.util.robots, name='robots'),
    path('.well-known/apple-app-site-association', views.util.apple_app_site_association, name='apple-app-site-association'),
]