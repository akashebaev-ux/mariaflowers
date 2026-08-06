from django.contrib import admin

from .models import (
    Order,
    OrderLineItem,
    Review,
    ReviewImage,
    ReviewReaction,
    WhatsAppMessage,
)


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
        'status',
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
        'status',
        'is_paid',
        'paid_at',
        'order_total',
        'delivery_cost',
        'grand_total',
    )

    ordering = ('-date',)


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0
    readonly_fields = (
        'uploaded_at',
    )


class ReviewAdmin(admin.ModelAdmin):
    inlines = (
        ReviewImageInline,
    )

    list_display = (
        'order',
        'rating',
        'created_at',
    )

    list_filter = (
        'rating',
        'created_at',
    )

    search_fields = (
        'order__order_number',
        'order__full_name',
        'order__email',
        'comment',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )


class ReviewReactionAdmin(admin.ModelAdmin):
    list_display = (
        'review',
        'user_profile',
        'created_at',
    )

    search_fields = (
        'review__order__order_number',
        'user_profile__user__username',
        'user_profile__user__email',
    )

    readonly_fields = (
        'created_at',
    )


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
    Review,
    ReviewAdmin,
)

admin.site.register(
    ReviewReaction,
    ReviewReactionAdmin,
)

admin.site.register(
    WhatsAppMessage,
    WhatsAppMessageAdmin,
)
