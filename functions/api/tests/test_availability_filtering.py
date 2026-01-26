"""
Tests for availability-based filtering (available_only and not_released_only).

These tests verify that venues are correctly filtered based on their availability status.
"""
from unittest.mock import patch

from api.tests.conftest import VenueFactory, AvailabilityFactory
from api.utils import filter_and_format_venues


class TestAvailableOnlyFilter:
    """Tests for available_only filter."""

    def test_available_only_passes_venues_with_times(self, available_only_filter, mock_config):
        """Venues with available times should pass available_only filter."""
        hits = VenueFactory.create_batch(3)

        with patch('api.utils.get_venue_availability') as mock_availability:
            mock_availability.return_value = AvailabilityFactory.available()

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, available_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 3
            assert all('availableTimes' in r for r in results)
            assert all(len(r['availableTimes']) > 0 for r in results)
            assert filtered_count['availability'] == 0

    def test_available_only_filters_sold_out(self, available_only_filter, mock_config):
        """Sold out venues should be filtered out."""
        hits = VenueFactory.create_batch(5)

        with patch('api.utils.get_venue_availability') as mock_availability:
            mock_availability.return_value = AvailabilityFactory.sold_out()

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, available_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 0
            assert filtered_count['availability'] == 5

    def test_available_only_filters_closed(self, available_only_filter, mock_config):
        """Closed venues should be filtered out."""
        hits = VenueFactory.create_batch(3)

        with patch('api.utils.get_venue_availability') as mock_availability:
            mock_availability.return_value = AvailabilityFactory.closed()

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, available_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 0
            assert filtered_count['availability'] == 3

    def test_available_only_filters_not_released(self, available_only_filter, mock_config):
        """Not released venues should be filtered out."""
        hits = VenueFactory.create_batch(4)

        with patch('api.utils.get_venue_availability') as mock_availability:
            mock_availability.return_value = AvailabilityFactory.not_released()

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, available_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 0
            assert filtered_count['availability'] == 4

    def test_available_only_filters_unable_to_fetch(self, available_only_filter, mock_config):
        """Venues with 'Unable to fetch' status should be filtered out."""
        hits = VenueFactory.create_batch(2)

        with patch('api.utils.get_venue_availability') as mock_availability:
            mock_availability.return_value = AvailabilityFactory.unable_to_fetch()

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, available_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 0
            assert filtered_count['availability'] == 2

    def test_available_only_mixed_statuses(self, available_only_filter, mock_config):
        """Test mix of available and unavailable venues."""
        hits = VenueFactory.create_batch(10)

        with patch('api.utils.get_venue_availability') as mock_availability:
            def availability_side_effect(venue_id, _day, _party_size, _config):
                # First 3 are available, rest are sold out
                if venue_id <= hits[2]['_source']['id']['resy']:
                    return AvailabilityFactory.available()
                return AvailabilityFactory.sold_out()

            mock_availability.side_effect = availability_side_effect

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, available_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 3
            assert filtered_count['availability'] == 7

    def test_available_only_without_fetch_availability(self, available_only_filter, mock_config):
        """available_only filter should not work without fetch_availability=True."""
        hits = VenueFactory.create_batch(5)

        # Should not filter when fetch_availability=False
        results, filtered_count, _seen_ids = filter_and_format_venues(
            hits, available_only_filter, config=mock_config, fetch_availability=False
        )

        # All venues should pass (no availability check)
        assert len(results) == 5
        assert filtered_count['availability'] == 0


