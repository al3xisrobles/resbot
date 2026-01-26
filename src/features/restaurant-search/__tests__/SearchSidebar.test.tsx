/**
 * Tests for SearchSidebar component.
 * 
 * Tests cover:
 * - Filter interactions
 * - Mode switching (browse, trending, top-rated, bookmarks)
 * - Reservation form updates
 * - Dropdown interactions
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SearchSidebar } from '../components/SearchSidebar'
import type { SearchFilters } from '../lib/types'
import type { SearchResult } from '@/lib/interfaces'

// Mock dependencies
vi.mock('jotai', async (importOriginal) => {
    const actual = await importOriginal<typeof import('jotai')>()
    return {
        ...actual,
        useAtom: vi.fn(() => [
            {
                partySize: '2',
                date: new Date('2026-02-14'),
                timeSlot: '19:00',
            },
            vi.fn(),
        ]),
    }
})

vi.mock('@/components/SearchResultItem', () => ({
    SearchResultItem: ({ name, onCardClick }: any) => (
        <div onClick={() => onCardClick('123')}>{name}</div>
    ),
}))

const mockSearchResults: SearchResult[] = [
    {
        id: '1',
        name: 'Test Restaurant 1',
        type: 'Italian',
        price_range: 2,
        locality: 'New York',
        region: 'NY',
        neighborhood: 'Manhattan',
        availableTimes: ['6:00 PM', '7:00 PM'],
        address: null
    },
    {
        id: '2',
        name: 'Test Restaurant 2',
        type: 'Japanese',
        price_range: 4,
        locality: 'New York',
        region: 'NY',
        neighborhood: 'Brooklyn',
        address: null
    },
]

const defaultProps = {
    filters: {
        query: '',
        cuisines: [],
        priceRanges: [],
        bookmarkedOnly: false,
        availableOnly: false,
        notReleasedOnly: false,
        mode: 'browse' as const,
    },
    setFilters: vi.fn(),
    searchResults: [],
    loading: false,
    hasSearched: false,
    pagination: null,
    currentPage: 1,
    hasNextPage: false,
    inputsHaveChanged: true,
    onSearch: vi.fn(),
    onPageChange: vi.fn(),
    onCardClick: vi.fn(),
    onCardHover: vi.fn(),
    onModeChange: vi.fn(),
}

describe('SearchSidebar', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('should render filter controls', () => {
        render(<SearchSidebar {...defaultProps} />)

        // Check for mode buttons
        expect(screen.getByText('Bookmarks')).toBeInTheDocument()
        expect(screen.getByText('Trending')).toBeInTheDocument()
        expect(screen.getByText('Top Rated')).toBeInTheDocument()
    })

    it('should handle mode switching to bookmarks', () => {
        const setFilters = vi.fn()
        render(<SearchSidebar {...defaultProps} setFilters={setFilters} />)

        const bookmarksButton = screen.getByText('Bookmarks').closest('button')
        fireEvent.click(bookmarksButton!)

        expect(setFilters).toHaveBeenCalledWith(
            expect.objectContaining({
                mode: 'bookmarks',
                bookmarkedOnly: true,
            })
        )
    })

    it('should handle mode switching to trending', () => {
        const setFilters = vi.fn()
        const onModeChange = vi.fn()
        render(
            <SearchSidebar
                {...defaultProps}
                setFilters={setFilters}
                onModeChange={onModeChange}
            />
        )

        const trendingButton = screen.getByText('Trending').closest('button')
        fireEvent.click(trendingButton!)

        expect(setFilters).toHaveBeenCalledWith(
            expect.objectContaining({
                mode: 'trending',
            })
        )
        expect(onModeChange).toHaveBeenCalledWith('trending')
    })

    it('should handle mode switching to top-rated', () => {
        const setFilters = vi.fn()
        const onModeChange = vi.fn()
        render(
            <SearchSidebar
                {...defaultProps}
                setFilters={setFilters}
                onModeChange={onModeChange}
            />
        )

        const topRatedButton = screen.getByText('Top Rated').closest('button')
        fireEvent.click(topRatedButton!)

        expect(setFilters).toHaveBeenCalledWith(
            expect.objectContaining({
                mode: 'top-rated',
            })
        )
        expect(onModeChange).toHaveBeenCalledWith('top-rated')
    })

    it('should toggle available_only filter', () => {
        const setFilters = vi.fn()
        render(<SearchSidebar {...defaultProps} setFilters={setFilters} />)

        // Open availability dropdown
        const availabilityButton = screen.getByText('Availability')
        fireEvent.click(availabilityButton)

        // Click "Available Only" option
        const availableOnlyOption = screen.getByText('Available Only')
        fireEvent.click(availableOnlyOption)

        expect(setFilters).toHaveBeenCalledWith(
            expect.objectContaining({
                availableOnly: true,
                notReleasedOnly: false,
            })
        )
    })

    it('should toggle not_released_only filter', () => {
        const setFilters = vi.fn()
        render(<SearchSidebar {...defaultProps} setFilters={setFilters} />)

        // Open availability dropdown
        const availabilityButton = screen.getByText('Availability')
        fireEvent.click(availabilityButton)

        // Click "Not Released" option
        const notReleasedOption = screen.getByText('Not Released')
        fireEvent.click(notReleasedOption)

        expect(setFilters).toHaveBeenCalledWith(
            expect.objectContaining({
                notReleasedOnly: true,
                availableOnly: false,
            })
        )
    })

    it('should display search results', () => {
        render(
            <SearchSidebar
                {...defaultProps}
                searchResults={mockSearchResults}
                hasSearched={true}
            />
        )

        expect(screen.getByText('Test Restaurant 1')).toBeInTheDocument()
        expect(screen.getByText('Test Restaurant 2')).toBeInTheDocument()
    })

    it('should display loading state', () => {
        render(<SearchSidebar {...defaultProps} loading={true} />)

        expect(screen.getByText('Loading results...')).toBeInTheDocument()
    })

    it('should display no results message', () => {
        render(
            <SearchSidebar
                {...defaultProps}
                searchResults={[]}
                hasSearched={true}
                loading={false}
            />
        )

        expect(
            screen.getByText('No restaurants found. Try a different search.')
        ).toBeInTheDocument()
    })

    it('should display pagination when available', () => {
        const pagination = {
            offset: 0,
            perPage: 20,
            nextOffset: 20,
            hasMore: true,
            total: 50,
        }

        render(
            <SearchSidebar
                {...defaultProps}
                searchResults={mockSearchResults}
                hasSearched={true}
                pagination={pagination}
                currentPage={1}
                hasNextPage={true}
            />
        )

        expect(screen.getByText('Found 50 restaurants')).toBeInTheDocument()
    })

    it('should handle card click', () => {
        const onCardClick = vi.fn()
        render(
            <SearchSidebar
                {...defaultProps}
                searchResults={mockSearchResults}
                hasSearched={true}
                onCardClick={onCardClick}
            />
        )

        const restaurantCard = screen.getByText('Test Restaurant 1')
        fireEvent.click(restaurantCard)

        expect(onCardClick).toHaveBeenCalledWith('1')
    })

    it('should handle page change', () => {
        const onPageChange = vi.fn()
        const pagination = {
            offset: 0,
            perPage: 20,
            nextOffset: 20,
            hasMore: true,
            total: 50,
        }

        render(
            <SearchSidebar
                {...defaultProps}
                searchResults={mockSearchResults}
                hasSearched={true}
                pagination={pagination}
                currentPage={1}
                hasNextPage={true}
                onPageChange={onPageChange}
            />
        )

        // Find and click next page button
        const nextButton = screen.getByLabelText('Go to next page')
        fireEvent.click(nextButton)

        expect(onPageChange).toHaveBeenCalledWith(2)
    })

    it('should show correct availability status', () => {
        const filters: SearchFilters = {
            query: '',
            cuisines: [],
            priceRanges: [],
            bookmarkedOnly: false,
            availableOnly: true,
            notReleasedOnly: false,
            mode: 'browse',
        }

        render(<SearchSidebar {...defaultProps} filters={filters} />)

        const availabilityButton = screen.getByText('Available Only')
        expect(availabilityButton).toBeInTheDocument()
    })

    it('should show correct not released status', () => {
        const filters: SearchFilters = {
            query: '',
            cuisines: [],
            priceRanges: [],
            bookmarkedOnly: false,
            availableOnly: false,
            notReleasedOnly: true,
            mode: 'browse',
        }

        render(<SearchSidebar {...defaultProps} filters={filters} />)

        const availabilityButton = screen.getByText('Not Released')
        expect(availabilityButton).toBeInTheDocument()
    })
})
