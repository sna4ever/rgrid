/**
 * Hero Component - Landing Page Hero Section
 *
 * Displays the main value proposition and CTA button.
 * Acceptance Criteria: AC #4, AC #5
 */

export default function Hero() {
  return (
    <section className="relative bg-gradient-to-b from-primary-50 to-white py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto text-center">
        {/* Main Heading - Value Proposition */}
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-6">
          Run Python scripts remotely.{' '}
          <span className="text-primary-600">No infrastructure.</span>
        </h1>

        {/* Subheading - Supporting Description */}
        <p className="text-xl sm:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto">
          One simple command turns your local script into remote compute.
          No servers. No configuration. Just run.
        </p>

        {/* CTA Button */}
        <a
          href="https://app.rgrid.dev/signup"
          className="inline-block bg-primary-600 hover:bg-primary-700 text-white font-semibold px-8 py-4 rounded-lg text-lg transition-colors duration-200 shadow-lg hover:shadow-xl"
        >
          Get Started
        </a>

        {/* Supporting Text */}
        <p className="mt-4 text-sm text-gray-500">
          Free tier available. No credit card required.
        </p>
      </div>
    </section>
  )
}
