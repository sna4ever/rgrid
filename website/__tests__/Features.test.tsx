/**
 * Unit tests for Features component (Story 10.1 - TDD)
 *
 * Acceptance Criteria tested:
 * - AC #6: Features section highlights: Simplicity, Cost, Scale
 */

import { render, screen } from '@testing-library/react'
import Features from '@/components/Features'

describe('Features Component', () => {
  it('should render a features section heading', () => {
    // Arrange & Act
    render(<Features />)

    // Assert - Check for section heading
    const heading = screen.getByRole('heading', { name: /features|why/i })
    expect(heading).toBeInTheDocument()
  })

  it('should display "Simplicity" feature card', () => {
    // Arrange & Act
    render(<Features />)

    // Assert - Check for Simplicity feature
    expect(screen.getByText(/simplicity/i)).toBeInTheDocument()
  })

  it('should display "Cost" feature card', () => {
    // Arrange & Act
    render(<Features />)

    // Assert - Check for Cost feature heading
    expect(screen.getByRole('heading', { name: /^cost$/i })).toBeInTheDocument()
  })

  it('should display "Scale" feature card', () => {
    // Arrange & Act
    render(<Features />)

    // Assert - Check for Scale feature heading
    expect(screen.getByRole('heading', { name: /^scale$/i })).toBeInTheDocument()
  })

  it('should display all three features (Simplicity, Cost, Scale)', () => {
    // Arrange & Act
    render(<Features />)

    // Assert - Verify all three features are present as headings
    const simplicityFeature = screen.getByRole('heading', { name: /^simplicity$/i })
    const costFeature = screen.getByRole('heading', { name: /^cost$/i })
    const scaleFeature = screen.getByRole('heading', { name: /^scale$/i })

    expect(simplicityFeature).toBeInTheDocument()
    expect(costFeature).toBeInTheDocument()
    expect(scaleFeature).toBeInTheDocument()
  })

  it('should have descriptive text for each feature', () => {
    // Arrange & Act
    render(<Features />)

    // Assert - Check that each feature has supporting description text
    // We'll verify by checking parent elements have sufficient content
    const features = screen.getAllByRole('article')
    expect(features).toHaveLength(3)

    features.forEach(feature => {
      // Each feature should have a heading and description
      expect(feature.textContent).not.toBe('')
      expect(feature.textContent!.length).toBeGreaterThan(20) // Meaningful content
    })
  })
})
