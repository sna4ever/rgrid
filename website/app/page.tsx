/**
 * Landing Page - RGrid Marketing Website
 *
 * Story 10.1: Build Marketing Website Landing Page
 * Acceptance Criteria: All ACs met (#1-7)
 */

import Hero from '@/components/Hero'
import Features from '@/components/Features'
import CodeExample from '@/components/CodeExample'
import Footer from '@/components/Footer'

export default function Home() {
  return (
    <main className="min-h-screen">
      <Hero />
      <Features />
      <CodeExample />
      <Footer />
    </main>
  )
}
