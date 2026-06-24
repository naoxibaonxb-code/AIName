<template>
  <view class="page"><view class="safe" />
    <view class="topbar"><view class="back" @tap="back">‹</view><view><text class="eyebrow">ADMIN CONSOLE</text><view class="title">公告配置</view></view><view class="spacer" /></view>
    <view class="content">
      <view class="admin-tabs"><view class="admin-tab" @tap="toUsers">用户管理</view><view class="admin-tab" @tap="toUsage">调用统计</view><view class="admin-tab" @tap="toKnowledge">知识库</view><view class="admin-tab active">公告</view></view>

      <view class="form-card">
        <view class="form-title">发布新公告</view>
        <input v-model.trim="form.title" class="input" maxlength="120" placeholder="公告标题" />
        <textarea v-model.trim="form.content" class="textarea" maxlength="1000" placeholder="公告内容，例如维护时间、额度调整、版本更新说明..." />
        <view class="chips"><view v-for="item in types" :key="item.value" :class="['chip', { active: form.type === item.value }]" @tap="form.type = item.value">{{ item.label }}</view></view>
        <view class="switch-row"><text>发布后立即启用</text><switch :checked="form.is_active" color="#315c4c" @change="form.is_active = $event.detail.value" /></view>
        <button class="create" :disabled="creating" @tap="create">{{ creating ? '发布中' : '发布公告' }}</button>
      </view>

      <view class="list-card">
        <view v-if="loading" class="empty">正在读取公告...</view>
        <view v-else-if="!items.length" class="empty">还没有公告</view>
        <template v-else>
          <view v-for="item in items" :key="item.id" class="notice-row">
            <view class="notice-main">
              <view class="notice-head"><text :class="['type', item.type]">{{ typeLabel(item.type) }}</text><text :class="['state', item.is_active ? 'on' : 'off']">{{ item.is_active ? '已启用' : '已停用' }}</text></view>
              <view class="notice-title">{{ item.title }}</view>
              <view class="notice-content">{{ item.content }}</view>
              <text class="time">{{ formatDate(item.created_at) }}</text>
            </view>
            <view class="actions"><button class="small" :disabled="changingId === item.id" @tap="toggle(item)">{{ item.is_active ? '停用' : '启用' }}</button><button class="small danger" :disabled="changingId === item.id" @tap="remove(item)">删除</button></view>
          </view>
        </template>
      </view>
      <view v-if="totalPages > 1" class="pagination"><button :disabled="page <= 1 || loading" @tap="changePage(-1)">上一页</button><text>{{ page }} / {{ totalPages }}</text><button :disabled="page >= totalPages || loading" @tap="changePage(1)">下一页</button></view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api } from '../../utils/request.js'

const types = [{ label: '普通', value: 'info' }, { label: '通知', value: 'notice' }, { label: '重要', value: 'warning' }]
const form = reactive({ title: '', content: '', type: 'info', is_active: true })
const items = ref([]), total = ref(0), page = ref(1), loading = ref(false), creating = ref(false), changingId = ref(null)
const pageSize = 20
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

