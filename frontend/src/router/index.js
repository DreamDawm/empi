import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/config', name: 'Config', component: () => import('../views/Config.vue') },
  { path: '/pending', name: 'Pending', component: () => import('../views/Pending.vue') },
  { path: '/merged', name: 'Merged', component: () => import('../views/Merged.vue') },
  { path: '/patients', name: 'Patients', component: () => import('../views/Patients.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes
})