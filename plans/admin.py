from django.contrib import admin
from .models import Plan, UserPlan, Wallet, WalletTransaction, DefaultFreeCredit

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'price', 'tokens', 'vacancy_limit', 'shift_post_limit', 'is_active')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_active')
    ordering = ('role', 'price')

@admin.register(UserPlan)
class UserPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'is_active', 'bought_at')
    list_filter = ('is_active', 'plan__role', 'bought_at')
    search_fields = ('user__username', 'plan__name')
    readonly_fields = ('bought_at', 'vacancy_limit_used', 'shift_post_used', 'vacancy_post_used')

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')  # updated_at hata diya — model mein nahi hai
    search_fields = ('user__username',)
    ordering = ('-balance',)

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet_user', 'transaction_type', 'amount', 'created_at', 'note')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('wallet__user__username', 'note')

    def wallet_user(self, obj):
        return obj.wallet.user.username
    wallet_user.short_description = 'User'

@admin.register(DefaultFreeCredit)
class DefaultFreeCreditAdmin(admin.ModelAdmin):
    list_display = ('role', 'free_tokens', 'free_vacancy_limit', 'free_shift_post_limit', 'free_vacancy_post_limit')

    def has_add_permission(self, request):
        if self.model.objects.count() >= 3:
            return False
        return super().has_add_permission(request)