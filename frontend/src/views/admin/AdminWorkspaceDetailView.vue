<template>
  <div>
    <RouterLink to="/admin/workspaces" class="text-sm text-brand-600 hover:underline">← 返回列表</RouterLink>
    <div v-if="loading" class="mt-4 text-slate-500">加载中…</div>
    <div v-else-if="detail" class="mt-4 space-y-6">
      <div class="card p-6">
        <h2 class="text-lg font-semibold">{{ detail.name }}</h2>
        <p class="mt-2 text-sm text-slate-500">
          所有者用户 ID {{ detail.owner_user_id }} · 创建于 {{ formatTime(detail.created_at) }}
        </p>
        <div class="mt-4 flex flex-wrap items-end gap-3">
          <div>
            <label class="mb-1 block text-xs text-slate-500">分配套餐</label>
            <select v-model="planId" class="input w-48">
              <option v-for="p in plans" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
          <button class="btn-primary" :disabled="saving" @click="assignPlan">保存套餐</button>
        </div>
        <p v-if="msg" class="mt-2 text-sm text-green-600">{{ msg }}</p>
      </div>

      <div class="card p-6">
        <h3 class="mb-3 font-semibold">成员（{{ detail.members.length }}）</h3>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b text-slate-500">
              <th class="pb-2 text-left">邮箱</th>
              <th class="pb-2 text-left">昵称</th>
              <th class="pb-2 text-left">角色</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in detail.members" :key="m.user_id" class="border-b border-slate-100">
              <td class="py-2">{{ m.email }}</td>
              <td>{{ m.display_name || '—' }}</td>
              <td>{{ m.role }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card p-6">
        <h3 class="mb-3 font-semibold">已购账号（{{ detail.accounts.length }}）</h3>
        <div v-if="!detail.accounts.length" class="text-sm text-slate-500">暂无</div>
        <ul v-else class="space-y-2 text-sm">
          <li v-for="a in detail.accounts" :key="a.id">@{{ a.handle }} · {{ a.tier }} · ¥{{ a.price }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { api, type AdminWorkspaceDetail, type WorkspacePlan } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const detail = ref<AdminWorkspaceDetail | null>(null)
const plans = ref<WorkspacePlan[]>([])
const planId = ref<number | null>(null)
const loading = ref(true)
const saving = ref(false)
const msg = ref('')

onMounted(async () => {
  if (!auth.token) return
  const id = Number(route.params.id)
  const [d, p] = await Promise.all([
    api.adminWorkspaceDetail(auth.token, id),
    api.adminPlans(auth.token),
  ])
  detail.value = d
  plans.value = p
  planId.value = d.plan?.id ?? p[0]?.id ?? null
  loading.value = false
})

async function assignPlan() {
  if (!auth.token || !detail.value || !planId.value) return
  saving.value = true
  msg.value = ''
  detail.value = await api.adminAssignPlan(auth.token, detail.value.id, planId.value)
  msg.value = '套餐已更新'
  saving.value = false
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}
</script>
