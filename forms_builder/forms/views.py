from types import SimpleNamespace
from django import forms
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView
from formtools.wizard.views import SessionWizardView
from forms_builder.forms.models import Form
from .models import Step

__all__ = ["form_sent", "MultiStepFormWizard", "form_detail"]

def convert_to_django_field(field_instance):
    # Beispielhafte Konvertierung – hier anpassen!
    if field_instance.field_type == 1:  # TEXT
        return forms.CharField(label=field_instance.label, required=field_instance.required)
    return forms.CharField(label=field_instance.label, required=field_instance.required)

class MultiStepFormWizard(SessionWizardView):
    template_name = "forms/multistep_form.html"

    @classmethod
    def get_initkwargs(cls, *args, **kwargs):
        """
        Überschreibe get_initkwargs, damit immer ein nicht-leeres form_list übergeben wird.
        """
        instance = cls(*args, **kwargs)
        # Versuche, die dynamische form_list zu erzeugen
        try:
            form_list = instance.get_form_list()
        except Exception:
            form_list = {}

        # Falls form_list leer ist, lege einen Dummy-Wert an
        if not form_list:
            dummy_form = type(
                "EmptyForm", (forms.Form,), {"dummy": forms.CharField(required=False, label="Dummy")}
            )
            form_list = {"default": dummy_form}

        return {"form_list": form_list}

    def get_form_list(self):
        """
        Erzeuge dynamisch eine Liste von Formularen für jeden Schritt.
        """
        # Falls self.kwargs noch nicht gesetzt sind, gib einen Dummy zurück
        if not hasattr(self, "form_instance"):
            dummy_form = type(
                "EmptyForm", (forms.Form,), {"dummy": forms.CharField(required=False, label="Dummy")}
            )
            return {"default": dummy_form}

        form_list = {}
        steps = self.form_instance.steps.all()  # Dank ordering im Step-Modell

        if not steps.exists():
            # Fallback: Verwende Felder direkt vom Formular
            fields = {}
            qs = self.form_instance.fields.all().order_by("order")
            for field in qs:
                fields[field.slug] = convert_to_django_field(field)
            if not fields:
                fields["dummy"] = forms.CharField(
                    required=False, label="Dummy-Feld (kein Feld definiert)"
                )
            form_class = type("StepForm_default", (forms.Form,), fields)
            form_list["default"] = form_class
        else:
            for step in steps:
                fields = {}
                qs = step.fields.all().order_by("order")
                for field in qs:
                    fields[field.slug] = convert_to_django_field(field)
                if not fields:
                    fields["dummy"] = forms.CharField(
                        required=False,
                        label=f"Dummy-Feld (kein Feld in Step {step.slug})"
                    )
                form_class = type(f"StepForm_{step.slug}", (forms.Form,), fields)
                form_list[step.slug] = form_class

        return form_list
    
    def get_form_initial(self, step):
        # Falls Du keine initialen Daten hast, gib ein leeres Dictionary zurück.
        return {}

    def dispatch(self, request, *args, **kwargs):
        # Lade hier das Form-Objekt anhand des URL-Parameters, damit später in get_form_list
        # die richtigen Daten verwendet werden können.
        form_slug = self.kwargs.get("slug")
        self.form_instance = get_object_or_404(Form, slug=form_slug)
        # Aktualisiere die form_list, falls nötig
        self.form_list = self.get_form_list()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context.update({"form_instance": self.form_instance})
        return context

    def done(self, form_list, **kwargs):
        combined_data = {}
        for form in form_list:
            combined_data.update(form.cleaned_data)
        return redirect(reverse("form_sent", kwargs={"slug": self.form_instance.slug}))

class FormDetail(TemplateView):
    template_name = "forms/form_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get("slug")
        # Hole das Form-Objekt, z.B. nur veroeffentlichte, je nach Logik:
        context["form"] = get_object_or_404(Form.objects.published(for_user=self.request.user), slug=slug)
        return context

def form_sent(request, slug, template="forms/form_sent.html"):
    from django.shortcuts import render, get_object_or_404
    from forms_builder.forms.models import Form
    published = Form.objects.published(for_user=request.user)
    context = {"form": get_object_or_404(published, slug=slug)}
    return render(request, template, context)

# Exportiere die Views als Modul-Attribute:
form_detail = FormDetail.as_view()