onLoad(() => {
  const user = uni.getStorageSync('user') || {}
  if (user.role !== 'admin') {
    uni.showToast({ title: '需要管理员权限', icon: 'none' })
    return setTimeout(() => uni.navigateBack(), 500)
  }
  load()
})
async function load() {
  loading.value = true
  try { const res = await api.adminAnnouncements({ page: page.value, pageSize }); items.value = res.items || []; total.value = res.total || 0 }
  catch (e) { toast(e.message) }
  finally { loading.value = false }
}
async function create() {
  if (!form.title || !form.content) return toast('请填写标题和内容')
  creating.value = true
  try {
    const item = await api.createAnnouncement({ ...form })
    items.value = [item, ...items.value]
    total.value += 1
    form.title = ''
    form.content = ''
    form.type = 'info'
    form.is_active = true
    toast('公告已发布')
  } catch (e) { toast(e.message) }
  finally { creating.value = false }
}
async function toggle(item) {
  changingId.value = item.id
  try {
    const updated = await api.updateAnnouncement(item.id, { is_active: !item.is_active })
    Object.assign(item, updated)
    toast(item.is_active ? '公告已启用' : '公告已停用')
  } catch (e) { toast(e.message) }
  finally { changingId.value = null }
}
function remove(item) {
  uni.showModal({ title: '删除公告', content: `确定删除「${item.title}」吗？`, confirmColor: '#a84f44', success: async ({ confirm }) => {
    if (!confirm) return
    changingId.value = item.id
    try { await api.deleteAnnouncement(item.id); items.value = items.value.filter(row => row.id !== item.id); total.value -= 1; toast('公告已删除') }
    catch (e) { toast(e.message) }
    finally { changingId.value = null }
  } })
}
function changePage(step) { page.value += step; load(); uni.pageScrollTo({ scrollTop: 0, duration: 200 }) }
function typeLabel(value) { return ({ info: '普通', notice: '通知', warning: '重要' })[value] || value }
function formatDate(value) { const d = new Date(value); return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}` }
function toast(title) { uni.showToast({ title, icon: 'none', duration: 2600 }) }
function toUsers() { uni.redirectTo({ url: '/pages/admin/users' }) }
function toUsage() { uni.redirectTo({ url: '/pages/admin/usage' }) }
function toKnowledge() { uni.redirectTo({ url: '/pages/knowledge/manage' }) }
function back() { uni.navigateBack() }
</script>

<style scoped>
.page{min-height:100vh;background:#f4f0e8;color:#29312d}.safe{height:var(--status-bar-height)}.topbar{height:130rpx;display:flex;align-items:center;padding:0 34rpx;border-bottom:1px solid rgba(47,59,51,.1);background:rgba(244,240,232,.94)}.back,.spacer{width:76rpx}.back{font-size:58rpx;color:#315c4c}.topbar>view:nth-child(2){flex:1;text-align:center}.eyebrow{font-size:16rpx;letter-spacing:3rpx;color:#a76d3c}.title{font-size:34rpx;font-weight:650;margin-top:4rpx}.content{box-sizing:border-box;width:100%;max-width:1000px;margin:auto;padding:34rpx 28rpx 70rpx}.admin-tabs{display:flex;padding:7rpx;margin-bottom:24rpx;border-radius:17rpx;background:#e7e5dd}.admin-tab{flex:1;padding:18rpx;text-align:center;border-radius:13rpx;color:#777b75;font-size:24rpx}.admin-tab.active{background:#fff;color:#315c4c;font-weight:650;box-shadow:0 4rpx 16rpx rgba(55,60,53,.07)}.form-card,.list-card{border-radius:24rpx;background:rgba(255,255,255,.78);box-shadow:0 16rpx 50rpx rgba(66,61,50,.07)}.form-card{padding:30rpx;margin-bottom:24rpx}.form-title{font-size:30rpx;font-weight:700;margin-bottom:22rpx}.input,.textarea{box-sizing:border-box;width:100%;background:#f7f5ef;border:1px solid #dedbd2;border-radius:16rpx;font-size:25rpx}.input{height:84rpx;padding:0 22rpx}.textarea{height:180rpx;margin-top:16rpx;padding:22rpx}.chips{display:flex;gap:12rpx;margin:18rpx 0}.chip{padding:13rpx 24rpx;border:1px solid #d9d7cf;border-radius:100rpx;color:#747870;font-size:22rpx}.chip.active{border-color:#315c4c;background:#e4ebe7;color:#315c4c;font-weight:650}.switch-row{display:flex;align-items:center;justify-content:space-between;color:#737770;font-size:23rpx}.create{height:82rpx;line-height:82rpx;margin-top:22rpx;border-radius:16rpx;background:#315c4c;color:#fff;font-size:25rpx}.create[disabled]{background:#8ca097}.list-card{padding:0 28rpx}.notice-row{display:flex;gap:20rpx;padding:30rpx 0;border-bottom:1px solid #e8e5dd}.notice-row:last-child{border-bottom:none}.notice-main{flex:1;min-width:0}.notice-head{display:flex;align-items:center;gap:12rpx}.type,.state{padding:5rpx 13rpx;border-radius:100rpx;font-size:18rpx}.type.info{background:#e4ebe7;color:#315c4c}.type.notice{background:#eee8df;color:#9a6b43}.type.warning{background:#f3dfdb;color:#a04c42}.state.on{background:#e4f0e8;color:#3d7557}.state.off{background:#eee9e5;color:#8f817a}.notice-title{margin-top:14rpx;font-size:29rpx;font-weight:700}.notice-content{margin-top:10rpx;color:#626860;font-size:23rpx;line-height:1.65;word-break:break-all}.time{display:block;margin-top:12rpx;color:#aaa79f;font-size:19rpx}.actions{flex:none;display:flex;flex-direction:column;gap:12rpx}.small{width:108rpx;height:58rpx;line-height:58rpx;margin:0;padding:0;border-radius:13rpx;background:#eef3ef;color:#315c4c;border:1px solid rgba(49,92,76,.18);font-size:21rpx}.small.danger{background:#fff5f1;color:#a84f44;border-color:#e2b8ae}.small[disabled]{opacity:.55}.empty{text-align:center;color:#92938d;padding:100rpx 20rpx;font-size:25rpx}.pagination{display:flex;align-items:center;justify-content:center;gap:22rpx;margin-top:28rpx;color:#777}.pagination button{width:130rpx;height:62rpx;line-height:62rpx;padding:0;border-radius:13rpx;background:#e4ebe7;color:#315c4c;font-size:21rpx}.pagination button[disabled]{color:#aaa;background:#eceae4}@media(max-width:560px){.topbar{height:112rpx;padding:0 20rpx}.back,.spacer{width:58rpx}.title{font-size:30rpx}.content{padding:25rpx 18rpx 60rpx}.admin-tabs{overflow-x:auto}.admin-tab{flex:0 0 150rpx}.form-card{padding:25rpx 22rpx}.list-card{padding:0 22rpx}.notice-row{flex-direction:column}.actions{flex-direction:row}.small{flex:1}}
</style>
