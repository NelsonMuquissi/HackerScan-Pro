import Link from 'next/link';

/**
 * App Router not-found page.
 * This is a pure Server Component — no hooks, no client state.
 * Providing this prevents Next.js from falling back to the legacy
 * Pages-Router _error.js during static prerendering, which was
 * crashing because of the dual-React-instance issue.
 */
export default function NotFound() {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          background: '#0a0a0a',
          color: '#e5e5e5',
          fontFamily: 'monospace',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <h1 style={{ fontSize: '4rem', color: '#00ff88', marginBottom: '0.5rem' }}>
            404
          </h1>
          <p style={{ color: '#888', marginBottom: '2rem' }}>
            PAGE NOT FOUND — NEURAL LINK BROKEN
          </p>
          <Link
            href="/dashboard"
            style={{
              color: '#00ff88',
              border: '1px solid #00ff88',
              padding: '0.5rem 1.5rem',
              textDecoration: 'none',
              borderRadius: '4px',
            }}
          >
            RETURN TO CONSOLE
          </Link>
        </div>
      </body>
    </html>
  );
}
