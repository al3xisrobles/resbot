"""
Integration tests for search endpoints (/search and /search_map).

These tests verify the full API flow including:
- Request parsing
- Resy API interaction (mocked)
- Filtering and pagination
- Response formatting
"""
from unittest.mock import Mock, patch

from flask import Flask
from firebase_functions.https_fn import Request

from api.tests.conftest import VenueFactory

# Import the actual function implementations
import api.search as search_module


class TestSearchEndpoint:
    """Tests for /search endpoint."""

    def create_mock_request(self, **kwargs):
        """Create a mock Request object with query parameters."""
        request = Mock(spec=Request)
        request.args = Mock()
        request.args.get = Mock(side_effect=lambda key, default='': kwargs.get(key, default))
        request.args.to_dict = Mock(return_value=kwargs)
        return request

    def call_endpoint(self, endpoint_func, request):
        """Call an endpoint function and extract the response."""
        app = Flask(__name__)
        with app.test_request_context():
            result = endpoint_func(request)
            # The decorator wraps the response, extract it
            if hasattr(result, 'get_json'):
                response = result.get_json()
                status_code = result.status_code
            else:
                response, status_code = result
            return response, status_code

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    @patch('api.search.fetch_until_enough_results')
    @patch('api.search.build_search_payload')
    @patch('api.search.requests.post')
    def test_search_basic(self, _mock_post, _mock_build_payload, mock_fetch, mock_headers, mock_credentials):
        """Basic search without filters."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}

        # Mock fetch_until_enough_results to return test data
        mock_venues = VenueFactory.create_batch(5)
        # Convert to format expected by the endpoint (already formatted by filter_and_format_venues)
        formatted_venues = []
        for venue in mock_venues:
            venue_data = venue.get('_source') or venue
            formatted_venues.append({
                'id': (
                    venue_data.get('id', {}).get('resy')
                    if isinstance(venue_data.get('id'), dict)
                    else venue_data.get('id')
                ),
                'name': venue_data.get('name', ''),
                'type': venue_data.get('cuisine', [None])[0] if venue_data.get('cuisine') else '',
                'price_range': venue_data.get('price_range_id', 0),
                'locality': venue_data.get('locality', 'N/A'),
                'region': venue_data.get('region', 'N/A'),
                'neighborhood': venue_data.get('neighborhood', ''),
                'latitude': venue_data.get('_geoloc', {}).get('lat'),
                'longitude': venue_data.get('_geoloc', {}).get('lng'),
                'imageUrl': venue_data.get('images', [None])[0] if venue_data.get('images') else None,
            })

        mock_fetch.return_value = (formatted_venues, 100, False)

        request = self.create_mock_request(
            userId='test_user',
            query='Italian',
        )

        response, status_code = self.call_endpoint(search_module.search, request)

        assert status_code == 200
        assert response['success'] is True
        assert len(response['data']) == 5
        assert 'pagination' in response

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    @patch('api.search.fetch_until_enough_results')
    @patch('api.search.build_search_payload')
    @patch('api.search.requests.post')
    def test_search_with_cuisines(self, _mock_post, _mock_build_payload, mock_fetch, mock_headers, mock_credentials):
        """Search with cuisine filter."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}

        mock_venues = VenueFactory.with_cuisine("Italian", 3)
        mock_fetch.return_value = (mock_venues, 50, False)

        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}

        mock_venues = VenueFactory.with_cuisine("Italian", 3)
        formatted_venues = []
        for venue in mock_venues:
            venue_data = venue.get('_source') or venue
            formatted_venues.append({
                'id': (
                    venue_data.get('id', {}).get('resy')
                    if isinstance(venue_data.get('id'), dict)
                    else venue_data.get('id')
                ),
                'name': venue_data.get('name', ''),
                'type': venue_data.get('cuisine', [None])[0] if venue_data.get('cuisine') else '',
                'price_range': venue_data.get('price_range_id', 0),
                'locality': venue_data.get('locality', 'N/A'),
                'region': venue_data.get('region', 'N/A'),
                'neighborhood': venue_data.get('neighborhood', ''),
                'latitude': venue_data.get('_geoloc', {}).get('lat'),
                'longitude': venue_data.get('_geoloc', {}).get('lng'),
                'imageUrl': venue_data.get('images', [None])[0] if venue_data.get('images') else None,
            })
        mock_fetch.return_value = (formatted_venues, 50, False)

        request = self.create_mock_request(
            userId='test_user',
            cuisines='Italian,Japanese',
        )

        response, status_code = self.call_endpoint(search_module.search, request)

        assert status_code == 200
        assert response['success'] is True
        assert len(response['data']) == 3

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    @patch('api.search.fetch_until_enough_results')
    @patch('api.search.build_search_payload')
    @patch('api.search.requests.post')
    def test_search_with_price_ranges(
        self, _mock_post, _mock_build_payload, mock_fetch, mock_headers, mock_credentials
    ):
        """Search with price range filter."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}

        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}

        mock_venues = VenueFactory.with_price_range(4, 2)
        formatted_venues = []
        for venue in mock_venues:
            venue_data = venue.get('_source') or venue
            formatted_venues.append({
                'id': (
                    venue_data.get('id', {}).get('resy')
                    if isinstance(venue_data.get('id'), dict)
                    else venue_data.get('id')
                ),
                'name': venue_data.get('name', ''),
                'type': venue_data.get('cuisine', [None])[0] if venue_data.get('cuisine') else '',
                'price_range': venue_data.get('price_range_id', 0),
                'locality': venue_data.get('locality', 'N/A'),
                'region': venue_data.get('region', 'N/A'),
                'neighborhood': venue_data.get('neighborhood', ''),
                'latitude': venue_data.get('_geoloc', {}).get('lat'),
                'longitude': venue_data.get('_geoloc', {}).get('lng'),
                'imageUrl': venue_data.get('images', [None])[0] if venue_data.get('images') else None,
            })
        mock_fetch.return_value = (formatted_venues, 30, False)

        request = self.create_mock_request(
            userId='test_user',
            priceRanges='2,4',
        )

        response, status_code = self.call_endpoint(search_module.search, request)

        assert status_code == 200
        assert response['success'] is True
        assert len(response['data']) == 2

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    def test_search_no_filters_error(self, mock_headers, mock_credentials):
        """Search without any filters should return error."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}

        request = self.create_mock_request(
            userId='test_user',
        )

        response, status_code = self.call_endpoint(search_module.search, request)

        assert status_code == 400
        assert response['success'] is False
        assert 'error' in response

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    @patch('api.search.fetch_until_enough_results')
    @patch('api.search.build_search_payload')
    @patch('api.search.requests.post')
    def test_search_pagination(self, _mock_post, _mock_build_payload, mock_fetch, mock_headers, mock_credentials):
        """Search with pagination (offset and perPage)."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}

        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}

        mock_venues = VenueFactory.create_batch(20)
        formatted_venues = []
        for venue in mock_venues:
            venue_data = venue.get('_source') or venue
            formatted_venues.append({
                'id': (
                    venue_data.get('id', {}).get('resy')
                    if isinstance(venue_data.get('id'), dict)
                    else venue_data.get('id')
                ),
                'name': venue_data.get('name', ''),
                'type': venue_data.get('cuisine', [None])[0] if venue_data.get('cuisine') else '',
                'price_range': venue_data.get('price_range_id', 0),
                'locality': venue_data.get('locality', 'N/A'),
                'region': venue_data.get('region', 'N/A'),
                'neighborhood': venue_data.get('neighborhood', ''),
                'latitude': venue_data.get('_geoloc', {}).get('lat'),
                'longitude': venue_data.get('_geoloc', {}).get('lng'),
                'imageUrl': venue_data.get('images', [None])[0] if venue_data.get('images') else None,
            })
        mock_fetch.return_value = (formatted_venues, 100, True)

        request = self.create_mock_request(
            userId='test_user',
            query='Restaurant',
            offset='20',
            perPage='20',
        )

        response, status_code = self.call_endpoint(search_module.search, request)

        assert status_code == 200
        assert response['success'] is True
        assert response['pagination']['offset'] == 20
        assert response['pagination']['hasMore'] is True


class TestSearchMapEndpoint:
    """Tests for /search_map endpoint."""

    def create_mock_request(self, **kwargs):
        """Create a mock Request object with query parameters."""
        request = Mock(spec=Request)
        request.args = Mock()
        request.args.get = Mock(side_effect=lambda key, default='': kwargs.get(key, default))
        request.args.to_dict = Mock(return_value=kwargs)
        return request

    def call_endpoint(self, endpoint_func, request):
        """Call an endpoint function and extract the response."""
        app = Flask(__name__)
        with app.test_request_context():
            result = endpoint_func(request)
            # The decorator wraps the response, extract it
            if hasattr(result, 'get_json'):
                response = result.get_json()
                status_code = result.status_code
            else:
                response, status_code = result
            return response, status_code

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    @patch('api.search.fetch_until_enough_results')
    @patch('api.search.get_search_cache_key')
    @patch('api.search.get_cached_search_results')
    @patch('api.search.save_search_results_to_cache')
    def test_search_map_basic(
        self, _mock_save_cache, mock_get_cache, mock_cache_key,
        mock_fetch, mock_headers, mock_credentials
    ):
        """Basic map search without filters."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}
        mock_get_cache.return_value = None  # Cache miss
        mock_cache_key.return_value = 'test_cache_key'

        mock_venues = VenueFactory.create_batch(10)
        mock_fetch.return_value = (mock_venues, 50, False)

        request = self.create_mock_request(
            userId='test_user',
            swLat='40.7',
            swLng='-74.02',
            neLat='40.8',
            neLng='-73.93',
        )

        response, status_code = self.call_endpoint(search_module.search_map, request)

        assert status_code == 200
        assert response['success'] is True
        assert len(response['data']) == 10
        assert 'pagination' in response

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    @patch('api.search.fetch_until_enough_results')
    @patch('api.search.get_search_cache_key')
    @patch('api.search.get_cached_search_results')
    def test_search_map_uses_cache(
        self, mock_get_cache, mock_cache_key,
        mock_fetch, mock_headers, mock_credentials
    ):
        """Map search should use cached results when available."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}
        mock_cache_key.return_value = 'test_cache_key'

        # Return cached data - enough for the requested page (offset=0, perPage=20)
        cached_venues = VenueFactory.create_batch(25)  # More than needed
        formatted_cached = []
        for venue in cached_venues:
            venue_data = venue.get('_source') or venue
            formatted_cached.append({
                'id': (
                    venue_data.get('id', {}).get('resy')
                    if isinstance(venue_data.get('id'), dict)
                    else venue_data.get('id')
                ),
                'name': venue_data.get('name', ''),
                'type': venue_data.get('cuisine', [None])[0] if venue_data.get('cuisine') else '',
                'price_range': venue_data.get('price_range_id', 0),
                'locality': venue_data.get('locality', 'N/A'),
                'region': venue_data.get('region', 'N/A'),
                'neighborhood': venue_data.get('neighborhood', ''),
                'latitude': venue_data.get('_geoloc', {}).get('lat'),
                'longitude': venue_data.get('_geoloc', {}).get('lng'),
                'imageUrl': venue_data.get('images', [None])[0] if venue_data.get('images') else None,
            })
        mock_get_cache.return_value = {
            'results': formatted_cached,
            'total': 50,
            'timestamp': 1000.0
        }

        request = self.create_mock_request(
            userId='test_user',
            swLat='40.7',
            swLng='-74.02',
            neLat='40.8',
            neLng='-73.93',
            offset='0',
            perPage='20',
        )

        response, status_code = self.call_endpoint(search_module.search_map, request)

        assert status_code == 200
        assert response['success'] is True
        assert len(response['data']) == 20  # perPage=20
        # Verify fetch_until_enough_results was not called (cache was sufficient)
        assert mock_fetch.call_count == 0
        # Should not call fetch_until_enough_results when cache hit
        mock_fetch.assert_not_called()

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    @patch('api.search.fetch_until_enough_results')
    @patch('api.search.get_search_cache_key')
    @patch('api.search.get_cached_search_results')
    @patch('api.search.save_search_results_to_cache')
    def test_search_map_available_only(
        self, _mock_save_cache, mock_get_cache, mock_cache_key,
        mock_fetch, mock_headers, mock_credentials
    ):
        """Map search with available_only filter."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}
        mock_get_cache.return_value = None
        mock_cache_key.return_value = 'test_cache_key'

        mock_venues = VenueFactory.create_batch(5)
        # Add availableTimes to mock venues
        for venue in mock_venues:
            venue['availableTimes'] = ['6:00 PM', '7:00 PM']

        mock_fetch.return_value = (mock_venues, 20, False)

        request = self.create_mock_request(
            userId='test_user',
            swLat='40.7',
            swLng='-74.02',
            neLat='40.8',
            neLng='-73.93',
            available_only='true',
            available_day='2026-02-14',
            available_party_size='2',
        )

        response, status_code = self.call_endpoint(search_module.search_map, request)

        assert status_code == 200
        assert response['success'] is True
        assert len(response['data']) == 5
        # Verify fetch_until_enough_results was called with fetch_availability=True
        call_args = mock_fetch.call_args
        assert call_args[1]['fetch_availability'] is True

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    @patch('api.search.fetch_until_enough_results')
    @patch('api.search.get_search_cache_key')
    @patch('api.search.get_cached_search_results')
    @patch('api.search.save_search_results_to_cache')
    def test_search_map_not_released_only(
        self, _mock_save_cache, mock_get_cache, mock_cache_key,
        mock_fetch, mock_headers, mock_credentials
    ):
        """Map search with not_released_only filter."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}
        mock_get_cache.return_value = None
        mock_cache_key.return_value = 'test_cache_key'

        mock_venues = VenueFactory.create_batch(3)
        # Add availabilityStatus to mock venues
        for venue in mock_venues:
            venue['availabilityStatus'] = 'Not released yet'

        mock_fetch.return_value = (mock_venues, 15, False)

        request = self.create_mock_request(
            userId='test_user',
            swLat='40.7',
            swLng='-74.02',
            neLat='40.8',
            neLng='-73.93',
            not_released_only='true',
            available_day='2026-02-14',
            available_party_size='2',
        )

        response, status_code = self.call_endpoint(search_module.search_map, request)

        assert status_code == 200
        assert response['success'] is True
        assert len(response['data']) == 3
        # Verify fetch_until_enough_results was called with fetch_availability=True
        call_args = mock_fetch.call_args
        assert call_args[1]['fetch_availability'] is True

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    @patch('api.search.fetch_until_enough_results')
    @patch('api.search.get_search_cache_key')
    @patch('api.search.get_cached_search_results')
    def test_search_map_pagination_over_filtered(
        self, mock_get_cache, mock_cache_key,
        mock_fetch, mock_headers, mock_credentials
    ):
        """Map search pagination when filtering by availability."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}
        mock_get_cache.return_value = None
        mock_cache_key.return_value = 'test_cache_key'

        # First 20 filtered results
        all_filtered = VenueFactory.create_batch(20)
        for venue in all_filtered:
            venue['availableTimes'] = ['6:00 PM']

        mock_fetch.return_value = (all_filtered, 100, False)

        request = self.create_mock_request(
            userId='test_user',
            swLat='40.7',
            swLng='-74.02',
            neLat='40.8',
            neLng='-73.93',
            available_only='true',
            available_day='2026-02-14',
            available_party_size='2',
            offset='0',
            perPage='20',
        )

        response, status_code = self.call_endpoint(search_module.search_map, request)

        assert status_code == 200
        assert response['success'] is True
        assert len(response['data']) == 20
        # When paginating over filtered results, total should be filtered count
        assert response['pagination']['total'] == 20

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    @patch('api.search.fetch_until_enough_results')
    @patch('api.search.get_search_cache_key')
    @patch('api.search.get_cached_search_results')
    @patch('api.search.update_search_progress')
    def test_search_map_with_job_id(
        self, mock_progress, mock_get_cache, mock_cache_key,
        mock_fetch, mock_headers, mock_credentials
    ):
        """Map search with job ID for progress tracking."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}
        mock_get_cache.return_value = None
        mock_cache_key.return_value = 'test_cache_key'

        mock_venues = VenueFactory.create_batch(10)
        mock_fetch.return_value = (mock_venues, 50, False)

        request = self.create_mock_request(
            userId='test_user',
            jobId='test_job_123',
            swLat='40.7',
            swLng='-74.02',
            neLat='40.8',
            neLng='-73.93',
        )

        _response, status_code = self.call_endpoint(search_module.search_map, request)

        assert status_code == 200
        # Verify progress updates were called
        assert mock_progress.call_count > 0

    @patch('api.search.load_credentials')
    @patch('api.search.get_resy_headers')
    def test_search_map_error_handling(self, mock_headers, mock_credentials):
        """Map search should handle errors gracefully."""
        mock_credentials.return_value = {'api_key': 'test', 'token': 'test'}
        mock_headers.return_value = {'Authorization': 'test'}

        # Simulate error in fetch_until_enough_results
        with patch('api.search.fetch_until_enough_results') as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")

            request = self.create_mock_request(
                userId='test_user',
                swLat='40.7',
                swLng='-74.02',
                neLat='40.8',
                neLng='-73.93',
            )

            response, status_code = self.call_endpoint(search_module.search_map, request)

            assert status_code == 500
            assert response['success'] is False
            assert 'error' in response
