from django.db import models
from django.conf import settings
from django.utils import timezone
from dateutil.relativedelta import relativedelta

User = settings.AUTH_USER_MODEL


# ─── Plan Types ───────────────────────────────────────────────
class Plan(models.Model):
    ROLE_CHOICES = [
        ('doctor',   'Doctor'),
        ('nurse',    'Nurse'),
        ('hospital', 'Hospital'),
    ]

    DURATION_CHOICES = [
        (1,  '1 Month'),
        (2,  '2 Months'),
        (3,  '3 Months'),
        (6,  '6 Months'),
        (12, '12 Months (1 Year)'),
    ]

    # Token mode choices — for Doctor / Nurse
    TOKEN_MODE_CHOICES = [
        ('disabled',  'No Tokens'),        # tokens feature hi nahi
        ('fixed',     'Fixed Amount'),     # X tokens milenge
        ('unlimited', 'Unlimited'),        # ∞ tokens
    ]

    name        = models.CharField(max_length=100)
    role        = models.CharField(max_length=20, choices=ROLE_CHOICES)
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    shift_view_enabled = models.BooleanField(
    default=False,
    help_text="Kya is plan mein Available Shifts dekhne ki permission hai?"
)
    urgent_shift_enabled = models.BooleanField(
    default=False,
    help_text="Dashboard pe urgent shifts dikhenge (shift_view_enabled bhi hona chahiye)"
)
    # ── Duration / Expiry ──────────────────────────────────────
    is_lifetime     = models.BooleanField(
        default=False,
        help_text="Check karo agar plan kabhi expire na ho (Lifetime)"
    )
    duration_months = models.PositiveIntegerField(
    choices=DURATION_CHOICES,
    default=1,
    null=True,      # ← add karo
    blank=True,     # ← add karo
    help_text="Plan kitne mahine ka hai (is_lifetime=False hone par kaam aata hai)"
)

    # ══════════════════════════════════════════════════════════
    # DOCTOR / NURSE FIELDS
    # ══════════════════════════════════════════════════════════
# plans/models.py — Plan class mein, urgent_shift_enabled ke neeche

    urgent_shift_post_enabled = models.BooleanField(
    default=False,
    help_text="Kya is plan mein urgent shift post karne ki permission hai?"
)
    # -- Tokens --
    token_mode = models.CharField(
        max_length=10,
        choices=TOKEN_MODE_CHOICES,
        default='disabled',
        help_text="disabled=tokens nahi, fixed=X tokens, unlimited=∞ tokens"
    )
    tokens = models.PositiveIntegerField(
        default=0,
        help_text="Sirf token_mode='fixed' hone par use hota hai"
    )

    # -- Vacancy Apply --
    vacancy_apply_enabled   = models.BooleanField(
        default=False,
        help_text="Kya is plan mein vacancy apply feature ON hai?"
    )
    unlimited_vacancy_apply = models.BooleanField(
        default=False,
        help_text="Unlimited vacancy apply? (vacancy_apply_enabled=True hona chahiye)"
    )
    vacancy_limit           = models.PositiveIntegerField(
        default=0,
        help_text="Kitni vacancies pe apply kar sakta hai (unlimited_vacancy_apply=False hone par)"
    )

    # ══════════════════════════════════════════════════════════
    # HOSPITAL FIELDS
    # ══════════════════════════════════════════════════════════

    # -- Shift Post --
    shift_post_enabled   = models.BooleanField(
        default=False,
        help_text="Kya is plan mein shift posting feature ON hai?"
    )
    unlimited_shift_post = models.BooleanField(default=False)
    shift_post_limit     = models.PositiveIntegerField(default=0)

    # -- Vacancy Post --
    vacancy_post_enabled   = models.BooleanField(
        default=False,
        help_text="Kya is plan mein vacancy posting feature ON hai?"
    )
    unlimited_vacancy_post = models.BooleanField(default=False)
    vacancy_post_limit     = models.PositiveIntegerField(default=0)

    # ── Convenience properties ─────────────────────────────────
    @property
    def unlimited_tokens(self):
        return self.token_mode == 'unlimited'

    @property
    def has_tokens(self):
        return self.token_mode != 'disabled'

    def __str__(self):
        duration = "Lifetime" if self.is_lifetime else f"{self.duration_months}M"
        return f"{self.name} ({self.role}) — ₹{self.price} / {duration}"

    class Meta:
        ordering = ['role', 'price']


