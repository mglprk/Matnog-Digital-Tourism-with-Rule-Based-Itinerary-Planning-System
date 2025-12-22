from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from config import settings
from config.decorator import permission_required
from destination.forms import DestinationForm
from destination.models import Destination, DestinationImage

mapbox_access_token = settings.MAPBOX_PUBLIC_TOKEN


@permission_required('can_view_destinations')
def destination_view(request):
    destinations = Destination.objects.all().order_by('-id')
    return render(request, 'administrator/admin/destinations/destinations.html', {
        'destinations': destinations
    })


@permission_required('can_manage_destinations')
def destination_add(request):
    form = DestinationForm()
    if request.method == 'POST':
        form = DestinationForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the destination
            destination = form.save(commit=False)
            destination.created_by = request.user
            destination.is_active = True
            destination.save()

            # Handle additional images
            additional_images = request.FILES.getlist('additional_images')
            for image in additional_images:
                DestinationImage.objects.create(
                    destination=destination,
                    image=image
                )

            messages.success(request, 'Destination added successfully.')
            return redirect('destination')
        else:
            for field, errors in form.errors.items():
                field_label = form.fields[field].label or field.capitalize()
                error_message = f"{field_label} field {' '.join(errors).replace('This field', '').strip().capitalize()}."
                messages.error(request, error_message)

    return render(request, 'administrator/admin/destinations/destination_add.html', {
        'form': form,
        'mapbox_access_token': mapbox_access_token
    })


@permission_required('can_manage_destinations')
def destination_edit(request, pk):
    destination = get_object_or_404(Destination, id=pk)
    form = DestinationForm(instance=destination)

    # Get existing additional images
    existing_images = destination.additional_images.all()

    if request.method == 'POST':
        form = DestinationForm(request.POST, request.FILES, instance=destination)
        if form.is_valid():
            destination = form.save(commit=False)
            destination.created_by = destination.created_by
            destination.is_active = destination.is_active
            destination.save()

            # Handle new additional images
            additional_images = request.FILES.getlist('additional_images')
            for image in additional_images:
                DestinationImage.objects.create(
                    destination=destination,
                    image=image
                )

            messages.success(request, 'Destination updated successfully.')
            return redirect('destination')
        else:
            for field, errors in form.errors.items():
                field_label = form.fields[field].label or field.capitalize()
                error_message = f"{field_label} field {' '.join(errors).replace('This field', '').strip().capitalize()}."
                messages.error(request, error_message)

    return render(request, 'administrator/admin/destinations/destination_add.html', {
        'form': form,
        'destination': destination,
        'existing_images': existing_images,
        'mapbox_access_token': mapbox_access_token
    })


@permission_required('can_manage_destinations')
def destination_delete(request, pk):
    destination = get_object_or_404(Destination, id=pk)
    destination.delete()  # This will cascade delete all DestinationImage objects
    messages.success(request, 'Destination deleted successfully.')
    return redirect('destination')


@permission_required('can_manage_destinations')
def destination_image_delete(request, pk):
    """Delete a single destination image"""
    image = get_object_or_404(DestinationImage, id=pk)
    destination_id = image.destination.id
    image.delete()
    messages.success(request, 'Image deleted successfully.')
    return redirect('destination_edit', pk=destination_id)