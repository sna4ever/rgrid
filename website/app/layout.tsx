import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'RGrid - Run Python Scripts Remotely',
  description: 'Run Python scripts remotely. No infrastructure. Simple, cost-effective, and scalable.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
