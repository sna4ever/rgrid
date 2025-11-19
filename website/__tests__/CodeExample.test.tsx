/**
 * Unit tests for CodeExample component (Story 10.1 - TDD)
 *
 * Acceptance Criteria tested:
 * - AC #7: Code example shows: `python script.py` → `rgrid run script.py`
 */

import { render, screen } from '@testing-library/react'
import CodeExample from '@/components/CodeExample'

describe('CodeExample Component', () => {
  it('should render a code example section', () => {
    // Arrange & Act
    render(<CodeExample />)

    // Assert - Check for section heading
    const heading = screen.getByRole('heading', { name: /one command/i })
    expect(heading).toBeInTheDocument()
  })

  it('should display "python script.py" in the before example', () => {
    // Arrange & Act
    render(<CodeExample />)

    // Assert - Check for traditional Python command
    expect(screen.getByText(/python script\.py/i)).toBeInTheDocument()
  })

  it('should display "rgrid run script.py" in the after example', () => {
    // Arrange & Act
    render(<CodeExample />)

    // Assert - Check for RGrid command
    expect(screen.getByText(/rgrid run script\.py/i)).toBeInTheDocument()
  })

  it('should show both before and after examples', () => {
    // Arrange & Act
    render(<CodeExample />)

    // Assert - Verify both commands are present
    const pythonCommand = screen.getByText(/python script\.py/i)
    const rgridCommand = screen.getByText(/rgrid run script\.py/i)

    expect(pythonCommand).toBeInTheDocument()
    expect(rgridCommand).toBeInTheDocument()
  })

  it('should have labels for before and after sections', () => {
    // Arrange & Act
    render(<CodeExample />)

    // Assert - Check for descriptive labels
    expect(screen.getByText(/before \(local\)/i)).toBeInTheDocument()
    expect(screen.getByText(/after \(with rgrid\)/i)).toBeInTheDocument()
  })

  it('should use code blocks for displaying commands', () => {
    // Arrange & Act
    const { container } = render(<CodeExample />)

    // Assert - Check that code elements exist
    const codeElements = container.querySelectorAll('code')
    expect(codeElements.length).toBeGreaterThanOrEqual(2) // At least 2 code blocks
  })
})
