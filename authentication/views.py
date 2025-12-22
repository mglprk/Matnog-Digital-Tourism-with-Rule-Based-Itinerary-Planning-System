# import this to require login
import json
import os
import random
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

# import this for sending email to user
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.db.models import Q, Count
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from accommodation.models import Accommodation
from authentication.forms import UserRegistrationForm, FirstTimePasswordChangeForm, UserProfileForm
from config import settings
from config.decorator import permission_required
from destination.models import Destination
from transportation.models import Transportation

# Create your views here.
mapbox_access_token = settings.MAPBOX_PUBLIC_TOKEN


@login_required(login_url='login')
@login_required(login_url='login')
def homepage(request):
    # Basic counts
    total_destinations = Destination.objects.filter(is_active=True).count()
    total_accommodations = Accommodation.objects.filter(is_active=True).count()
    total_transportations = Transportation.objects.filter(is_active=True).count()
    pending_users = User.objects.filter(is_active=False).count()
    active_users = User.objects.filter(is_active=True).count()

    # Destinations by category
    category_colors = {
        'nature': '#1E90FF',
        'cultural': '#FF8C00',
        'historical': '#8B4513',
        'food': '#FF1493',
        'adventure': '#32CD32',
        'shopping': '#9400D3',
        'other': '#EA4335'
    }

    destinations_by_category = []
    category_counts = Destination.objects.filter(is_active=True).values('category').annotate(
        count=Count('id')).order_by('-count')

    for cat in category_counts:
        category_name = cat['category'] or 'other'
        percentage = round((cat['count'] / total_destinations * 100), 1) if total_destinations > 0 else 0
        destinations_by_category.append({
            'name': category_name,
            'count': cat['count'],
            'percentage': percentage,
            'color': category_colors.get(category_name, category_colors['other'])
        })

    # Recent users
    recent_users = User.objects.order_by('-date_joined')[:5]

    # Accessibility features count
    wheelchair_friendly_destinations = Destination.objects.filter(
        wheelchair_friendly=True,
        is_active=True
    ).count()

    kid_friendly_destinations = Destination.objects.filter(
        kid_friendly=True,
        is_active=True
    ).count()

    wheelchair_friendly_accommodations = Accommodation.objects.filter(
        wheelchair_friendly=True,
        is_active=True
    ).count()

    # Missing images count
    missing_images = Destination.objects.filter(
        Q(image='') | Q(image__isnull=True),
        is_active=True
    ).count()

    # Incomplete destinations (missing description or coordinates)
    incomplete_destinations = Destination.objects.filter(
        Q(description='') | Q(description__isnull=True) |
        Q(latitude__isnull=True) | Q(longitude__isnull=True),
        is_active=True
    ).count()

    # Prepare destinations for map (including accommodations and transportation)
    destinations_list = []

    # Add regular destinations
    for dest in Destination.objects.filter(is_active=True):
        if dest.latitude and dest.longitude:
            destinations_list.append({
                'name': dest.name,
                'latitude': float(dest.latitude),
                'longitude': float(dest.longitude),
                'category': dest.category or 'other'
            })

    # Add accommodations as special category
    for acc in Accommodation.objects.filter(is_active=True):
        if acc.latitude and acc.longitude:
            destinations_list.append({
                'name': acc.name,
                'latitude': float(acc.latitude),
                'longitude': float(acc.longitude),
                'category': 'accommodation',
                'type': acc.get_type_display()
            })

    # Add transportation hubs
    for trans in Transportation.objects.filter(is_active=True):
        if trans.latitude and trans.longitude:
            destinations_list.append({
                'name': trans.name,
                'latitude': float(trans.latitude),
                'longitude': float(trans.longitude),
                'category': 'transportation',
                'hub_type': trans.get_hub_type_display()
            })

    # Accommodation statistics
    accommodation_types = Accommodation.objects.filter(is_active=True).values('type').annotate(
        count=Count('id')
    ).order_by('-count')

    accommodation_stats = []
    for acc_type in accommodation_types:
        accommodation_stats.append({
            'type': dict(Accommodation.ACCOMMODATION_TYPES).get(acc_type['type'], acc_type['type']),
            'count': acc_type['count']
        })

    # Budget distribution
    budget_distribution = {
        'destinations': {
            'low': Destination.objects.filter(budget_category='low', is_active=True).count(),
            'medium': Destination.objects.filter(budget_category='medium', is_active=True).count(),
            'high': Destination.objects.filter(budget_category='high', is_active=True).count(),
        },
        'accommodations': {
            'low': Accommodation.objects.filter(budget_category='low', is_active=True).count(),
            'medium': Accommodation.objects.filter(budget_category='medium', is_active=True).count(),
            'high': Accommodation.objects.filter(budget_category='high', is_active=True).count(),
        }
    }

    # Facilities count
    facilities_stats = {
        'parking_destinations': Destination.objects.filter(parking_available=True, is_active=True).count(),
        'parking_accommodations': Accommodation.objects.filter(parking_available=True, is_active=True).count(),
        'wifi_accommodations': Accommodation.objects.filter(wifi_available=True, is_active=True).count(),
        'wheelchair_destinations': wheelchair_friendly_destinations,
        'wheelchair_accommodations': wheelchair_friendly_accommodations,
        'kid_friendly': kid_friendly_destinations,
    }

    context = {
        'mapbox_access_token': mapbox_access_token,
        'destinations': json.dumps(destinations_list),
        'total_destinations': total_destinations,
        'total_accommodations': total_accommodations,
        'total_transportations': total_transportations,
        'pending_users': pending_users,
        'active_users': active_users,
        'destinations_by_category': destinations_by_category,
        'recent_users': recent_users,
        'missing_images': missing_images,
        'incomplete_destinations': incomplete_destinations,
        'accommodation_stats': accommodation_stats,
        'budget_distribution': budget_distribution,
        'facilities_stats': facilities_stats,
        'last_updated': datetime.now(),
    }

    return render(request, 'administrator/admin/overview/overview.html', context)


