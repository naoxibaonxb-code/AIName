<template>
  <view class="page"><view class="safe" />
    <view class="topbar"><view class="back" @tap="back">‹</view><view><text class="eyebrow">ADMIN CONSOLE</text><view class="title">用户管理</view></view><view class="spacer" /></view>
    <view class="content">
      <view class="admin-tabs"><view class="admin-tab active">用户管理</view><view class="admin-tab" @tap="toUsage">调用统计</view><view class="admin-tab" @tap="toKnowledge">知识库</view><view class="admin-tab" @tap="toAnnouncements">公告</view></view>
      <view class="summary"><view><text class="summary-label">普通用户总数</text><view class="count">{{ total }}</view></view><view class="summary-mark">人</view></view>
      <view class="toolbar"><input v-model.trim="search" class="search" confirm-type="search" placeholder="搜索用户名或邮箱" @confirm="doSearch" /><button class="search-btn" @tap="doSearch">搜索</button></view>
      <view class="list-card">
        <view v-if="loading" class="empty">正在加载用户...</view>
        <view v-else-if="!users.length" class="empty">没有找到符合条件的用户</view>
        <template v-else>
          <view v-for="item in users" :key="item.id" class="user-row">
            <view :class="['avatar', { disabled: !item.is_active }]">{{ initial(item.username) }}</view>
            <view class="info"><view class="name-line"><text class="name">{{ item.username }}</text><text :class="['badge', item.is_active ? 'normal' : 'blocked']">{{ item.is_active ? '正常' : '已禁用' }}</text></view><text class="email">{{ item.email }}</text><text class="uid">用户 ID：{{ item.id }}</text></view>
            <button :class="['action', item.is_active ? 'danger' : 'restore']" :disabled="changingId === item.id" @tap="confirmStatus(item)">{{ changingId === item.id ? '处理中' : item.is_active ? '禁用' : '恢复' }}</button>
          </view>
        </template>
      </view>
      <view v-if="totalPages > 1" class="pagination"><button class="page-btn" :disabled="page <= 1 || loading" @tap="changePage(-1)">上一页</button><text>{{ page }} / {{ totalPages }}</text><button class="page-btn" :disabled="page >= totalPages || loading" @tap="changePage(1)">下一页</button></view>
    </view>
  </view>
