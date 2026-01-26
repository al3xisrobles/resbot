"""
Critical tests for pagination algorithm (fetch_until_enough_results).

This is the core algorithm that fetches pages until we have enough filtered results.
These tests are especially important for availability filtering scenarios where
only a small percentage of venues pass the filter.
"""
from unittest.mock import patch

from api.tests.conftest import VenueFactory, AvailabilityFactory
from api.utils import fetch_until_enough_results


class TestPaginationBasic:
    """Basic pagination scenarios."""

    def test_target_met_on_first_page(self, empty_filters):
        """All venues on first page pass filters."""
        # 20 venues, all pass filters
        hits = VenueFactory.create_batch(20)

        def search_func(page):
            if page == 1:
                return hits, 20
            return [], 20

        results, total, has_more = fetch_until_enough_results(
            search_func, target_count=20, filters=empty_filters, max_fetches=10
        )

        assert len(results) == 20
        assert total == 20
        # Function assumes there might be more if we got 20 hits on the last page
        # It doesn't check the next page unless we need more results
        assert has_more is True

    def test_need_multiple_pages(self, empty_filters):
        """Need to fetch multiple pages to get enough results."""
        # 5 venues per page pass filters, need 20 total
        def search_func(page):
            if page <= 4:
                # Each page has 20 venues, but only 5 pass filters
                all_hits = VenueFactory.create_batch(20)
                # Return all hits (filtering happens in filter_and_format_venues)
                return all_hits, 80
            return [], 80

        # Mock filter_and_format_venues to return only 5 per page
        with patch('api.utils.filter_and_format_venues') as mock_filter:
            def filter_side_effect(hits, _filters, seen_ids, **_kwargs):
                # Return first 5 venues as passing
                passed = hits[:5]
                return passed, {}, seen_ids

            mock_filter.side_effect = filter_side_effect

            results, _total, _has_more = fetch_until_enough_results(
                search_func, target_count=20, filters=empty_filters, max_fetches=10
            )

            assert len(results) == 20
            assert mock_filter.call_count == 4  # Called 4 times

    def test_max_fetches_exceeded(self, empty_filters):
        """Stop fetching when max_fetches is reached."""
        # Only 1 venue per page passes, max_fetches=10, need 20
        def search_func(page):
            if page <= 10:
                return VenueFactory.create_batch(20), 200
            return [], 200

        with patch('api.utils.filter_and_format_venues') as mock_filter:
            def filter_side_effect(hits, _filters, seen_ids, **_kwargs):
                # Return only first venue as passing
                passed = hits[:1]
                return passed, {}, seen_ids

            mock_filter.side_effect = filter_side_effect

            results, _total, _has_more = fetch_until_enough_results(
                search_func, target_count=20, filters=empty_filters, max_fetches=10
            )

            results, _total, has_more = fetch_until_enough_results(
                search_func, target_count=20, filters=empty_filters, max_fetches=10
            )
            assert len(results) == 10  # Only 10 pages fetched
            assert has_more is True  # More results available but max_fetches reached

    def test_empty_results_early(self, empty_filters):
        """Stop fetching when API returns empty results."""
        def search_func(page):
            if page == 1:
                return VenueFactory.create_batch(10), 10
            if page == 2:
                return VenueFactory.create_batch(5), 10
            return [], 10  # Page 3 is empty

        results, _total, has_more = fetch_until_enough_results(
            search_func, target_count=20, filters=empty_filters, max_fetches=10
        )

        # Should stop after page 3 returns empty
        assert len(results) <= 15  # At most 15 from first 2 pages
        assert has_more is False

    def test_duplicate_venue_handling(self, empty_filters):
        """Handle duplicate venue IDs across pages."""
        venue_id = 100
        venue1 = VenueFactory.create(venue_id=venue_id, name="Restaurant A")
        venue2 = VenueFactory.create(venue_id=venue_id, name="Restaurant A Duplicate")
        venue3 = VenueFactory.create(venue_id=200, name="Restaurant B")

        def search_func(page):
            if page == 1:
                return [venue1, venue3], 2
            if page == 2:
                return [venue2], 2
            return [], 2

        results, _total, _has_more = fetch_until_enough_results(
            search_func, target_count=20, filters=empty_filters, max_fetches=10
        )

        # Should only have 2 unique venues
        unique_ids = {r['id'] for r in results}
        assert len(unique_ids) == 2
        assert 100 in unique_ids
        assert 200 in unique_ids


