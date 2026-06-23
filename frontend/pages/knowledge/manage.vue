<template>
  <view class="page"><view class="safe" />
    <view class="topbar"><view class="back" @tap="back">‹</view><view><text class="eyebrow">KNOWLEDGE BASE</text><view class="title">知识库管理</view></view><view class="spacer" /></view>
    <view class="content">
      <view class="overview">
        <view><text class="overview-label">我的私有知识库</text><view class="overview-num">{{ stats.private_ready }} / {{ stats.private_total }}</view><text class="overview-tip">仅自己起企业名时参考</text></view>
        <view><text class="overview-label">平台公共知识库</text><view class="overview-num">{{ stats.public_ready }} / {{ stats.public_total }}</view><text class="overview-tip">所有用户都可参考</text></view>
      </view>

      <view class="tabs">
        <view :class="['tab', { active: scope === 'private' }]" @tap="switchScope('private')">私有知识库</view>
        <view :class="['tab', { active: scope === 'public' }]" @tap="switchScope('public')">公共知识库</view>
      </view>

      <view class="toolbar">
        <view><text class="section-title">{{ scope === 'private' ? '我的资料' : '平台资料' }}</text><text class="section-sub">{{ scope === 'private' ? '品牌资料、产品介绍、行业偏好都可以放在这里' : '公共规则由管理员维护，会被所有企业起名请求参考' }}</text></view>
        <button v-if="canUpload" class="upload" :disabled="uploading" @tap="chooseFile">{{ uploading ? `${uploadProgress}%` : '上传文件' }}</button>
      </view>

      <view class="file-panel">
        <view v-if="loading" class="empty">正在读取知识库...</view>
        <view v-else-if="!files.length" class="empty">{{ scope === 'private' ? '还没有上传私有知识库' : '暂无平台公共知识库' }}</view>
        <template v-else>
          <view v-for="item in files" :key="item.id" class="file-card">
            <view class="file-icon">{{ suffix(item.original_name) }}</view>
            <view class="file-main">
              <view class="file-head"><text class="file-name">{{ item.original_name }}</text><text :class="['status', item.status, { off: !item.is_enabled }]">{{ statusText(item) }}</text></view>
              <view class="meta"><text>{{ formatSize(item.file_size) }}</text><text>{{ item.chunk_count }} 个片段</text><text>{{ formatDate(item.uploaded_at) }}</text></view>
              <text v-if="item.error_message" class="error">{{ item.error_message }}</text>
              <view class="actions">
                <button class="small" :disabled="changingId === item.id || item.status === 'processing'" @tap="toggleFile(item)">{{ item.is_enabled ? '停用' : '启用' }}</button>
                <button class="small danger" :disabled="changingId === item.id" @tap="confirmDelete(item)">删除</button>
              </view>
            </view>
          </view>
        </template>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { api } from '../../utils/request.js'

const scope = ref('private'), files = ref([]), loading = ref(false), uploading = ref(false), uploadProgress = ref(0), changingId = ref(null)
const stats = reactive({ private_total: 0, private_ready: 0, public_total: 0, public_ready: 0 })
const user = ref({})
const canUpload = computed(() => scope.value === 'private' || user.value.role === 'admin')

onLoad(() => {
  const token = uni.getStorageSync('token')
  if (!token) return uni.reLaunch({ url: '/pages/login/login' })
  user.value = uni.getStorageSync('user') || {}
})
onShow(() => { loadAll() })

