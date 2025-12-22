# core/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def permission_required(permission_attr):
    """
    Decorator that checks if user.profile has the specified permission.
    Usage: @permission_required('can_view_users')
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            # Superusers bypass all permission checks
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(request.user, 'profile', None)
            if profile and getattr(profile, permission_attr, False):
                return view_func(request, *args, **kwargs)

            messages.error(request, "You don't have permission to access this page.")
            return redirect('homepage')  # or wherever you want

        return wrapper

    return decorator