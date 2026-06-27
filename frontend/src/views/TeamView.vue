<template>
  <div>
    <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="text-sm text-slate-500">当前团队空间内的成员共享账号、任务与执行日志</p>
      </div>
      <div class="flex items-center gap-2">
        <label class="text-sm text-slate-600">切换空间</label>
        <select v-model="selectedId" class="input w-48" @change="onSwitch">
          <option v-for="w in workspaces" :key="w.id" :value="w.id">{{ w.name }}</option>
        </select>
      </div>
    </div>

    <div class="grid gap-6 lg:grid-cols-2">
      <div class="card space-y-4 p-6">
        <h2 class="font-semibold">空间信息</h2>
        <dl v-if="current" class="space-y-2 text-sm">
          <div class="flex justify-between"><dt class="text-slate-500">名称</dt><dd>{{ current.name }}</dd></div>
          <div class="flex justify-between"><dt class="text-slate-500">成员</dt><dd>{{ current.member_count }}</dd></div>
          <div class="flex justify-between"><dt class="text-slate-500">已购账号</dt><dd>{{ current.account_count }}</dd></div>
          <div class="flex justify-between">
            <dt class="text-slate-500">套餐</dt>
            <dd>{{ current.plan?.name ?? '未分配套餐' }}</dd>
          </div>
        </dl>
      </div>

      <div class="card space-y-4 p-6">
        <h2 class="font-semibold">邀请成员</h2>
        <p class="text-sm text-slate-500">输入对方邮箱，已注册用户将立即加入；未注册用户注册后自动加入。</p>
        <form class="flex gap-2" @submit.prevent="invite">
          <input v-model="inviteEmail" class="input flex-1" type="email" placeholder="colleague@company.com" required />
          <button class="btn-primary shrink-0" type="submit" :disabled="inviting">邀请</button>
        </form>
        <p v-if="inviteMsg" class="text-sm" :class="inviteOk ? 'text-green-600' : 'text-red-600'">{{ inviteMsg }}</p>
      </div>
    </div>

    <div class="card mt-6 p-6">
      <h2 class="mb-4 font-semibold">成员列表</h2>
      <div v-if="loading" class="text-slate-500">加载中…</div>
      <table v-else class="w-full text-left text-sm">
        <thead>
          <tr class="border-b text-slate-500">
            <th class="pb-2">邮箱</th>
            <th class="pb-2">昵称</th>
            <th class="pb-2">角色</th>
            <th class="pb-2">加入时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in members" :key="m.user_id" class="border-b border-slate-100">
            <td class="py-3">{{ m.email }}</td>
            <td>{{ m.display_name || '—' }}</td>
            <td><span class="badge bg-slate-100 text-slate-700">{{ m.role === 'owner' ? '所有者' : '成员' }}</span></td>
            <td class="text-slate-500">{{ formatTime(m.joined_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Workspace, type WorkspaceMember } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const workspaces = ref<Workspace[]>([])
const current = ref<Workspace | null>(null)
const members = ref<WorkspaceMember[]>([])
const selectedId = ref<number | null>(null)
const inviteEmail = ref('')
const inviting = ref(false)
const inviteMsg = ref('')
const inviteOk = ref(true)
const loading = ref(true)

async function load() {
  if (!auth.token) return
  loading.value = true
  workspaces.value = await api.listWorkspaces(auth.token)
  current.value = await api.currentWorkspace(auth.token)
  selectedId.value = current.value.id
  members.value = await api.workspaceMembers(auth.token)
  loading.value = false
}

async function onSwitch() {
  if (!auth.token || !selectedId.value) return
  current.value = await api.switchWorkspace(auth.token, selectedId.value)
  const me = await api.me(auth.token)
  auth.user = me
  localStorage.setItem('spider_radar_user', JSON.stringify(me))
  members.value = await api.workspaceMembers(auth.token)
}

async function invite() {
  if (!auth.token) return
  inviting.value = true
  inviteMsg.value = ''
  try {
    await api.inviteMember(auth.token, inviteEmail.value)
    inviteMsg.value = '邀请已发送'
    inviteOk.value = true
    inviteEmail.value = ''
    members.value = await api.workspaceMembers(auth.token)
    current.value = await api.currentWorkspace(auth.token)
  } catch (e) {
    inviteMsg.value = e instanceof Error ? e.message : '邀请失败'
    inviteOk.value = false
  } finally {
    inviting.value = false
  }
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(load)
</script>
