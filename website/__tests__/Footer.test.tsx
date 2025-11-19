/**
 * Unit tests for Footer component (Story 10.1 - TDD)
 *
 * Tests the footer section with links and copyright
 */

import { render, screen } from '@testing-library/react'
import Footer from '@/components/Footer'

describe('Footer Component', () => {
  it('should render the footer element', () => {
    // Arrange & Act
    const { container } = render(<Footer />)

    // Assert
    const footer = container.querySelector('footer')
    expect(footer).toBeInTheDocument()
  })

  it('should display copyright text', () => {
    // Arrange & Act
    render(<Footer />)

    // Assert - Check for copyright notice
    expect(screen.getByText(/© 2025 RGrid/i)).toBeInTheDocument()
  })

  it('should have link to documentation', () => {
    // Arrange & Act
    render(<Footer />)

    // Assert - Check for docs link
    const docsLink = screen.getByRole('link', { name: /docs|documentation/i })
    expect(docsLink).toBeInTheDocument()
  })

  it('should have link to API', () => {
    // Arrange & Act
    render(<Footer />)

    // Assert - Check for API link
    const apiLink = screen.getByRole('link', { name: /api/i })
    expect(apiLink).toBeInTheDocument()
  })

  it('should have link to GitHub', () => {
    // Arrange & Act
    render(<Footer />)

    // Assert - Check for GitHub link
    const githubLink = screen.getByRole('link', { name: /github/i })
    expect(githubLink).toBeInTheDocument()
  })

  it('should display RGrid brand name', () => {
    // Arrange & Act
    render(<Footer />)

    // Assert - Check for brand heading
    expect(screen.getByRole('heading', { name: /^rgrid$/i })).toBeInTheDocument()
  })
})
