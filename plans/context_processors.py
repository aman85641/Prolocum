from plans.utils import get_active_plan

def plan_permissions(request):
    if not request.user.is_authenticated:
        return {
            'ctx_can_view_shifts':    False,
            'ctx_can_view_urgent':    False,
            'ctx_can_apply_vacancy':  False,
            'ctx_can_post_shift':     False,
        }

    active_plan = get_active_plan(request.user)

    can_view_shifts   = False
    can_view_urgent   = False
    can_apply_vacancy = False
    can_post_shift    = False
    can_post_shift_h   = False
    can_post_vacancy_h = False

    if active_plan and active_plan.plan:
        p = active_plan.plan
        can_view_shifts   = p.shift_view_enabled
        can_view_urgent   = p.urgent_shift_enabled and p.shift_view_enabled
        can_apply_vacancy = p.vacancy_apply_enabled
        can_post_shift    = p.shift_post_enabled
        can_post_shift_h   = p.shift_post_enabled
        can_post_vacancy_h = p.vacancy_post_enabled

    return {
         'ctx_can_view_shifts':    can_view_shifts,
    'ctx_can_view_urgent':    can_view_urgent,
    'ctx_can_apply_vacancy':  can_apply_vacancy,
    'ctx_can_post_shift':     can_post_shift or can_post_shift_h,
    'ctx_can_post_vacancy':   can_post_vacancy_h,
    }