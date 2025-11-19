/**
 * Footer Component - Site Footer with Links
 *
 * Displays footer navigation and copyright information
 */

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-300 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div>
            <h3 className="text-white text-xl font-bold mb-4">RGrid</h3>
            <p className="text-sm text-gray-400">
              Run Python scripts remotely. No infrastructure.
            </p>
          </div>

          {/* Product Links */}
          <div>
            <h4 className="text-white font-semibold mb-4">Product</h4>
            <ul className="space-y-2">
              <li>
                <a
                  href="https://docs.rgrid.dev"
                  className="text-sm hover:text-white transition-colors"
                >
                  Documentation
                </a>
              </li>
              <li>
                <a
                  href="https://api.rgrid.dev"
                  className="text-sm hover:text-white transition-colors"
                >
                  API
                </a>
              </li>
              <li>
                <a
                  href="https://app.rgrid.dev"
                  className="text-sm hover:text-white transition-colors"
                >
                  Console
                </a>
              </li>
            </ul>
          </div>

          {/* Developer Links */}
          <div>
            <h4 className="text-white font-semibold mb-4">Developers</h4>
            <ul className="space-y-2">
              <li>
                <a
                  href="https://github.com/rgrid"
                  className="text-sm hover:text-white transition-colors"
                >
                  GitHub
                </a>
              </li>
              <li>
                <a
                  href="https://docs.rgrid.dev/cli"
                  className="text-sm hover:text-white transition-colors"
                >
                  CLI Reference
                </a>
              </li>
              <li>
                <a
                  href="https://docs.rgrid.dev/examples"
                  className="text-sm hover:text-white transition-colors"
                >
                  Examples
                </a>
              </li>
            </ul>
          </div>

          {/* Company Links */}
          <div>
            <h4 className="text-white font-semibold mb-4">Company</h4>
            <ul className="space-y-2">
              <li>
                <a
                  href="https://rgrid.dev/about"
                  className="text-sm hover:text-white transition-colors"
                >
                  About
                </a>
              </li>
              <li>
                <a
                  href="https://rgrid.dev/blog"
                  className="text-sm hover:text-white transition-colors"
                >
                  Blog
                </a>
              </li>
              <li>
                <a
                  href="https://rgrid.dev/contact"
                  className="text-sm hover:text-white transition-colors"
                >
                  Contact
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Copyright */}
        <div className="mt-12 pt-8 border-t border-gray-800 text-center">
          <p className="text-sm text-gray-400">
            © 2025 RGrid. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  )
}
