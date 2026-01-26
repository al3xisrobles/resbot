"""
Search-related Cloud Functions for Resy Bot
Handles restaurant search by name and by map bounding box
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from firebase_functions.https_fn import on_request, Request
from firebase_functions.options import CorsOptions
from firebase_admin import firestore as admin_firestore

from .utils import (
    load_credentials,
    get_resy_headers,
    parse_search_filters,
    fetch_until_enough_results,
    build_search_payload,
    get_search_cache_key,
    get_cached_search_results,
    save_search_results_to_cache,
    get_venue_availability,
    update_search_progress
)
from .cities import get_city_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# TODO: Right now /search doesn’t use job progress at all
@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]))
def search(req: Request):
    """
    GET /search
    Search for restaurants by name
    Query parameters:
    - userId: Optional Firebase user ID for personalized credentials
    - query: Optional restaurant name search
    - city: Optional city ID (default: 'nyc')
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

        print(
            f"[SEARCH] Raw params - query: '{query}', available_only: {filters['available_only']}, "
            f"offset: {filters['offset']}, perPage: {filters['per_page']}"
        )
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

        # Get city configuration (default to NYC if not provided)
        city_id = req.args.get('city', 'nyc')
        city_config = get_city_config(city_id)
        geo_center = {
            'lat': city_config['center']['lat'],
            'lng': city_config['center']['lng'],
            'radius': city_config['radius']
        }
        print(
            f"[SEARCH] Using {city_config['name']} geo center: lat={geo_center['lat']}, "
            f"lng={geo_center['lng']}, radius={geo_center['radius']}m"
        )

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
                headers=headers,
                timeout=30
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

        print("[SEARCH] Sample result imageUrl:")
        if all_results:
            print(all_results[0]['imageUrl'])

        # Slice results based on offset
        results = all_results[filters['offset']:filters['offset'] + filters['per_page']]

        print(
            f"[SEARCH] Fetched {len(all_results)} total filtered results, "
            f"returning {len(results)} for offset {filters['offset']}"
        )
        print(f"[SEARCH] Resy total (unfiltered): {total_resy_results}")

        # Calculate next offset
        next_offset = (
            filters['offset'] + len(results)
            if (len(all_results) > filters['offset'] + filters['per_page'] or has_more)
            else None
        )

        return {
            'success': True,
            'data': results,
            'pagination': {
                'offset': filters['offset'],
                'perPage': filters['per_page'],
                'nextOffset': next_offset,
                'hasMore': next_offset is not None,
                'total': total_resy_results  # from Resy API (unfiltered estimate)
            }
        }

    except Exception as e:
        logger.exception("Error searching venues")
        return {
            'success': False,
            'error': str(e)
        }, 500


