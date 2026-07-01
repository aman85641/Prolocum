from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import Plan, UserPlan, Wallet, WalletTransaction, DefaultFreeCredit

User = get_user_model()
DURATION_CHOICES = Plan.DURATION_CHOICES


def is_admin(user):
    return user.is_authenticated and user.is_staff

def _extract_plan_fields(post, plan=None):
    token_mode = post.get('token_mode', 'disabled')
    if token_mode not in ('disabled', 'fixed', 'unlimited'):
        token_mode = 'disabled'

    role = post.get('role', '')

    unlimited_vacancy  = 'unlimited_vacancy_apply' in post
    unlimited_vac_post = 'unlimited_vacancy_post'  in post

    def safe_int(val, fallback=0):
        try:
            return int(str(val).strip()) if str(val).strip() not in ('', 'None') else fallback
        except (ValueError, TypeError):
            return fallback

    if role == 'hospital':
        shift_post_enabled        = 'shift_post_enabled_hosp'   in post
        unlimited_shift_post      = 'unlimited_shift_post_hosp' in post
        raw_shift_limit           = post.get('shift_post_limit_hosp', '0')
        urgent_shift_post_enabled = 'urgent_shift_post_enabled_hosp' in post  # ✅ hospital wala
    else:
        shift_post_enabled        = 'shift_post_enabled'   in post
        unlimited_shift_post      = 'unlimited_shift_post' in post
        raw_shift_limit           = post.getlist('shift_post_limit')[0] if post.getlist('shift_post_limit') else '0'
        urgent_shift_post_enabled = 'urgent_shift_post_enabled' in post  # ✅ doctor/nurse wala

    return dict(
        name        = post.get('name', ''),
        role        = role,
        price       = post.get('price', 0),
        description = post.get('description', ''),
        is_active   = 'is_active' in post,

        is_lifetime     = 'is_lifetime' in post,
        duration_months = None if 'is_lifetime' in post else safe_int(post.get('duration_months'), 1),

        token_mode = token_mode,
        tokens     = safe_int(post.get('tokens', 0)) if token_mode == 'fixed' else 0,

        # Doctor/Nurse fields
        shift_view_enabled        = 'shift_view_enabled' in post,
        urgent_shift_enabled      = 'urgent_shift_enabled' in post,
        urgent_shift_post_enabled = urgent_shift_post_enabled,  # ✅ upar se aayega

        vacancy_apply_enabled   = 'vacancy_apply_enabled' in post,
        unlimited_vacancy_apply = unlimited_vacancy,
        vacancy_limit = 0 if unlimited_vacancy else safe_int(
            post.get('vacancy_limit') or post.get('vacancy_limit_h', 0)
        ),

        shift_post_enabled   = shift_post_enabled,
        unlimited_shift_post = unlimited_shift_post,
        shift_post_limit     = 0 if unlimited_shift_post else safe_int(
            raw_shift_limit or post.get('shift_post_limit_h', 0)
        ),

        # Hospital fields
        vacancy_post_enabled   = 'vacancy_post_enabled' in post,
        unlimited_vacancy_post = unlimited_vac_post,
        vacancy_post_limit = 0 if unlimited_vac_post else safe_int(
            post.get('vacancy_post_limit') or post.get('vacancy_post_limit_h', 0)
        ),
    )

# ─── Plans List ───────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def plan_list(request):
    plans = Plan.objects.all().order_by('role', 'price')
    return render(request, 'admin_panel/plans/plan_list.html', {
        'doctor_plans':   plans.filter(role='doctor'),
        'nurse_plans':    plans.filter(role='nurse'),
        'hospital_plans': plans.filter(role='hospital'),
    })


# ─── Create Plan ─────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def plan_create(request):
    if request.method == 'POST':
        fields = _extract_plan_fields(request.POST)
        Plan.objects.create(**fields)
        messages.success(request, '✅ Plan created successfully!')
        return redirect('admin_plan_list')

    return render(request, 'admin_panel/plans/plan_form.html', {
        'action':           'Create',
        'duration_choices': DURATION_CHOICES,
    })


