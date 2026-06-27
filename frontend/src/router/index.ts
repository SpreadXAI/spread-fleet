import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory('/spreadfleet/'),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { guest: true } },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { guest: true },
    },
    {
      path: '/admin',
      component: () => import('@/components/AdminLayout.vue'),
      meta: { requiresAuth: true, admin: true },
      children: [
        { path: '', name: 'admin-overview', component: () => import('@/views/admin/AdminOverviewView.vue') },
        { path: 'workspaces', name: 'admin-workspaces', component: () => import('@/views/admin/AdminWorkspacesView.vue') },
        {
          path: 'workspaces/:id',
          name: 'admin-workspace-detail',
          component: () => import('@/views/admin/AdminWorkspaceDetailView.vue'),
        },
        { path: 'plans', name: 'admin-plans', component: () => import('@/views/admin/AdminPlansView.vue') },
      ],
    },
    {
      path: '/',
      component: () => import('@/components/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
        { path: 'team', name: 'team', component: () => import('@/views/TeamView.vue') },
        { path: 'market', name: 'market', component: () => import('@/views/MarketView.vue') },
        { path: 'my-accounts', name: 'my-accounts', component: () => import('@/views/MyAccountsView.vue') },
        {
          path: 'my-accounts/:id',
          name: 'account-detail',
          component: () => import('@/views/AccountDetailView.vue'),
        },
        { path: 'batch-tasks', name: 'batch-tasks', component: () => import('@/views/BatchTasksView.vue') },
        { path: 'logs', name: 'logs', component: () => import('@/views/LogsView.vue') },
        { path: 'profile', name: 'profile', component: () => import('@/views/ProfileView.vue') },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return { name: 'login' }
  if (to.meta.guest && auth.isAuthenticated) return { name: 'dashboard' }
  if (to.meta.admin && !auth.user?.is_admin) return { name: 'dashboard' }
  return true
})

export default router
