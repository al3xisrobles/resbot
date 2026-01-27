/**
 * Tests for restaurant search API layer.
 * 
 * Tests cover:
 * - searchRestaurantsByMap function
 * - Parameter building and URL construction
 * - Response parsing and error handling
 * - Pagination handling
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { searchRestaurants, searchRestaurantsByMap } from '@/lib/api'
import type { MapSearchFilters, SearchFilters } from '@/lib/interfaces'

// Mock fetch globally
// eslint-disable-next-line @typescript-eslint/no-explicit-any
global.fetch = vi.fn() as any

describe('searchRestaurantsByMap', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    afterEach(() => {
        vi.restoreAllMocks()
    })

    it('should make correct API call with basic parameters', async () => {
        const mockResponse = {
            success: true,
            data: [
                {
                    id: '123',
                    name: 'Test Restaurant',
                    type: 'Italian',
                    price_range: 2,
                    locality: 'New York',
                    region: 'NY',
                    neighborhood: 'Manhattan',
                },
            ],
            pagination: {
                offset: 0,
                perPage: 20,
                nextOffset: 20,
                hasMore: true,
                total: 100,
            },
        }

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ; (global.fetch as any).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            })

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
        }

        const result = await searchRestaurantsByMap('test_user_id', filters)

        expect(global.fetch).toHaveBeenCalledTimes(1)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const callUrl = (global.fetch as any).mock.calls[0][0]
        expect(callUrl).toContain('/search_map')
        expect(callUrl).toContain('userId=test_user_id')
        expect(callUrl).toContain('swLat=40.7')
        expect(callUrl).toContain('swLng=-74.02')
        expect(callUrl).toContain('neLat=40.8')
        expect(callUrl).toContain('neLng=-73.93')

        expect(result.results).toHaveLength(1)
        expect(result.results[0].name).toBe('Test Restaurant')
        expect(result.pagination).toEqual(mockResponse.pagination)
    })

    it('should include cuisine filters in request', async () => {
        const mockResponse = {
            success: true,
            data: [],
            pagination: {
                offset: 0,
                perPage: 20,
                nextOffset: null,
                hasMore: false,
                total: 0,
            },
        }

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ; (global.fetch as any).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            })

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
            cuisines: ['Italian', 'Japanese'],
        }

        await searchRestaurantsByMap('test_user_id', filters)

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const callUrl = (global.fetch as any).mock.calls[0][0]
        expect(callUrl).toContain('cuisines=Italian%2CJapanese')
    })

    it('should include price range filters in request', async () => {
        const mockResponse = {
            success: true,
            data: [],
            pagination: {
                offset: 0,
                perPage: 20,
                nextOffset: null,
                hasMore: false,
                total: 0,
            },
        }

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ; (global.fetch as any).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            })

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
            priceRanges: ['2', '4'],
        }

        await searchRestaurantsByMap('test_user_id', filters)

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const callUrl = (global.fetch as any).mock.calls[0][0]
        expect(callUrl).toContain('priceRanges=2%2C4')
    })

    it('should include pagination parameters', async () => {
        const mockResponse = {
            success: true,
            data: [],
            pagination: {
                offset: 40,
                perPage: 20,
                nextOffset: 60,
                hasMore: true,
                total: 100,
            },
        }

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ; (global.fetch as any).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            })

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
            offset: 40,
            perPage: 20,
        }

        const result = await searchRestaurantsByMap('test_user_id', filters)

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const callUrl = (global.fetch as any).mock.calls[0][0]
        expect(callUrl).toContain('offset=40')
        expect(callUrl).toContain('perPage=20')

        expect(result.pagination.offset).toBe(40)
        expect(result.pagination.hasMore).toBe(true)
    })

    it('should include available_only filter with date and party size', async () => {
        const mockResponse = {
            success: true,
            data: [
                {
                    id: '123',
                    name: 'Available Restaurant',
                    availableTimes: ['6:00 PM', '7:00 PM'],
                },
            ],
            pagination: {
                offset: 0,
                perPage: 20,
                nextOffset: null,
                hasMore: false,
                total: 1,
            },
        }

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ; (global.fetch as any).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            })

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
            availableOnly: true,
            day: '2026-02-14',
            partySize: '2',
        }

        await searchRestaurantsByMap('test_user_id', filters)

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const callUrl = (global.fetch as any).mock.calls[0][0]
        expect(callUrl).toContain('available_only=true')
        expect(callUrl).toContain('available_day=2026-02-14')
        expect(callUrl).toContain('available_party_size=2')
    })

    it('should throw error if available_only without day and party size', async () => {
        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
            availableOnly: true,
            // Missing day and partySize
        }

        await expect(
            searchRestaurantsByMap('test_user_id', filters)
        ).rejects.toThrow('Both day and party_size must be provided')
    })

    it('should include not_released_only filter', async () => {
        const mockResponse = {
            success: true,
            data: [
                {
                    id: '456',
                    name: 'Not Released Restaurant',
                    availabilityStatus: 'Not released yet',
                },
            ],
            pagination: {
                offset: 0,
                perPage: 20,
                nextOffset: null,
                hasMore: false,
                total: 1,
            },
        }

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ; (global.fetch as any).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            })

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
            notReleasedOnly: true,
            day: '2026-02-14',
            partySize: '2',
        }

        await searchRestaurantsByMap('test_user_id', filters)

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const callUrl = (global.fetch as any).mock.calls[0][0]
        expect(callUrl).toContain('not_released_only=true')
        expect(callUrl).toContain('available_day=2026-02-14')
        expect(callUrl).toContain('available_party_size=2')
    })

    it('should throw error if not_released_only without day and party size', async () => {
        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
            notReleasedOnly: true,
            // Missing day and partySize
        }

        await expect(
            searchRestaurantsByMap('test_user_id', filters)
        ).rejects.toThrow('Both day and party_size must be provided')
    })

    it('should include desired_time when availability filters are enabled', async () => {
        const mockResponse = {
            success: true,
            data: [],
            pagination: {
                offset: 0,
                perPage: 20,
                nextOffset: null,
                hasMore: false,
                total: 0,
            },
        }

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ; (global.fetch as any).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            })

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
            availableOnly: true, // Availability filter must be enabled
            day: '2026-02-14',
            partySize: '2',
            desiredTime: '19:00',
        }

        await searchRestaurantsByMap('test_user_id', filters)

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const callUrl = (global.fetch as any).mock.calls[0][0]
        expect(callUrl).toContain('desired_time=19%3A00')
        expect(callUrl).toContain('available_day=2026-02-14')
        expect(callUrl).toContain('available_party_size=2')
    })

    it('should include jobId when provided', async () => {
        const mockResponse = {
            success: true,
            data: [],
            pagination: {
                offset: 0,
                perPage: 20,
                nextOffset: null,
                hasMore: false,
                total: 0,
            },
        }

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ; (global.fetch as any).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            })

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
            jobId: 'test_job_123',
        }

        await searchRestaurantsByMap('test_user_id', filters)

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const callUrl = (global.fetch as any).mock.calls[0][0]
        expect(callUrl).toContain('jobId=test_job_123')
    })

    it('should handle API error responses', async () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ; (global.fetch as any).mockResolvedValueOnce({
            ok: false,
            status: 500,
            json: async () => ({
                success: false,
                error: 'Internal server error',
            }),
        })

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
        }

        await expect(
            searchRestaurantsByMap('test_user_id', filters)
        ).rejects.toThrow('Failed to search restaurants by map')
    })

    it('should handle network errors', async () => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ; (global.fetch as any).mockRejectedValueOnce(new Error('Network error'))

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
        }

        await expect(
            searchRestaurantsByMap('test_user_id', filters)
        ).rejects.toThrow()
    })

    it('should provide default pagination when missing', async () => {
        const mockResponse = {
            success: true,
            data: [],
            // Missing pagination
        }

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ; (global.fetch as any).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            })

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
        }

        const result = await searchRestaurantsByMap('test_user_id', filters)

        expect(result.pagination).toEqual({
            offset: 0,
            perPage: 20,
            nextOffset: null,
            hasMore: false,
        })
    })

    it('should handle empty results array', async () => {
        const mockResponse = {
            success: true,
            data: [],
            pagination: {
                offset: 0,
                perPage: 20,
                nextOffset: null,
                hasMore: false,
                total: 0,
            },
        }

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ; (global.fetch as any).mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            })

        const filters: MapSearchFilters = {
            swLat: 40.7,
            swLng: -74.02,
            neLat: 40.8,
            neLng: -73.93,
        }

        const result = await searchRestaurantsByMap('test_user_id', filters)

        expect(result.results).toEqual([])
        expect(result.pagination.hasMore).toBe(false)
    })

    describe('availability parameter handling', () => {
        /**
         * Issue: Previously, the frontend would send day, partySize, and desiredTime
         * parameters to the backend even when availability filters (availableOnly or
         * notReleasedOnly) were not enabled. This caused the backend to fetch availability
         * for all restaurants, showing "Not released yet" status even when users didn't
         * want to filter by availability.
         *
         * Fix: Only send day, partySize, and desiredTime when availability filters are
         * enabled. This prevents unnecessary availability fetching and ensures restaurants
         * only show availability status when the user explicitly enables those filters.
         */

        it('should NOT send availability params when filters are disabled', async () => {
            const mockResponse = {
                success: true,
                data: [],
                pagination: {
                    offset: 0,
                    perPage: 20,
                    nextOffset: null,
                    hasMore: false,
                    total: 0,
                },
            }

                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                ; (global.fetch as any).mockResolvedValueOnce({
                    ok: true,
                    json: async () => mockResponse,
                })

            const filters: MapSearchFilters = {
                swLat: 40.7,
                swLng: -74.02,
                neLat: 40.8,
                neLng: -73.93,
                // Availability filters are NOT enabled
                availableOnly: false,
                notReleasedOnly: false,
                // But day/partySize/desiredTime are provided
                day: '2026-02-14',
                partySize: '2',
                desiredTime: '19:00',
            }

            await searchRestaurantsByMap('test_user_id', filters)

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const callUrl = (global.fetch as any).mock.calls[0][0]
            // These params should NOT be in the URL
            expect(callUrl).not.toContain('available_day')
            expect(callUrl).not.toContain('available_party_size')
            expect(callUrl).not.toContain('desired_time')
        })

        it('should send availability params when availableOnly is enabled', async () => {
            const mockResponse = {
                success: true,
                data: [],
                pagination: {
                    offset: 0,
                    perPage: 20,
                    nextOffset: null,
                    hasMore: false,
                    total: 0,
                },
            }

                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                ; (global.fetch as any).mockResolvedValueOnce({
                    ok: true,
                    json: async () => mockResponse,
                })

            const filters: MapSearchFilters = {
                swLat: 40.7,
                swLng: -74.02,
                neLat: 40.8,
                neLng: -73.93,
                availableOnly: true, // Filter is enabled
                day: '2026-02-14',
                partySize: '2',
                desiredTime: '19:00',
            }

            await searchRestaurantsByMap('test_user_id', filters)

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const callUrl = (global.fetch as any).mock.calls[0][0]
            // These params SHOULD be in the URL
            expect(callUrl).toContain('available_day=2026-02-14')
            expect(callUrl).toContain('available_party_size=2')
            expect(callUrl).toContain('desired_time=19%3A00')
            expect(callUrl).toContain('available_only=true')
        })

        it('should send availability params when notReleasedOnly is enabled', async () => {
            const mockResponse = {
                success: true,
                data: [],
                pagination: {
                    offset: 0,
                    perPage: 20,
                    nextOffset: null,
                    hasMore: false,
                    total: 0,
                },
            }

                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                ; (global.fetch as any).mockResolvedValueOnce({
                    ok: true,
                    json: async () => mockResponse,
                })

            const filters: MapSearchFilters = {
                swLat: 40.7,
                swLng: -74.02,
                neLat: 40.8,
                neLng: -73.93,
                notReleasedOnly: true, // Filter is enabled
                day: '2026-02-14',
                partySize: '2',
                desiredTime: '19:00',
            }

            await searchRestaurantsByMap('test_user_id', filters)

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const callUrl = (global.fetch as any).mock.calls[0][0]
            // These params SHOULD be in the URL
            expect(callUrl).toContain('available_day=2026-02-14')
            expect(callUrl).toContain('available_party_size=2')
            expect(callUrl).toContain('desired_time=19%3A00')
            expect(callUrl).toContain('not_released_only=true')
        })

        it('should send availability params when both filters are enabled', async () => {
            const mockResponse = {
                success: true,
                data: [],
                pagination: {
                    offset: 0,
                    perPage: 20,
                    nextOffset: null,
                    hasMore: false,
                    total: 0,
                },
            }

                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                ; (global.fetch as any).mockResolvedValueOnce({
                    ok: true,
                    json: async () => mockResponse,
                })

            const filters: MapSearchFilters = {
                swLat: 40.7,
                swLng: -74.02,
                neLat: 40.8,
                neLng: -73.93,
                availableOnly: true,
                notReleasedOnly: true, // Both filters enabled
                day: '2026-02-14',
                partySize: '2',
                desiredTime: '19:00',
            }

            await searchRestaurantsByMap('test_user_id', filters)

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const callUrl = (global.fetch as any).mock.calls[0][0]
            // These params SHOULD be in the URL
            expect(callUrl).toContain('available_day=2026-02-14')
            expect(callUrl).toContain('available_party_size=2')
            expect(callUrl).toContain('desired_time=19%3A00')
        })
    })
})