</template>
<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api } from '../../utils/request.js'
const users = ref([]), search = ref(''), total = ref(0), page = ref(1), loading = ref(false), changingId = ref(null)
const pageSize = 20
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
onLoad(() => {
  const user = uni.getStorageSync('user') || {}
  if (user.role !== 'admin') {
    uni.showToast({ title: '需要管理员权限', icon: 'none' })
    return setTimeout(() => uni.navigateBack(), 500)
  }
  loadUsers()
})
async function loadUsers() {
  loading.value = true
  try { const res = await api.adminUsers({ search: search.value, page: page.value, pageSize }); users.value = res.items || []; total.value = res.total || 0 }
  catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
  finally { loading.value = false }
}
function doSearch() { page.value = 1; loadUsers() }
function changePage(step) { page.value += step; loadUsers(); uni.pageScrollTo({ scrollTop: 0, duration: 200 }) }
function initial(name) { return (name || '用').slice(0, 1).toUpperCase() }
function confirmStatus(item) {
  const next = !item.is_active
  uni.showModal({ title: next ? '恢复用户' : '禁用用户', content: next ? `确定恢复 ${item.username} 的访问权限吗？` : `禁用后，${item.username} 将无法登录或使用起名服务。`, confirmColor: next ? '#315c4c' : '#b55346', success: ({ confirm }) => { if (confirm) updateStatus(item, next) } })
}
async function updateStatus(item, isActive) {
  changingId.value = item.id
  try { const updated = await api.setUserActive(item.id, isActive); item.is_active = updated.is_active; uni.showToast({ title: isActive ? '已恢复用户' : '已禁用用户' }) }
  catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
  finally { changingId.value = null }
}
function back() { uni.navigateBack() }
function toUsage() { uni.redirectTo({ url: '/pages/admin/usage' }) }
function toKnowledge() { uni.navigateTo({ url: '/pages/knowledge/manage' }) }
function toAnnouncements() { uni.redirectTo({ url: '/pages/admin/announcements' }) }
</script>
<style scoped>
.page{min-height:100vh;background:#f4f0e8;color:#29312d}.safe{height:var(--status-bar-height)}.topbar{height:130rpx;display:flex;align-items:center;padding:0 34rpx;border-bottom:1px solid rgba(47,59,51,.1);background:rgba(244,240,232,.94)}.back,.spacer{width:76rpx}.back{font-size:58rpx;color:#315c4c}.topbar>view:nth-child(2){flex:1;text-align:center}.eyebrow{font-size:16rpx;letter-spacing:3rpx;color:#a76d3c}.title{font-size:34rpx;font-weight:650;margin-top:4rpx}.content{padding:34rpx 28rpx 70rpx;max-width:1000rpx;margin:auto}.summary{height:180rpx;padding:0 38rpx;border-radius:26rpx;background:linear-gradient(135deg,#315c4c,#456f5e);color:#fff;display:flex;align-items:center;justify-content:space-between;box-shadow:0 16rpx 36rpx rgba(49,92,76,.2)}.summary-label{font-size:24rpx;color:#dbe7e1}.count{font:600 58rpx serif;margin-top:8rpx}.summary-mark{font:italic 48rpx serif;color:rgba(255,255,255,.28)}.toolbar{display:flex;gap:14rpx;margin:30rpx 0}.search{flex:1;height:86rpx;padding:0 24rpx;background:#fff;border:1px solid #dedbd2;border-radius:16rpx;font-size:25rpx}.search-btn{width:140rpx;height:86rpx;line-height:86rpx;padding:0;border-radius:16rpx;background:#315c4c;color:#fff;font-size:25rpx}.list-card{background:rgba(255,255,255,.78);border-radius:24rpx;padding:0 28rpx;box-shadow:0 16rpx 50rpx rgba(66,61,50,.07)}.user-row{display:flex;align-items:center;gap:22rpx;padding:30rpx 0;border-bottom:1px solid #e8e5dd}.user-row:last-child{border-bottom:none}.avatar{flex:none;width:76rpx;height:76rpx;border-radius:22rpx;background:#e3ece7;color:#315c4c;display:flex;align-items:center;justify-content:center;font-size:30rpx;font-weight:600}.avatar.disabled{background:#eee9e5;color:#9a8278}.info{flex:1;min-width:0}.name-line{display:flex;align-items:center;gap:12rpx}.name{font-size:27rpx;font-weight:650}.badge{padding:4rpx 12rpx;border-radius:100rpx;font-size:18rpx}.badge.normal{background:#e4f0e8;color:#3d7557}.badge.blocked{background:#f4e5e1;color:#a74d42}.email,.uid{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.email{font-size:23rpx;color:#717670;margin-top:8rpx}.uid{font-size:19rpx;color:#aaa79f;margin-top:5rpx}.action{flex:none;width:116rpx;height:68rpx;line-height:68rpx;padding:0;border-radius:14rpx;font-size:22rpx;background:transparent}.action.danger{border:1px solid #dcb6af;color:#a84f44}.action.restore{border:1px solid #aac8b7;color:#397155}.empty{text-align:center;color:#92938d;padding:100rpx 20rpx;font-size:25rpx}.pagination{display:flex;align-items:center;justify-content:center;gap:28rpx;margin-top:32rpx;font-size:23rpx;color:#777}.page-btn{width:150rpx;height:70rpx;line-height:70rpx;padding:0;background:#fff;color:#315c4c;border-radius:14rpx;font-size:22rpx}.page-btn[disabled]{color:#aaa;background:#e8e6df}@media(min-width:700px){.summary{height:140px}.user-row{padding:22px 0}.content{padding-top:28px}}
.content{width:100%;max-width:1000px}.email{overflow-wrap:anywhere}
@media(max-width:480px){.topbar{height:112rpx;padding:0 20rpx}.back,.spacer{width:58rpx}.back{font-size:52rpx}.title{font-size:30rpx}.content{padding:26rpx 18rpx 60rpx}.summary{height:150rpx;padding:0 28rpx;border-radius:22rpx}.count{font-size:48rpx}.toolbar{gap:10rpx;margin:22rpx 0}.search{min-width:0;padding:0 18rpx}.search-btn{width:118rpx}.list-card{padding:0 20rpx}.user-row{align-items:flex-start;flex-wrap:wrap;gap:16rpx}.avatar{width:68rpx;height:68rpx;border-radius:19rpx}.info{flex:1 1 calc(100% - 90rpx)}.name-line{flex-wrap:wrap}.email,.uid{white-space:normal;word-break:break-all}.action{width:calc(100% - 84rpx);margin-left:84rpx;height:62rpx;line-height:62rpx}.pagination{gap:14rpx}.page-btn{width:128rpx}}
@media(max-width:350px){.toolbar{flex-direction:column}.search,.search-btn{width:100%}.search-btn{margin:0}.summary-mark{display:none}.pagination{justify-content:space-between}.page-btn{width:112rpx}}
@media(min-width:768px){.content{padding:28px 28px 60px}.summary{height:150px;padding:0 38px}.list-card{padding:0 32px}.user-row{padding:22px 0}.action{width:88px}}
.admin-tabs{display:flex;padding:7rpx;margin-bottom:24rpx;border-radius:17rpx;background:#e7e5dd}.admin-tab{flex:1;padding:18rpx;text-align:center;border-radius:13rpx;color:#777b75;font-size:24rpx}.admin-tab.active{background:#fff;color:#315c4c;font-weight:650;box-shadow:0 4rpx 16rpx rgba(55,60,53,.07)}
</style>