def email_user(request, user):
    """Send activation email to new user with generated password."""
    current_site = get_current_site(request)
    mail_subject = "Activate your account"

    # Render the message
    message = render_to_string(
        'administrator/authentication/email_activation/activate_email_message.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),
        }
    )

    # Send the email
    email = EmailMessage(
        mail_subject,
        message,
        to=[user.email]
    )
    email.content_subtype = "html"  # make sure HTML template renders properly
    email.send()


def register(request):
    """User registration - no password required, admin activates later"""
    if request.user.is_authenticated:
        return redirect('overview')

    form = UserRegistrationForm()
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # User inactive until admin activates
            user.set_unusable_password()  # No password set yet
            user.save()

            messages.success(
                request,
                'Registration successful! Your account is pending admin approval. '
                'You will receive an email with login credentials once approved.'
            )
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    return render(request, 'administrator/authentication/register.html', {
        'form': form
    })


def send_activation_email(request, user, password):
    """Send email with generated password to newly activated user"""
    mail_subject = "Your Account Has Been Activated"
    current_site = get_current_site(request)
    message = render_to_string(
        'administrator/authentication/email_activation/activate_email_message.html', {
            'user': user,
            'password': password,
            'domain': current_site.domain,
        }
    )

    email = EmailMessage(
        mail_subject,
        message,
        to=[user.email]
    )
    email.content_subtype = "html"
    email.send()



# to activate user from email
def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Account successfully activated. Login using the credentials.")
    else:
        messages.error(request, "Account activation failed!")
    return redirect('login')

def login_check(request):
    """ check if user is first_time_login and redirect to change password page """
    if request.user.is_authenticated:
        if request.user.profile.first_time_login:
            return redirect('change_password')
        else:
            return redirect('homepage')
    else:
        return redirect('login')




@login_required(login_url='login')
def change_password(request):
    form = FirstTimePasswordChangeForm(user=request.user)

    if request.method == 'POST':
        form = FirstTimePasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Re-authenticate user to prevent logout after password change
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)

            # Update first_time_login flag
            profile = request.user.profile
            profile.first_time_login = False
            profile.save()

            messages.success(request, 'Password changed successfully.')
            return redirect('homepage')
        else:
            for field, errors in form.errors.items():
                error_message = "\n".join(errors)
                messages.error(request, error_message)

    return render(request, 'administrator/authentication/change_password.html', {
        'form': form
    })



@permission_required('can_view_users')
def users_view(request):
    users = User.objects.all().order_by('-id')

    return render(request, 'administrator/admin/users/users.html', {
        'users': users
    })

@permission_required('can_manage_users')
def user_add(request):
    form = UserRegistrationForm()
    perm_form = UserProfileForm()
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        perm_form = UserProfileForm(request.POST)
        if form.is_valid() and perm_form.is_valid():
            user = form.save(commit=False)
            user.is_active = True  # directly activate user when added from admin
            user.save()
            profile = perm_form.save(commit=False)
            profile.user = user
            profile.save()
            messages.success(request, 'User added successfully.')
            return redirect('users')
        else:
            for field, errors in form.errors.items():
                error_message = "\n".join(errors)  # join with new lines
                messages.error(request, error_message)

    return render(request, 'administrator/admin/users/user_add.html', {
        'form': form,
        'perm_form': perm_form
    })

@permission_required('can_manage_users')
def user_edit(request, pk):
    user = User.objects.get(id=pk)
    form = UserRegistrationForm(instance=user)
    perm_form = UserProfileForm(instance=user.profile)
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, instance=user)
        perm_form = UserProfileForm(request.POST, instance=user.profile)
        if form.is_valid() and perm_form.is_valid():
            form = form.save(commit=False)
            form.save()
            perm_form = perm_form.save(commit=False)
            perm_form.user = user
            perm_form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('users')
        else:
            for field, errors in form.errors.items():
                error_message = "\n".join(errors)  # join with new lines
                messages.error(request, error_message)

    return render(request, 'administrator/admin/users/user_add.html', {
        'form': form,
        'perm_form': perm_form,
        'users': user
    })

@permission_required('can_manage_users')
def user_activate(request, pk):
    user = User.objects.get(id=pk)
    if not user.is_active:
        # Generate a random password
        password = ''.join(random.choices(
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()', k=10))
        user.set_password(password)
        user.is_active = True
        user.save()
        print("password", password)
        send_activation_email(request, user, password)
        messages.success(request, f'User {user.username} activated and email sent.')
    else:
        messages.info(request, f'User {user.username} is already active.')

    return redirect('users')
