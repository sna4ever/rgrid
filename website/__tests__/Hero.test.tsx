/**
 * Unit tests for Hero component (Story 10.1 - TDD)
 *
 * Acceptance Criteria tested:
 * - AC #4: Hero section shows: "Run Python scripts remotely. No infrastructure."
 * - AC #5: Clear CTA: "Get Started" → https://app.rgrid.dev/signup
 */

import { render, screen } from '@testing-library/react'
import Hero from '@/components/Hero'

describe('Hero Component', () => {
  it('should render the hero heading with value proposition', () => {
    // Arrange & Act
    render(<Hero />)

    // Assert - Check for the main value proposition
    const heading = screen.getByRole('heading', {
      name: /run python scripts remotely/i,
      level: 1
    })
    expect(heading).toBeInTheDocument()
  })

  it('should display "No infrastructure" text', () => {
    // Arrange & Act
    render(<Hero />)

    // Assert - Verify the key message is present
    expect(screen.getByText(/no infrastructure/i)).toBeInTheDocument()
  })

  it('should render a "Get Started" CTA button', () => {
    // Arrange & Act
    render(<Hero />)

    // Assert - Check for CTA button
    const ctaButton = screen.getByRole('link', { name: /get started/i })
    expect(ctaButton).toBeInTheDocument()
  })

  it('should link CTA button to https://app.rgrid.dev/signup', () => {
    // Arrange & Act
    render(<Hero />)

    // Assert - Verify correct URL
    const ctaButton = screen.getByRole('link', { name: /get started/i })
    expect(ctaButton).toHaveAttribute('href', 'https://app.rgrid.dev/signup')
  })

  it('should have descriptive subheading text', () => {
    // Arrange & Act
    render(<Hero />)

    // Assert - Check for supporting text (description)
    const description = screen.getByText(/simple.*command.*remote.*compute/i)
    expect(description).toBeInTheDocument()
  })
})
