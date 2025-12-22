# itinerary/views.py
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator
import json

from accommodation.models import Accommodation
from config import settings
from destination.models import Destination
from general.models import Announcement
from transportation.models import Transportation
from .services import ItineraryPlannerService, TravelPreferences


# Function-Based View
@csrf_exempt
@require_http_methods(["POST"])
def generate_itinerary(request):
    """
    Generate travel itinerary based on user preferences
    POST /itinerary/generate/
    """
    try:
        # Parse JSON body
        data = json.loads(request.body)

        # Validate required fields
        required_fields = ['days', 'pax', 'budget_category', 'pace_preference']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)

        # Validate field values
        try:
            days = int(data['days'])
            pax = int(data['pax'])

            if days < 1 or days > 14:
                return JsonResponse({
                    'success': False,
                    'error': 'Days must be between 1 and 14'
                }, status=400)

            if pax < 1:
                return JsonResponse({
                    'success': False,
                    'error': 'Number of travelers must be at least 1'
                }, status=400)

            if data['budget_category'] not in ['low', 'medium', 'high']:
                return JsonResponse({
                    'success': False,
                    'error': 'Budget category must be: low, medium, or high'
                }, status=400)

            if data['pace_preference'] not in ['relaxed', 'moderate', 'packed']:
                return JsonResponse({
                    'success': False,
                    'error': 'Pace preference must be: relaxed, moderate, or packed'
                }, status=400)

            # Validate travel time hours
            travel_time_hours = float(data.get('travel_time_hours', 0))
            if travel_time_hours < 0 or travel_time_hours > 24:
                return JsonResponse({
                    'success': False,
                    'error': 'Travel time must be between 0 and 24 hours'
                }, status=400)

            # Validate start_date format if provided
            start_date = data.get('start_date')
            if start_date:
                from datetime import datetime
                try:
                    datetime.strptime(start_date, '%Y-%m-%d')
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Start date must be in YYYY-MM-DD format'
                    }, status=400)

        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid data type: {str(e)}'
            }, status=400)

        # Create preferences object
        preferences = TravelPreferences(
            days=days,
            pax=pax,
            budget_category=data['budget_category'],
            starting_point=data.get('starting_point', 'sorsogon_city'),
            transport_mode=data.get('transport_mode', []),
            interests=data.get('interests', []),
            pace_preference=data['pace_preference'],
            has_children=data.get('has_children', False),
            has_seniors=data.get('has_seniors', False),
            has_disabilities=data.get('has_disabilities', False),
            has_pets=data.get('has_pets', False),
            include_accommodation=data.get('include_accommodation', True),
            accommodation_types=data.get('accommodation_types', []),
            max_travel_time=int(data.get('max_travel_time', 120)),
            must_visit_ids=data.get('must_visit_ids', []),
            exclude_destination_ids=data.get('exclude_destination_ids', []),
            exclude_categories=data.get('exclude_categories', []),
            accommodation_id=data.get('accommodation_id'),
            # New fields
            point_of_origin=data.get('point_of_origin', 'Sorsogon City'),
            travel_time_hours=travel_time_hours,
            activity_on_same_day=data.get('activity_on_same_day', True),
            start_date=start_date
        )

        # Generate itinerary
        planner = ItineraryPlannerService(preferences)
        itinerary = planner.generate_itinerary()

        return JsonResponse({
            'success': True,
            'data': itinerary
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON format'
        }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


# Class-Based View (alternative)
@method_decorator(csrf_exempt, name='dispatch')
class GenerateItineraryView(View):
    """
    Class-based view to generate itinerary
    POST /itinerary/generate/
    """

    def post(self, request):
        try:
            data = json.loads(request.body)

            # Validate required fields
            required_fields = ['days', 'pax', 'budget_category', 'pace_preference']
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                return JsonResponse({
                    'success': False,
                    'error': f'Missing required fields: {", ".join(missing_fields)}'
                }, status=400)

            # Validate values
            days = int(data['days'])
            pax = int(data['pax'])

            if days < 1 or days > 14:
                return JsonResponse({
                    'success': False,
                    'error': 'Days must be between 1 and 14'
                }, status=400)

            if pax < 1:
                return JsonResponse({
                    'success': False,
                    'error': 'Number of travelers must be at least 1'
                }, status=400)

            # Validate travel time hours
            travel_time_hours = float(data.get('travel_time_hours', 0))
            if travel_time_hours < 0 or travel_time_hours > 24:
                return JsonResponse({
                    'success': False,
                    'error': 'Travel time must be between 0 and 24 hours'
                }, status=400)

            # Validate start_date format if provided
            start_date = data.get('start_date')
            if start_date:
                from datetime import datetime
                try:
                    datetime.strptime(start_date, '%Y-%m-%d')
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'error': 'Start date must be in YYYY-MM-DD format'
                    }, status=400)

            # Create preferences
            preferences = TravelPreferences(
                days=days,
                pax=pax,
                budget_category=data['budget_category'],
                starting_point=data.get('starting_point', 'sorsogon_city'),
                transport_mode=data.get('transport_mode', []),
                interests=data.get('interests', []),
                pace_preference=data['pace_preference'],
                has_children=data.get('has_children', False),
                has_seniors=data.get('has_seniors', False),
                has_disabilities=data.get('has_disabilities', False),
                has_pets=data.get('has_pets', False),
                include_accommodation=data.get('include_accommodation', True),
                accommodation_types=data.get('accommodation_types', []),
                max_travel_time=int(data.get('max_travel_time', 120)),
                must_visit_ids=data.get('must_visit_ids', []),
                exclude_destination_ids=data.get('exclude_destination_ids', []),
                exclude_categories=data.get('exclude_categories', []),
                accommodation_id=data.get('accommodation_id'),
                # New fields
                point_of_origin=data.get('point_of_origin', 'Sorsogon City'),
                travel_time_hours=travel_time_hours,
                activity_on_same_day=data.get('activity_on_same_day', True),
                start_date=start_date
            )

            # Generate itinerary
            planner = ItineraryPlannerService(preferences)
            itinerary = planner.generate_itinerary()

            return JsonResponse({
                'success': True,
                'data': itinerary
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON format'
            }, status=400)

        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid data: {str(e)}'
            }, status=400)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Server error: {str(e)}'
            }, status=500)



