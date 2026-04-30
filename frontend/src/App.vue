<template>
  <el-config-provider :locale="zhCn">
    <el-container>
      <el-header>
        <h1>EMPI 患者主索引系统</h1>
        <el-menu mode="horizontal" :default-active="$route.path" router>
          <el-menu-item index="/">仪表盘</el-menu-item>
          <el-menu-item index="/config">配置管理</el-menu-item>
          <el-menu-item index="/pending">待审核</el-menu-item>
          <el-menu-item index="/merged">已合并</el-menu-item>
          <el-menu-item index="/patients">患者查询</el-menu-item>
        </el-menu>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-config-provider>
</template>

<script setup>
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import { useRoute } from 'vue-router'

const $route = useRoute()
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.el-header {
  display: flex;
  align-items: center;
  gap: 2rem;
  border-bottom: 1px solid #e0e0e0;
}
.el-header h1 {
  margin: 0;
  font-size: 1.25rem;
}
</style>