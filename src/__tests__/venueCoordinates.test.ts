/**
 * Unit tests for venue coordinate calculation
 * Verifies that venues with known coordinates are correctly positioned on the map
 */

import { describe, it, expect } from 'vitest'

interface SearchResult {
  id: string
  name: string
  latitude?: number | null
  longitude?: number | null
}

/**
 * Calculate venue position from search result
 * Uses real coordinates if available, otherwise falls back to hash-based generation
 */
function calculateVenuePosition(result: SearchResult): [number, number] {
  // Use real coordinates from API if available
  if (result.latitude != null && result.longitude != null) {
    return [result.latitude, result.longitude]
  }

  // Fallback: Generate stable pseudo-random position based on venue ID
  const hash = String(result.id).split('').reduce((acc: number, char: string) => {
    return char.charCodeAt(0) + ((acc << 5) - acc)
  }, 0)

  const latOffset = ((hash % 100) / 100 - 0.5) * 0.05
  const lngOffset = (((hash * 7) % 100) / 100 - 0.5) * 0.05

  return [
    40.7589 + latOffset,
    -73.9851 + lngOffset
  ]
}

describe('Venue Coordinate Calculation', () => {
  it('should use real coordinates for Tacombi - NoLita (ID: 637)', () => {
    // Arrange
    const venue: SearchResult = {
      id: '637',
      name: 'Tacombi - NoLita',
      latitude: 40.724037,
      longitude: -73.993855
    }

    // Act
    const position = calculateVenuePosition(venue)

    // Assert
    expect(position[0]).toBe(40.724037)
    expect(position[1]).toBe(-73.993855)
  })

  it('should use real coordinates for Carne Mare (ID: 55555)', () => {
    // Arrange
    const venue: SearchResult = {
      id: '55555',
      name: 'Carne Mare',
      latitude: 40.706470,
      longitude: -74.003738
    }

    // Act
    const position = calculateVenuePosition(venue)

    // Assert
    expect(position[0]).toBe(40.706470)
    expect(position[1]).toBe(-74.003738)
  })

  it('should generate stable fallback coordinates when real coordinates are null', () => {
    // Arrange
    const venue: SearchResult = {
      id: '12345',
      name: 'Test Restaurant',
      latitude: null,
      longitude: null
    }

    // Act
    const position1 = calculateVenuePosition(venue)
    const position2 = calculateVenuePosition(venue)

    // Assert - should generate same coordinates consistently
    expect(position1).toEqual(position2)

    // Should be within Manhattan bounds (rough check)
    expect(position1[0]).toBeGreaterThan(40.7)
    expect(position1[0]).toBeLessThan(40.8)
    expect(position1[1]).toBeGreaterThan(-74.05)
    expect(position1[1]).toBeLessThan(-73.9)
  })

  it('should generate stable fallback coordinates when real coordinates are undefined', () => {
    // Arrange
    const venue: SearchResult = {
      id: '98765',
      name: 'Another Test Restaurant'
    }

    // Act
    const position1 = calculateVenuePosition(venue)
    const position2 = calculateVenuePosition(venue)

    // Assert - should generate same coordinates consistently
    expect(position1).toEqual(position2)
  })

  it('should generate different coordinates for different venue IDs', () => {
    // Arrange
    const venue1: SearchResult = {
      id: '111',
      name: 'Restaurant One'
    }
    const venue2: SearchResult = {
      id: '222',
      name: 'Restaurant Two'
    }

    // Act
    const position1 = calculateVenuePosition(venue1)
    const position2 = calculateVenuePosition(venue2)

    // Assert - different IDs should generate different positions
    expect(position1).not.toEqual(position2)
  })

  it('should prefer real coordinates even when venue ID would generate different position', () => {
    // Arrange
    const venue: SearchResult = {
      id: '99999',
      name: 'Real Coords Test',
      latitude: 40.750000,
      longitude: -74.000000
    }

    // Act
    const position = calculateVenuePosition(venue)

    // Assert - should use real coordinates, not generated ones
    expect(position[0]).toBe(40.750000)
    expect(position[1]).toBe(-74.000000)
  })
})
