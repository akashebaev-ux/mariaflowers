from django.contrib import admin
from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "subject",
        "order_reference",
        "email_sent",
        "whatsapp_sent",
        "created_at",
    )

    list_filter = (
        "subject",
        "email_sent",
        "whatsapp_sent",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "phone",
        "order_reference",
        "message",
    )

    readonly_fields = (
        "created_at",
        "email_sent",
        "whatsapp_sent",
    )
