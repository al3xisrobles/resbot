"""
Search-related Cloud Functions for Resy Bot
Handles restaurant search by name and by map bounding box
"""

import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions

from .utils import (
    load_credentials,
    get_resy_headers,
    parse_search_filters,
    fetch_until_enough_results,
    build_search_payload,
    get_search_cache_key,
    get_cached_search_results,
    save_search_results_to_cache,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
def search(req: Request):
    """
    GET /search
    Search for restaurants by name (NYC only)
    Query parameters:
    - userId: Optional Firebase user ID for personalized credentials
    - query: Optional restaurant name search
    - available_only: Optional availability-only boolean
    - available_day: Optional day if available_only is true (format: 'YYYY-MM-DD')
    - available_party_size: Optional party size if available_only is true (default: 2)
    - cuisines: Optional comma-separated list of cuisines
    - priceRanges: Optional comma-separated list of price ranges (1-4)
    - offset: Optional offset for pagination (default: 0)
    - perPage: Optional results per page (default: 20, max: 50)
    """
    try:
        user_id = req.args.get('userId')
        query = req.args.get('query', '').strip()

        # Parse filters using helper function
        filters = parse_search_filters(req.args)

        print(f"[SEARCH] Raw params - query: '{query}', available_only: {filters['available_only']}, offset: {filters['offset']}, perPage: {filters['per_page']}")
        print(f"[SEARCH] Parsed filters - cuisines: {filters['cuisines']}, priceRanges: {filters['price_ranges']}")

        # At least one filter must be provided
        if not query and not filters['cuisines'] and not filters['price_ranges']:
            return {
                'success': False,
                'error': 'At least one search parameter is required (query, cuisines, or priceRanges)'
            }, 400

        # Load credentials (from Firestore if userId provided, else from credentials.json)
        config = load_credentials(user_id)
        headers = get_resy_headers(config)

        # Default to Times Square with large radius
        geo_center = {'lat': 40.758896, 'lng': -73.985130, 'radius': 16100}  # Times Square, ~10 miles
        print(f"[SEARCH] Using default NYC geo center: lat={geo_center['lat']}, lng={geo_center['lng']}, radius={geo_center['radius']}m")

        # Build geo config for payload
        geo_config = {
            "latitude": geo_center['lat'],
            "longitude": geo_center['lng'],
            "radius": geo_center['radius']
        }

        # Create fetch function for Resy API
        def fetch_resy_page(page_num):
            payload = build_search_payload(query, filters, geo_config, page=page_num)

            response = requests.post(
                'https://api.resy.com/3/venuesearch/search',
                json=payload,
                headers=headers
            )

            if response.status_code != 200:
                raise Exception(f'API returned status {response.status_code}: {response.text[:200]}')

            data = response.json()
            hits = data.get('search', {}).get('hits', [])
            total = data.get('meta', {}).get('total', 0)

            return hits, total

        # Fetch enough results to satisfy offset + perPage
        target_count = filters['offset'] + filters['per_page']
        all_results, total_resy_results, has_more = fetch_until_enough_results(
            fetch_resy_page,
            target_count,
            filters,
            max_fetches=10
        )

        # Slice results based on offset
        results = all_results[filters['offset']:filters['offset'] + filters['per_page']]

        print(f"[SEARCH] Fetched {len(all_results)} total filtered results, returning {len(results)} for offset {filters['offset']}")
        print(f"[SEARCH] Resy total (unfiltered): {total_resy_results}")

        # Calculate next offset
        next_offset = filters['offset'] + len(results) if (len(all_results) > filters['offset'] + filters['per_page'] or has_more) else None

        return {
            'success': True,
            'data': results,
            'pagination': {
                'offset': filters['offset'],
                'perPage': filters['per_page'],
                'nextOffset': next_offset,
                'hasMore': next_offset is not None,
                'total': total_resy_results  # Total from Resy API (unfiltered estimate)
            }
        }

    except Exception as e:
        logger.error(f"Error searching venues: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }, 500


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
def search_map(req: Request):
    """
    GET /search_map
    Search for restaurants by map bounding box
    Query parameters:
    - userId: Optional Firebase user ID for personalized credentials
    - swLat: Southwest latitude (bottom-left)
    - swLng: Southwest longitude (bottom-left)
    - neLat: Northeast latitude (top-right)
    - neLng: Northeast longitude (top-right)
    - query: Optional restaurant name search
    - available_only: Optional availability-only boolean
    - available_day: Optional day if available_only is true (format: 'YYYY-MM-DD')
    - available_party_size: Optional party size if available_only is true (default: 2)
    - cuisines: Optional comma-separated list of cuisines
    - priceRanges: Optional comma-separated list of price ranges (1-4)
    - offset: Optional offset for pagination (default: 0)
    - perPage: Optional results per page (default: 20, max: 50)
    """
    try:
        user_id = req.args.get('userId')

        print(f"[MAP SEARCH] Received request with args: {req.args.to_dict()}")

        # Get bounding box coordinates
        sw_lat = float(req.args.get('swLat', 0))
        sw_lng = float(req.args.get('swLng', 0))
        ne_lat = float(req.args.get('neLat', 0))
        ne_lng = float(req.args.get('neLng', 0))

        query = req.args.get('query', '').strip()

        # Parse filters using helper function
        filters = parse_search_filters(req.args)

        print(f"[MAP SEARCH] Bounding box: SW({sw_lat}, {sw_lng}) to NE({ne_lat}, {ne_lng})")
        print(f"[MAP SEARCH] Params - query: '{query}', available_only: {filters['available_only']}, not_released_only: {filters.get('not_released_only', False)}, offset: {filters['offset']}, perPage: {filters['per_page']}")
        print(f"[MAP SEARCH] Parsed filters - cuisines: {filters['cuisines']}, priceRanges: {filters['price_ranges']}")

        # Load credentials (from Firestore if userId provided, else from credentials.json)
        config = load_credentials(user_id)
        headers = get_resy_headers(config)

        # Build geo config for bounding box
        geo_config = {
            "bounding_box": [sw_lat, sw_lng, ne_lat, ne_lng]
        }

        # Determine if we should fetch availability
        # Only fetch if the user has provided all reservation details
        should_fetch_availability = bool(
            filters.get('available_day') and
            filters.get('available_party_size')
        )

        if should_fetch_availability:
            print(f"[MAP SEARCH] Will fetch availability for date: {filters['available_day']}, party size: {filters['available_party_size']}")

        # Generate cache key (exclude availability params from cache key since we fetch that separately)
        cache_key = get_search_cache_key(query, filters, geo_config)

        # Try to get from cache
        cached_data = get_cached_search_results(cache_key)

        # Check if we have enough cached results for this page
        need_fetch = True
        if cached_data:
            cached_count = len(cached_data['results'])
            required_count = filters['offset'] + filters['per_page']

            if cached_count >= required_count:
                # Cache has enough results for this page
                all_results = cached_data['results']
                total_resy_results = cached_data['total']
                has_more = False  # Cached results are complete
                need_fetch = False
                print(f"[MAP SEARCH] Using cached results ({len(all_results)} results, need {required_count})")
            else:
                # Cache doesn't have enough, need to fetch more
                print(f"[MAP SEARCH] Cache insufficient ({cached_count} cached, need {required_count}), fetching more")

        if need_fetch:
            # Cache miss - fetch from API
            print(f"[MAP SEARCH] Cache miss - fetching from Resy API")

            # Create fetch function for Resy API
            def fetch_resy_page(page_num):
                payload = build_search_payload(query, filters, geo_config, page=page_num)

                response = requests.post(
                    'https://api.resy.com/3/venuesearch/search',
                    json=payload,
                    headers=headers
                )

                if response.status_code != 200:
                    raise Exception(f'API returned status {response.status_code}: {response.text[:200]}')

                data = response.json()
                hits = data.get('search', {}).get('hits', [])
                total = data.get('meta', {}).get('total', 0)

                return hits, total

            # Fetch enough results - we'll fetch more than requested to have a good cache
            # Fetch at least 100 results (5 pages worth) to make pagination smooth
            # NOTE: We do NOT fetch availability here - we'll fetch it only for the current page
            target_count = filters['offset'] + filters['per_page']
            all_results, total_resy_results, has_more = fetch_until_enough_results(
                fetch_resy_page,
                target_count,
                filters,
                max_fetches=10,
                config=config,
                fetch_availability=False  # Don't fetch availability during caching
            )

            # Save to cache (restaurant data only, no availability)
            save_search_results_to_cache(cache_key, all_results, total_resy_results)

        # Slice results based on offset to get current page
        results = all_results[filters['offset']:filters['offset'] + filters['per_page']]

        # Now fetch availability ONLY for the current page results (in parallel)
        if should_fetch_availability and results:
            from utils import get_venue_availability

            print(f"[MAP SEARCH] Fetching availability for {len(results)} restaurants on current page (parallel)")

            # Use ThreadPoolExecutor to fetch availability in parallel
            # Max 3 concurrent workers to avoid rate limiting (Resy has strict rate limits)
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all availability fetch tasks
                future_to_result = {
                    executor.submit(
                        get_venue_availability,
                        result['id'],
                        filters['available_day'],
                        filters['available_party_size'],
                        config,
                        filters.get('desired_time')
                    ): result
                    for result in results
                }

                # Process completed tasks as they finish
                for future in as_completed(future_to_result):
                    result = future_to_result[future]
                    try:
                        availability_data = future.result()

                        # Add availability data to result
                        if availability_data['times']:
                            result['availableTimes'] = availability_data['times']
                        elif availability_data['status']:
                            result['availabilityStatus'] = availability_data['status']

                        # If available_only filter is enabled and no times available, mark for removal
                        if filters.get('available_only') and not availability_data['times']:
                            result['_should_filter'] = True

                        # If not_released_only filter is enabled and status is not "Not released yet", mark for removal
                        if filters.get('not_released_only'):
                            print(f"[NOT_RELEASED_FILTER] Checking {result.get('name')}: status='{availability_data['status']}', times={len(availability_data.get('times', []))}")
                            if availability_data['status'] != 'Not released yet':
                                result['_should_filter'] = True
                                print(f"[NOT_RELEASED_FILTER] ❌ Filtering out {result.get('name')} - status is '{availability_data['status']}'")
                            else:
                                print(f"[NOT_RELEASED_FILTER] ✓ Keeping {result.get('name')} - status is 'Not released yet'")
                    except Exception as e:
                        print(f"[AVAILABILITY] Error in parallel fetch for venue {result['id']}: {str(e)}")
                        result['availabilityStatus'] = 'Unable to fetch'

            # Filter out venues based on availability filters
            if filters.get('available_only') or filters.get('not_released_only'):
                original_count = len(results)
                results = [r for r in results if not r.get('_should_filter')]
                filtered_count = original_count - len(results)
                if filtered_count > 0:
                    filter_type = "without availability" if filters.get('available_only') else "not 'Not released yet'"
                    print(f"[MAP SEARCH] Filtered out {filtered_count} venues {filter_type}")

        print(f"[MAP SEARCH] Returning {len(results)} results for offset {filters['offset']} (have {len(all_results)} total cached)")
        print(f"[MAP SEARCH] Resy total (unfiltered): {total_resy_results}")

        # Calculate next offset
        # When available_only or not_released_only is enabled, we need to check if there are potentially more results
        # by eagerly checking the NEXT page for any matching restaurants
        next_offset = None
        if filters.get('available_only') or filters.get('not_released_only'):
            # Calculate next page offset
            potential_next_offset = filters['offset'] + len(results)

            # Check if we have more cached restaurants to check
            if len(all_results) > potential_next_offset:
                from utils import get_venue_availability

                # We have more cached restaurants - peek at next page to see if any match the filter
                filter_name = "available" if filters.get('available_only') else "not released yet"
                print(f"[MAP SEARCH] Checking next page (offset {potential_next_offset}) for {filter_name} restaurants...")
                next_page_results = all_results[potential_next_offset:potential_next_offset + filters['per_page']]

                # Check availability for next page
                has_matching_restaurants = False
                with ThreadPoolExecutor(max_workers=3) as executor:
                    future_to_result = {
                        executor.submit(
                            get_venue_availability,
                            result['id'],
                            filters['available_day'],
                            filters['available_party_size'],
                            config,
                            filters.get('desired_time')
                        ): result
                        for result in next_page_results
                    }

                    for future in as_completed(future_to_result):
                        try:
                            availability_data = future.result()
                            # Check based on active filter
                            if filters.get('available_only') and availability_data['times']:
                                has_matching_restaurants = True
                                break
                            elif filters.get('not_released_only') and availability_data['status'] == 'Not released yet':
                                has_matching_restaurants = True
                                break
                        except Exception:
                            pass

                if has_matching_restaurants:
                    next_offset = potential_next_offset
                    print(f"[MAP SEARCH] Next page has {filter_name} restaurants - enabling pagination")
                else:
                    print(f"[MAP SEARCH] Next page has no {filter_name} restaurants - disabling pagination")
            else:
                print(f"[MAP SEARCH] No more cached restaurants - pagination disabled")
        else:
            # For normal search: show next if there are more results in cache or API
            next_offset = filters['offset'] + len(results) if (len(all_results) > filters['offset'] + filters['per_page'] or has_more) else None

        # For available_only or not_released_only filter, show current offset + results count (not total available)
        # This is more accurate since we filter by availability AFTER fetching
        if filters.get('available_only') or filters.get('not_released_only'):
            # Show cumulative count: offset (already shown) + current page results
            display_total = filters['offset'] + len(results)
        else:
            # Show Resy's total count
            display_total = total_resy_results

        return {
            'success': True,
            'data': results,
            'pagination': {
                'offset': filters['offset'],
                'perPage': filters['per_page'],
                'nextOffset': next_offset,
                'hasMore': next_offset is not None,
                'total': display_total  # Cumulative count for available_only, Resy total otherwise
            }
        }

    except Exception as e:
        logger.error(f"Error searching venues by map: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }, 500