class TestNotReleasedOnlyFilter:
    """Tests for not_released_only filter."""

    def test_not_released_only_passes_not_released(self, not_released_only_filter, mock_config):
        """Venues with 'Not released yet' status should pass."""
        hits = VenueFactory.create_batch(3)

        with patch('api.utils.get_venue_availability') as mock_availability:
            mock_availability.return_value = AvailabilityFactory.not_released()

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, not_released_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 3
            assert all('availabilityStatus' in r for r in results)
            assert all(r['availabilityStatus'] == 'Not released yet' for r in results)
            assert filtered_count.get('not_released', 0) == 0

    def test_not_released_only_filters_available(self, not_released_only_filter, mock_config):
        """Available venues should be filtered out."""
        hits = VenueFactory.create_batch(5)

        with patch('api.utils.get_venue_availability') as mock_availability:
            mock_availability.return_value = AvailabilityFactory.available()

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, not_released_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 0
            assert filtered_count.get('not_released', 0) == 5

    def test_not_released_only_filters_sold_out(self, not_released_only_filter, mock_config):
        """Sold out venues should be filtered out."""
        hits = VenueFactory.create_batch(4)

        with patch('api.utils.get_venue_availability') as mock_availability:
            mock_availability.return_value = AvailabilityFactory.sold_out()

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, not_released_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 0
            assert filtered_count.get('not_released', 0) == 4

    def test_not_released_only_filters_closed(self, not_released_only_filter, mock_config):
        """Closed venues should be filtered out."""
        hits = VenueFactory.create_batch(3)

        with patch('api.utils.get_venue_availability') as mock_availability:
            mock_availability.return_value = AvailabilityFactory.closed()

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, not_released_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 0
            assert filtered_count.get('not_released', 0) == 3

    def test_not_released_only_filters_unable_to_fetch(self, not_released_only_filter, mock_config):
        """Venues with 'Unable to fetch' should be filtered out."""
        hits = VenueFactory.create_batch(2)

        with patch('api.utils.get_venue_availability') as mock_availability:
            mock_availability.return_value = AvailabilityFactory.unable_to_fetch()

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, not_released_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 0
            assert filtered_count.get('not_released', 0) == 2

    def test_not_released_only_mixed_statuses(self, not_released_only_filter, mock_config):
        """Test mix of not-released and other statuses."""
        hits = VenueFactory.create_batch(10)

        with patch('api.utils.get_venue_availability') as mock_availability:
            def availability_side_effect(venue_id, _day, _party_size, _config):
                # First 2 are not released, rest are available
                if venue_id <= hits[1]['_source']['id']['resy']:
                    return AvailabilityFactory.not_released()
                return AvailabilityFactory.available()

            mock_availability.side_effect = availability_side_effect

            results, filtered_count, _seen_ids = filter_and_format_venues(
                hits, not_released_only_filter, config=mock_config, fetch_availability=True
            )

            assert len(results) == 2
            assert filtered_count.get('not_released', 0) == 8

    def test_not_released_only_without_fetch_availability(self, not_released_only_filter, mock_config):
        """not_released_only filter should not work without fetch_availability=True."""
        hits = VenueFactory.create_batch(5)

        # Should not filter when fetch_availability=False
        results, filtered_count, _seen_ids = filter_and_format_venues(
            hits, not_released_only_filter, config=mock_config, fetch_availability=False
        )

        # All venues should pass (no availability check)
        assert len(results) == 5
        assert filtered_count.get('not_released', 0) == 0


