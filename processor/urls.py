from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("api/sessions/start/", views.start_session, name="start_session"),
    path("api/detect/", views.detect_frame, name="detect_frame"),
    path("api/sessions/finish/", views.finish_session, name="finish_session"),
]
