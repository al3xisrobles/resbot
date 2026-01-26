"""
Unit tests for search utility functions.

Tests cover:
- parse_search_filters: Parameter parsing and validation
- filter_and_format_venues: Venue filtering and formatting logic
- get_search_cache_key: Cache key generation
"""
import time
from unittest.mock import Mock

from api.tests.conftest import VenueFactory
from api.utils import (
    SEARCH_CACHE,
    SEARCH_CACHE_TTL,
    parse_search_filters,
    filter_and_format_venues,
    get_search_cache_key,
    get_cached_search_results,
    save_search_results_to_cache,
)


class TestParseSearchFilters:
    """Tests for parse_search_filters function."""

    def test_empty_filters(self):
        """Parse empty request args."""
        args = Mock()
        args.get = Mock(side_effect=lambda key, default='': default)

        filters = parse_search_filters(args)

        assert filters['cuisines'] == []
        assert filters['price_ranges'] == []
        assert filters['available_only'] is False
        assert filters['not_released_only'] is False
        assert filters['offset'] == 0
        assert filters['per_page'] == 20

    def test_cuisines_parsing(self):
        """Parse cuisine filter from comma-separated string."""
        args = Mock()
        args.get = Mock(side_effect=lambda key, default='': {
            'cuisines': 'Italian,Japanese,French',
            'priceRanges': '',
            'available_only': 'false',
            'not_released_only': 'false',
            'available_day': '',
            'available_party_size': '2',
            'desired_time': '',
            'offset': '0',
            'perPage': '20',
        }.get(key, default))

        filters = parse_search_filters(args)

        assert filters['cuisines'] == ['Italian', 'Japanese', 'French']

    def test_price_ranges_parsing(self):
        """Parse price ranges from comma-separated string."""
        args = Mock()
        args.get = Mock(side_effect=lambda key, default='': {
            'cuisines': '',
            'priceRanges': '1,2,4',
            'available_only': 'false',
            'not_released_only': 'false',
            'available_day': '',
            'available_party_size': '2',
            'desired_time': '',
            'offset': '0',
            'perPage': '20',
        }.get(key, default))

        filters = parse_search_filters(args)

        assert filters['price_ranges'] == [1, 2, 4]

    def test_available_only_flag(self):
        """Parse available_only boolean flag."""
        args = Mock()
        args.get = Mock(side_effect=lambda key, default='': {
            'cuisines': '',
            'priceRanges': '',
            'available_only': 'true',
            'not_released_only': 'false',
            'available_day': '2026-02-14',
            'available_party_size': '4',
            'desired_time': '',
            'offset': '0',
            'perPage': '20',
        }.get(key, default))

        filters = parse_search_filters(args)

        assert filters['available_only'] is True
        assert filters['available_day'] == '2026-02-14'
        assert filters['available_party_size'] == 4

    def test_not_released_only_flag(self):
        """Parse not_released_only boolean flag."""
        args = Mock()
        args.get = Mock(side_effect=lambda key, default='': {
            'cuisines': '',
            'priceRanges': '',
            'available_only': 'false',
            'not_released_only': 'true',
            'available_day': '2026-02-14',
            'available_party_size': '2',
            'desired_time': '',
            'offset': '0',
            'perPage': '20',
        }.get(key, default))

        filters = parse_search_filters(args)

        assert filters['not_released_only'] is True

    def test_pagination_params(self):
        """Parse offset and perPage parameters."""
        args = Mock()
        args.get = Mock(side_effect=lambda key, default='': {
            'cuisines': '',
            'priceRanges': '',
            'available_only': 'false',
            'not_released_only': 'false',
            'available_day': '',
            'available_party_size': '2',
            'desired_time': '',
            'offset': '40',
            'perPage': '50',
        }.get(key, default))

        filters = parse_search_filters(args)

        assert filters['offset'] == 40
        assert filters['per_page'] == 50

    def test_per_page_capped_at_50(self):
        """Per page should be capped at 50."""
        args = Mock()
        args.get = Mock(side_effect=lambda key, default='': {
            'cuisines': '',
            'priceRanges': '',
            'available_only': 'false',
            'not_released_only': 'false',
            'available_day': '',
            'available_party_size': '2',
            'desired_time': '',
            'offset': '0',
            'perPage': '100',
        }.get(key, default))

        filters = parse_search_filters(args)

        assert filters['per_page'] == 50


