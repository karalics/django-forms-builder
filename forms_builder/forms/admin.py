import nested_admin
from django.contrib import admin
from django.db.models import Count
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _
from forms_builder.forms.models import Form, Field, FormEntry  # und ggf. FieldEntry
from forms_builder.forms.settings import EDITABLE_SLUGS, USE_SITES
from .models import Step

# Zuerst definieren wir den FieldInline, der Felder innerhalb eines Steps verwaltet
class FieldInline(nested_admin.NestedTabularInline):
    model = Field
    extra = 1
    exclude = ('slug',)

# Dann definieren wir den StepInline, in dem der FieldInline verschachtelt wird
class StepInline(nested_admin.NestedStackedInline):
    model = Step
    extra = 1
    inlines = [FieldInline]

# Nun kann FormAdmin die StepInline verwenden:
class FormAdmin(nested_admin.NestedModelAdmin):
    inlines = [StepInline]
    list_display = ("title", "status", "publish_date", "expiry_date", "total_entries", "admin_links")
    list_editable = ("status", "publish_date", "expiry_date")
    search_fields = ("title", "intro", "response", "email_from", "email_copies")
    fieldsets = [
        (None, {"fields": ("title", ("status", "login_required"), ("publish_date", "expiry_date"),
                             "intro", "button_text", "response", "redirect_url")}),
        (_("Email"), {"fields": ("send_email", "email_from", "email_copies", "email_subject", "email_message")}),
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(total_entries=Count("entries"))

    def admin_links(self, obj):
        return '<a href="{0}">{1}</a>'.format(obj.get_absolute_url(), _("View form on site"))
    admin_links.allow_tags = True
    admin_links.short_description = _("Admin links")

    def get_urls(self):
        urls = super().get_urls()
        extra_urls = [
            path("<int:form_id>/entries/", self.admin_site.admin_view(self.entries_view), name="form_entries"),
            path("<int:form_id>/entries/show/", self.admin_site.admin_view(self.entries_view), {"show": True}, name="form_entries_show"),
            path("<int:form_id>/entries/export/", self.admin_site.admin_view(self.entries_view), {"export": True}, name="form_entries_export"),
            path("file/<int:field_entry_id>/", self.admin_site.admin_view(self.file_view), name="form_file"),
        ]
        return extra_urls + urls


    def entries_view(self, request, form_id, show=False, export=False,
                     export_xls=False):
        form = get_object_or_404(self.model, id=form_id)
        entries = FormEntry.objects.filter(form=form)

        # Filter by date range if provided
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            entries = entries.filter(created_at__gte=parse_date(start_date))
        if end_date:
            entries = entries.filter(created_at__lte=parse_date(end_date))

        context = {
            "original": form,
            "entries": entries,
        }
        return render(request, "admin/forms/entries.html", context)


    def file_view(self, request, field_entry_id):
        # Beispielhafte Implementierung zum Ausliefern der Datei
        from os.path import join
        from mimetypes import guess_type
        from django.core.files.storage import FileSystemStorage
        fs = FileSystemStorage()
        field_entry = get_object_or_404(Field, id=field_entry_id)
        path_file = join(fs.location, field_entry.value)
        response = HttpResponse(content_type=guess_type(path_file)[0])
        with open(path_file, "rb") as f:
            response["Content-Disposition"] = "attachment; filename=%s" % f.name
            response.write(f.read())
        return response

admin.site.register(Form, FormAdmin)