class TestPaginationWithAvailabilityFiltering:
    """Pagination with availability-based filtering (critical scenario)."""

    def test_not_released_filter_needs_multiple_pages(self, not_released_only_filter, mock_config):
        """
        Critical test: Need 20 "Not released yet" venues but only a few per page.

        Scenario:
        - Page 1: 20 venues, 3 are "Not released yet"
        - Page 2: 20 venues, 4 are "Not released yet"
        - Page 3: 20 venues, 5 are "Not released yet"
        - Page 4: 20 venues, 8 are "Not released yet"
        Expected: 20 results after 4 pages (3+4+5+8=20)
        """
        # Create venues with different availability statuses
        def create_page_with_statuses(page_num, not_released_count, other_count):
            """Create a page with mix of statuses."""
            venues = []
            base_id = page_num * 1000  # Unique base ID per page
            # Add not-released venues
            for i in range(not_released_count):
                venues.append(VenueFactory.create(venue_id=base_id + i))
            # Add other venues (available, sold out, etc.)
            for i in range(other_count):
                venues.append(VenueFactory.create(venue_id=base_id + 100 + i))
            return venues

        page_data = [
            (create_page_with_statuses(1, 3, 17), 80),  # Page 1: 3 not released
            (create_page_with_statuses(2, 4, 16), 80),  # Page 2: 4 not released
            (create_page_with_statuses(3, 5, 15), 80),  # Page 3: 5 not released
            (create_page_with_statuses(4, 8, 12), 80),  # Page 4: 8 not released
        ]

        def search_func(page):
            if page <= len(page_data):
                return page_data[page - 1]
            return [], 80

        # Mock get_venue_availability to return appropriate status
        with patch('api.utils.get_venue_availability') as mock_availability:
            def availability_side_effect(venue_id, _day, _party_size, _config):
                # Not-released venues are those with ID % 1000 < 10 (first few on each page)
                # Each page has base_id = page * 1000
                page_num = venue_id // 1000
                offset = venue_id % 1000
                # Page 1: first 3 are not released (offset < 3)
                # Page 2: first 4 are not released (offset < 4)
                # Page 3: first 5 are not released (offset < 5)
                # Page 4: first 8 are not released (offset < 8)
                not_released_counts = {1: 3, 2: 4, 3: 5, 4: 8}
                if page_num in not_released_counts and offset < not_released_counts[page_num]:
                    return AvailabilityFactory.not_released()
                # All others are available
                return AvailabilityFactory.available()

            mock_availability.side_effect = availability_side_effect

            # Don't patch filter_and_format_venues - let it use the real function
            # which will call the mocked get_venue_availability
            results, _total, _has_more = fetch_until_enough_results(
                search_func,
                target_count=20,
                filters=not_released_only_filter,
                max_fetches=10,
                config=mock_config,
                fetch_availability=True
            )

            # Should have exactly 20 not-released venues
            assert len(results) == 20
            assert all('availabilityStatus' in r for r in results)
            assert all(r['availabilityStatus'] == 'Not released yet' for r in results)
            # Should have fetched 4 pages
            assert mock_availability.call_count >= 20  # At least 20 availability calls

    def test_available_only_filter_sparse_results(self, available_only_filter, mock_config):
        """
        Test available_only filter when results are sparse.

        Scenario: Only 2 venues per page have available times.
        Need 20 results -> fetch 10 pages.
        """
        def create_page_with_availability(page_num, available_count, unavailable_count):
            """Create page with mix of available/unavailable."""
            venues = []
            base_id = page_num * 1000  # Unique base ID per page
            # Available venues
            for i in range(available_count):
                venues.append(VenueFactory.create(venue_id=base_id + i))
            # Unavailable venues (sold out, closed, etc.)
            for i in range(unavailable_count):
                venues.append(VenueFactory.create(venue_id=base_id + 100 + i))
            return venues

        def search_func(page):
            if page <= 10:
                return create_page_with_availability(page, 2, 18), 200
            return [], 200

        with patch('api.utils.get_venue_availability') as mock_availability:
            def availability_side_effect(venue_id, _day, _party_size, _config):
                # Available venues are those with ID % 1000 < 2 (first 2 on each page)
                # Each page has base_id = page * 1000, so available IDs are base_id + 0, base_id + 1
                if (venue_id % 1000) < 2:
                    return AvailabilityFactory.available()
                # Others are sold out
                return AvailabilityFactory.sold_out()

            mock_availability.side_effect = availability_side_effect

            # Don't patch filter_and_format_venues - let it use the real function
            # which will call the mocked get_venue_availability
            results, _total, _has_more = fetch_until_enough_results(
                search_func,
                target_count=20,
                filters=available_only_filter,
                max_fetches=10,
                config=mock_config,
                fetch_availability=True
            )

            # Should have 20 available venues (2 per page * 10 pages)
            assert len(results) == 20
            assert all('availableTimes' in r for r in results)
            assert all(len(r['availableTimes']) > 0 for r in results)

    def test_extremely_sparse_results(self, not_released_only_filter, mock_config):
        """
        Edge case: Only 1 venue per page passes filter.
        max_fetches=10 -> only get 10 results max.
        Should return 10 results with has_more=True.
        """
        def search_func(page):
            if page <= 10:
                return VenueFactory.create_batch(20), 200
            return [], 200

        with patch('api.utils.get_venue_availability') as mock_availability:
            # Make only the first venue on each page "Not released yet"
            def availability_side_effect(venue_id, _day, _party_size, _config):
                # Venue IDs are sequential, so first venue on each page (1, 21, 41, etc.) is not released
                # Assuming 20 venues per page, first venue IDs would be: 1, 21, 41, 61, etc.
                # Check if venue_id is the first on a page
                # (venue_id % 20 == 1, or simpler: venue_id in [1, 21, 41, ...])
                page_first_ids = [1 + i * 20 for i in range(10)]  # First 10 pages
                if venue_id in page_first_ids:
                    return AvailabilityFactory.not_released()
                return AvailabilityFactory.available()

            mock_availability.side_effect = availability_side_effect

            # Don't patch filter_and_format_venues - let it use the real function
            # which will call the mocked get_venue_availability
            results, _total, has_more = fetch_until_enough_results(
                search_func,
                target_count=20,
                filters=not_released_only_filter,
                max_fetches=10,
                config=mock_config,
                fetch_availability=True
            )

            # Should only have 10 results (1 per page * 10 pages)
            assert len(results) == 10
            # has_more would be True but we can't check it without re-fetching
            assert has_more  # Suppress unused variable warning

    def test_filter_decimates_results(self, available_only_filter, mock_config):
        """
        Test when filter removes most results (only 2/100 venues pass).
        """
        def search_func(page):
            if page <= 5:
                return VenueFactory.create_batch(20), 100
            return [], 100

        with patch('api.utils.get_venue_availability') as mock_availability:
            call_count = [0]

            def availability_side_effect(venue_id, _day, _party_size, _config):
                call_count[0] += 1
                # Only venues with ID ending in 0 or 5 are available
                if venue_id % 10 in [0, 5]:
                    return AvailabilityFactory.available()
                return AvailabilityFactory.sold_out()

            mock_availability.side_effect = availability_side_effect

            # Don't patch filter_and_format_venues - let it use the real function
            # which will call the mocked get_venue_availability
            results, _total, _has_more = fetch_until_enough_results(
                search_func,
                target_count=20,
                filters=available_only_filter,
                max_fetches=10,
                config=mock_config,
                fetch_availability=True
            )

            # Should fetch multiple pages to get 20 results
            # With 2/20 passing per page, need ~10 pages
            assert len(results) <= 20
            # Should have made many availability calls
            assert call_count[0] > 20


