<template>
  <view class="page"><view class="safe" />
    <view class="header"><view><text class="mini">AI NAMING STUDIO</text><view class="logo">知名<text class="dot">.</text></view></view><view class="header-actions"><view v-if="user.role === 'admin'" class="admin-link" @tap="toAdmin"><text class="admin-full">用户管理</text><text class="admin-short">管理</text></view><view class="account-action" @tap="toProfile"><view class="user">{{ userInitial }}</view><text class="profile-label">个人中心</text></view><view class="logout-action" @tap="logout"><text class="logout-mark">↗</text><text>退出</text></view></view></view>
    <view class="hero"><view class="hero-copy"><text class="hero-small">为你的故事，找到最好的名字</text><view class="hero-title">一字一意，<text>皆有来处</text></view></view><view class="inspiration-link" @tap="toHistory"><text class="inspiration-mark">藏</text><view><text class="inspiration-title">历史与收藏</text><text class="inspiration-sub">回看每一次灵感 →</text></view></view></view>
    <view v-if="announcements.length" class="announcements">
      <view v-for="item in announcements" :key="item.id" :class="['announcement', item.type]">
        <text class="announcement-tag">{{ announcementType(item.type) }}</text>
        <view><text class="announcement-title">{{ item.title }}</text><text class="announcement-content">{{ item.content }}</text></view>
      </view>
    </view>
    <view class="panel">
      <text class="section-label">01 / 起名类型</text>
      <view class="segments"><view v-for="item in categories" :key="item" :class="['segment', { active: form.category === item }]" @tap="chooseCategory(item)">{{ item }}</view></view>
      <view v-if="form.category === '企业名'" class="knowledge-box">
        <view class="knowledge-head"><view><text class="label">企业知识库</text><text class="knowledge-tip">上传品牌资料、行业规范或产品介绍，AI 将优先参考</text></view><view class="knowledge-actions"><button class="manage-btn" @tap="toKnowledge">管理</button><button class="upload-btn" :disabled="uploading" @tap="chooseKnowledgeFile">{{ uploading ? `${uploadProgress}%` : '上传资料' }}</button></view></view>
        <view v-if="!knowledgeFiles.length" class="knowledge-empty">支持 PDF、TXT，单个文件不超过 10MB</view>
        <view v-for="file in knowledgeFiles" :key="file.id" class="knowledge-file">
          <view class="file-icon">{{ file.original_name.split('.').pop().toUpperCase() }}</view>
          <view class="file-info"><text class="file-name">{{ file.original_name }}</text><text v-if="file.status === 'failed'" class="file-error">{{ file.error_message || '解析失败' }}</text></view>
          <text :class="['file-status', file.status]">{{ knowledgeStatus(file.status) }}</text>
        </view>
      </view>
      <view v-if="form.category === '人名'" class="field"><text class="label">姓氏 <text class="required">必填</text></text><input v-model.trim="form.surname" class="input" maxlength="4" placeholder="例如：林" /></view>
      <view v-if="form.category === '人名'" class="field"><text class="label">性别偏好</text><view class="chips"><view v-for="item in genders" :key="item" :class="['chip', { active: form.gender === item }]" @tap="form.gender = item">{{ item }}</view></view></view>
      <view class="field"><text class="label">名字长度 <text class="hint">{{ lengthHint }}</text></text><view class="chips"><view v-for="item in availableLengths" :key="item" :class="['chip', { active: form.length === item }]" @tap="form.length = item">{{ item }}</view></view></view>
      <view class="field"><text class="label">更多期待 <text class="hint">选填</text></text><textarea v-model="form.other" class="textarea" maxlength="300" placeholder="说说你期待的气质、行业、意象或故事..." /></view>
      <view class="field"><text class="label">避开的字 <text class="hint">用逗号分隔</text></text><input v-model="excludeText" class="input" placeholder="例如：强, 伟" /></view>
      <view v-if="user.role !== 'admin'" :class="['quota-card', { exhausted: quotaExhausted }]">
        <view><text class="quota-title">今日免费额度</text><text class="quota-tip">仅成功生成后计入次数</text></view>
        <view class="quota-value"><text>{{ quota.remaining === null ? '--' : quota.remaining }}</text><text>/ {{ quota.daily_limit }}</text></view>
      </view>
      <view v-else class="quota-card admin-quota"><view><text class="quota-title">管理员模式</text><text class="quota-tip">生成额度不受每日限制</text></view><text class="admin-quota-mark">∞</text></view>
      <button class="generate" :disabled="loading" @tap="generate"><text>{{ loading ? '正在寻名...' : quotaExhausted ? '今日额度已用完' : '生成名字' }}</text><text class="arrow">→</text></button>
    </view>
    <view v-if="names.length" class="results">
      <view class="result-head"><view><text class="section-label">02 / 灵感结果</text><view class="result-title">为你找到 {{ names.length }} 个名字</view></view><view :class="['again', { loading }]" @tap="regenerate"><view v-if="loading" class="again-spinner" /><text>{{ loading ? '生成中' : '换一批' }}</text></view></view>
      <view v-for="(item, index) in names" :key="`${item.name}-${index}`" class="name-card">
        <view class="number">0{{ index + 1 }}</view><view class="name-main"><view class="name-row"><view class="name">{{ item.name }}</view><view :class="['favorite-action', { active: favoriteIndexes.includes(index), loading: favoriteLoadingIndex === index }]" @tap="favoriteName(index)"><text>{{ favoriteIndexes.includes(index) ? '已收藏' : favoriteLoadingIndex === index ? '收藏中' : '收藏' }}</text></view></view><view class="moral">{{ item.moral }}</view>
          <view class="detail"><text class="tag">出处</text><text>{{ item.reference }}</text></view>
          <view v-if="item.domain" class="detail"><text class="tag">域名</text><text>{{ item.domain }}</text><text class="status">{{ item.domain_status }}</text></view>
        </view>
      </view>
      <view v-if="threadId" class="feedback"><text class="label">还想怎么调整？</text><view class="feedback-row"><input v-model.trim="feedbackText" class="feedback-input" placeholder="例如：更现代一些，保留清雅的感觉" /><button class="send" :disabled="feedbackLoading" @tap="sendFeedback">{{ feedbackLoading ? '...' : '调整' }}</button></view></view>
    </view>
    <view class="footer">名字，是故事的第一句话</view>
  </view>
