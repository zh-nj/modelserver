<template>
  <div id="app">
    <!-- Framework7应用根组件 -->
    <f7-app :params="f7params">
      <!-- 状态栏 -->
      <f7-statusbar />
      
      <!-- 主视图 -->
      <f7-view
        main
        class="safe-areas"
        url="/"
        :browser-history="true"
        :browser-history-separator="'#'"
      />
      
      <!-- 弹出层容器 -->
      <f7-popup />
      <f7-login-screen />
      <f7-popover />
      <f7-actions />
      <f7-sheet />
      <f7-toast />
    </f7-app>
  </div>
</template>

<script setup lang="ts">
import { f7params } from './main'
</script>

<style>
/* 全局样式 */
:root {
  --f7-theme-color: #007aff;
  --f7-theme-color-rgb: 0, 122, 255;
}

/* 安全区域适配 */
.safe-areas {
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left: env(safe-area-inset-left);
  padding-right: env(safe-area-inset-right);
}

/* 桌面端样式 */
@media (min-width: 1024px) {
  .desktop .view-main {
    max-width: 1200px;
    margin: 0 auto;
  }
}

/* 移动端样式 */
@media (max-width: 767px) {
  .mobile .navbar {
    height: 44px;
  }
}
</style>