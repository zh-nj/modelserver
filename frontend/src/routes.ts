/**
 * Framework7路由配置
 */
import Dashboard from './pages/Dashboard.vue'
import Models from './pages/Models.vue'
import Monitoring from './pages/Monitoring.vue'
import Settings from './pages/Settings.vue'
import Context7 from './pages/Context7.vue'

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
  },
  {
    path: '/context7',
    component: Context7,
    options: {
      transition: 'f7-fade'
    }
  }
]

export default routes