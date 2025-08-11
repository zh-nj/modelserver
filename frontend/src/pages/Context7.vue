<template>
  <f7-page name="context7">
    <f7-navbar title="Context7 检查" />
    <f7-block strong inset>
      <p>如果你能看到这个页面，说明 Framework7 + Router 工作正常。</p>
      <f7-button fill @click="goHome">返回首页</f7-button>
    </f7-block>
  </f7-page>
</template>

<script setup lang="ts">
import { f7 } from 'framework7-vue'

const goHome = () => {
  f7.views.main.router.navigate('/')
}
</script>