def home(request):
    """Landing page view"""
    # Get stats
    total_destinations = Destination.objects.filter(is_active=True, status='active').count()
    total_accommodations = Accommodation.objects.filter(is_active=True, status='active').count()
    total_transportation = Transportation.objects.filter(is_active=True, status='active').count()

    # Get destinations for carousel and featured section
    destinations_with_images = Destination.objects.filter(
        is_active=True,
        status='active'
    ).exclude(image='')[:10]

    destinations = Destination.objects.filter(
        Q(latitude__isnull=False) & Q(longitude__isnull=False)
        # status is active
        & Q(is_active=True)
    ).values('name', 'latitude', 'longitude', 'category')


    accommodations = Accommodation.objects.filter(
        Q(latitude__isnull=False) & Q(longitude__isnull=False)
        # status is active
        & Q(is_active=True)
    )
    transportations = Transportation.objects.filter(
        Q(latitude__isnull=False) & Q(longitude__isnull=False)
        # status is active
        & Q(is_active=True)
    )

    # Convert Decimal to float
    destinations_list = [
        {
            'name': d['name'],
            'latitude': float(d['latitude']),
            'longitude': float(d['longitude']),
            'category': d['category']
        } for d in destinations
    ]
    accommodations_list = [
        {
            'name': a.name,
            'latitude': float(a.latitude),
            'longitude': float(a.longitude),
            'category': 'accommodation'
        } for a in accommodations
    ]
    print("accommodation_List", accommodations_list)

    transportations_list = [
        {
            'name': t.name,
            'latitude': float(t.latitude),
            'longitude': float(t.longitude),
            'category': 'transportation'
        } for t in transportations
    ]

    all_destinations = destinations_list + accommodations_list + transportations_list

    # Get active announcements
    now = timezone.now()
    announcements = Announcement.objects.filter(
        is_published=True,
        publish_date__lte=now
    ).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=now)
    ).order_by('-priority', '-publish_date')[:5]

    # Get featured/urgent announcement for banner
    urgent_announcement = Announcement.objects.filter(
        is_published=True,
        publish_date__lte=now,
        priority__in=['urgent', 'high']
    ).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=now)
    ).first()


    context = {
        'total_destinations': total_destinations,
        'total_accommodations': total_accommodations,
        'total_transportation': total_transportation,
        'featured_destinations': all_destinations,  # For the featured section
        'mapbox_access_token': getattr(settings, 'MAPBOX_PUBLIC_TOKEN', ''),
        'announcements': announcements,
        'urgent_announcement': urgent_announcement,
    }
    return render(request, 'public/home.html', context)


