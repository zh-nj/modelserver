/**
 * LLM推理服务前端应用程序入口
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Framework7 from 'framework7/lite-bundle'
import Framework7Vue from 'framework7-vue/bundle'
import App from './App.vue'
import routes from './routes'

// Framework7样式
import 'framework7/css/bundle'

// 初始化Framework7-Vue插件
Framework7.use(Framework7Vue)

// Framework7参数
export const f7params = {
  name: 'LLM推理服务',
  theme: 'auto', // 自动检测主题
  colors: {
    primary: '#007aff',
  },
  routes,
  
  // 桌面端配置
  desktop: {
    enabled: true,
    theme: 'desktop',
    width: 1200,
    height: 800,
  },
  
  // 移动端配置
  input: {
    scrollIntoViewOnFocus: true,
  },
  statusbar: {
    iosOverlaysWebView: true,
    androidOverlaysWebView: false,
  },
  
  // 通用配置
  view: {
    pushState: true,
    animate: true,
  },
  
  // 触摸配置
  touch: {
    tapHold: true,
    disableContextMenu: false,
  },
}

// 创建Vue应用
const app = createApp(App)

// 使用Framework7 Vue插件
app.use(Framework7Vue, f7params)

// 使用Pinia状态管理
app.use(createPinia())

// 挂载应用
app.mount('#app')