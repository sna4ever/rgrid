/**
 * Tests for Landing Page (Story 10-1)
 *
 * Verifies acceptance criteria:
 * - Hero section shows: "Run Python scripts remotely. No infrastructure."
 * - CTA: "Get Started" → https://app.rgrid.dev/signup
 * - Features section highlights: Simplicity, Cost, Scale
 * - Code example shows: `python script.py` → `rgrid run script.py`
 */
import { render, screen } from '@testing-library/react'
import Home from '../app/page'

describe('Landing Page', () => {
  beforeEach(() => {
    render(<Home />)
  })

  describe('Hero Section', () => {
    it('displays the main headline', () => {
      expect(screen.getByText('Run Python scripts remotely.')).toBeInTheDocument()
      expect(screen.getByText('No infrastructure.')).toBeInTheDocument()
    })

    it('displays the subheadline with product value', () => {
      expect(screen.getByText(/execute your scripts in the cloud/i)).toBeInTheDocument()
    })
  })

  describe('Call-to-Action', () => {
    it('has Get Started buttons linking to signup', () => {
      const ctaButtons = screen.getAllByRole('link', { name: /get started/i })
      expect(ctaButtons.length).toBeGreaterThanOrEqual(1)

      ctaButtons.forEach((button) => {
        expect(button).toHaveAttribute('href', 'https://app.rgrid.dev/signup')
      })
    })

    it('has a primary CTA in the hero section', () => {
      const primaryCta = screen.getByTestId('cta-button')
      expect(primaryCta).toBeInTheDocument()
      expect(primaryCta).toHaveAttribute('href', 'https://app.rgrid.dev/signup')
    })
  })

  describe('Features Section', () => {
    it('highlights Simplicity feature', () => {
      expect(screen.getByText('Simplicity')).toBeInTheDocument()
      expect(screen.getByText(/no docker, kubernetes/i)).toBeInTheDocument()
    })

    it('highlights Cost feature', () => {
      expect(screen.getByText('Cost')).toBeInTheDocument()
      expect(screen.getByText(/pay only for what you use/i)).toBeInTheDocument()
    })

    it('highlights Scale feature', () => {
      expect(screen.getByText('Scale')).toBeInTheDocument()
      expect(screen.getByText(/run one script or thousands/i)).toBeInTheDocument()
    })
  })

  describe('Code Example', () => {
    it('shows before example: python script.py', () => {
      expect(screen.getByText('python script.py')).toBeInTheDocument()
      expect(screen.getByText('Runs on your machine')).toBeInTheDocument()
    })

    it('shows after example: rgrid run script.py', () => {
      // rgrid run appears multiple times (hero + code example), verify at least one exists
      const rgridRuns = screen.getAllByText('rgrid run')
      expect(rgridRuns.length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('Runs in the cloud')).toBeInTheDocument()
    })

    it('shows before/after labels', () => {
      expect(screen.getByText('Before')).toBeInTheDocument()
      expect(screen.getByText('After')).toBeInTheDocument()
    })
  })

  describe('Navigation', () => {
    it('displays the RGrid logo', () => {
      const logos = screen.getAllByText('Grid')
      expect(logos.length).toBeGreaterThanOrEqual(1)
    })

    it('has link to features section', () => {
      expect(screen.getByRole('link', { name: /features/i })).toHaveAttribute('href', '#features')
    })

    it('has link to documentation', () => {
      expect(screen.getByRole('link', { name: /docs/i })).toHaveAttribute('href', 'https://docs.rgrid.dev')
    })
  })

  describe('Footer', () => {
    it('displays documentation link', () => {
      expect(screen.getByRole('link', { name: /documentation/i })).toHaveAttribute('href', 'https://docs.rgrid.dev')
    })

    it('displays GitHub link', () => {
      expect(screen.getByRole('link', { name: /github/i })).toHaveAttribute('href', 'https://github.com/rgrid')
    })

    it('displays support link', () => {
      expect(screen.getByRole('link', { name: /support/i })).toHaveAttribute('href', 'mailto:support@rgrid.dev')
    })

    it('displays copyright notice', () => {
      expect(screen.getByText(/2024 RGrid/)).toBeInTheDocument()
    })
  })
})
