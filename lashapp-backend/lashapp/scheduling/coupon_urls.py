from django.urls import path

from scheduling.views import CouponListCreateView

app_name = "coupons"

urlpatterns = [
    path("", CouponListCreateView.as_view(), name="coupon-list-create"),
]