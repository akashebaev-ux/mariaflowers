from django.urls import path

from . import views
from .webhooks import webhook


urlpatterns = [
    path(
        '',
        views.checkout,
        name='checkout',
    ),
    path(
        'checkout_success/<order_number>',
        views.checkout_success,
        name='checkout_success',
    ),
    path(
        'cache_checkout_data/',
        views.cache_checkout_data,
        name='cache_checkout_data',
    ),

    # Customer Reviews
    path(
        'review/item/<int:line_item_id>/',
        views.submit_review,
        name='submit_review',
    ),
    path(
        'reviews/<int:review_id>/helpful/',
        views.toggle_review_reaction,
        name='toggle_review_reaction',
    ),

    path(
        'wh/',
        webhook,
        name='webhook',
    ),
]
