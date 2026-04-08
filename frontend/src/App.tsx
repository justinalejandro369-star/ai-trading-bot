/**
 * App is kept as a re-export entry for tests and storybook.
 * Routing and auth session restore happen in main.tsx via RouterProvider.
 */
export { default as Landing } from '@/pages/Landing'
export { default as Login } from '@/pages/Login'
export { default as Dashboard } from '@/pages/Dashboard'
