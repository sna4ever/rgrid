/**
 * Features Component - Highlights Key Benefits
 *
 * Displays three main features: Simplicity, Cost, Scale
 * Acceptance Criteria: AC #6
 */

export default function Features() {
  const features = [
    {
      title: 'Simplicity',
      description:
        'One command transforms your local script into a remote job. No Docker, no YAML, no infrastructure to manage.',
      icon: '⚡',
    },
    {
      title: 'Cost',
      description:
        'Pay only for execution time. No idle servers, no monthly fees. Typical job costs under $0.01.',
      icon: '💰',
    },
    {
      title: 'Scale',
      description:
        'Run 1 job or 1,000 jobs. We provision workers on-demand and clean up automatically. Infinite scale, zero maintenance.',
      icon: '📈',
    },
  ]

  return (
    <section className="py-16 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-6xl mx-auto">
        {/* Section Heading */}
        <h2 className="text-3xl sm:text-4xl font-bold text-center text-gray-900 mb-12">
          Why RGrid?
        </h2>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {features.map((feature) => (
            <article
              key={feature.title}
              className="bg-gray-50 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Icon */}
              <div className="text-4xl mb-4">{feature.icon}</div>

              {/* Title */}
              <h3 className="text-xl font-semibold text-gray-900 mb-3">
                {feature.title}
              </h3>

              {/* Description */}
              <p className="text-gray-600 leading-relaxed">{feature.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
