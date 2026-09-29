import { useState, useEffect } from 'react'

const systemLight = window.matchMedia('(prefers-color-scheme: light)')

function savedTheme() {
  try {
    return localStorage.getItem('theme')
  } catch {
    return null
  }
}

// Light/dark switch. index.html sets the starting theme; a click saves the choice, and
// until then the page keeps following the system setting.
export default function ThemeToggle() {
  const [theme, setTheme] = useState(document.documentElement.dataset.theme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => {
    const follow = e => {
      if (!savedTheme()) setTheme(e.matches ? 'light' : 'dark')
    }
    systemLight.addEventListener('change', follow)
    return () => systemLight.removeEventListener('change', follow)
  }, [])

  const next = theme === 'light' ? 'dark' : 'light'
  const toggle = () => {
    try {
      localStorage.setItem('theme', next)
    } catch {
      // Private mode: the choice lasts until reload
    }
    setTheme(next)
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
    >
      {theme === 'light' ? (
        // Moon
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      ) : (
        // Sun
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      )}
    </button>
  )
}
