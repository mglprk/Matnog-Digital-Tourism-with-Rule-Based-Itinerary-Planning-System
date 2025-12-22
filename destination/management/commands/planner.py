import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.forms.models import model_to_dict

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
    interests: List[
        str]  # 'nature', 'beaches', 'adventure', 'cultural', 'historical', 'wildlife', 'photography', 'relaxation', 'hiking', 'water_sports', 'local_cuisine', 'shopping'
    pace_preference: str  # 'relaxed', 'moderate', 'packed'
    has_children: bool = False
    has_seniors: bool = False
    has_disabilities: bool = False
    has_pets: bool = False
    include_accommodation: bool = True
    accommodation_types: List[str] = field(
        default_factory=list)  # 'resort', 'hotel', 'inn', 'homestay', 'hostel', 'bnb'
    max_travel_time: int = 120  # minutes
    must_visit: List[str] = field(default_factory=list)  # List of destination names
    exclude_destinations: List[str] = field(default_factory=list)  # List of destination names to exclude
    exclude_categories: List[str] = field(
        default_factory=list)  # 'nature', 'adventure', 'cultural', 'historical', 'shopping', 'other'


@dataclass
class Activity:
    """Represents a scheduled activity"""
    destination: Dict
    start_time: str
    end_time: str
    duration_minutes: int
    travel_time_from_previous: int = 0
    notes: str = ""


@dataclass
class DayPlan:
    """Represents a full day itinerary"""
    day_number: int
    date: str
    activities: List[Activity]
    accommodation: Optional[Dict] = None
    total_activities: int = 0
    total_travel_time: int = 0
    is_rest_day: bool = False