describe('searchRestaurants', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    afterEach(() => {
        vi.restoreAllMocks()
    })

    describe('availability parameter handling', () => {
        /**
         * Same issue as searchRestaurantsByMap: availability params should only
         * be sent when availability filters are enabled.
         */

        it('should NOT send availability params when filters are disabled', async () => {
            const mockResponse = {
                success: true,
                data: [],
                pagination: {
                    offset: 0,
                    perPage: 20,
                    nextOffset: null,
                    hasMore: false,
                    total: 0,
                },
            }

                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                ; (global.fetch as any).mockResolvedValueOnce({
                    ok: true,
                    json: async () => mockResponse,
                })

            const filters: SearchFilters = {
                query: 'test',
                // Availability filters are NOT enabled
                availableOnly: false,
                notReleasedOnly: false,
                // But day/partySize are provided
                day: '2026-02-14',
                partySize: '2',
            }

            await searchRestaurants('test_user_id', filters)

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const callUrl = (global.fetch as any).mock.calls[0][0]
            // These params should NOT be in the URL
            expect(callUrl).not.toContain('available_day')
            expect(callUrl).not.toContain('available_party_size')
        })

        it('should send availability params when availableOnly is enabled', async () => {
            const mockResponse = {
                success: true,
                data: [],
                pagination: {
                    offset: 0,
                    perPage: 20,
                    nextOffset: null,
                    hasMore: false,
                    total: 0,
                },
            }

                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                ; (global.fetch as any).mockResolvedValueOnce({
                    ok: true,
                    json: async () => mockResponse,
                })

            const filters: SearchFilters = {
                query: 'test',
                availableOnly: true, // Filter is enabled
                day: '2026-02-14',
                partySize: '2',
            }

            await searchRestaurants('test_user_id', filters)

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const callUrl = (global.fetch as any).mock.calls[0][0]
            // These params SHOULD be in the URL
            expect(callUrl).toContain('available_day=2026-02-14')
            expect(callUrl).toContain('available_party_size=2')
            expect(callUrl).toContain('available_only=true')
        })

        it('should send availability params when notReleasedOnly is enabled', async () => {
            const mockResponse = {
                success: true,
                data: [],
                pagination: {
                    offset: 0,
                    perPage: 20,
                    nextOffset: null,
                    hasMore: false,
                    total: 0,
                },
            }

                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                ; (global.fetch as any).mockResolvedValueOnce({
                    ok: true,
                    json: async () => mockResponse,
                })

            const filters: SearchFilters = {
                query: 'test',
                notReleasedOnly: true, // Filter is enabled
                day: '2026-02-14',
                partySize: '2',
            }

            await searchRestaurants('test_user_id', filters)

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const callUrl = (global.fetch as any).mock.calls[0][0]
            // These params SHOULD be in the URL
            expect(callUrl).toContain('available_day=2026-02-14')
            expect(callUrl).toContain('available_party_size=2')
            expect(callUrl).toContain('not_released_only=true')
        })
    })
})
