from django.contrib import admin

from .models import Order, OrderLineItem, WhatsAppMessage


class OrderLineItemAdminInline(admin.TabularInline):
    model = OrderLineItem
    fields = (
        "product",
        "quantity",
        "greeting_message",
        "lineitem_total",
    )
    readonly_fields = ('lineitem_total',)


class OrderAdmin(admin.ModelAdmin):
    inlines = (OrderLineItemAdminInline,)

    readonly_fields = (
        'order_number',
        'date',
        'paid_at',
        'delivery_date',
        'delivery_time',
        'delivery_cost',
        'order_total',
        'grand_total',
        'original_bag',
        'stripe_pid',
    )

    fields = (
        'order_number',
        'user_profile',
        'date',
        'is_paid',
        'paid_at',
        'delivery_date',
        'delivery_time',
        'full_name',
        'email',
        'phone_number',
        'country',
        'postcode',
        'town_or_city',
        'street_address1',
        'street_address2',
        'county',
        'delivery_cost',
        'order_total',
        'grand_total',
        'original_bag',
        'stripe_pid',
    )

    list_display = (
        'order_number',
        'date',
        'delivery_date',
        'delivery_time',
        'full_name',
        'is_paid',
        'paid_at',
        'order_total',
        'delivery_cost',
        'grand_total',
    )

    ordering = ('-date',)


class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'recipient',
        'status',
        'created_at',
        'sent_at',
    )

    readonly_fields = (
        'order',
        'recipient',
        'message_body',
        'status',
        'provider_message_id',
        'error_message',
        'created_at',
        'sent_at',
    )


admin.site.register(Order, OrderAdmin)
admin.site.register(
    WhatsAppMessage,
    WhatsAppMessageAdmin,
)
