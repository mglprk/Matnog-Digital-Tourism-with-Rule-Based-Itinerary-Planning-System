from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from accommodation.forms import AccommodationForm
from accommodation.models import Accommodation, AccommodationImage
from config import settings
from config.decorator import permission_required

mapbox_access_token = settings.MAPBOX_PUBLIC_TOKEN


@permission_required('can_view_accommodations')
def accommodation_view(request):
    accommodations = Accommodation.objects.all().order_by('-id')
    return render(request, 'administrator/admin/accommodations/accommodations.html', {
        'accommodations': accommodations
    })


@permission_required('can_manage_accommodations')
def accommodation_add(request):
    form = AccommodationForm()
    if request.method == 'POST':
        form = AccommodationForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the accommodation
            accommodation = form.save(commit=False)
            accommodation.created_by = request.user
            accommodation.is_active = True
            accommodation.save()

            # Handle additional images
            additional_images = request.FILES.getlist('additional_images')
            for image in additional_images:
                AccommodationImage.objects.create(
                    accommodation=accommodation,
                    image=image
                )

            messages.success(request, 'Accommodation added successfully.')
            return redirect('accommodation')
        else:
            for field, errors in form.errors.items():
                field_label = form.fields[field].label or field.capitalize()
                error_message = f"{field_label} field {' '.join(errors).replace('This field', '').strip().capitalize()}."
                messages.error(request, error_message)

    return render(request, 'administrator/admin/accommodations/accommodation_add.html', {
        'form': form,
        'mapbox_access_token': mapbox_access_token
    })


@permission_required('can_manage_accommodations')
def accommodation_edit(request, pk):
    accommodation = get_object_or_404(Accommodation, id=pk)
    form = AccommodationForm(instance=accommodation)

    # Get existing additional images
    existing_images = accommodation.additional_images.all()

    if request.method == 'POST':
        form = AccommodationForm(request.POST, request.FILES, instance=accommodation)
        if form.is_valid():
            accommodation = form.save(commit=False)
            accommodation.created_by = accommodation.created_by
            accommodation.is_active = accommodation.is_active
            accommodation.save()

            # Handle new additional images
            additional_images = request.FILES.getlist('additional_images')
            for image in additional_images:
                AccommodationImage.objects.create(
                    accommodation=accommodation,
                    image=image
                )

            messages.success(request, 'Accommodation updated successfully.')
            return redirect('accommodation')
        else:
            for field, errors in form.errors.items():
                field_label = form.fields[field].label or field.capitalize()
                error_message = f"{field_label} field {' '.join(errors).replace('This field', '').strip().capitalize()}."
                messages.error(request, error_message)

    return render(request, 'administrator/admin/accommodations/accommodation_add.html', {
        'form': form,
        'accommodation': accommodation,
        'existing_images': existing_images,
        'mapbox_access_token': mapbox_access_token
    })


@permission_required('can_manage_accommodations')
def accommodation_delete(request, pk):
    accommodation = get_object_or_404(Accommodation, id=pk)
    accommodation.delete()
    messages.success(request, 'Accommodation deleted successfully.')
    return redirect('accommodation')


@permission_required('can_manage_accommodations')
def accommodation_image_delete(request, pk):
    """Delete a single accommodation image"""
    image = get_object_or_404(AccommodationImage, id=pk)
    accommodation_id = image.accommodation.id
    image.delete()
    messages.success(request, 'Image deleted successfully.')
    return redirect('accommodation_edit', pk=accommodation_id)


def get_accommodations(request):
    """API endpoint to fetch available accommodations"""
    accommodations = Accommodation.objects.filter(
        is_active=True,
        status='active'
    ).values('id', 'name', 'type', 'budget_category', 'address')
    return JsonResponse(list(accommodations), safe=False)