from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect

from config.decorator import permission_required
from .forms import AnnouncementForm
from .models import Announcement
from config import settings


# Create your views here.

mapbox_access_token = settings.MAPBOX_PUBLIC_TOKEN


@permission_required('can_view_announcements')
def announcement_view(request):
    announcements = Announcement.objects.all().order_by('-id')

    return render(request, 'administrator/admin/announcements/announcements.html', {
        'announcements': announcements
    })

@permission_required('can_manage_announcements')
def announcement_add(request):
    form = AnnouncementForm()
    if request.method == 'POST':

        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            # set the user who created this announcement
            form = form.save(commit=False)
            form.save()
            messages.success(request, 'announcement added successfully.')
            return redirect('general:announcement')
        else:
            for field, errors in form.errors.items():
                field_label = form.fields[field].label or field.capitalize()
                # Make message more natural: "Name field is required."
                error_message = f"{field_label} field {' '.join(errors).replace('This field', '').strip().capitalize()}."
                messages.error(request, error_message)

    return render(request, 'administrator/admin/announcements/announcement_add.html', {
        'form': form,
        'mapbox_access_token': mapbox_access_token
    })

@permission_required('can_manage_announcements')
def announcement_edit(request, pk):
    announcement = Announcement.objects.get(id=pk)
    form = AnnouncementForm(instance=announcement)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            form = form.save(commit=False)
            form.save()
            messages.success(request, 'announcement updated successfully.')
            return redirect('general:announcement')
        else:
            for field, errors in form.errors.items():
                field_label = form.fields[field].label or field.capitalize()
                # Make message more natural: "Name field is required."
                error_message = f"{field_label} field {' '.join(errors).replace('This field', '').strip().capitalize()}."
                messages.error(request, error_message)

    return render(request, 'administrator/admin/announcements/announcement_add.html', {
        'form': form,
        'announcement': announcement,
        'mapbox_access_token': mapbox_access_token
    })


def get_announcements(request):
    """API endpoint to fetch available announcements"""
    announcements = Announcement.objects.filter(
        is_active=True,
        status='active'
    ).values('id', 'name', 'type', 'budget_category', 'address')

    return JsonResponse(list(announcements), safe=False)

@permission_required('can_manage_announcements')
def announcement_delete(request, pk):
    instance = Announcement.objects.get(id=pk)
    instance.delete()
    messages.success(request, 'announcement deleted successfully.')
    return redirect('general:announcement')