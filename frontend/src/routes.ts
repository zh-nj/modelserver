/**
 * Framework7路由配置
 */
import Dashboard from './pages/Dashboard.vue'
import Models from './pages/Models.vue'
import Monitoring from './pages/Monitoring.vue'
import Settings from './pages/Settings.vue'

const routes = [
  {
    path: '/',
    component: Dashboard,
    options: {
      transition: 'f7-cover'
    }
  },
  {
    path: '/models',
    component: Models,
    options: {
      transition: 'f7-cover'
    }
  },
  {
    path: '/monitoring',
    component: Monitoring,
    options: {
      transition: 'f7-cover'
    }
  },
  {
    path: '/settings',
    component: Settings,
    options: {
      transition: 'f7-cover'
    }
  }
]

export default routes