"""
plans/utils.py

Updated with:
- Plan expiry check (start_date / end_date)
- Unlimited tokens / limits support
"""
from django.utils import timezone
from .models import Wallet, UserPlan, DefaultFreeCredit


def get_active_plan(user):
    """
    Returns the user's active and non-expired plan.
    If the plan has expired, it deactivates it and clears wallet tokens.
    """
    plan = UserPlan.objects.filter(user=user, is_active=True).first()
    if not plan:
        return None

    if plan.is_expired:
        plan.is_active = False
        plan.save()

        # Wallet tokens bhi clear karo jab plan expire ho
        try:
            wallet = user.wallet
            if wallet.balance > 0:
                old_balance = wallet.balance
                wallet.balance = 0
                wallet.save()
                from .models import WalletTransaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=old_balance,
                    transaction_type='debit',
                    note=f"Plan expired: {plan.plan.name if plan.plan else 'Unknown'} — tokens cleared",
                )
        except Exception:
            pass

        return None

    return plan

# ─── Wallet: Token Deduction (On Shift Acceptance) ─────────────
def deduct_shift_token(user, shift, token_cost=10):
    """
    Call this when the hospital accepts a shift application.
    Token deduction is skipped for plans with unlimited tokens.
    Returns: (success: bool, message: str)
    """
    active_plan = get_active_plan(user)

    # Unlimited tokens check
    if active_plan and active_plan.plan and active_plan.plan.unlimited_tokens:
        return True, "Unlimited tokens — deduction skipped"

    try:
        wallet = user.wallet
    except Wallet.DoesNotExist:
        return False, "Wallet not found"

    if wallet.balance < token_cost:
        return False, f"Insufficient tokens. Required: {token_cost}, Available: {wallet.balance}"

    wallet.deduct_tokens(token_cost, note=f"Shift accepted: {shift.id}")
    return True, "Tokens deducted successfully"


# ─── New User Free Credits Setup ─────────────────────────────
def setup_free_credits(user):
    try:
        credit = DefaultFreeCredit.objects.get(role=user.role)
    except DefaultFreeCredit.DoesNotExist:
        return

    duration = credit.free_duration_months or 1

    if user.role in ['doctor', 'nurse']:
        wallet, _ = Wallet.objects.get_or_create(user=user)
        if credit.free_tokens > 0:
            wallet.add_tokens(credit.free_tokens, note="Welcome! Free tokens")

        if credit.free_vacancy_limit > 0:
            from .models import Plan
            free_plan, _ = Plan.objects.get_or_create(
                name='Free',
                role=user.role,
                defaults={
                    'price':                  0,
                    'token_mode':             'fixed',       # ← FIX 1: yeh add karo
                    'tokens':                 credit.free_tokens,
                    'vacancy_apply_enabled':  True,           # ← FIX 1: yeh add karo
                    'vacancy_limit':          credit.free_vacancy_limit,
                    'duration_months':        duration,
                    'is_lifetime':            credit.free_is_lifetime,  # ← bonus
                }
            )
            UserPlan.objects.create(user=user, plan=free_plan)

    elif user.role == 'hospital':
        if credit.free_shift_post_limit > 0 or credit.free_vacancy_post_limit > 0:
            from .models import Plan
            free_plan, _ = Plan.objects.get_or_create(
                name='Free',
                role='hospital',
                defaults={
                    'price':                 0,
                    'shift_post_enabled':    credit.free_shift_post_limit > 0,   # ← bonus
                    'shift_post_limit':      credit.free_shift_post_limit,
                    'vacancy_post_enabled':  credit.free_vacancy_post_limit > 0, # ← bonus
                    'vacancy_post_limit':    credit.free_vacancy_post_limit,
                    'duration_months':       duration,
                    'is_lifetime':           credit.free_is_lifetime,            # ← bonus
                }
            )
            UserPlan.objects.create(user=user, plan=free_plan)


def can_apply_vacancy(user):
    plan = get_active_plan(user)
    if not plan:
        return False, "You do not have an active plan or your plan has expired. Please purchase a plan first."

    if not plan.plan.vacancy_apply_enabled:
        return False, "Your current plan does not include vacancy apply feature. Please upgrade your plan."

    if plan.plan.unlimited_vacancy_apply:
        return True, "OK"

    # vacancy_limit = 0 aur unlimited nahi → not allowed
    if plan.plan.vacancy_limit <= 0:
        return False, "Your plan does not allow vacancy applications. Please upgrade your plan."

    if plan.vacancy_limit_remaining <= 0:
        return False, f"Your vacancy application limit is exhausted ({plan.plan.vacancy_limit}/{plan.plan.vacancy_limit}). Please purchase a new plan."

    return True, "OK"