def destinations(request):
    """Destinations listing page with filters"""
    # Get filter parameters
    category = request.GET.get('category', '')
    budget = request.GET.get('budget', '')
    search = request.GET.get('search', '')

    # Base queryset
    destinations_list = Destination.objects.filter(is_active=True, status='active')

    # Apply filters
    if category:
        destinations_list = destinations_list.filter(category=category)
    if budget:
        destinations_list = destinations_list.filter(budget_category=budget)
    if search:
        destinations_list = destinations_list.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(address__icontains=search)
        )

    # Get all categories and budgets for filter options
    categories = Destination.CATEGORY_CHOICES
    budgets = Destination.BUDGET_CHOICES

    context = {
        'destinations': destinations_list,
        'categories': categories,
        'budgets': budgets,
        'selected_category': category,
        'selected_budget': budget,
        'search_query': search,
    }
    return render(request, 'public/destinations.html', context)


def destination_detail(request, pk):
    """Detailed view of a single destination with carousel"""
    destination = get_object_or_404(
        Destination.objects.prefetch_related('additional_images'),
        pk=pk,
        is_active=True,
        status='active'
    )

    # Get all images (primary + additional)
    all_images = []
    if destination.image:
        all_images.append({
            'url': destination.image.url,
            'is_primary': True
        })

    for img in destination.additional_images.all():
        all_images.append({
            'url': img.image.url,
            'is_primary': False
        })

    # Get related destinations (same category)
    related_destinations = Destination.objects.filter(
        category=destination.category,
        is_active=True,
        status='active'
    ).exclude(pk=pk)[:4]

    context = {
        'destination': destination,
        'all_images': all_images,
        'related_destinations': related_destinations,
        'mapbox_access_token': settings.MAPBOX_PUBLIC_TOKEN,
    }
    return render(request, 'public/destination_detail.html', context)


def accommodations(request):
    """Accommodations listing page with filters"""
    # Get filter parameters
    acc_type = request.GET.get('type', '')
    budget = request.GET.get('budget', '')
    search = request.GET.get('search', '')

    # Base queryset
    accommodations_list = Accommodation.objects.filter(is_active=True, status='active')

    # Apply filters
    if acc_type:
        accommodations_list = accommodations_list.filter(type=acc_type)
    if budget:
        accommodations_list = accommodations_list.filter(budget_category=budget)
    if search:
        accommodations_list = accommodations_list.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(address__icontains=search)
        )

    # Get all types and budgets for filter options
    types = Accommodation.ACCOMMODATION_TYPES
    budgets = Accommodation.BUDGET_CHOICES

    context = {
        'accommodations': accommodations_list,
        'types': types,
        'budgets': budgets,
        'selected_type': acc_type,
        'selected_budget': budget,
        'search_query': search,
    }
    return render(request, 'public/accommodations.html', context)


