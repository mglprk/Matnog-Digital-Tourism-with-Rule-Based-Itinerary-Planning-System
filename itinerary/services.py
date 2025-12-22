# itinerary/services.py
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from decimal import Decimal

from accommodation.models import Accommodation
from destination.models import Destination
from transportation.models import Transportation


@dataclass
class TravelPreferences:
    """User travel preferences"""
    days: int
    pax: int
    budget_category: str  # 'low', 'medium', 'high'
    starting_point: str
    transport_mode: List[str]
    interests: List[str]
    pace_preference: str  # 'relaxed', 'moderate', 'packed'
    has_children: bool = False
    has_seniors: bool = False
    has_disabilities: bool = False
    has_pets: bool = False
    include_accommodation: bool = True
    accommodation_types: List[str] = field(default_factory=list)
    max_travel_time: int = 120  # minutes
    must_visit_ids: List[int] = field(default_factory=list)  # Destination IDs
    exclude_destination_ids: List[int] = field(default_factory=list)  # Destination IDs to exclude
    exclude_categories: List[str] = field(default_factory=list)
    accommodation_id: Optional[int] = None

    # New fields
    point_of_origin: str = "Sorsogon City"  # Address of starting point
    travel_time_hours: float = 0.0  # Hours to travel from origin to Sorsogon
    activity_on_same_day: bool = True  # Whether to do activities on arrival day
    start_date: Optional[str] = None  # ISO format date string (YYYY-MM-DD)


@dataclass
class Activity:
    """Represents a scheduled activity"""
    destination: Destination
    start_time: str
    end_time: str
    duration_minutes: int
    travel_time_from_previous: int = 0
    distance_from_previous: float = 0.0  # in km
    activity_type: str = "destination"  # 'destination', 'travel_to', 'travel_from', 'checkin', 'checkout'


@dataclass
class DayPlan:
    """Represents a full day itinerary"""
    day_number: int
    date: str
    activities: List[Activity]
    accommodation: Optional[Accommodation] = None
    total_activities: int = 0
    total_travel_time: int = 0
    total_distance: float = 0.0  # in km
    is_rest_day: bool = False
    is_travel_day: bool = False
    day_type: str = "regular"  # 'travel_to', 'travel_from', 'regular', 'rest'