</template>
<script setup>
import { computed, onUnmounted, reactive, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { api } from '../../utils/request.js'
const categories = ['人名', '企业名', '宠物名'], genders = ['不限', '男', '女']
const BUSY_MESSAGE = '当前访问人数较多，生成服务暂时繁忙，请稍后重新尝试。'
const form = reactive({ category: '人名', surname: '', gender: '不限', length: '不限', other: '' })
const excludeText = ref(''), names = ref([]), threadId = ref(''), loading = ref(false), feedbackLoading = ref(false), feedbackText = ref('')
const currentRound = ref(1), favoriteIndexes = ref([]), favoriteLoadingIndex = ref(-1)
const knowledgeFiles = ref([]), uploading = ref(false), uploadProgress = ref(0)
const user = ref({})
const announcements = ref([])
const quota = reactive({ daily_limit: 3, used: 0, remaining: null })
let knowledgeTimer
const userInitial = computed(() => (user.value.username || '我').slice(0, 1).toUpperCase())
const lengthOptions = {
  人名: ['不限', '单字名', '双字名'],
  企业名: ['不限', '2-4字（推荐）', '3-5字'],
  宠物名: ['不限', '1-2字', '2-3字']
}
const lengthHints = {
  人名: '名的字数，不含姓氏',
  企业名: '短名更利于传播',
  宠物名: '越短越好叫'
}
const availableLengths = computed(() => lengthOptions[form.category] || lengthOptions['人名'])
const lengthHint = computed(() => lengthHints[form.category] || '')
const quotaExhausted = computed(() => user.value.role !== 'admin' && quota.remaining === 0)
onLoad(() => { const token = uni.getStorageSync('token'); if (!token) return uni.reLaunch({ url: '/pages/login/login' }); user.value = uni.getStorageSync('user') || {} })
onShow(() => { if (uni.getStorageSync('token')) loadQuota(); loadAnnouncements() })
onUnmounted(() => clearTimeout(knowledgeTimer))
function chooseCategory(item) { form.category = item; if (item !== '人名') { form.surname = ''; form.gender = '不限' }; if (!availableLengths.value.includes(form.length)) form.length = '不限'; if (item === '企业名') loadKnowledgeFiles(); else clearTimeout(knowledgeTimer) }
function payload() { return { ...form, exclude: excludeText.value.split(/[，,\s]+/).map(v => v.trim()).filter(Boolean) } }
async function generate() {
  if (form.category === '人名' && !form.surname) return uni.showToast({ title: '请先填写姓氏', icon: 'none' })
  if (quotaExhausted.value) return showQuotaModal()
  loading.value = true
  try {
    const res = await api.generate(payload())
    if (!Array.isArray(res.names) || !res.names.length) throw new Error(BUSY_MESSAGE)
    names.value = res.names
    threadId.value = res.thread_id || ''
    currentRound.value = 1
    favoriteIndexes.value = []
    loadQuota()
    setTimeout(() => uni.pageScrollTo({ selector: '.results', duration: 300 }), 50)
    return true
  } catch (e) { showNamingError(e); return false }
  finally { loading.value = false }
}
async function regenerate() {
  if (loading.value) return
  const success = await generate()
  if (success) uni.showToast({ title: '已换一批', icon: 'success' })
}
async function sendFeedback() {
  if (!feedbackText.value) return uni.showToast({ title: '请填写调整意见', icon: 'none' })
  if (quotaExhausted.value) return showQuotaModal()
  feedbackLoading.value = true
  try {
    const res = await api.feedback({ thread_id: threadId.value, category: form.category, feedback: feedbackText.value })
    if (!Array.isArray(res.names) || !res.names.length) throw new Error(BUSY_MESSAGE)
    names.value = res.names
    threadId.value = res.thread_id
    currentRound.value += 1
    favoriteIndexes.value = []
    feedbackText.value = ''
    loadQuota()
    uni.showToast({ title: '已重新调整' })
  } catch (e) { showNamingError(e) }
  finally { feedbackLoading.value = false }
}
function toAdmin() { uni.navigateTo({ url: '/pages/admin/users' }) }
function toProfile() { uni.navigateTo({ url: '/pages/profile/profile' }) }
function toHistory() { uni.navigateTo({ url: '/pages/history/history' }) }
function toKnowledge() { uni.navigateTo({ url: '/pages/knowledge/manage' }) }
function logout() { uni.showModal({ title: '退出登录', content: '确定退出当前账号吗？', confirmColor: '#9b5f42', success: ({ confirm }) => { if (confirm) { uni.clearStorageSync(); uni.reLaunch({ url: '/pages/login/login' }) } } }) }
function showNamingError(error) {
  const message = error?.message || BUSY_MESSAGE
  if (/免费生成次数已用完|额度已用完/.test(message)) {
    loadQuota()
    return showQuotaModal()
  }
  if (error?.statusCode === 429 || /请求过于频繁|重复提交/.test(message)) {
    return uni.showModal({ title: '请求有些频繁', content: message, showCancel: false, confirmText: '稍后再试', confirmColor: '#315c4c' })
  }
  if (/访问人数|繁忙|超时/.test(message)) {
    return uni.showModal({ title: '生成暂时繁忙', content: message, showCancel: false, confirmText: '知道了', confirmColor: '#315c4c' })
  }
  uni.showToast({ title: message, icon: 'none', duration: 3000 })
}
function showQuotaModal() { uni.showModal({ title: '今日额度已用完', content: '每日可免费成功生成 3 次，失败请求不会扣除额度。额度将在次日恢复。', showCancel: false, confirmText: '知道了', confirmColor: '#315c4c' }) }
async function loadAnnouncements() {
  try { announcements.value = await api.activeAnnouncements() }
  catch (e) { announcements.value = [] }
}
function announcementType(type) { return ({ info: '公告', notice: '通知', warning: '重要' })[type] || '公告' }
async function loadQuota() {
  if (user.value.role === 'admin') return
  try { Object.assign(quota, await api.quota()) }
  catch (e) { /* 登录失效由请求层统一处理，其余情况保留上次额度显示。 */ }
}
async function loadKnowledgeFiles(silent = true) {
  try {
    knowledgeFiles.value = await api.knowledgeFiles()
    if (knowledgeFiles.value.some(file => ['pending', 'processing'].includes(file.status))) {
      clearTimeout(knowledgeTimer)
      knowledgeTimer = setTimeout(() => loadKnowledgeFiles(true), 3000)
    }
  } catch (e) { if (!silent) uni.showToast({ title: e.message, icon: 'none' }) }
}
function chooseKnowledgeFile() {
  const choose = uni.chooseFile
    ? options => uni.chooseFile(options)
    : uni.chooseMessageFile
      ? options => uni.chooseMessageFile(options)
      : null
  if (!choose) return uni.showToast({ title: '当前设备暂不支持文件选择', icon: 'none' })
  choose({ count: 1, type: 'file', extension: ['pdf', 'txt'], success: result => uploadSelectedFile(result) })
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
    const file = await api.uploadKnowledge(filePath, progress => { uploadProgress.value = progress })
    knowledgeFiles.value.unshift(file)
    uni.showToast({ title: '上传成功，正在解析' })
    clearTimeout(knowledgeTimer)
    knowledgeTimer = setTimeout(() => loadKnowledgeFiles(true), 2000)
  } catch (e) { uni.showToast({ title: e.message, icon: 'none', duration: 3000 }) }
  finally { uploading.value = false; uploadProgress.value = 0 }
}
function knowledgeStatus(status) { return ({ pending: '等待处理', processing: '解析中', ready: '可使用', failed: '处理失败' })[status] || status }
async function favoriteName(index) {
  if (!threadId.value || favoriteIndexes.value.includes(index) || favoriteLoadingIndex.value >= 0) return
  favoriteLoadingIndex.value = index
  try {
    await api.addFavorite({ session_id: threadId.value, round_number: currentRound.value, name_index: index })
    favoriteIndexes.value = [...favoriteIndexes.value, index]
    uni.showToast({ title: '已加入收藏', icon: 'success' })
  } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
  finally { favoriteLoadingIndex.value = -1 }
}
</script>
<style scoped>
.page{min-height:100vh;background:#f4f0e8}.safe{height:var(--status-bar-height)}.header{height:120rpx;padding:0 40rpx;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(47,59,51,.1)}.mini{font-size:16rpx;letter-spacing:3rpx;color:#8c8d86}.logo{font:600 38rpx serif;letter-spacing:8rpx}.dot,.required{color:#b66f3e}.header-actions{display:flex;align-items:center;gap:16rpx}.admin-link{font-size:24rpx;color:#315c4c;font-weight:600}.account-action{height:72rpx;box-sizing:border-box;display:flex;align-items:center;gap:14rpx;padding:7rpx 20rpx 7rpx 7rpx;border:1px solid rgba(49,92,76,.16);border-radius:100rpx;background:rgba(255,255,255,.58);box-shadow:0 6rpx 20rpx rgba(49,67,57,.06)}.account-action:active{background:#e6ece7;transform:scale(.98)}.user{width:56rpx;height:56rpx;border-radius:50%;background:#315c4c;color:white;display:flex;align-items:center;justify-content:center;font-size:25rpx}.profile-label{color:#53635b;font-size:22rpx;font-weight:500;white-space:nowrap}.logout-action{height:72rpx;box-sizing:border-box;display:flex;align-items:center;justify-content:center;gap:9rpx;padding:0 22rpx;border:1px solid rgba(155,95,66,.28);border-radius:100rpx;background:#f5e9df;color:#8e5439;font-size:22rpx;font-weight:600;white-space:nowrap}.logout-action:active{background:#ecd9ca;transform:scale(.98)}.logout-mark{font-size:25rpx;line-height:1;transform:rotate(45deg)}.hero{padding:70rpx 40rpx 50rpx;max-width:900rpx;margin:auto}.hero-small{font-size:24rpx;color:#787c76;letter-spacing:2rpx}.hero-title{font:600 58rpx/1.35 serif;margin-top:18rpx}.hero-title text{color:#315c4c}.panel,.results{margin:0 28rpx 42rpx;padding:40rpx 32rpx;background:rgba(255,255,255,.75);border-radius:28rpx;box-shadow:0 20rpx 60rpx rgba(66,61,50,.08);max-width:900rpx}.section-label{font-size:20rpx;color:#a76d3c;letter-spacing:3rpx}.segments{display:flex;background:#eceae3;padding:8rpx;border-radius:18rpx;margin:24rpx 0 40rpx}.segment{flex:1;text-align:center;padding:22rpx 4rpx;font-size:27rpx;border-radius:14rpx;color:#747770}.segment.active{background:#fff;color:#315c4c;font-weight:600;box-shadow:0 4rpx 16rpx rgba(55,60,53,.08)}.field{margin-bottom:34rpx}.label{display:block;font-weight:600;font-size:26rpx;margin-bottom:16rpx}.hint,.required{font-size:20rpx;font-weight:400;margin-left:8rpx}.hint{color:#999}.input,.textarea{box-sizing:border-box;width:100%;background:#f5f4ef;border:1px solid #e1dfd7;border-radius:16rpx;padding:0 24rpx;font-size:27rpx}.input{height:88rpx}.textarea{height:190rpx;padding-top:22rpx}.chips{display:flex;flex-wrap:wrap;gap:14rpx}.chip{min-width:110rpx;text-align:center;padding:18rpx 24rpx;border:1px solid #d9d7d0;border-radius:100rpx;color:#73766f;font-size:25rpx}.chip.active{border-color:#315c4c;background:#e7eee9;color:#315c4c;font-weight:600}.generate{height:100rpx;line-height:100rpx;border-radius:18rpx;background:#315c4c;color:white;font-size:29rpx;display:flex;justify-content:center;gap:26rpx;box-shadow:0 14rpx 30rpx rgba(49,92,76,.2)}.generate[disabled]{background:#8ca097}.arrow{font-size:38rpx}.result-head{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:28rpx}.result-title{font:600 38rpx serif;margin-top:12rpx}.again{color:#315c4c;font-size:25rpx}.name-card{display:flex;gap:24rpx;padding:34rpx 0;border-top:1px solid #e3e0d8}.number{color:#b98962;font:italic 22rpx serif}.name-main{flex:1}.name{font:600 48rpx serif;letter-spacing:10rpx;color:#263b32}.moral{font-size:26rpx;line-height:1.8;color:#60655f;margin:14rpx 0 22rpx}.detail{display:flex;align-items:flex-start;gap:14rpx;margin-top:10rpx;font-size:22rpx;color:#858780;line-height:1.6}.tag{flex:none;color:#a76d3c}.status{margin-left:auto;color:#557565}.feedback{border-top:1px solid #e3e0d8;padding-top:32rpx}.feedback-row{display:flex;gap:14rpx}.feedback-input{flex:1;height:82rpx;background:#f5f4ef;border-radius:14rpx;padding:0 20rpx;font-size:24rpx}.send{width:130rpx;height:82rpx;line-height:82rpx;background:#315c4c;color:#fff;border-radius:14rpx;font-size:24rpx}.footer{text-align:center;padding:20rpx 0 60rpx;color:#a09e96;font:24rpx serif;letter-spacing:4rpx}@media(max-width:430px){.profile-label{display:none}.account-action{width:70rpx;padding:7rpx;justify-content:center}.logout-action{height:68rpx;padding:0 18rpx}.admin-link{font-size:22rpx}}@media(min-width:700px){.panel,.results{margin-left:auto;margin-right:auto}.header{padding-left:calc((100% - 900px)/2);padding-right:calc((100% - 900px)/2)}}
.admin-short{display:none}.hero{max-width:900px}.panel,.results{width:calc(100% - 56rpx);max-width:900px;margin-left:auto;margin-right:auto}.name-main{min-width:0}.detail{flex-wrap:wrap;overflow-wrap:anywhere}.logout-mark{transform:none}
@media(max-width:480px){.header{min-height:112rpx;height:auto;padding:12rpx 20rpx}.mini{display:none}.logo{font-size:34rpx;letter-spacing:5rpx}.header-actions{gap:8rpx}.admin-link{font-size:21rpx}.admin-full{display:none}.admin-short{display:inline}.profile-label{display:none}.account-action{width:64rpx;height:64rpx;padding:4rpx;justify-content:center}.user{width:54rpx;height:54rpx}.logout-action{height:64rpx;padding:0 15rpx;font-size:21rpx}.logout-mark{display:none}.hero{padding:48rpx 28rpx 36rpx}.hero-title{font-size:48rpx}.panel,.results{width:calc(100% - 32rpx);padding:32rpx 24rpx;border-radius:22rpx}.segments{margin-bottom:32rpx}.segment{font-size:24rpx;padding:19rpx 2rpx}.chip{min-width:98rpx;padding:16rpx 18rpx}.result-head{align-items:flex-start}.result-title{font-size:33rpx}.name-card{gap:16rpx}.name{font-size:42rpx}.detail .status{width:100%;margin-left:0;padding-left:58rpx}}
@media(max-width:360px){.header{padding-left:14rpx;padding-right:14rpx}.logo{font-size:31rpx}.header-actions{gap:6rpx}.admin-link{font-size:19rpx}.account-action{width:58rpx;height:58rpx}.user{width:48rpx;height:48rpx}.logout-action{height:58rpx;padding:0 12rpx;font-size:20rpx}.hero-title{font-size:43rpx}.panel,.results{padding:28rpx 20rpx}.feedback-row{flex-direction:column}.feedback-input,.send{width:100%}.send{margin-top:10rpx}.code-row{flex-direction:column}}
@media(min-width:768px){.header{padding-left:32px;padding-right:32px}.hero{padding:54px 28px 38px}.panel,.results{padding:36px 40px;margin-bottom:32px}.hero-title{font-size:48px}.name-card{padding:26px 0}}
@media(min-width:1024px){.header{padding-left:calc((100% - 900px)/2);padding-right:calc((100% - 900px)/2)}}
.again{min-width:126rpx;height:60rpx;padding:0 18rpx;border:1px solid rgba(49,92,76,.2);border-radius:100rpx;background:#e8eee9;display:flex;align-items:center;justify-content:center;gap:10rpx;color:#315c4c;font-size:23rpx;font-weight:600;white-space:nowrap;transition:transform .15s ease,background-color .15s ease}.again:active{transform:scale(.95);background:#dce7e0}.again.loading{color:#718078;background:#edf0ec;pointer-events:none}.again-spinner{width:22rpx;height:22rpx;border:3rpx solid rgba(49,92,76,.2);border-top-color:#315c4c;border-radius:50%;animation:again-spin .75s linear infinite}@keyframes again-spin{to{transform:rotate(360deg)}}
.knowledge-box{margin:-10rpx 0 36rpx;padding:28rpx;border:1px solid #dce3dd;border-radius:20rpx;background:#f0f4f1}.knowledge-head{display:flex;align-items:flex-start;justify-content:space-between;gap:24rpx}.knowledge-head .label{margin-bottom:6rpx}.knowledge-tip{display:block;max-width:540rpx;color:#7f8781;font-size:21rpx;line-height:1.6}.knowledge-actions{display:flex;gap:12rpx;flex:none}.upload-btn,.manage-btn{width:152rpx;height:68rpx;line-height:68rpx;margin:0;padding:0;border-radius:14rpx;font-size:22rpx}.upload-btn{background:#315c4c;color:#fff}.manage-btn{background:#fff;color:#315c4c;border:1px solid rgba(49,92,76,.24)}.upload-btn[disabled]{background:#83968d}.knowledge-empty{padding:26rpx 0 2rpx;color:#9a9e99;font-size:21rpx}.knowledge-file{display:flex;align-items:center;gap:16rpx;margin-top:20rpx;padding-top:20rpx;border-top:1px solid #dce2dd}.file-icon{flex:none;width:64rpx;height:54rpx;border-radius:11rpx;background:#dde8e1;color:#315c4c;display:flex;align-items:center;justify-content:center;font-size:18rpx;font-weight:700}.file-info{flex:1;min-width:0}.file-name,.file-error{display:block}.file-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#424b46;font-size:23rpx}.file-error{margin-top:5rpx;color:#a05247;font-size:19rpx}.file-status{flex:none;padding:6rpx 12rpx;border-radius:100rpx;font-size:18rpx}.file-status.pending,.file-status.processing{background:#eee8dc;color:#99713f}.file-status.ready{background:#dcebe2;color:#397155}.file-status.failed{background:#f3dfdb;color:#a04c42}
.hero{display:flex;align-items:flex-end;justify-content:space-between;gap:32rpx}.inspiration-link{flex:none;display:flex;align-items:center;gap:16rpx;padding:18rpx 22rpx;border:1px solid rgba(49,92,76,.15);border-radius:20rpx;background:rgba(255,255,255,.48)}.inspiration-link:active{background:#e5ece7}.inspiration-mark{width:52rpx;height:52rpx;border-radius:15rpx;background:#315c4c;color:#fff;display:flex;align-items:center;justify-content:center;font:600 25rpx serif}.inspiration-title,.inspiration-sub{display:block}.inspiration-title{color:#315c4c;font-size:23rpx;font-weight:650}.inspiration-sub{color:#8a8d87;font-size:18rpx;margin-top:4rpx}.name-row{display:flex;align-items:center;justify-content:space-between;gap:18rpx}.favorite-action{flex:none;padding:9rpx 17rpx;border:1px solid #d8c4aa;border-radius:100rpx;color:#9a6a3e;font-size:20rpx}.favorite-action:active{transform:scale(.95)}.favorite-action.active{border-color:#b87a48;background:#f2e5d7;color:#8b562f}.favorite-action.loading{opacity:.65}
.quota-card{display:flex;align-items:center;justify-content:space-between;gap:20rpx;margin:8rpx 0 24rpx;padding:20rpx 24rpx;border:1px solid #d8e2dc;border-radius:17rpx;background:#edf3ef;color:#315c4c}.quota-card.exhausted{border-color:#e5c9bd;background:#f7ece7;color:#97543e}.quota-title,.quota-tip{display:block}.quota-title{font-size:24rpx;font-weight:650}.quota-tip{margin-top:5rpx;color:#858d87;font-size:19rpx}.quota-value{display:flex;align-items:baseline;gap:5rpx;white-space:nowrap}.quota-value text:first-child{font:600 40rpx serif}.quota-value text:last-child{font-size:20rpx;color:#7d8881}.admin-quota{background:#eee9df;border-color:#e2d6c7;color:#8d623f}.admin-quota-mark{font:600 42rpx serif}.generate[disabled]{opacity:.82}
.announcements{width:calc(100% - 56rpx);max-width:900px;margin:-20rpx auto 34rpx}.announcement{display:flex;gap:18rpx;padding:22rpx 24rpx;margin-bottom:14rpx;border:1px solid #dedbd2;border-radius:20rpx;background:rgba(255,255,255,.66);box-shadow:0 10rpx 30rpx rgba(66,61,50,.05)}.announcement.warning{border-color:#e7c7bf;background:#fff4ef}.announcement.notice{border-color:#e1d3bf;background:#fbf5eb}.announcement-tag{flex:none;height:42rpx;line-height:42rpx;padding:0 15rpx;border-radius:100rpx;background:#e3ece7;color:#315c4c;font-size:19rpx;font-weight:650}.announcement.warning .announcement-tag{background:#f1ded9;color:#a04c42}.announcement.notice .announcement-tag{background:#eee3d5;color:#9a6b43}.announcement-title,.announcement-content{display:block}.announcement-title{font-size:25rpx;font-weight:700;color:#29312d}.announcement-content{margin-top:7rpx;color:#6f746e;font-size:21rpx;line-height:1.55}
@media(max-width:480px){.knowledge-box{padding:24rpx 20rpx}.knowledge-head{gap:14rpx}.knowledge-tip{font-size:19rpx}.upload-btn{width:132rpx}.knowledge-file{align-items:flex-start;flex-wrap:wrap}.file-info{flex:1 1 calc(100% - 84rpx)}.file-status{margin-left:80rpx}}
@media(max-width:360px){.knowledge-head{flex-direction:column}.knowledge-actions,.upload-btn,.manage-btn{width:100%}.file-status{margin-left:0}}
@media(max-width:650px){.hero{align-items:flex-start;flex-direction:column}.inspiration-link{align-self:stretch;justify-content:flex-start}.inspiration-sub{font-size:19rpx}}
</style>