class TestFilterAndFormatVenues:
    """Tests for filter_and_format_venues function."""

    def test_basic_formatting(self, empty_filters):
        """Format venues without filters."""
        hits = VenueFactory.create_batch(3)

        results, _filtered_count, _seen_ids = filter_and_format_venues(
            hits, empty_filters
        )

        assert len(results) == 3
        assert all('id' in r for r in results)
        assert all('name' in r for r in results)
        assert all('type' in r for r in results)
        assert all('price_range' in r for r in results)

    def test_cuisine_filter(self, cuisine_filter):
        """Filter venues by cuisine."""
        # Create 5 Italian, 3 Japanese, 2 French
        hits = (
            VenueFactory.with_cuisine("Italian", 5) +
            VenueFactory.with_cuisine("Japanese", 3) +
            VenueFactory.with_cuisine("French", 2)
        )

        results, filtered_count, _seen_ids = filter_and_format_venues(
            hits, cuisine_filter
        )

        assert len(results) == 5
        assert all(r['type'] == 'Italian' for r in results)
        assert filtered_count['cuisine'] == 5  # 3 Japanese + 2 French

    def test_price_range_filter(self, price_filter):
        """Filter venues by price range."""
        # Create 4 venues with price 4, 6 with price 2
        hits = (
            VenueFactory.with_price_range(4, 4) +
            VenueFactory.with_price_range(2, 6)
        )

        results, filtered_count, _seen_ids = filter_and_format_venues(
            hits, price_filter
        )

        assert len(results) == 4
        assert all(r['price_range'] == 4 for r in results)
        assert filtered_count['price'] == 6

    def test_duplicate_filtering(self, empty_filters):
        """Skip duplicate venue IDs."""
        # Create venues with same ID
        venue1 = VenueFactory.create(venue_id=100, name="Restaurant A")
        venue2 = VenueFactory.create(venue_id=100, name="Restaurant A Duplicate")
        venue3 = VenueFactory.create(venue_id=200, name="Restaurant B")

        hits = [venue1, venue2, venue3]

        results, filtered_count, seen_ids = filter_and_format_venues(
            hits, empty_filters
        )

        assert len(results) == 2
        assert filtered_count['duplicate'] == 1
        assert 100 in seen_ids
        assert 200 in seen_ids

    def test_combined_filters(self):
        """Apply multiple filters simultaneously."""
        filters = {
            'cuisines': ['Italian'],
            'price_ranges': [4],
            'available_only': False,
            'not_released_only': False,
            'available_day': '',
            'available_party_size': 2,
            'desired_time': '',
            'offset': 0,
            'per_page': 20,
        }

        # Create: 3 Italian/$$$$, 2 Italian/$$, 2 Japanese/$$$$, 1 Japanese/$$
        hits = (
            VenueFactory.create_batch(3, cuisine="Italian", price_range_id=4) +
            VenueFactory.create_batch(2, cuisine="Italian", price_range_id=2) +
            VenueFactory.create_batch(2, cuisine="Japanese", price_range_id=4) +
            VenueFactory.create_batch(1, cuisine="Japanese", price_range_id=2)
        )

        results, filtered_count, _seen_ids = filter_and_format_venues(
            hits, filters
        )

        assert len(results) == 3  # Only Italian/$$$$
        assert filtered_count['cuisine'] == 3  # 2 Japanese/$$$$ + 1 Japanese/$$
        assert filtered_count['price'] == 2  # 2 Italian/$$

    def test_venue_without_name_skipped(self, empty_filters):
        """Skip venues without name."""
        venue1 = VenueFactory.create(name="Valid Restaurant")
        venue2 = VenueFactory.create(name="")
        venue3 = {"_source": {"id": {"resy": 999}}}  # No name field

        hits = [venue1, venue2, venue3]

        results, _filtered_count, _seen_ids = filter_and_format_venues(
            hits, empty_filters
        )

        assert len(results) == 1
        assert results[0]['name'] == "Valid Restaurant"

    def test_seen_ids_preserved(self, empty_filters):
        """seen_ids set should be preserved across calls."""
        hits1 = VenueFactory.create_batch(2)
        hits2 = VenueFactory.create_batch(2)

        # First call
        results1, _, seen_ids = filter_and_format_venues(
            hits1, empty_filters
        )

        # Second call with same seen_ids
        results2, _, _seen_ids = filter_and_format_venues(
            hits2, empty_filters, seen_ids=seen_ids
        )

        # Should have 4 total results
        assert len(results1) == 2
        assert len(results2) == 2
        # All IDs should be in seen_ids
        all_ids = {r['id'] for r in results1 + results2}
        assert all_ids.issubset(seen_ids)