def accommodation_detail(request, pk):
    """Detailed view of a single accommodation with carousel"""
    accommodation = get_object_or_404(
        Accommodation.objects.prefetch_related('additional_images'),
        pk=pk,
        is_active=True,
        status='active'
    )

    # Get all images (primary + additional)
    all_images = []
    if accommodation.image:
        all_images.append({
            'url': accommodation.image.url,
            'is_primary': True
        })

    for img in accommodation.additional_images.all():
        all_images.append({
            'url': img.image.url,
            'is_primary': False
        })

    # Get related accommodations (same type)
    related_accommodations = Accommodation.objects.filter(
        type=accommodation.type,
        is_active=True,
        status='active'
    ).exclude(pk=pk)[:4]

    context = {
        'accommodation': accommodation,
        'all_images': all_images,
        'related_accommodations': related_accommodations,
        'mapbox_access_token': settings.MAPBOX_PUBLIC_TOKEN,
    }
    return render(request, 'public/accommodation_detail.html', context)


def transportation(request):
    """Transportation hubs listing page with filters"""
    # Get filter parameters
    hub_type = request.GET.get('type', '')
    search = request.GET.get('search', '')

    # Base queryset
    transportation_list = Transportation.objects.filter(is_active=True, status='active')

    # Apply filters
    if hub_type:
        transportation_list = transportation_list.filter(hub_type=hub_type)
    if search:
        transportation_list = transportation_list.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(address__icontains=search)
        )

    # Get all hub types for filter options
    hub_types = Transportation.HUB_TYPES

    context = {
        'transportation_hubs': transportation_list,
        'hub_types': hub_types,
        'selected_type': hub_type,
        'search_query': search,
    }
    return render(request, 'public/transportation.html', context)


def about(request):
    """About Sorsogon page"""
    return render(request, 'public/about.html')


def plan_trip(request):
    """Itinerary planning tool page"""
    # Get all active destinations, accommodations for the planner
    destinations_list = Destination.objects.filter(is_active=True, status='active')
    accommodations_list = Accommodation.objects.filter(is_active=True, status='active')

    context = {
        'destinations': destinations_list,
        'accommodations': accommodations_list,
    }
    return render(request, 'public/plan_trip.html', context)


def announcements(request):
    """Public announcements listing page"""
    now = timezone.now()

    # Get filter parameters
    priority = request.GET.get('priority', '')
    search = request.GET.get('search', '')

    # Base queryset - only published and within date range
    announcements_list = Announcement.objects.filter(
        is_published=True,
        publish_date__lte=now
    ).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=now)
    )

    # Apply filters
    if priority:
        announcements_list = announcements_list.filter(priority=priority)
    if search:
        announcements_list = announcements_list.filter(
            Q(title__icontains=search) |
            Q(content__icontains=search) |
            Q(excerpt__icontains=search)
        )

    # Order by priority and date
    announcements_list = announcements_list.order_by('-priority', '-publish_date')

    # Pagination
    paginator = Paginator(announcements_list, 9)  # 9 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get priority choices for filter
    priorities = Announcement.PRIORITY_CHOICES

    context = {
        'announcements': page_obj,
        'priorities': priorities,
        'selected_priority': priority,
        'search_query': search,
        'total_count': announcements_list.count(),
    }
    return render(request, 'public/announcements.html', context)


def announcement_detail(request, pk):
    """Single announcement detail page"""
    now = timezone.now()

    # Get the announcement (must be published and within date range)
    announcement = get_object_or_404(
        Announcement,
        pk=pk,
        is_published=True,
        publish_date__lte=now
    )

    # Check if expired
    if announcement.expiry_date and announcement.expiry_date < now:
        from django.http import Http404
        raise Http404("Announcement has expired")

    # Get related/recent announcements
    related_announcements = Announcement.objects.filter(
        is_published=True,
        publish_date__lte=now
    ).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=now)
    ).exclude(pk=pk).order_by('-publish_date')[:3]

    context = {
        'announcement': announcement,
        'related_announcements': related_announcements,
    }
    return render(request, 'public/announcement_detail.html', context)