class ItineraryPlanner:
    """Rule-based itinerary planner for Sorsogon Province"""

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

    def __init__(self, destinations: List[Dict], accommodations: List[Dict],
                 hubs: List[Dict], preferences: TravelPreferences):
        self.destinations = destinations
        self.accommodations = accommodations
        self.hubs = hubs
        self.prefs = preferences
        self.pace_config = self.PACE_RULES[preferences.pace_preference]

    def generate_itinerary(self) -> List[DayPlan]:
        """Main method to generate complete itinerary"""
        print("🚀 Starting itinerary generation...")

        # Step 1: Filter destinations based on preferences
        filtered_destinations = self._filter_destinations()
        print(f"✓ Filtered to {len(filtered_destinations)} suitable destinations")

        # Step 2: Score and rank destinations
        ranked_destinations = self._score_destinations(filtered_destinations)
        print(f"✓ Ranked destinations by relevance")

        # Step 3: Select accommodation(s)
        selected_accommodations = self._select_accommodations()
        print(f"✓ Selected {len(selected_accommodations)} accommodation(s)")

        # Step 4: Cluster destinations geographically
        clusters = self._cluster_destinations(ranked_destinations, selected_accommodations)
        print(f"✓ Organized into {len(clusters)} geographic clusters")

        # Step 5: Build daily itinerary
        itinerary = self._build_daily_itinerary(clusters, selected_accommodations)
        print(f"✓ Generated {len(itinerary)} day itinerary")

        return itinerary

    def _filter_destinations(self) -> List[Dict]:
        """Filter destinations based on user preferences"""
        filtered = []

        # Budget hierarchy
        budget_hierarchy = {'low': 1, 'medium': 2, 'high': 3}

        for dest in self.destinations:
            # Exclude specific destinations
            if dest.get('name') in self.prefs.exclude_destinations:
                continue

            # Budget filter - inclusive (can visit equal or lower budget places)
            user_budget = budget_hierarchy.get(self.prefs.budget_category, 2)
            dest_budget = budget_hierarchy.get(dest.get('budget_category', 'low'), 1)

            if dest_budget > user_budget:
                # Destination is too expensive for user's budget
                continue

            # Traveler profile filters
            if self.prefs.has_children and not dest.get('kid_friendly', False):
                continue
            if self.prefs.has_seniors and not dest.get('senior_friendly', False):
                continue
            if self.prefs.has_disabilities and not dest.get('wheelchair_friendly', False):
                continue

            # Exclude categories
            if dest.get('category') in self.prefs.exclude_categories:
                continue

            # Status check
            if dest.get('status') != 'active':
                continue

            filtered.append(dest)

        return filtered

    def _score_destinations(self, destinations: List[Dict]) -> List[Tuple[Dict, float]]:
        """Score destinations based on user interests"""
        scored = []

        for dest in destinations:
            score = 0.0
            dest_category = dest.get('category', '')

            # Interest matching
            for interest in self.prefs.interests:
                matching_categories = self.INTEREST_MAPPING.get(interest, [])
                if dest_category in matching_categories:
                    score += 10.0

            # Must-visit boost
            if dest.get('name') in self.prefs.must_visit:
                score += 50.0

            # Duration preference based on pace
            duration = dest.get('avg_duration_minutes', 90)
            if self.prefs.pace_preference == 'relaxed' and duration >= 90:
                score += 5.0
            elif self.prefs.pace_preference == 'packed' and duration <= 60:
                score += 5.0
            elif self.prefs.pace_preference == 'moderate':
                score += 3.0

            # Entrance fee consideration
            entrance_fee = dest.get('entrance_fee', 0)
            if isinstance(entrance_fee, Decimal):
                entrance_fee = float(entrance_fee)
            if entrance_fee == 0:
                score += 2.0

            scored.append((dest, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _select_accommodations(self) -> List[Dict]:
        """Select suitable accommodations"""
        # If accommodation not needed, return empty list
        if not self.prefs.include_accommodation:
            return []

        filtered = []

        # Budget hierarchy
        budget_hierarchy = {'low': 1, 'medium': 2, 'high': 3}
        user_budget = budget_hierarchy.get(self.prefs.budget_category, 2)

        for acc in self.accommodations:
            # Budget filter - inclusive (can book equal or lower budget accommodations)
            acc_budget = budget_hierarchy.get(acc.get('budget_category', 'low'), 1)

            if acc_budget > user_budget:
                # Accommodation is too expensive for user's budget
                continue

            # Type filter (only if user specified preferred types)
            if self.prefs.accommodation_types and \
                    acc.get('type') not in self.prefs.accommodation_types:
                continue

            # Pet-friendly filter
            if self.prefs.has_pets and not acc.get('pet_friendly', False):
                continue

            # Traveler profile
            if self.prefs.has_disabilities and not acc.get('wheelchair_friendly', False):
                continue

            # Status check
            if acc.get('status') != 'active':
                continue

            filtered.append(acc)

        # For short trips (1-3 days), select 1 accommodation
        # For longer trips, might select multiple based on geography
        if self.prefs.days <= 3:
            return filtered[:1] if filtered else []
        else:
            return filtered[:2] if filtered else []

    def _cluster_destinations(self, ranked_destinations: List[Tuple[Dict, float]],
                              accommodations: List[Dict]) -> List[List[Dict]]:
        """Cluster destinations by geographic proximity"""
        if not accommodations:
            # No accommodation selected, cluster around starting point
            return [self._get_destinations_by_score(ranked_destinations,
                                                    self.prefs.days * self.pace_config['activities_per_day'][1])]

        # Simple clustering: group destinations near each accommodation
        clusters = []
        must_visit_destinations = []

        for acc in accommodations:
            acc_lat = float(acc.get('latitude', 0))
            acc_lon = float(acc.get('longitude', 0))

            nearby = []
            for dest, score in ranked_destinations:
                dest_lat = float(dest.get('latitude', 0))
                dest_lon = float(dest.get('longitude', 0))

                # Always include must-visit destinations regardless of distance
                if dest.get('name') in self.prefs.must_visit:
                    if dest not in must_visit_destinations:
                        must_visit_destinations.append(dest)
                        nearby.append(dest)
                elif self._calculate_distance(acc_lat, acc_lon, dest_lat, dest_lon) <= 30:  # 30km radius
                    nearby.append(dest)

            if nearby:
                clusters.append(nearby)

        # If no clusters formed, create one with top destinations including must-visit
        if not clusters:
            top_destinations = self._get_destinations_by_score(ranked_destinations,
                                                               self.prefs.days * self.pace_config['activities_per_day'][
                                                                   1])
            # Ensure must-visit destinations are included
            for dest, score in ranked_destinations:
                if dest.get('name') in self.prefs.must_visit and dest not in top_destinations:
                    top_destinations.insert(0, dest)
            clusters = [top_destinations]

        return clusters

    def _get_destinations_by_score(self, ranked_destinations: List[Tuple[Dict, float]],
                                   count: int) -> List[Dict]:
        """Get top N destinations by score"""
        return [dest for dest, score in ranked_destinations[:count]]

    def _calculate_distance(self, lat1: float, lon1: float,
                            lat2: float, lon2: float) -> float:
        """Calculate approximate distance in km using Haversine formula"""
        R = 6371  # Earth's radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(delta_lon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def _estimate_travel_time(self, distance_km: float) -> int:
        """Estimate travel time in minutes based on distance"""
        # Assume average speed of 40 km/h for local roads
        return int((distance_km / 40) * 60)

    def _build_daily_itinerary(self, clusters: List[List[Dict]],
                               accommodations: List[Dict]) -> List[DayPlan]:
        """Build day-by-day itinerary"""
        itinerary = []
        activities_per_day = self.pace_config['activities_per_day']
        current_accommodation = accommodations[0] if accommodations else None

        # Determine if rest days are needed (only for trips 5+ days)
        rest_days = []
        if self.prefs.days >= 5:
            # Add rest day in the middle for longer trips
            rest_days = [self.prefs.days // 2]

        destination_pool = []
        for cluster in clusters:
            destination_pool.extend(cluster)

        # Remove duplicates while preserving order
        seen = set()
        must_visit_dests = []
        other_dests = []

        # Separate must-visit from other destinations
        for dest in destination_pool:
            if dest['name'] not in seen:
                seen.add(dest['name'])
                if dest['name'] in self.prefs.must_visit:
                    must_visit_dests.append(dest)
                else:
                    other_dests.append(dest)

        # Calculate active days (excluding rest days)
        active_days = [d for d in range(1, self.prefs.days + 1) if d not in rest_days]

        # Distribute must-visit destinations evenly across days
        # Ensure at least one must-visit per day if possible
        must_visit_per_day = {}
        if must_visit_dests and active_days:
            for idx, dest in enumerate(must_visit_dests):
                day_idx = idx % len(active_days)
                day_num = active_days[day_idx]
                if day_num not in must_visit_per_day:
                    must_visit_per_day[day_num] = []
                must_visit_per_day[day_num].append(dest)

        other_dest_index = 0

        for day in range(1, self.prefs.days + 1):
            # Check if it's a rest day
            if day in rest_days:
                day_plan = DayPlan(
                    day_number=day,
                    date=(datetime.now() + timedelta(days=day - 1)).strftime('%Y-%m-%d'),
                    activities=[],
                    accommodation=current_accommodation,
                    is_rest_day=True
                )
                itinerary.append(day_plan)
                continue

            # Determine number of activities for this day
            num_activities = activities_per_day[0] if day == 1 or day == self.prefs.days \
                else activities_per_day[1]

            daily_activities = []
            current_time = datetime.strptime(self.pace_config['earliest_start'], '%H:%M')
            last_location = current_accommodation or {'latitude': 12.97, 'longitude': 124.00}
            total_travel = 0

            # Get must-visit destinations for this day
            day_must_visit = must_visit_per_day.get(day, [])
            activities_added = 0

            # First, schedule must-visit destinations for this day
            for dest in day_must_visit:
                if activities_added >= num_activities:
                    break

                # Calculate travel time from last location
                last_lat = float(last_location.get('latitude', 12.97))
                last_lon = float(last_location.get('longitude', 124.00))
                dest_lat = float(dest.get('latitude', 12.97))
                dest_lon = float(dest.get('longitude', 124.00))

                distance = self._calculate_distance(last_lat, last_lon, dest_lat, dest_lon)
                travel_time = self._estimate_travel_time(distance)

                # Relax constraints for must-visit destinations
                max_travel = self.prefs.max_travel_time * 1.5
                max_daily_travel = self.pace_config['max_daily_travel_time'] * 1.5

                # Check if travel time exceeds relaxed limit
                if travel_time > max_travel:
                    continue

                # Add travel time
                current_time += timedelta(minutes=travel_time)
                total_travel += travel_time

                # Check if we exceed daily travel limit (with relaxed constraint)
                if total_travel > max_daily_travel:
                    break

                # Schedule activity
                start_time = current_time.strftime('%H:%M')
                duration = dest.get('avg_duration_minutes', 90)
                current_time += timedelta(minutes=duration)
                end_time = current_time.strftime('%H:%M')

                # Add buffer time
                current_time += timedelta(minutes=self.pace_config['buffer_time'])

                activity = Activity(
                    destination=dest,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=duration,
                    travel_time_from_previous=travel_time,
                    notes=dest.get('description', '')
                )

                daily_activities.append(activity)
                last_location = dest
                activities_added += 1

                # Check if we've exceeded latest end time
                latest_end = datetime.strptime(self.pace_config['latest_end'], '%H:%M')
                if current_time > latest_end:
                    break

            # Then fill remaining slots with other destinations
            while activities_added < num_activities and other_dest_index < len(other_dests):
                dest = other_dests[other_dest_index]

                # Calculate travel time from last location
                last_lat = float(last_location.get('latitude', 12.97))
                last_lon = float(last_location.get('longitude', 124.00))
                dest_lat = float(dest.get('latitude', 12.97))
                dest_lon = float(dest.get('longitude', 124.00))

                distance = self._calculate_distance(last_lat, last_lon, dest_lat, dest_lon)
                travel_time = self._estimate_travel_time(distance)

                # Check if travel time exceeds limit
                if travel_time > self.prefs.max_travel_time:
                    other_dest_index += 1
                    continue

                # Add travel time
                current_time += timedelta(minutes=travel_time)
                total_travel += travel_time

                # Check if we exceed daily travel limit
                if total_travel > self.pace_config['max_daily_travel_time']:
                    break

                # Schedule activity
                start_time = current_time.strftime('%H:%M')
                duration = dest.get('avg_duration_minutes', 90)
                current_time += timedelta(minutes=duration)
                end_time = current_time.strftime('%H:%M')

                # Add buffer time
                current_time += timedelta(minutes=self.pace_config['buffer_time'])

                activity = Activity(
                    destination=dest,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=duration,
                    travel_time_from_previous=travel_time,
                    notes=dest.get('description', '')
                )

                daily_activities.append(activity)
                last_location = dest
                other_dest_index += 1
                activities_added += 1

                # Check if we've exceeded latest end time
                latest_end = datetime.strptime(self.pace_config['latest_end'], '%H:%M')
                if current_time > latest_end:
                    break

            day_plan = DayPlan(
                day_number=day,
                date=(datetime.now() + timedelta(days=day - 1)).strftime('%Y-%m-%d'),
                activities=daily_activities,
                accommodation=current_accommodation,
                total_activities=len(daily_activities),
                total_travel_time=total_travel
            )

            itinerary.append(day_plan)

        return itinerary

    def print_itinerary(self, itinerary: List[DayPlan]):
        """Print formatted itinerary"""
        print("\n" + "=" * 80)
        print(f"🗺️  SORSOGON TRAVEL ITINERARY - {self.prefs.days} DAYS")
        print(f"👥 {self.prefs.pax} travelers | 💰 {self.prefs.budget_category.upper()} budget | "
              f"⚡ {self.prefs.pace_preference.upper()} pace")
        print("=" * 80 + "\n")

        total_cost = 0

        for day_plan in itinerary:
            print(f"📅 DAY {day_plan.day_number} - {day_plan.date}")
            print("-" * 80)

            if day_plan.is_rest_day:
                print("🏖️  REST DAY - Free time to relax or explore on your own")
                if day_plan.accommodation:
                    print(f"🏨 Accommodation: {day_plan.accommodation['name']}")
                print()
                continue

            if not day_plan.activities:
                print("⚠️  No activities scheduled for this day")
                print()
                continue

            for i, activity in enumerate(day_plan.activities, 1):
                dest = activity.destination
                print(f"\n{i}. {dest['name']} ({dest['category'].upper()})")
                print(f"   ⏰ {activity.start_time} - {activity.end_time} ({activity.duration_minutes} min)")
                if activity.travel_time_from_previous > 0:
                    print(f"   🚗 Travel time: {activity.travel_time_from_previous} min")
                print(f"   📍 {dest['address']}")

                entrance_fee = dest.get('entrance_fee', 0)
                if isinstance(entrance_fee, Decimal):
                    entrance_fee = float(entrance_fee)
                print(f"   💵 Entrance fee: ₱{entrance_fee}")
                total_cost += entrance_fee * self.prefs.pax

                opening = dest.get('opening_time')
                closing = dest.get('closing_time')
                if opening and closing:
                    # Handle time objects from Django model
                    if hasattr(opening, 'strftime'):
                        opening = opening.strftime('%H:%M')
                    if hasattr(closing, 'strftime'):
                        closing = closing.strftime('%H:%M')
                    print(f"   🕐 Open: {opening} - {closing}")

                description = activity.notes[:100] if activity.notes else "No description available"
                print(f"   📝 {description}...")
                print(f" latitude longitude: {dest.get('latitude', 'N/A')}, {dest.get('longitude', 'N/A')}")

            print(f"\n📊 Day Summary:")
            print(f"   • Total activities: {day_plan.total_activities}")
            print(f"   • Total travel time: {day_plan.total_travel_time} minutes")

            if day_plan.accommodation:
                acc = day_plan.accommodation
                print(f"\n🏨 Accommodation: {acc['name']}")
                print(f"   📍 {acc['address']}")
                print(f"   📞 {acc.get('contact_number', 'N/A')}")
                amenities = []
                if acc.get('wifi_available'): amenities.append("WiFi")
                if acc.get('parking_available'): amenities.append("Parking")
                if acc.get('breakfast_included'): amenities.append("Breakfast")
                if acc.get('air_conditioned'): amenities.append("A/C")
                if amenities:
                    print(f"   ✨ Amenities: {', '.join(amenities)}")

            print("\n" + "=" * 80 + "\n")

        # Print summary
        total_destinations = sum(len(day.activities) for day in itinerary if not day.is_rest_day)
        total_travel = sum(day.total_travel_time for day in itinerary if not day.is_rest_day)

        print("\n🎯 TRIP SUMMARY")
        print("-" * 80)
        print(f"📍 Total unique destinations: {total_destinations}")
        print(f"🚗 Total travel time: {total_travel} minutes ({total_travel / 60:.1f} hours)")
        print(f"💰 Budget category: {self.prefs.budget_category.upper()}")
        print(f"💵 Total entrance fees: ₱{total_cost:.2f} ({self.prefs.pax} pax)")
        print(f"⚡ Pace: {self.prefs.pace_preference.upper()}")


class Command(BaseCommand):
    help = 'Generate a travel itinerary for Sorsogon Province based on user preferences'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting Itinerary Planner...'))

        # Load data from Django models
        try:
            destinations = list(Destination.objects.filter(is_active=True).values())
            accommodations = list(Accommodation.objects.filter(is_active=True).values())
            hubs = list(Transportation.objects.filter(is_active=True).values())

            # Convert Decimal fields to float for calculations
            for dest in destinations:
                if dest.get('latitude'):
                    dest['latitude'] = float(dest['latitude'])
                if dest.get('longitude'):
                    dest['longitude'] = float(dest['longitude'])
                if dest.get('entrance_fee'):
                    dest['entrance_fee'] = float(dest['entrance_fee'])

            for acc in accommodations:
                if acc.get('latitude'):
                    acc['latitude'] = float(acc['latitude'])
                if acc.get('longitude'):
                    acc['longitude'] = float(acc['longitude'])

            for hub in hubs:
                if hub.get('latitude'):
                    hub['latitude'] = float(hub['latitude'])
                if hub.get('longitude'):
                    hub['longitude'] = float(hub['longitude'])

            self.stdout.write(f"✓ Loaded {len(destinations)} destinations")
            self.stdout.write(f"✓ Loaded {len(accommodations)} accommodations")
            self.stdout.write(f"✓ Loaded {len(hubs)} transport hubs")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading data: {str(e)}'))
            return

        # Create sample preferences (in production, this would come from user input)
        preferences = TravelPreferences(
            days=3,
            pax=2,
            budget_category='medium',
            starting_point='sorsogon_city',
            transport_mode=['rental_car'],
            interests=['nature', 'beaches', 'wildlife', 'adventure'],
            pace_preference='moderate',
            has_children=False,
            has_seniors=False,
            has_disabilities=False,
            has_pets=False,
            include_accommodation=True,
            accommodation_types=['hotel', 'resort'],
            max_travel_time=120,
            must_visit=['Donsol Whale Shark Interaction', 'Bulusan Lake'],
            exclude_destinations=[],
            exclude_categories=['shopping']
        )

        # Generate itinerary
        try:
            planner = ItineraryPlanner(destinations, accommodations, hubs, preferences)
            itinerary = planner.generate_itinerary()
            planner.print_itinerary(itinerary)

            self.stdout.write(self.style.SUCCESS('\n✅ Itinerary generation completed successfully!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating itinerary: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())