class TestGetSearchCacheKey:
    """Tests for get_search_cache_key function."""

    def test_basic_cache_key(self, geo_config_nyc):
        """Generate cache key from basic search params."""
        query = "Italian"
        filters = {
            'cuisines': ['Italian'],
            'price_ranges': [2, 3],
            'available_only': False,
            'not_released_only': False,
        }

        key1 = get_search_cache_key(query, filters, geo_config_nyc)
        key2 = get_search_cache_key(query, filters, geo_config_nyc)

        # Same params should generate same key
        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length

    def test_cache_key_includes_availability_when_filtering(self, geo_config_nyc):
        """Cache key should include availability params when include_availability=True."""
        query = ""
        filters1 = {
            'available_only': True,
            'available_day': '2026-02-14',
            'available_party_size': 2,
            'desired_time': '19:00',
        }
        filters2 = {
            'available_only': True,
            'available_day': '2026-02-15',  # Different day
            'available_party_size': 2,
            'desired_time': '19:00',
        }

        key1 = get_search_cache_key(query, filters1, geo_config_nyc, include_availability=True)
        key2 = get_search_cache_key(query, filters2, geo_config_nyc, include_availability=True)

        # Different days should generate different keys
        assert key1 != key2

    def test_cache_key_excludes_availability_when_not_filtering(self, geo_config_nyc):
        """Cache key should not include availability params when include_availability=False."""
        query = ""
        filters1 = {
            'available_only': True,
            'available_day': '2026-02-14',
            'available_party_size': 2,
        }
        filters2 = {
            'available_only': True,
            'available_day': '2026-02-15',  # Different day
            'available_party_size': 2,
        }

        key1 = get_search_cache_key(query, filters1, geo_config_nyc, include_availability=False)
        key2 = get_search_cache_key(query, filters2, geo_config_nyc, include_availability=False)

        # Same key when not including availability
        assert key1 == key2

    def test_cache_key_sorted_params(self, geo_config_nyc):
        """Cache key should be stable regardless of filter order."""
        query = ""
        filters1 = {
            'cuisines': ['Italian', 'Japanese'],
            'price_ranges': [2, 4],
        }
        filters2 = {
            'cuisines': ['Japanese', 'Italian'],  # Different order
            'price_ranges': [4, 2],  # Different order
        }

        key1 = get_search_cache_key(query, filters1, geo_config_nyc)
        key2 = get_search_cache_key(query, filters2, geo_config_nyc)

        # Should generate same key despite different order
        assert key1 == key2


class TestCacheOperations:
    """Tests for cache get/save operations."""

    def test_save_and_get_cache(self):
        """Save and retrieve from cache."""
        SEARCH_CACHE.clear()  # Clear cache before test

        cache_key = "test_key_123"
        results = VenueFactory.create_batch(5)
        total = 100

        save_search_results_to_cache(cache_key, results, total)

        cached = get_cached_search_results(cache_key)

        assert cached is not None
        assert len(cached['results']) == 5
        assert cached['total'] == 100
        assert 'timestamp' in cached

    def test_cache_miss(self):
        """Get None for non-existent cache key."""
        SEARCH_CACHE.clear()

        cached = get_cached_search_results("nonexistent_key")

        assert cached is None

    def test_cache_expiration(self):
        """Cache should expire after TTL."""
        SEARCH_CACHE.clear()

        cache_key = "test_key_expire"
        results = VenueFactory.create_batch(2)

        save_search_results_to_cache(cache_key, results, 50)

        # Manually set timestamp to past
        SEARCH_CACHE[cache_key]['timestamp'] = time.time() - SEARCH_CACHE_TTL - 1

        cached = get_cached_search_results(cache_key)

        assert cached is None
        assert cache_key not in SEARCH_CACHE
