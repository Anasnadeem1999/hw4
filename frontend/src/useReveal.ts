import { useEffect } from 'react'

/**
 * Reveals elements marked `data-reveal` as they scroll into view.
 *
 * Uses IntersectionObserver rather than scroll handlers so it costs nothing
 * while idle, and bails out entirely when the visitor has asked for reduced
 * motion — in which case everything is simply visible from the start.
 */
export function useReveal(deps: unknown[] = []) {
  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const nodes = Array.from(document.querySelectorAll('[data-reveal]'))

    if (reduced) {
      nodes.forEach((n) => n.classList.add('is-revealed'))
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-revealed')
            observer.unobserve(entry.target)
          }
        })
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.05 },
    )

    nodes.forEach((n) => {
      if (!n.classList.contains('is-revealed')) observer.observe(n)
    })
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