class ItineraryPlannerService:
    """Rule-based itinerary planner service for Django integration"""

    # Pace configuration
    PACE_RULES = {
        'relaxed': {
            'activities_per_day': (2, 3),
            'max_daily_travel_time': 60,
            'buffer_time': 90,
            'earliest_start': '09:00',
            'latest_end': '18:00',
            'mandatory_rest': True
        },
        'moderate': {
            'activities_per_day': (3, 4),
            'max_daily_travel_time': 120,
            'buffer_time': 60,
            'earliest_start': '08:00',
            'latest_end': '20:00',
            'mandatory_rest': False
        },
        'packed': {
            'activities_per_day': (5, 7),
            'max_daily_travel_time': 180,
            'buffer_time': 30,
            'earliest_start': '06:00',
            'latest_end': '22:00',
            'mandatory_rest': False
        }
    }

    # Interest to category mapping
    INTEREST_MAPPING = {
        'nature': ['nature'],
        'beaches': ['nature'],
        'adventure': ['adventure', 'nature'],
        'cultural': ['cultural'],
        'historical': ['historical', 'cultural'],
        'wildlife': ['adventure', 'nature'],
        'photography': ['nature', 'cultural', 'historical'],
        'relaxation': ['nature'],
        'hiking': ['adventure', 'nature'],
        'water_sports': ['adventure', 'nature'],
        'local_cuisine': ['cultural', 'food'],
        'shopping': ['shopping', 'other']
    }

    def __init__(self, preferences: TravelPreferences):
        self.prefs = preferences
        self.pace_config = self.PACE_RULES[preferences.pace_preference]

        # Calculate actual start date for activities
        self.trip_start_date = self._parse_start_date()
        self.needs_arrival_travel = preferences.travel_time_hours > 0
        self.needs_departure_travel = preferences.travel_time_hours > 0

    def _parse_start_date(self) -> datetime:
        """Parse start date or use today"""
        if self.prefs.start_date:
            try:
                return datetime.strptime(self.prefs.start_date, '%Y-%m-%d')
            except ValueError:
                pass
        return datetime.now()

    def generate_itinerary(self) -> Dict:
        """Main method to generate complete itinerary - returns serializable dict"""

        # Step 1: Filter destinations
        filtered_destinations = self._filter_destinations()

        # Step 2: Score and rank destinations
        ranked_destinations = self._score_destinations(filtered_destinations)

        # Step 3: Select accommodations
        selected_accommodations = self._select_accommodations()

        # Step 4: Cluster destinations
        clusters = self._cluster_destinations(ranked_destinations, selected_accommodations)

        # Step 5: Build daily itinerary (now includes travel days)
        itinerary = self._build_daily_itinerary(clusters, selected_accommodations)

        # Step 6: Convert to serializable format
        return self._serialize_itinerary(itinerary)

    def _filter_destinations(self) -> List[Destination]:
        """Filter destinations based on preferences using Django ORM"""
        queryset = Destination.objects.filter(is_active=True, status='active')

        # Exclude specific destinations
        if self.prefs.exclude_destination_ids:
            queryset = queryset.exclude(id__in=self.prefs.exclude_destination_ids)

        # Exclude categories
        if self.prefs.exclude_categories:
            queryset = queryset.exclude(category__in=self.prefs.exclude_categories)

        # Budget filter - inclusive
        budget_hierarchy = {'low': 1, 'medium': 2, 'high': 3}
        user_budget_level = budget_hierarchy.get(self.prefs.budget_category, 2)

        # Get all budget categories that are within user's budget
        acceptable_budgets = [k for k, v in budget_hierarchy.items() if v <= user_budget_level]
        queryset = queryset.filter(budget_category__in=acceptable_budgets)

        # Traveler profile filters
        if self.prefs.has_children:
            queryset = queryset.filter(kid_friendly=True)
        if self.prefs.has_seniors:
            queryset = queryset.filter(senior_friendly=True)
        if self.prefs.has_disabilities:
            queryset = queryset.filter(wheelchair_friendly=True)

        return list(queryset.select_related())

    def _score_destinations(self, destinations: List[Destination]) -> List[tuple]:
        """Score destinations based on user interests"""
        scored = []

        for dest in destinations:
            score = 0.0

            # Interest matching
            for interest in self.prefs.interests:
                matching_categories = self.INTEREST_MAPPING.get(interest, [])
                if dest.category in matching_categories:
                    score += 10.0

            # Must-visit boost
            if dest.id in self.prefs.must_visit_ids:
                score += 50.0

            # Duration preference
            duration = dest.avg_duration_minutes or 90
            if self.prefs.pace_preference == 'relaxed' and duration >= 90:
                score += 5.0
            elif self.prefs.pace_preference == 'packed' and duration <= 60:
                score += 5.0
            elif self.prefs.pace_preference == 'moderate':
                score += 3.0

            # Free entrance bonus
            entrance_fee = float(dest.entrance_fee) if dest.entrance_fee else 0
            if entrance_fee == 0:
                score += 2.0

            scored.append((dest, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _select_accommodations(self) -> List[Accommodation]:
        """Select accommodation - use pre-selected if provided"""
        if not self.prefs.include_accommodation:
            return []

        # If user selected specific accommodation, use it
        if self.prefs.accommodation_id:
            try:
                accommodation = Accommodation.objects.get(
                    id=self.prefs.accommodation_id,
                    is_active=True,
                    status='active'
                )
                return [accommodation]
            except Accommodation.DoesNotExist:
                print(f"Accommodation with ID {self.prefs.accommodation_id} not found or inactive")

        # Fall back to auto-selection if no accommodation_id or not found
        queryset = Accommodation.objects.filter(is_active=True, status='active')

        # Budget filter - inclusive
        budget_hierarchy = {'low': 1, 'medium': 2, 'high': 3}
        user_budget_level = budget_hierarchy.get(self.prefs.budget_category, 2)
        acceptable_budgets = [k for k, v in budget_hierarchy.items() if v <= user_budget_level]
        queryset = queryset.filter(budget_category__in=acceptable_budgets)

        # Type filter
        if self.prefs.accommodation_types:
            queryset = queryset.filter(type__in=self.prefs.accommodation_types)

        # Pet-friendly filter
        if self.prefs.has_pets:
            queryset = queryset.filter(pet_friendly=True)

        # Accessibility filter
        if self.prefs.has_disabilities:
            queryset = queryset.filter(wheelchair_friendly=True)

        # Select based on trip duration
        limit = 1 if self.prefs.days <= 3 else 2
        return list(queryset[:limit])

    def _cluster_destinations(self, ranked_destinations: List[tuple],
                              accommodations: List[Accommodation]) -> List[List[Destination]]:
        """Cluster destinations geographically"""
        if not accommodations:
            # No accommodation - return top destinations
            count = self.prefs.days * self.pace_config['activities_per_day'][1]
            return [[dest for dest, score in ranked_destinations[:count]]]

        clusters = []
        must_visit_dests = []

        for acc in accommodations:
            nearby = []

            for dest, score in ranked_destinations:
                # Always include must-visit
                if dest.id in self.prefs.must_visit_ids:
                    if dest not in must_visit_dests:
                        must_visit_dests.append(dest)
                        nearby.append(dest)
                elif self._calculate_distance(
                        float(acc.latitude), float(acc.longitude),
                        float(dest.latitude), float(dest.longitude)
                ) <= 30:
                    nearby.append(dest)

            if nearby:
                clusters.append(nearby)

        if not clusters:
            count = self.prefs.days * self.pace_config['activities_per_day'][1]
            top_destinations = [dest for dest, score in ranked_destinations[:count]]

            # Ensure must-visit included
            for dest, score in ranked_destinations:
                if dest.id in self.prefs.must_visit_ids and dest not in top_destinations:
                    top_destinations.insert(0, dest)

            clusters = [top_destinations]

        return clusters

    def _calculate_distance(self, lat1: float, lon1: float,
                            lat2: float, lon2: float) -> float:
        """Calculate distance in km using Haversine formula"""
        R = 6371
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(delta_lon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def _estimate_travel_time(self, distance_km: float) -> int:
        """Estimate travel time in minutes (40 km/h average)"""
        return int((distance_km / 40) * 60)

    def _build_daily_itinerary(self, clusters: List[List[Destination]],
                               accommodations: List[Accommodation]) -> List[DayPlan]:
        """Build day-by-day itinerary including travel days"""
        itinerary = []
        current_accommodation = accommodations[0] if accommodations else None

        # Calculate effective activity days
        effective_days = self.prefs.days
        activity_start_day = 1
        activity_end_day = self.prefs.days
        current_day = 1  # Track actual day number

        # Handle arrival travel
        if self.needs_arrival_travel:
            if not self.prefs.activity_on_same_day:
                # Full travel day - activities start on day 2
                itinerary.append(self._create_travel_day(
                    day_number=current_day,
                    current_accommodation=current_accommodation,
                    is_arrival=True
                ))
                current_day += 1
                activity_start_day = current_day
                effective_days -= 1
            else:
                # Partial day - will add travel time to first activity day
                pass

        # Handle departure travel
        if self.needs_departure_travel:
            effective_days -= 1

        # Rest days for long trips
        rest_days = []
        if effective_days >= 5:
            rest_days = [activity_start_day + (effective_days // 2)]

        # Collect and deduplicate destinations
        destination_pool = []
        for cluster in clusters:
            destination_pool.extend(cluster)

        seen_ids = set()
        must_visit_dests = []
        other_dests = []

        # Get accommodation coordinates for distance calculation
        acc_lat = float(
            current_accommodation.latitude) if current_accommodation and current_accommodation.latitude else 12.97
        acc_lon = float(
            current_accommodation.longitude) if current_accommodation and current_accommodation.longitude else 124.00

        for dest in destination_pool:
            if dest.id not in seen_ids:
                seen_ids.add(dest.id)
                if dest.id in self.prefs.must_visit_ids:
                    must_visit_dests.append(dest)
                else:
                    other_dests.append(dest)

        # Sort other destinations by distance from accommodation (nearest first)
        other_dests_with_distance = []
        for dest in other_dests:
            dest_lat = float(dest.latitude) if dest.latitude else 12.97
            dest_lon = float(dest.longitude) if dest.longitude else 124.00
            distance = self._calculate_distance(acc_lat, acc_lon, dest_lat, dest_lon)
            other_dests_with_distance.append((dest, distance))

        other_dests_with_distance.sort(key=lambda x: x[1])
        other_dests = [dest for dest, dist in other_dests_with_distance]

        # Distribute must-visit across active days
        active_days = [d for d in range(activity_start_day, activity_end_day + 1) if d not in rest_days]
        must_visit_per_day = {}

        if must_visit_dests and active_days:
            for idx, dest in enumerate(must_visit_dests):
                day_idx = idx % len(active_days)
                day_num = active_days[day_idx]
                if day_num not in must_visit_per_day:
                    must_visit_per_day[day_num] = []
                must_visit_per_day[day_num].append(dest)

        other_dest_index = 0

        # Build activity days
        for day in range(activity_start_day, activity_end_day + 1):
            current_date = self.trip_start_date + timedelta(days=day - 1)

            if day in rest_days:
                day_plan = DayPlan(
                    day_number=current_day,
                    date=current_date.strftime('%Y-%m-%d'),
                    activities=[],
                    accommodation=current_accommodation,
                    is_rest_day=True,
                    day_type='rest'
                )
                itinerary.append(day_plan)
                current_day += 1
                continue

            # Determine number of activities for this day
            is_first_activity_day = (day == activity_start_day)
            is_last_activity_day = (day == activity_start_day + effective_days - 1)

            # Adjust for partial days
            if is_first_activity_day and self.needs_arrival_travel and self.prefs.activity_on_same_day:
                # CHECKED: Reduced activities on arrival day (includes travel time)
                num_activities = self.pace_config['activities_per_day'][0]
            elif is_last_activity_day:
                # Reduced activities on departure day
                num_activities = self.pace_config['activities_per_day'][0]
            else:
                num_activities = self.pace_config['activities_per_day'][1]

            daily_activities = []

            # Set start time
            if is_first_activity_day and self.needs_arrival_travel and self.prefs.activity_on_same_day:
                # CHECKED: Account for travel time on Day 1
                travel_minutes = int(self.prefs.travel_time_hours * 60)
                # Assume early start (6 AM) + travel time + checkin buffer (30 min)
                arrival_time = datetime.strptime('06:00', '%H:%M') + timedelta(minutes=travel_minutes + 30)
                current_time = arrival_time
            else:
                current_time = datetime.strptime(self.pace_config['earliest_start'], '%H:%M')

            # Start location - always from accommodation
            if current_accommodation and current_accommodation.latitude:
                last_lat = float(current_accommodation.latitude)
                last_lon = float(current_accommodation.longitude)
            else:
                last_lat = 12.97
                last_lon = 124.00

            total_travel = 0
            total_distance = 0.0
            activities_added = 0

            # Schedule must-visit for this day
            day_must_visit = must_visit_per_day.get(day, [])

            for dest in day_must_visit:
                if activities_added >= num_activities:
                    break

                dest_lat = float(dest.latitude) if dest.latitude else 12.97
                dest_lon = float(dest.longitude) if dest.longitude else 124.00

                distance = self._calculate_distance(last_lat, last_lon, dest_lat, dest_lon)
                travel_time = self._estimate_travel_time(distance)

                # Relaxed constraints for must-visit
                max_travel = self.prefs.max_travel_time * 1.5
                max_daily_travel = self.pace_config['max_daily_travel_time'] * 1.5

                if travel_time > max_travel or total_travel + travel_time > max_daily_travel:
                    continue

                current_time += timedelta(minutes=travel_time)
                total_travel += travel_time
                total_distance += distance

                start_time = current_time.strftime('%H:%M')
                duration = dest.avg_duration_minutes or 90
                current_time += timedelta(minutes=duration)
                end_time = current_time.strftime('%H:%M')
                current_time += timedelta(minutes=self.pace_config['buffer_time'])

                activity = Activity(
                    destination=dest,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=duration,
                    travel_time_from_previous=travel_time,
                    distance_from_previous=distance,
                    activity_type='destination'
                )

                daily_activities.append(activity)
                last_lat, last_lon = dest_lat, dest_lon
                activities_added += 1

                latest_end = datetime.strptime(self.pace_config['latest_end'], '%H:%M')
                if current_time > latest_end:
                    break

            # Fill remaining slots with other destinations
            while activities_added < num_activities and other_dest_index < len(other_dests):
                dest = other_dests[other_dest_index]

                dest_lat = float(dest.latitude) if dest.latitude else 12.97
                dest_lon = float(dest.longitude) if dest.longitude else 124.00

                distance = self._calculate_distance(last_lat, last_lon, dest_lat, dest_lon)
                travel_time = self._estimate_travel_time(distance)

                if travel_time > self.prefs.max_travel_time:
                    other_dest_index += 1
                    continue

                if total_travel + travel_time > self.pace_config['max_daily_travel_time']:
                    break

                current_time += timedelta(minutes=travel_time)
                total_travel += travel_time
                total_distance += distance

                start_time = current_time.strftime('%H:%M')
                duration = dest.avg_duration_minutes or 90
                current_time += timedelta(minutes=duration)
                end_time = current_time.strftime('%H:%M')
                current_time += timedelta(minutes=self.pace_config['buffer_time'])

                activity = Activity(
                    destination=dest,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=duration,
                    travel_time_from_previous=travel_time,
                    distance_from_previous=distance,
                    activity_type='destination'
                )

                daily_activities.append(activity)
                last_lat, last_lon = dest_lat, dest_lon
                other_dest_index += 1
                activities_added += 1

                latest_end = datetime.strptime(self.pace_config['latest_end'], '%H:%M')
                if current_time > latest_end:
                    break

            # Calculate return journey to accommodation
            if current_accommodation and current_accommodation.latitude and daily_activities:
                last_activity = daily_activities[-1]
                last_dest_lat = float(
                    last_activity.destination.latitude) if last_activity.destination.latitude else last_lat
                last_dest_lon = float(
                    last_activity.destination.longitude) if last_activity.destination.longitude else last_lon

                acc_lat = float(current_accommodation.latitude)
                acc_lon = float(current_accommodation.longitude)
                return_distance = self._calculate_distance(last_dest_lat, last_dest_lon, acc_lat, acc_lon)
                return_travel_time = self._estimate_travel_time(return_distance)

                total_travel += return_travel_time
                total_distance += return_distance

            day_plan = DayPlan(
                day_number=current_day,
                date=current_date.strftime('%Y-%m-%d'),
                activities=daily_activities,
                accommodation=current_accommodation,
                total_activities=len(daily_activities),
                total_travel_time=total_travel,
                total_distance=round(total_distance, 2),
                day_type='regular'
            )

            itinerary.append(day_plan)
            current_day += 1

        # Add departure travel day if needed
        if self.needs_departure_travel:
            itinerary.append(self._create_travel_day(
                day_number=current_day,
                current_accommodation=current_accommodation,
                is_arrival=False
            ))

        return itinerary

    def _create_travel_day(self, day_number: int, current_accommodation: Optional[Accommodation],
                           is_arrival: bool) -> DayPlan:
        """Create a travel day (arrival or departure)"""
        current_date = self.trip_start_date + timedelta(days=day_number - 1)

        travel_type = "arrival" if is_arrival else "departure"
        day_type = "travel_to" if is_arrival else "travel_from"

        return DayPlan(
            day_number=day_number,
            date=current_date.strftime('%Y-%m-%d'),
            activities=[],
            accommodation=current_accommodation if is_arrival else None,
            is_travel_day=True,
            day_type=day_type,
            total_activities=0,
            total_travel_time=int(self.prefs.travel_time_hours * 60),
            total_distance=0.0
        )

    def _serialize_itinerary(self, itinerary: List[DayPlan]) -> Dict:
        """Convert itinerary to JSON-serializable format"""
        days_data = []
        total_cost = 0

        for day_plan in itinerary:
            activities_data = []

            for activity in day_plan.activities:
                dest = activity.destination
                entrance_fee = float(dest.entrance_fee) if dest.entrance_fee else 0
                total_cost += entrance_fee * self.prefs.pax

                activities_data.append({
                    'destination_id': dest.id,
                    'destination_name': dest.name,
                    'category': dest.category,
                    'description': dest.description,
                    'address': dest.address,
                    'latitude': float(dest.latitude) if dest.latitude else None,
                    'longitude': float(dest.longitude) if dest.longitude else None,
                    'start_time': activity.start_time,
                    'end_time': activity.end_time,
                    'duration_minutes': activity.duration_minutes,
                    'travel_time_from_previous': activity.travel_time_from_previous,
                    'distance_from_previous_km': round(activity.distance_from_previous, 2),
                    'entrance_fee': entrance_fee,
                    'opening_time': dest.opening_time.strftime('%H:%M') if dest.opening_time else None,
                    'closing_time': dest.closing_time.strftime('%H:%M') if dest.closing_time else None,
                    'image': dest.image.url if dest.image else None,
                    'activity_type': activity.activity_type,
                })

            accommodation_data = None
            if day_plan.accommodation:
                acc = day_plan.accommodation
                accommodation_data = {
                    'id': acc.id,
                    'name': acc.name,
                    'type': acc.type,
                    'address': acc.address,
                    'contact_number': acc.contact_number,
                    'email': acc.email,
                    'website': acc.website,
                    'latitude': float(acc.latitude) if acc.latitude else None,
                    'longitude': float(acc.longitude) if acc.longitude else None,
                    'amenities': {
                        'wifi': acc.wifi_available,
                        'parking': acc.parking_available,
                        'breakfast': acc.breakfast_included,
                        'ac': acc.air_conditioned,
                    },
                    'image': acc.image.url if acc.image else None,
                }

            days_data.append({
                'day_number': day_plan.day_number,
                'date': day_plan.date,
                'is_rest_day': day_plan.is_rest_day,
                'is_travel_day': day_plan.is_travel_day,
                'day_type': day_plan.day_type,
                'activities': activities_data,
                'accommodation': accommodation_data,
                'total_activities': day_plan.total_activities,
                'total_travel_time_minutes': day_plan.total_travel_time,
                'total_distance_km': day_plan.total_distance,
            })

        total_destinations = sum(len(day['activities']) for day in days_data
                                 if not day['is_rest_day'] and not day['is_travel_day'])
        total_travel_time = sum(day['total_travel_time_minutes'] for day in days_data)
        total_distance = sum(day['total_distance_km'] for day in days_data
                             if not day['is_travel_day'])

        return {
            'preferences': {
                'days': self.prefs.days,
                'pax': self.prefs.pax,
                'budget_category': self.prefs.budget_category,
                'pace': self.prefs.pace_preference,
                'point_of_origin': self.prefs.point_of_origin,
                'travel_time_hours': self.prefs.travel_time_hours,
                'activity_on_same_day': self.prefs.activity_on_same_day,
                'start_date': self.prefs.start_date,
            },
            'itinerary': days_data,
            'summary': {
                'total_destinations': total_destinations,
                'total_travel_time_minutes': total_travel_time,
                'total_travel_time_hours': round(total_travel_time / 60, 1),
                'total_distance_km': round(total_distance, 2),
                'total_entrance_fees': round(total_cost, 2),
                'currency': 'PHP',
            }
        }