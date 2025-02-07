from django.urls import path
from .views import MultiStepFormWizard

from . import views

urlpatterns = [
    path("<slug:slug>/multistep/", MultiStepFormWizard.as_view(), name="multistep_form"),
    path("<slug:slug>/sent/", views.form_sent, name="form_sent"),
    path("<slug:slug>/", views.form_detail, name="form_detail"),
    
]
