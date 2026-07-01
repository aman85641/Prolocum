from django.urls import path
from . import views
# from . import payment_views

urlpatterns = [
    # ── Admin: Plans CRUD ─────────────────────────────────────
    path('',                            views.plan_list,        name='admin_plan_list'),
    path('create/',                     views.plan_create,      name='admin_plan_create'),
    path('<int:pk>/edit/',              views.plan_edit,        name='admin_plan_edit'),
    path('<int:pk>/delete/',            views.plan_delete,      name='admin_plan_delete'),

    # ── Admin: Wallets ────────────────────────────────────────
    path('wallets/',                    views.wallet_list,      name='admin_wallet_list'),
    path('wallets/<int:user_id>/',      views.wallet_detail,    name='admin_wallet_detail'),

    # ── Admin: User Plans ─────────────────────────────────────
    path('user-plans/',                 views.user_plan_list,   name='admin_user_plan_list'),
    path('assign/<int:user_id>/',       views.assign_plan,      name='admin_assign_plan'),
path('all-users/', views.all_users_plan, name='admin_all_users_plan'),

    # ── Admin: Default Free Credits ───────────────────────────
    path('default-credits/',            views.default_credits,  name='admin_default_credits'),

    # ── User: Plan Purchase (Razorpay) ────────────────────────
    path('my-plans/',                   views.my_plans,         name='my_plans'),
    path('order/<int:plan_id>/',        views.create_order,     name='plan_create_order'),
    path('verify/',                     views.verify_payment,   name='plan_verify_payment'),
    path('success/',                    views.payment_success,  name='plan_payment_success'),
]