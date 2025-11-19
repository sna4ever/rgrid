/**
 * Integration tests for Landing Page (Story 10.1)
 *
 * Tests that all components are properly integrated
 */

import { render, screen } from '@testing-library/react'
import Home from '@/app/page'

describe('Landing Page Integration', () => {
  it('should render the complete landing page', () => {
    // Arrange & Act
    render(<Home />)

    // Assert - Check that all major sections are present
    expect(screen.getByRole('heading', { name: /run python scripts remotely/i })).toBeInTheDocument()
  })

  it('should include Hero section with CTA', () => {
    // Arrange & Act
    render(<Home />)

    // Assert
    const ctaButton = screen.getByRole('link', { name: /get started/i })
    expect(ctaButton).toBeInTheDocument()
    expect(ctaButton).toHaveAttribute('href', 'https://app.rgrid.dev/signup')
  })

  it('should include Features section with all three features', () => {
    // Arrange & Act
    render(<Home />)

    // Assert - All three features present as headings
    expect(screen.getByRole('heading', { name: /^simplicity$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^cost$/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /^scale$/i })).toBeInTheDocument()
  })

  it('should include CodeExample section', () => {
    // Arrange & Act
    render(<Home />)

    // Assert - Both commands present
    expect(screen.getByText(/python script\.py/i)).toBeInTheDocument()
    expect(screen.getByText(/rgrid run script\.py/i)).toBeInTheDocument()
  })

  it('should include Footer with links', () => {
    // Arrange & Act
    render(<Home />)

    // Assert
    expect(screen.getByText(/© 2025 RGrid/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /documentation/i })).toBeInTheDocument()
  })
})