async function loadAll() {
  await Promise.all([loadStats(), loadFiles()])
}
async function loadStats() {
  try { Object.assign(stats, await api.knowledgeStats()) }
  catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
}
async function loadFiles() {
  loading.value = true
  try { files.value = await api.knowledgeFiles(scope.value) }
  catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
  finally { loading.value = false }
}
function switchScope(next) {
  if (scope.value === next) return
  scope.value = next
  loadFiles()
}
function chooseFile() {
  const choose = uni.chooseFile
    ? options => uni.chooseFile(options)
    : uni.chooseMessageFile
      ? options => uni.chooseMessageFile(options)
      : null
  if (!choose) return uni.showToast({ title: '当前设备暂不支持文件选择', icon: 'none' })
  choose({ count: 1, type: 'file', extension: ['pdf', 'txt'], success: uploadSelectedFile })
}
async function uploadSelectedFile(result) {
  const selected = result.tempFiles?.[0]
  const filePath = selected?.path || result.tempFilePaths?.[0]
  const fileName = selected?.name || filePath?.split(/[\\/]/).pop() || ''
  if (!filePath) return
  if (!/\.(pdf|txt)$/i.test(fileName)) return uni.showToast({ title: '仅支持 PDF 和 TXT 文件', icon: 'none' })
  if (selected?.size > 10 * 1024 * 1024) return uni.showToast({ title: '文件不能超过 10MB', icon: 'none' })
  uploading.value = true
  uploadProgress.value = 0
  try {
    const file = await api.uploadKnowledge(filePath, progress => { uploadProgress.value = progress }, scope.value)
    files.value = [file, ...files.value]
    uni.showToast({ title: '上传成功，正在解析' })
    setTimeout(loadAll, 2000)
  } catch (e) { uni.showToast({ title: e.message, icon: 'none', duration: 3000 }) }
  finally { uploading.value = false; uploadProgress.value = 0 }
}
async function toggleFile(item) {
  changingId.value = item.id
  try {
    const updated = await api.updateKnowledgeFile(item.id, { is_enabled: !item.is_enabled })
    Object.assign(item, updated)
    uni.showToast({ title: item.is_enabled ? '已启用' : '已停用' })
    loadStats()
  } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
  finally { changingId.value = null }
}
function confirmDelete(item) {
  uni.showModal({ title: '删除知识库文件', content: `确定删除「${item.original_name}」吗？删除后将不再参与起名参考。`, confirmColor: '#b55346', success: ({ confirm }) => { if (confirm) deleteFile(item) } })
}
async function deleteFile(item) {
  changingId.value = item.id
  try {
    await api.deleteKnowledgeFile(item.id)
    files.value = files.value.filter(file => file.id !== item.id)
    uni.showToast({ title: '已删除' })
    loadStats()
  } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
  finally { changingId.value = null }
}
function statusText(item) {
  if (!item.is_enabled) return '已停用'
  return ({ pending: '等待解析', processing: '解析中', ready: '可使用', failed: '解析失败' })[item.status] || item.status
}
function suffix(name) { return (name.split('.').pop() || 'FILE').slice(0, 4).toUpperCase() }
function formatSize(size = 0) {
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`
  if (size >= 1024) return `${Math.ceil(size / 1024)} KB`
  return `${size || 0} B`
}
function formatDate(value) { return value ? String(value).slice(0, 10) : '-' }
function back() { uni.navigateBack() }
</script>

<style scoped>
.page{min-height:100vh;background:#f4f0e8;color:#29312d}.safe{height:var(--status-bar-height)}.topbar{height:130rpx;display:flex;align-items:center;padding:0 34rpx;border-bottom:1px solid rgba(47,59,51,.1);background:rgba(244,240,232,.94)}.back,.spacer{width:76rpx}.back{font-size:58rpx;color:#315c4c}.topbar>view:nth-child(2){flex:1;text-align:center}.eyebrow{font-size:16rpx;letter-spacing:3rpx;color:#a76d3c}.title{font-size:34rpx;font-weight:650;margin-top:4rpx}.content{width:100%;max-width:1000px;margin:auto;padding:34rpx 28rpx 70rpx;box-sizing:border-box}.overview{display:grid;grid-template-columns:1fr 1fr;gap:18rpx}.overview>view{padding:30rpx;border-radius:24rpx;background:linear-gradient(135deg,#315c4c,#4b7564);color:#fff;box-shadow:0 16rpx 36rpx rgba(49,92,76,.18)}.overview>view:nth-child(2){background:linear-gradient(135deg,#8f623f,#b1784f)}.overview-label,.overview-tip{display:block}.overview-label{font-size:22rpx;color:rgba(255,255,255,.82)}.overview-num{font:600 52rpx serif;margin:10rpx 0 4rpx}.overview-tip{font-size:19rpx;color:rgba(255,255,255,.65)}.tabs{display:flex;padding:7rpx;margin:28rpx 0 24rpx;border-radius:17rpx;background:#e7e5dd}.tab{flex:1;padding:18rpx;text-align:center;border-radius:13rpx;color:#777b75;font-size:24rpx}.tab.active{background:#fff;color:#315c4c;font-weight:650;box-shadow:0 4rpx 16rpx rgba(55,60,53,.07)}.toolbar{display:flex;align-items:flex-start;justify-content:space-between;gap:20rpx;margin-bottom:22rpx}.section-title,.section-sub{display:block}.section-title{font-size:30rpx;font-weight:700}.section-sub{margin-top:8rpx;color:#7f837d;font-size:21rpx;line-height:1.5}.upload{flex:none;width:160rpx;height:76rpx;line-height:76rpx;margin:0;padding:0;border-radius:16rpx;background:#315c4c;color:#fff;font-size:24rpx}.upload[disabled]{background:#8ca097}.file-panel{background:rgba(255,255,255,.78);border-radius:24rpx;padding:0 28rpx;box-shadow:0 16rpx 50rpx rgba(66,61,50,.07)}.empty{text-align:center;color:#92938d;padding:110rpx 20rpx;font-size:25rpx}.file-card{display:flex;gap:22rpx;padding:30rpx 0;border-bottom:1px solid #e8e5dd}.file-card:last-child{border-bottom:none}.file-icon{flex:none;width:76rpx;height:66rpx;border-radius:17rpx;background:#e3ece7;color:#315c4c;display:flex;align-items:center;justify-content:center;font-size:19rpx;font-weight:700}.file-main{flex:1;min-width:0}.file-head{display:flex;align-items:center;justify-content:space-between;gap:16rpx}.file-name{font-size:27rpx;font-weight:650;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.status{flex:none;padding:6rpx 13rpx;border-radius:100rpx;font-size:18rpx}.status.pending,.status.processing{background:#eee8dc;color:#99713f}.status.ready{background:#dcebe2;color:#397155}.status.failed,.status.off{background:#f3dfdb;color:#a04c42}.meta{display:flex;flex-wrap:wrap;gap:16rpx;margin-top:10rpx;color:#8c8e88;font-size:20rpx}.error{display:block;margin-top:8rpx;color:#a04c42;font-size:20rpx}.actions{display:flex;gap:12rpx;margin-top:20rpx}.small{width:118rpx;height:58rpx;line-height:58rpx;margin:0;padding:0;border-radius:13rpx;background:#eef3ef;color:#315c4c;border:1px solid rgba(49,92,76,.18);font-size:21rpx}.small.danger{background:#fff5f1;color:#a84f44;border-color:#e2b8ae}.small[disabled]{opacity:.55}@media(max-width:520px){.topbar{height:112rpx;padding:0 20rpx}.back,.spacer{width:58rpx}.title{font-size:30rpx}.content{padding:26rpx 18rpx 60rpx}.overview{grid-template-columns:1fr}.toolbar{flex-direction:column}.upload{width:100%}.file-panel{padding:0 20rpx}.file-card{gap:16rpx}.file-head{align-items:flex-start;flex-direction:column}.file-name{white-space:normal;word-break:break-all}.actions{width:100%}.small{flex:1}}
</style>