def use_vacancy_limit(user):
    """
    Increments the usage counter for vacancy applications.
    """
    plan = get_active_plan(user)
    if plan and not plan.plan.unlimited_vacancy_apply:
        plan.vacancy_limit_used += 1
        plan.save()


# ─── Hospital: Shift Post Limit Check ────────────────────────
def can_post_shift(user):
    """
    Check if the hospital is allowed to post a new shift.
    """
    plan = get_active_plan(user)
    if not plan:
        return False, "You do not have an active plan or your plan has expired. Please purchase a plan first."

    if plan.plan.unlimited_shift_post:
        return True, "OK"

    if plan.shift_post_remaining <= 0:
        return False, "Your shift posting limit is exhausted. Please purchase a new plan."

    return True, "OK"


def use_shift_post_limit(user):
    """
    Increments the usage counter for shift posts.
    """
    plan = get_active_plan(user)
    if plan and not plan.plan.unlimited_shift_post:
        plan.shift_post_used += 1
        plan.save()


# ─── Hospital: Vacancy Post Limit Check ──────────────────────
def can_post_vacancy(user):
    """
    Check if the hospital is allowed to post a permanent vacancy.
    """
    plan = get_active_plan(user)
    if not plan:
        return False, "You don't have any active plan yet, please purchase a plan."

    if plan.plan.unlimited_vacancy_post:
        return True, "OK"

    if plan.vacancy_post_remaining <= 0:
        return False, "Your vacancy limit is exhausted, please purchase a new plan."

    return True, "OK"


def use_vacancy_post_limit(user):
    """
    Increments the usage counter for vacancy posts.
    """
    plan = get_active_plan(user)
    if plan and not plan.plan.unlimited_vacancy_post:
        plan.vacancy_post_used += 1
        plan.save()


# ─── Token Balance Check ─────────────────────────────────────
def get_wallet_balance(user):
    """
    Returns the current token balance. Returns infinity if the plan is unlimited.
    """
    active_plan = get_active_plan(user)
    if active_plan and active_plan.plan and active_plan.plan.unlimited_tokens:
        return float('inf')
    try:
        return user.wallet.balance
    except Exception:
        return 0


# ─── User Plan Info ──────────────────────────────────────────
def get_user_plan_info(user):
    """
    Returns the current active plan for the user.
    """
    return get_active_plan(user)









def can_post_shift(user):
    plan = get_active_plan(user)
    if not plan:
        return False, "No active plan. Please purchase a plan first."

    p = plan.plan

    if not p.shift_post_enabled:
        return False, "Your plan does not include shift posting. Please upgrade."

    if p.unlimited_shift_post:
        return True, "OK"

    # Limit-based (limit > 0)
    if p.shift_post_limit > 0:
        if plan.shift_post_remaining <= 0:
            return False, "Shift posting limit exhausted. Please purchase a new plan."
        return True, "OK"

    # limit = 0 → token-based, can_post allowed (token check alag)
    return True, "OK"


def deduct_shift_post_token(user, cost=1):
    active_plan = get_active_plan(user)

    if not active_plan or not active_plan.plan:
        return False, "No active plan"

    p = active_plan.plan

    # Unlimited token mode → free
    if p.token_mode == 'unlimited':
        return True, "Unlimited plan — skipped"

    # Unlimited shift post toggle → free
    if p.unlimited_shift_post:
        return True, "Unlimited shift post — skipped"

    # Limit set hai → limit counter se chal raha, tokens nahi katenge
    if p.shift_post_limit > 0:
        return True, "Limit-based — tokens skipped"

    # limit = 0, unlimited nahi → tokens katao
    if cost <= 0:
        return True, "No cost — skipped"

    try:
        wallet = user.wallet
    except Exception:
        return False, "Wallet not found"

    if wallet.balance < cost:
        return False, f"Insufficient tokens. Required: {cost}, Available: {wallet.balance}"

    wallet.deduct_tokens(cost, note=f"Shift post: {cost} tokens deducted")
    return True, "Tokens deducted"