class TestAvailabilityStatusTable:
    """
    Comprehensive test of availability status filtering table.

    | Status | available_only=true | not_released_only=true |
    |--------|---------------------|------------------------|
    | Has available times | PASS | FAIL |
    | Sold out | FAIL | FAIL |
    | Closed | FAIL | FAIL |
    | Not released yet | FAIL | PASS |
    | Unable to fetch | FAIL | FAIL |
    """

    def test_availability_status_table(self, mock_config):
        """Test all combinations from the status table."""
        statuses = [
            ('available', AvailabilityFactory.available(), True, False),
            ('sold_out', AvailabilityFactory.sold_out(), False, False),
            ('closed', AvailabilityFactory.closed(), False, False),
            ('not_released', AvailabilityFactory.not_released(), False, True),
            ('unable_to_fetch', AvailabilityFactory.unable_to_fetch(), False, False),
        ]

        for status_name, availability_data, should_pass_available, should_pass_not_released in statuses:
            # Test available_only filter
            available_filter = {
                'cuisines': [],
                'price_ranges': [],
                'available_only': True,
                'not_released_only': False,
                'available_day': '2026-02-14',
                'available_party_size': 2,
                'desired_time': '',
                'offset': 0,
                'per_page': 20,
            }

            hits = VenueFactory.create_batch(1)

            with patch('api.utils.get_venue_availability') as mock_availability:
                mock_availability.return_value = availability_data

                results, _filtered_count, _ = filter_and_format_venues(
                    hits, available_filter, config=mock_config, fetch_availability=True
                )

                if should_pass_available:
                    assert len(results) == 1, f"{status_name} should pass available_only filter"
                else:
                    assert len(results) == 0, f"{status_name} should fail available_only filter"

            # Test not_released_only filter
            not_released_filter = {
                'cuisines': [],
                'price_ranges': [],
                'available_only': False,
                'not_released_only': True,
                'available_day': '2026-02-14',
                'available_party_size': 2,
                'desired_time': '',
                'offset': 0,
                'per_page': 20,
            }

            with patch('api.utils.get_venue_availability') as mock_availability:
                mock_availability.return_value = availability_data

                results, _filtered_count, _ = filter_and_format_venues(
                    hits, not_released_filter, config=mock_config, fetch_availability=True
                )

                if should_pass_not_released:
                    assert len(results) == 1, f"{status_name} should pass not_released_only filter"
                else:
                    assert len(results) == 0, f"{status_name} should fail not_released_only filter"


class TestAvailabilityWithOtherFilters:
    """Test availability filters combined with cuisine/price filters."""

    def test_available_only_with_cuisine_filter(self, mock_config):
        """Combine available_only with cuisine filter."""
        filters = {
            'cuisines': ['Italian'],
            'price_ranges': [],
            'available_only': True,
            'not_released_only': False,
            'available_day': '2026-02-14',
            'available_party_size': 2,
            'desired_time': '',
            'offset': 0,
            'per_page': 20,
        }

        # Create mix of Italian and Japanese venues
        hits = (
            VenueFactory.with_cuisine("Italian", 3) +
            VenueFactory.with_cuisine("Japanese", 2)
        )

        with patch('api.utils.get_venue_availability') as mock_availability:
            def availability_side_effect(venue_id, _day, _party_size, _config):
                # First 2 Italian venues are available, rest are sold out
                if venue_id <= hits[1]['_source']['id']['resy']:
                    return AvailabilityFactory.available()
                return AvailabilityFactory.sold_out()

            mock_availability.side_effect = availability_side_effect

            results, _filtered_count, _seen_ids = filter_and_format_venues(
                hits, filters, config=mock_config, fetch_availability=True
            )

            # Should only have 2 Italian venues that are available
            assert len(results) == 2
            assert all(r['type'] == 'Italian' for r in results)
            assert all('availableTimes' in r for r in results)

    def test_not_released_only_with_price_filter(self, mock_config):
        """Combine not_released_only with price filter."""
        filters = {
            'cuisines': [],
            'price_ranges': [4],
            'available_only': False,
            'not_released_only': True,
            'available_day': '2026-02-14',
            'available_party_size': 2,
            'desired_time': '',
            'offset': 0,
            'per_page': 20,
        }

        # Create mix of price ranges
        hits = (
            VenueFactory.with_price_range(4, 3) +
            VenueFactory.with_price_range(2, 2)
        )

        with patch('api.utils.get_venue_availability') as mock_availability:
            def availability_side_effect(venue_id, _day, _party_size, _config):
                # First 2 price-4 venues are not released, rest are available
                if venue_id <= hits[1]['_source']['id']['resy']:
                    return AvailabilityFactory.not_released()
                return AvailabilityFactory.available()

            mock_availability.side_effect = availability_side_effect

            results, _filtered_count, _seen_ids = filter_and_format_venues(
                hits, filters, config=mock_config, fetch_availability=True
            )

            # Should only have 2 price-4 venues that are not released
            assert len(results) == 2
            assert all(r['price_range'] == 4 for r in results)
            assert all(r['availabilityStatus'] == 'Not released yet' for r in results)
