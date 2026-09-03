from django.contrib import admin

from professionals.models import Professional


@admin.register(Professional)
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = ["business_name", "slug", "user", "is_active"]
    prepopulated_fields = {"slug": ("business_name",)}