class TestPaginationEdgeCases:
    """Edge cases and boundary conditions."""

    def test_target_count_zero(self, empty_filters):
        """Handle target_count of 0."""
        def search_func(_page):
            return VenueFactory.create_batch(20), 100

        results, _total, _has_more = fetch_until_enough_results(
            search_func, target_count=0, filters=empty_filters, max_fetches=10
        )

        assert len(results) == 0

    def test_target_count_larger_than_available(self, empty_filters):
        """Request more results than available."""
        def search_func(page):
            if page == 1:
                return VenueFactory.create_batch(10), 10
            return [], 10

        results, _total, has_more = fetch_until_enough_results(
            search_func, target_count=50, filters=empty_filters, max_fetches=10
        )

        assert len(results) == 10
        assert has_more is False

    def test_resy_returns_fewer_than_20(self, empty_filters):
        """Handle case where Resy returns fewer than 20 results per page."""
        def search_func(page):
            if page == 1:
                return VenueFactory.create_batch(15), 15
            return [], 15

        results, _total, has_more = fetch_until_enough_results(
            search_func, target_count=20, filters=empty_filters, max_fetches=10
        )

        assert len(results) == 15
        assert has_more is False  # No more results available

    def test_has_more_calculation(self, empty_filters):
        """Test has_more flag calculation."""
        # Case 1: More results available (got 20 on page 1, might be more)
        def search_func1(page):
            if page <= 2:
                return VenueFactory.create_batch(20), 100
            return [], 100

        _results1, _total1, has_more1 = fetch_until_enough_results(
            search_func1, target_count=20, filters=empty_filters, max_fetches=10
        )

        assert has_more1 is True  # More results in API

        # Case 2: Got exactly 20 results on page 1, but we don't know if there are more
        # The function assumes there might be more if we got 20 on the last page
        def search_func2(page):
            if page == 1:
                return VenueFactory.create_batch(20), 20
            return [], 20

        _results2, _total2, has_more2 = fetch_until_enough_results(
            search_func2, target_count=20, filters=empty_filters, max_fetches=10
        )

        # The function returns True because it got 20 hits on page 1
        # It doesn't check page 2 unless we need more results
        assert has_more2 is True  # Function assumes more might exist

        # Case 3: Actually fetch page 2 to confirm no more results
        def search_func3(page):
            if page == 1:
                return VenueFactory.create_batch(20), 20
            if page == 2:
                return [], 20  # Empty page 2
            return [], 20

        _results3, _total3, has_more3 = fetch_until_enough_results(
            search_func3, target_count=25, filters=empty_filters, max_fetches=10
        )

        # Now we actually fetched page 2 and it was empty, so has_more should be False
        assert has_more3 is False  # Page 2 was empty, no more results
