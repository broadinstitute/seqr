const env = process.env.NODE_ENV || 'development'

export const computeDashboardUrl = () => (
  env === 'development' ?
    '/dashboard.html' :
    '/dashboard'
)

