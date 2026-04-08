import { createBrowserRouter, Navigate } from 'react-router-dom'
import Landing from '@/pages/Landing'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import PrivateRoute from '@/router/PrivateRoute'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Landing />,
  },
  {
    path: '/login',
    element: <Login />,
  },
  {
    element: <PrivateRoute />,
    children: [
      {
        path: '/dashboard',
        element: <Dashboard />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
])