@login_required
@user_passes_test(is_admin)
def plan_edit(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    if request.method == 'POST':
        fields = _extract_plan_fields(request.POST)
        for attr, value in fields.items():
            setattr(plan, attr, value)
        plan.save()
        messages.success(request, '✅ Plan updated successfully!')
        return redirect('admin_plan_list')

    return render(request, 'admin_panel/plans/plan_form.html', {
        'action':           'Edit',
        'plan':             plan,
        'duration_choices': DURATION_CHOICES,
    })

# ─── Delete Plan ─────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def plan_delete(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, '🗑️ Plan deleted successfully!')
    return redirect('admin_plan_list')


# ─── User Wallets (Admin) ─────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def wallet_list(request):
    role   = request.GET.get('role', 'doctor')
    search = request.GET.get('search', '').strip()
    wallets = Wallet.objects.select_related('user').filter(user__role=role).order_by('-balance')
    if search:
        wallets = wallets.filter(user__username__icontains=search)
    return render(request, 'admin_panel/plans/wallet_list.html', {
        'wallets': wallets, 'role': role, 'search': search,
    })


# ─── Wallet Detail + Adjust Tokens (Admin) ───────────────────
@login_required
@user_passes_test(is_admin)
def wallet_detail(request, user_id):
    user   = get_object_or_404(User, pk=user_id)
    wallet, _ = Wallet.objects.get_or_create(user=user)
    transactions = wallet.transactions.all()[:20]

    if request.method == 'POST':
        action = request.POST.get('action')
        amount = int(request.POST.get('amount', 0))
        note   = request.POST.get('note', 'Admin adjustment')

        if action == 'add' and amount > 0:
            wallet.add_tokens(amount, note=note)
            messages.success(request, f'✅ {amount} tokens added!')
        elif action == 'deduct' and amount > 0:
            if wallet.deduct_tokens(amount, note=note):
                messages.success(request, f'✅ {amount} tokens deducted!')
            else:
                messages.error(request, '❌ Insufficient tokens!')
        return redirect('admin_wallet_detail', user_id=user_id)

    return render(request, 'admin_panel/plans/wallet_detail.html', {
        'target_user': user, 'wallet': wallet, 'transactions': transactions,
    })


# ─── User Plans (Admin) ───────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def user_plan_list(request):
    role   = request.GET.get('role', '')
    search = request.GET.get('search', '').strip()
    user_plans = UserPlan.objects.select_related('user', 'plan').filter(is_active=True).order_by('-bought_at')
    if role:
        user_plans = user_plans.filter(user__role=role)
    if search:
        user_plans = user_plans.filter(user__username__icontains=search)
    return render(request, 'admin_panel/plans/user_plan_list.html', {
        'user_plans': user_plans, 'role': role, 'search': search,
    })


# ─── Assign Plan to User (Admin) ─────────────────────────────
@login_required
@user_passes_test(is_admin)
def assign_plan(request, user_id):
    target_user  = get_object_or_404(User, pk=user_id)
    plans        = Plan.objects.filter(role=target_user.role, is_active=True)
    current_plan = UserPlan.objects.filter(user=target_user, is_active=True).first()

    if request.method == 'POST':
        plan = get_object_or_404(Plan, pk=request.POST.get('plan_id'))
        UserPlan.objects.filter(user=target_user, is_active=True).update(is_active=False)
        UserPlan.objects.create(user=target_user, plan=plan)

        if target_user.role in ['doctor', 'nurse'] and plan.token_mode == 'fixed' and plan.tokens > 0:
            wallet, _ = Wallet.objects.get_or_create(user=target_user)
            wallet.add_tokens(plan.tokens, note=f"Plan upgrade: {plan.name}")

        messages.success(request, f'✅ {plan.name} plan assigned successfully!')
        return redirect('admin_user_plan_list')

    return render(request, 'admin_panel/plans/assign_plan.html', {
        'target_user': target_user, 'plans': plans, 'current_plan': current_plan,
    })


# ─── Default Free Credits Setting (Admin) ────────────────────
@login_required
@user_passes_test(is_admin)
def default_credits(request):
    doctor_credit,   _ = DefaultFreeCredit.objects.get_or_create(role='doctor')
    nurse_credit,    _ = DefaultFreeCredit.objects.get_or_create(role='nurse')
    hospital_credit, _ = DefaultFreeCredit.objects.get_or_create(role='hospital')

    if request.method == 'POST':
        doctor_credit.free_tokens           = request.POST.get('doctor_tokens', 0)
        doctor_credit.free_vacancy_limit    = request.POST.get('doctor_vacancy_limit', 0)
        doctor_credit.free_duration_months  = request.POST.get('doctor_duration', 1)
        doctor_credit.free_is_lifetime      = 'doctor_lifetime' in request.POST
        doctor_credit.save()

        nurse_credit.free_tokens            = request.POST.get('nurse_tokens', 0)
        nurse_credit.free_vacancy_limit     = request.POST.get('nurse_vacancy_limit', 0)
        nurse_credit.free_duration_months   = request.POST.get('nurse_duration', 1)
        nurse_credit.free_is_lifetime       = 'nurse_lifetime' in request.POST
        nurse_credit.save()

        hospital_credit.free_shift_post_limit   = request.POST.get('hospital_shift_limit', 0)
        hospital_credit.free_vacancy_post_limit = request.POST.get('hospital_vacancy_limit', 0)
        hospital_credit.free_duration_months    = request.POST.get('hospital_duration', 1)
        hospital_credit.free_is_lifetime        = 'hospital_lifetime' in request.POST
        hospital_credit.save()

        messages.success(request, '✅ Default credits updated!')
        return redirect('admin_default_credits')

    return render(request, 'admin_panel/plans/default_credits.html', {
        'doctor_credit': doctor_credit, 'nurse_credit': nurse_credit,
        'hospital_credit': hospital_credit,
        'duration_choices': Plan.DURATION_CHOICES,
    })


# ══════════════════════════════════════════════════════════════
# RAZORPAY + USER-FACING VIEWS
# ══════════════════════════════════════════════════════════════

import razorpay, json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required
def my_plans(request):
    role         = getattr(request.user, 'role', 'doctor')
    plans        = Plan.objects.filter(role=role, is_active=True).order_by('price')
    current_plan = UserPlan.objects.filter(user=request.user, is_active=True).first()

    if current_plan and current_plan.is_expired:
        current_plan.is_active = False
        current_plan.save()
        current_plan = None

    wallet_balance, wallet_transactions, plan_history = 0, [], []

    if role in ['doctor', 'nurse']:
        try:
            wallet = request.user.wallet
            wallet_balance      = wallet.balance
            wallet_transactions = wallet.transactions.order_by('-created_at')[:20]
        except Exception:
            pass
    elif role == 'hospital':
        plan_history = UserPlan.objects.filter(user=request.user).select_related('plan').order_by('-bought_at')[:20]

    template_map = {
        'doctor':   'doctors/plans.html',
        'nurse':    'nurses/plans.html',
        'hospital': 'hospitals/plans.html',
    }
    return render(request, template_map.get(role, 'doctors/plans.html'), {
        'plans':               plans,
        'current_plan':        current_plan,
        'wallet_balance':      wallet_balance,
        'wallet_transactions': wallet_transactions,
        'plan_history':        plan_history,
        'razorpay_key':        settings.RAZORPAY_KEY_ID,
    })


@login_required
def create_order(request, plan_id):
    plan = get_object_or_404(Plan, pk=plan_id, is_active=True)
    if request.method == 'POST':
        amount_paise = int(plan.price * 100)
        order = client.order.create({
            'amount': amount_paise, 'currency': 'INR', 'payment_capture': 1,
            'notes': {'plan_id': plan.id, 'user_id': request.user.id}
        })
        return JsonResponse({
            'order_id': order['id'], 'amount': amount_paise, 'currency': 'INR',
            'plan_name': plan.name, 'plan_id': plan.id,
            'key': settings.RAZORPAY_KEY_ID, 'user_name': request.user.username,
        })
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def verify_payment(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id':   data.get('razorpay_order_id'),
                'razorpay_payment_id': data.get('razorpay_payment_id'),
                'razorpay_signature':  data.get('razorpay_signature'),
            })
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'success': False, 'error': 'Payment verification failed'})

        plan = get_object_or_404(Plan, pk=data.get('plan_id'))
        user = request.user
        UserPlan.objects.filter(user=user, is_active=True).update(is_active=False)
        UserPlan.objects.create(user=user, plan=plan)

        # Tokens sirf tab add karo jab token_mode = 'fixed'
        if getattr(user, 'role', '') in ['doctor', 'nurse'] and plan.token_mode == 'fixed' and plan.tokens > 0:
            wallet, _ = Wallet.objects.get_or_create(user=user)
            wallet.add_tokens(plan.tokens, note=f"Plan purchase: {plan.name} (₹{plan.price})")

        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def payment_success(request):
    messages.success(request, '🎉 Payment successful! Plan activated.')
    return redirect('my_plans')


@login_required
@user_passes_test(is_admin)
def all_users_plan(request):
    role   = request.GET.get('role', 'hospital')
    search = request.GET.get('search', '').strip()
    users  = User.objects.filter(role=role).order_by('username')
    if search:
        users = users.filter(username__icontains=search)
    for user in users:
        user.current_plan = UserPlan.objects.filter(user=user, is_active=True).first()
    return render(request, 'admin_panel/plans/all_users_plan.html', {
        'users': users, 'role': role, 'search': search,
    })