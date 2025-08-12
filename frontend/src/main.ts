/**
 * LLM推理服务前端应用程序入口
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Framework7 from 'framework7/lite-bundle'
import Framework7Vue, { f7ready } from 'framework7-vue/bundle'
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
const vueApp = app.mount('#app')

// 将Framework7实例暴露到全局作用域，以便在index.html中访问
declare global {
  interface Window {
    f7: any;
    vueApp: any;
  }
}

// 直接创建Framework7实例并暴露到全局作用域
const f7Instance = new Framework7(f7params);
window.f7 = f7Instance;
window.vueApp = vueApp;
console.log('Framework7实例已直接创建并暴露到全局作用域');

// 备用方案：通过Vue mixin确保实例可用
app.mixin({
  mounted() {
    if ((this as any).$f7 && !window.f7) {
      window.f7 = (this as any).$f7;
      console.log('Framework7实例通过Vue mixin暴露到全局作用域');
    }
  }
});