@on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET"]), timeout_sec=120)
def search_map(req: Request):
    """
    GET /search_map
    Search for restaurants by map bounding box
    Query parameters:
    - userId: Optional Firebase user ID for personalized credentials
    - jobId: Optional job ID for Firestore progress tracking
    - swLat: Southwest latitude (bottom-left)
    - swLng: Southwest longitude (bottom-left)
    - neLat: Northeast latitude (top-right)
    - neLng: Northeast longitude (top-right)
    - query: Optional restaurant name search
    - available_only: Optional availability-only boolean
    - not_released_only: Optional filter for "not released yet" venues
    - available_day: Optional day if available_only is true (format: 'YYYY-MM-DD')
    - available_party_size: Optional party size if available_only is true (default: 2)
    - cuisines: Optional comma-separated list of cuisines
    - priceRanges: Optional comma-separated list of price ranges (1-4)
    - offset: Optional offset for pagination (default: 0)
    - perPage: Optional results per page (default: 20, max: 50)
    """
    start_time = time.time()
    job_id = None

    try:
        user_id = req.args.get('userId')
        job_id = req.args.get('jobId')

        print(f"[MAP SEARCH] Received request with args: {req.args.to_dict()}")

        # Initialize job progress if jobId provided
        if job_id:
            update_search_progress(job_id, {
                "status": "started",
                "stage": "initializing",
                "createdAt": admin_firestore.SERVER_TIMESTAMP,
                "filteredCount": 0,
                "pagesFetched": 0,
            })

        # Get bounding box coordinates
        sw_lat = float(req.args.get('swLat', 0))
        sw_lng = float(req.args.get('swLng', 0))
        ne_lat = float(req.args.get('neLat', 0))
        ne_lng = float(req.args.get('neLng', 0))

        query = req.args.get('query', '').strip()

        # Parse filters using helper function
        filters = parse_search_filters(req.args)

        print(f"[MAP SEARCH] Bounding box: SW({sw_lat}, {sw_lng}) to NE({ne_lat}, {ne_lng})")
        print(
            f"[MAP SEARCH] Params - query: '{query}', available_only: {filters['available_only']}, "
            f"not_released_only: {filters.get('not_released_only', False)}, "
            f"offset: {filters['offset']}, perPage: {filters['per_page']}"
        )
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

        # Determine if we need to paginate over availability-filtered results
        # When available_only or not_released_only is enabled, we paginate over the filtered list
        paginate_over_filtered = (
            (filters.get('available_only') or filters.get('not_released_only')) and
            should_fetch_availability
        )

        if should_fetch_availability:
            print(
                f"[MAP SEARCH] Will fetch availability for date: {filters['available_day']}, "
                f"party size: {filters['available_party_size']}"
            )

        if paginate_over_filtered:
            print(
                f"[MAP SEARCH] Paginating over availability-filtered results "
                f"(available_only={filters.get('available_only')}, "
                f"not_released_only={filters.get('not_released_only')})"
            )

        # Generate cache key
        # When paginating over filtered results, include availability params in cache key
        cache_key = get_search_cache_key(query, filters, geo_config, include_availability=paginate_over_filtered)

        # Try to get from cache
        cached_data = get_cached_search_results(cache_key)

        # Check if we have enough cached results for this page
        need_fetch = True
        all_results = []
        total_resy_results = 0
        has_more = False

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
            print("[MAP SEARCH] Cache miss - fetching from Resy API")

            # Create fetch function for Resy API
            def fetch_resy_page(page_num):
                payload = build_search_payload(query, filters, geo_config, page=page_num)

                response = requests.post(
                    'https://api.resy.com/3/venuesearch/search',
                    json=payload,
                    headers=headers,
                    timeout=30
                )

                if response.status_code != 200:
                    raise Exception(f'API returned status {response.status_code}: {response.text[:200]}')

                data = response.json()
                hits = data.get('search', {}).get('hits', [])
                total = data.get('meta', {}).get('total', 0)

                return hits, total

            # Fetch enough results
            # When paginating over filtered results, we need to fetch with availability
            # so that filter_and_format_venues can filter by availability status
            target_count = filters['offset'] + filters['per_page']

            # For availability-filtered pagination, limit max_fetches since each page
            # requires availability API calls (slower). Users can paginate for more.
            if paginate_over_filtered:
                max_fetches = 4
                print(f"[MAP SEARCH] Fetching with availability filtering (max_fetches={max_fetches})")
            else:
                max_fetches = 10

            all_results, total_resy_results, has_more = fetch_until_enough_results(
                fetch_resy_page,
                target_count,
                filters,
                max_fetches=max_fetches,
                config=config,
                fetch_availability=paginate_over_filtered,  # Fetch availability when filtering by it
                job_id=job_id
            )

            # Save to cache
            save_search_results_to_cache(cache_key, all_results, total_resy_results)

        # Handle pagination based on whether we're filtering by availability
        if paginate_over_filtered:
            # ========================================================================
            # AVAILABILITY-FILTERED PAGINATION
            # all_results is already filtered by available_only/not_released_only
            # and each result has availableTimes/availabilityStatus populated
            # ========================================================================
            print(f"[MAP SEARCH] Paginating over {len(all_results)} availability-filtered results")

            # Simply slice the already-filtered results
            results = all_results[filters['offset']:filters['offset'] + filters['per_page']]

            # Calculate pagination based on the filtered list
            filtered_total = len(all_results)
            end_of_current_page = filters['offset'] + len(results)

            # Determine if there are more results
            if end_of_current_page < filtered_total:
                next_offset = end_of_current_page
            elif has_more:
                # We have more venues in Resy to fetch, so there might be more matches
                next_offset = end_of_current_page
            else:
                next_offset = None

            display_total = filtered_total

            print(
                f"[MAP SEARCH] Returning {len(results)} results for offset {filters['offset']} "
                f"(filtered_total={filtered_total}, has_more={has_more})"
            )

        else:
            # ========================================================================
            # NORMAL PAGINATION (no availability filtering)
            # Paginate over raw results, then optionally fetch availability for current page
            # ========================================================================

            # Slice results based on offset to get current page
            results = all_results[filters['offset']:filters['offset'] + filters['per_page']]

            # Now fetch availability ONLY for the current page results (in parallel)
            if should_fetch_availability and results:
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
                        except Exception as e:
                            print(f"[AVAILABILITY] Error in parallel fetch for venue {result['id']}: {str(e)}")
                            result['availabilityStatus'] = 'Unable to fetch'

            print(
                f"[MAP SEARCH] Returning {len(results)} results for offset {filters['offset']} "
                f"(have {len(all_results)} total cached)"
            )
            print(f"[MAP SEARCH] Resy total (unfiltered): {total_resy_results}")

            # For normal search: show next if there are more results in cache or API
            next_offset = (
                filters['offset'] + len(results)
                if (len(all_results) > filters['offset'] + filters['per_page'] or has_more)
                else None
            )
            display_total = total_resy_results

        # Mark job as done
        if job_id:
            duration_ms = int((time.time() - start_time) * 1000)
            update_search_progress(job_id, {
                "status": "done",
                "stage": "complete",
                "filteredCount": len(all_results),
                "returnedCount": len(results),
                "durationMs": duration_ms,
            })

        return {
            'success': True,
            'data': results,
            'pagination': {
                'offset': filters['offset'],
                'perPage': filters['per_page'],
                'nextOffset': next_offset,
                'hasMore': next_offset is not None,
                'total': display_total
            }
        }

    except Exception as e:
        logger.error("Error searching venues by map: %s", e)
        # Mark job as error
        if job_id:
            duration_ms = int((time.time() - start_time) * 1000)
            update_search_progress(job_id, {
                "status": "error",
                "error": str(e),
                "durationMs": duration_ms,
            })
        return {
            'success': False,
            'error': str(e)
        }, 500
