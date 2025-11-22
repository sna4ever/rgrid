export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black text-white">
      {/* Navigation */}
      <nav className="flex justify-between items-center px-8 py-6 max-w-7xl mx-auto">
        <div className="text-2xl font-bold">
          <span className="text-emerald-400">R</span>Grid
        </div>
        <div className="flex gap-6 items-center">
          <a href="#features" className="text-gray-300 hover:text-white transition-colors">
            Features
          </a>
          <a href="https://docs.rgrid.dev" className="text-gray-300 hover:text-white transition-colors">
            Docs
          </a>
          <a
            href="https://app.rgrid.dev/signup"
            className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            Get Started
          </a>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="px-8 py-24 max-w-7xl mx-auto text-center">
        <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
          Run Python scripts remotely.
          <br />
          <span className="text-emerald-400">No infrastructure.</span>
        </h1>
        <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
          Execute your scripts in the cloud without managing servers, containers, or clusters.
          Just run <code className="text-emerald-400 bg-gray-800 px-2 py-1 rounded">rgrid run</code> and go.
        </p>
        <a
          href="https://app.rgrid.dev/signup"
          className="inline-block bg-emerald-500 hover:bg-emerald-600 text-white text-lg px-8 py-4 rounded-lg font-medium transition-colors"
          data-testid="cta-button"
        >
          Get Started
        </a>
      </section>

      {/* Code Example Section */}
      <section className="px-8 py-16 max-w-4xl mx-auto">
        <div className="bg-gray-800 rounded-xl p-8 border border-gray-700">
          <div className="grid md:grid-cols-2 gap-8 items-center">
            <div className="text-center">
              <p className="text-gray-400 mb-3 text-sm uppercase tracking-wide">Before</p>
              <div className="bg-gray-900 rounded-lg p-4 font-mono text-lg">
                <span className="text-gray-400">$</span>{" "}
                <span className="text-white">python script.py</span>
              </div>
              <p className="text-gray-500 mt-2 text-sm">Runs on your machine</p>
            </div>
            <div className="text-center">
              <p className="text-emerald-400 mb-3 text-sm uppercase tracking-wide">After</p>
              <div className="bg-gray-900 rounded-lg p-4 font-mono text-lg border border-emerald-500/30">
                <span className="text-gray-400">$</span>{" "}
                <span className="text-emerald-400">rgrid run</span>{" "}
                <span className="text-white">script.py</span>
              </div>
              <p className="text-gray-500 mt-2 text-sm">Runs in the cloud</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="px-8 py-24 max-w-7xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-16">Why RGrid?</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {/* Simplicity */}
          <div className="bg-gray-800/50 rounded-xl p-8 border border-gray-700">
            <div className="w-12 h-12 bg-emerald-500/20 rounded-lg flex items-center justify-center mb-6">
              <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-3">Simplicity</h3>
            <p className="text-gray-400">
              No Docker, Kubernetes, or cloud configuration. Just add <code className="text-emerald-400">rgrid run</code> before your command.
            </p>
          </div>

          {/* Cost */}
          <div className="bg-gray-800/50 rounded-xl p-8 border border-gray-700">
            <div className="w-12 h-12 bg-emerald-500/20 rounded-lg flex items-center justify-center mb-6">
              <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-3">Cost</h3>
            <p className="text-gray-400">
              Pay only for what you use. Ephemeral compute means no idle resources. Track costs per execution with micron-level precision.
            </p>
          </div>

          {/* Scale */}
          <div className="bg-gray-800/50 rounded-xl p-8 border border-gray-700">
            <div className="w-12 h-12 bg-emerald-500/20 rounded-lg flex items-center justify-center mb-6">
              <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-3">Scale</h3>
            <p className="text-gray-400">
              Run one script or thousands in parallel. Automatic batch processing with <code className="text-emerald-400">--batch</code> flag. No capacity planning needed.
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-8 py-24 max-w-7xl mx-auto text-center">
        <h2 className="text-3xl font-bold mb-6">Ready to run your scripts in the cloud?</h2>
        <p className="text-gray-400 mb-10 max-w-xl mx-auto">
          Get started in minutes. No credit card required for the free tier.
        </p>
        <a
          href="https://app.rgrid.dev/signup"
          className="inline-block bg-emerald-500 hover:bg-emerald-600 text-white text-lg px-8 py-4 rounded-lg font-medium transition-colors"
        >
          Get Started
        </a>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 px-8 py-12">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="text-xl font-bold">
            <span className="text-emerald-400">R</span>Grid
          </div>
          <div className="flex gap-8 text-gray-400">
            <a href="https://docs.rgrid.dev" className="hover:text-white transition-colors">Documentation</a>
            <a href="https://github.com/rgrid" className="hover:text-white transition-colors">GitHub</a>
            <a href="mailto:support@rgrid.dev" className="hover:text-white transition-colors">Support</a>
          </div>
          <p className="text-gray-500 text-sm">&copy; 2024 RGrid. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
