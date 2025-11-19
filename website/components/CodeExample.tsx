/**
 * CodeExample Component - Shows Before/After Code Comparison
 *
 * Displays traditional Python command vs. RGrid command
 * Acceptance Criteria: AC #7
 */

export default function CodeExample() {
  return (
    <section className="py-16 px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="max-w-4xl mx-auto">
        {/* Section Heading */}
        <h2 className="text-3xl sm:text-4xl font-bold text-center text-gray-900 mb-12">
          One Command. Infinite Compute.
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Before: Traditional Python */}
          <div className="bg-white rounded-lg p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-500 uppercase mb-3">
              Before (Local)
            </h3>
            <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm overflow-x-auto">
              <code>$ python script.py</code>
            </div>
            <p className="mt-3 text-sm text-gray-600">
              Runs on your laptop. Limited by your hardware.
            </p>
          </div>

          {/* After: With RGrid */}
          <div className="bg-white rounded-lg p-6 shadow-sm ring-2 ring-primary-500">
            <h3 className="text-sm font-semibold text-primary-600 uppercase mb-3">
              After (With RGrid)
            </h3>
            <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm overflow-x-auto">
              <code>$ rgrid run script.py</code>
            </div>
            <p className="mt-3 text-sm text-gray-600">
              Runs remotely on ephemeral compute. Scale instantly.
            </p>
          </div>
        </div>

        {/* Additional Benefits */}
        <div className="mt-8 text-center">
          <p className="text-gray-600">
            Same script. Same syntax. Zero infrastructure. That's RGrid.
          </p>
        </div>
      </div>
    </section>
  )
}