# ─── User ka Active Plan ──────────────────────────────────────
class UserPlan(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plans')
    plan      = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    bought_at = models.DateTimeField(auto_now_add=True)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date   = models.DateTimeField(null=True, blank=True)   # None = Lifetime

    # Doctor / Nurse usage
    vacancy_limit_used = models.PositiveIntegerField(default=0)

    # Hospital usage
    shift_post_used   = models.PositiveIntegerField(default=0)
    vacancy_post_used = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.pk and self.plan:
            self.start_date = timezone.now()
            if self.plan.is_lifetime:
                self.end_date = None          # kabhi expire nahi hoga
            else:
                self.end_date = self.start_date + relativedelta(months=self.plan.duration_months)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} → {self.plan.name if self.plan else 'No Plan'}"

    @property
    def is_expired(self):
        if not self.end_date:
            return False   # Lifetime plan
        return timezone.now() > self.end_date

    @property
    def days_remaining(self):
        if not self.end_date:
            return None    # Lifetime
        return max(0, (self.end_date - timezone.now()).days)

    # ── Remaining limits ──
    @property
    def vacancy_limit_remaining(self):
        if not self.plan or not self.plan.vacancy_apply_enabled:
            return 0
        if self.plan.unlimited_vacancy_apply:
            return float('inf')
        return max(0, self.plan.vacancy_limit - self.vacancy_limit_used)

    @property
    def shift_post_remaining(self):
        if not self.plan or not self.plan.shift_post_enabled:
            return 0
        if self.plan.unlimited_shift_post:
            return float('inf')
        return max(0, self.plan.shift_post_limit - self.shift_post_used)

    @property
    def vacancy_post_remaining(self):
        if not self.plan or not self.plan.vacancy_post_enabled:
            return 0
        if self.plan.unlimited_vacancy_post:
            return float('inf')
        return max(0, self.plan.vacancy_post_limit - self.vacancy_post_used)

    class Meta:
        ordering = ['-bought_at']


# ─── Doctor/Nurse Token Wallet ────────────────────────────────
class Wallet(models.Model):
    user    = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} — {self.balance} tokens"

    def add_tokens(self, amount, note=""):
        self.balance += amount
        self.save()
        WalletTransaction.objects.create(
            wallet=self, amount=amount, transaction_type='credit', note=note,
        )

    def deduct_tokens(self, amount, note=""):
        if self.balance < amount:
            return False
        self.balance -= amount
        self.save()
        WalletTransaction.objects.create(
            wallet=self, amount=amount, transaction_type='debit', note=note,
        )
        return True


# ─── Wallet Transaction History ───────────────────────────────
class WalletTransaction(models.Model):
    TYPE_CHOICES = [('credit', 'Credit'), ('debit', 'Debit')]

    wallet           = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount           = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    note             = models.CharField(max_length=255, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.user.username} — {self.transaction_type} {self.amount} tokens"

    class Meta:
        ordering = ['-created_at']


# ─── Admin Default Free Credits Setting ───────────────────────
class DefaultFreeCredit(models.Model):
    ROLE_CHOICES = [
        ('doctor',   'Doctor'),
        ('nurse',    'Nurse'),
        ('hospital', 'Hospital'),
    ]

    role                    = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    free_tokens             = models.PositiveIntegerField(default=0)
    free_vacancy_limit      = models.PositiveIntegerField(default=0)
    free_shift_post_limit   = models.PositiveIntegerField(default=0)
    free_vacancy_post_limit = models.PositiveIntegerField(default=0)
    free_duration_months    = models.PositiveIntegerField(default=1)
    free_is_lifetime        = models.BooleanField(default=False)

    def __str__(self):
        return f"Default Credits — {self.role}"

    class Meta:
        verbose_name = "Default Free Credit Setting"