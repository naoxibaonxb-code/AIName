<template>
  <view class="page"><view class="safe" />
    <view class="topbar">
      <view class="back" @tap="back">‹</view>
      <view class="top-title"><text class="eyebrow">MY ACCOUNT</text><view>个人中心</view></view>
      <view class="spacer" />
    </view>

    <view class="content">
      <view class="identity">
        <view class="avatar">{{ initial }}</view>
        <view class="identity-main"><view class="username">{{ profile.username || '用户' }}</view><text class="email">{{ profile.email }}</text></view>
        <text v-if="profile.role === 'admin'" class="role">管理员</text>
      </view>

      <view class="stats">
        <view class="stat"><text class="stat-value">{{ profile.usage_count || 0 }}</text><text class="stat-label">使用次数</text></view>
        <view class="divider" />
        <view class="stat"><text class="stat-value">{{ loginCount }}</text><text class="stat-label">登录次数</text></view>
        <view class="divider" />
        <view class="stat"><text class="stat-value small">{{ joinDate }}</text><text class="stat-label">加入时间</text></view>
      </view>

      <view class="inspiration-menu"><view class="inspiration-item" @tap="toInspiration('history')"><view class="menu-mark">录</view><view><text>起名历史</text><text>查看每轮生成与调整</text></view><text class="menu-arrow">›</text></view><view class="inspiration-item warm" @tap="toInspiration('favorites')"><view class="menu-mark">藏</view><view><text>我的收藏</text><text>珍藏满意的好名字</text></view><text class="menu-arrow">›</text></view></view>

      <view class="card">
        <view class="card-head"><view><text class="card-index">01</text><text class="card-title">基本资料</text></view><text class="card-note">修改邮箱需验证</text></view>
        <view class="field"><text class="label">用户名</text><input v-model.trim="profileForm.username" class="input" maxlength="20" placeholder="2-20 个字符" /></view>
        <view class="field"><text class="label">邮箱</text><input v-model.trim="profileForm.email" class="input" type="text" placeholder="请输入新邮箱" /></view>
        <template v-if="emailChanged">
          <view class="field"><text class="label">当前密码</text><input v-model="profileForm.current_password" class="input" password placeholder="用于确认本人操作" /></view>
          <view class="field"><text class="label">新邮箱验证码</text><view class="code-row"><input v-model.trim="profileForm.email_code" class="input" type="number" maxlength="4" placeholder="4 位验证码" /><button class="code-btn" :disabled="countdown > 0 || sending" @tap="sendCode">{{ countdown ? `${countdown}s` : sending ? '发送中' : '获取验证码' }}</button></view></view>
        </template>
        <button class="primary" :disabled="savingProfile" @tap="saveProfile">{{ savingProfile ? '保存中...' : '保存资料' }}</button>
      </view>

      <view class="card">
        <view class="card-head"><view><text class="card-index">02</text><text class="card-title">修改密码</text></view><text class="card-note">建议定期更换</text></view>
        <view class="field"><text class="label">当前密码</text><input v-model="passwordForm.current_password" class="input" password placeholder="请输入当前密码" /></view>
        <view class="field"><text class="label">新密码</text><input v-model="passwordForm.new_password" class="input" password maxlength="20" placeholder="6-20 个字符" /></view>
        <view class="field"><text class="label">确认新密码</text><input v-model="passwordForm.confirm_password" class="input" password maxlength="20" placeholder="再次输入新密码" /></view>
        <button class="primary secondary" :disabled="savingPassword" @tap="savePassword">{{ savingPassword ? '修改中...' : '修改密码' }}</button>
      </view>

      <view class="card">
        <view class="card-head"><view><text class="card-index">03</text><text class="card-title">最近登录</text></view><text class="card-note">最近 20 条</text></view>
        <view v-if="!records.length" class="empty">暂无登录记录</view>
        <view v-for="record in records" :key="record.id" class="record">
          <view class="record-dot" /><view class="record-main"><text class="record-device">{{ deviceName(record.user_agent) }}</text><text class="record-time">{{ formatDateTime(record.login_at) }}</text></view><text class="record-ip">{{ record.ip_address || '未知 IP' }}</text>
        </view>
      </view>

      <button class="logout-btn" @tap="logout">退出当前账号</button>

      <view class="danger-card">
        <view class="danger-title">注销账号</view>
        <view class="danger-text">注销后账号将无法恢复，登录权限会立即失效。请输入密码并填写“注销”确认。</view>
        <input v-model="cancelForm.password" class="input danger-input" password placeholder="当前密码" />
        <input v-model.trim="cancelForm.confirmation" class="input danger-input" placeholder="请输入“注销”" />
        <button class="cancel-btn" :disabled="cancelling" @tap="confirmCancel">{{ cancelling ? '正在注销...' : '永久注销账号' }}</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onUnmounted, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api } from '../../utils/request.js'

const profile = reactive({}), profileForm = reactive({ username: '', email: '', current_password: '', email_code: '' })
const passwordForm = reactive({ current_password: '', new_password: '', confirm_password: '' })
const cancelForm = reactive({ password: '', confirmation: '' })
const records = ref([]), loginCount = ref(0), originalEmail = ref('')
const savingProfile = ref(false), savingPassword = ref(false), sending = ref(false), countdown = ref(0), cancelling = ref(false)
let timer
const initial = computed(() => (profile.username || '我').slice(0, 1).toUpperCase())
const emailChanged = computed(() => profileForm.email && profileForm.email !== originalEmail.value)
const joinDate = computed(() => profile.created_at ? formatDate(profile.created_at) : '--')

onLoad(loadData)
onUnmounted(() => clearInterval(timer))

async function loadData() {
  try {
    const [center, loginRecords] = await Promise.all([api.userCenter(), api.loginRecords()])
    Object.assign(profile, center.user)
    profileForm.username = center.user.username
    profileForm.email = center.user.email
    originalEmail.value = center.user.email
    loginCount.value = center.login_count || 0
    records.value = loginRecords || []
    uni.setStorageSync('user', center.user)
  } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
}

async function sendCode() {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(profileForm.email)) return toast('请输入正确的新邮箱')
  sending.value = true
  try {
    await api.sendCode(profileForm.email)
    uni.showToast({ title: '验证码已发送' })
    countdown.value = 60
    clearInterval(timer)
    timer = setInterval(() => { if (--countdown.value <= 0) clearInterval(timer) }, 1000)
  } catch (e) { toast(e.message) }
  finally { sending.value = false }
}

async function saveProfile() {
  if (profileForm.username.length < 2) return toast('用户名至少 2 个字符')
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(profileForm.email)) return toast('请输入正确的邮箱')
  if (emailChanged.value && (!profileForm.current_password || profileForm.email_code.length !== 4)) return toast('请填写当前密码和验证码')
  savingProfile.value = true
  try {
    const payload = { username: profileForm.username, email: profileForm.email }
    if (emailChanged.value) {
      payload.current_password = profileForm.current_password
      payload.email_code = profileForm.email_code
    }
    const updated = await api.updateProfile(payload)
    Object.assign(profile, updated)
    originalEmail.value = updated.email
    profileForm.current_password = ''
    profileForm.email_code = ''
    profileForm.username = updated.username
    profileForm.email = updated.email
    uni.setStorageSync('user', updated)
    uni.showToast({ title: '资料已更新' })
  } catch (e) { toast(e.message) }
  finally { savingProfile.value = false }
}

async function savePassword() {
  if (passwordForm.current_password.length < 6 || passwordForm.new_password.length < 6) return toast('密码至少 6 位')
  if (passwordForm.new_password !== passwordForm.confirm_password) return toast('两次新密码输入不一致')
  savingPassword.value = true
  try {
    await api.updatePassword({ ...passwordForm })
    Object.assign(passwordForm, { current_password: '', new_password: '', confirm_password: '' })
    uni.showToast({ title: '密码修改成功' })
  } catch (e) { toast(e.message) }
  finally { savingPassword.value = false }
}

function logout() {
  uni.showModal({ title: '退出登录', content: '确定退出当前账号吗？', success: ({ confirm }) => { if (confirm) clearSession() } })
}

function confirmCancel() {
  if (!cancelForm.password || cancelForm.confirmation !== '注销') return toast('请填写密码并输入“注销”')
  uni.showModal({ title: '永久注销账号', content: '此操作不可恢复，确定继续吗？', confirmColor: '#a84f44', success: ({ confirm }) => { if (confirm) cancelAccount() } })
}

async function cancelAccount() {
  cancelling.value = true
  try { await api.cancelAccount({ ...cancelForm }); clearSession() }
  catch (e) { toast(e.message) }
  finally { cancelling.value = false }
}

function clearSession() { uni.clearStorageSync(); uni.reLaunch({ url: '/pages/login/login' }) }
function toInspiration(tab) { uni.navigateTo({ url: `/pages/history/history?tab=${tab}` }) }
function back() { uni.navigateBack() }
function toast(message) { uni.showToast({ title: message, icon: 'none' }) }
function formatDate(value) { const d = new Date(value); return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}` }
function formatDateTime(value) { const d = new Date(value); return `${formatDate(value)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` }
function deviceName(agent = '') {
  if (/MicroMessenger/i.test(agent)) return '微信客户端'
  if (/iPhone|iPad/i.test(agent)) return 'iPhone / iPad'
  if (/Android/i.test(agent)) return 'Android 设备'
  if (/Windows/i.test(agent)) return 'Windows 设备'
  if (/Macintosh/i.test(agent)) return 'Mac 设备'
  return '未知设备'
}
</script>

<style scoped>
.page{min-height:100vh;background:#f4f0e8;color:#29312d}.safe{height:var(--status-bar-height)}
.topbar{height:130rpx;display:flex;align-items:center;padding:0 34rpx;border-bottom:1px solid rgba(47,59,51,.1)}.back,.spacer{width:76rpx}.back{font-size:58rpx;color:#315c4c}.top-title{flex:1;text-align:center;font-size:34rpx;font-weight:650}.eyebrow{display:block;font-size:16rpx;letter-spacing:3rpx;color:#a76d3c;margin-bottom:4rpx}
.content{padding:36rpx 28rpx 80rpx;max-width:900rpx;margin:auto}.identity{display:flex;align-items:center;gap:22rpx;padding:12rpx 10rpx 34rpx}.avatar{width:100rpx;height:100rpx;border-radius:30rpx;background:#315c4c;color:#fff;display:flex;align-items:center;justify-content:center;font:600 40rpx serif}.identity-main{flex:1}.username{font-size:34rpx;font-weight:650}.email{display:block;color:#7c807a;font-size:23rpx;margin-top:8rpx}.role{padding:8rpx 18rpx;border-radius:100rpx;background:#e2ebe6;color:#315c4c;font-size:20rpx}
.stats{display:flex;align-items:center;padding:30rpx 10rpx;background:linear-gradient(135deg,#315c4c,#496f60);border-radius:26rpx;color:#fff;box-shadow:0 16rpx 36rpx rgba(49,92,76,.18);margin-bottom:28rpx}.stat{flex:1;text-align:center}.stat-value,.stat-label{display:block}.stat-value{font:600 38rpx serif}.stat-value.small{font-size:25rpx;line-height:48rpx}.stat-label{font-size:19rpx;color:#d4e1da;margin-top:8rpx}.divider{width:1px;height:58rpx;background:rgba(255,255,255,.2)}
.card{background:rgba(255,255,255,.76);border-radius:26rpx;padding:34rpx 30rpx;margin-top:26rpx;box-shadow:0 14rpx 44rpx rgba(66,61,50,.07)}.card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:32rpx}.card-index{color:#b97a49;font:italic 20rpx serif;margin-right:14rpx}.card-title{font-size:29rpx;font-weight:650}.card-note{font-size:20rpx;color:#9a9b94}.field{margin-bottom:25rpx}.label{display:block;font-size:24rpx;font-weight:600;margin-bottom:13rpx}.input{box-sizing:border-box;width:100%;height:86rpx;padding:0 23rpx;background:#f5f4ef;border:1px solid #e1dfd7;border-radius:15rpx;font-size:26rpx}.code-row{display:flex;gap:13rpx}.code-row .input{flex:1;min-width:0}.code-btn{width:190rpx;height:86rpx;line-height:86rpx;padding:0;border-radius:15rpx;background:#e4ece7;color:#315c4c;font-size:23rpx}.primary{height:88rpx;line-height:88rpx;border-radius:16rpx;background:#315c4c;color:#fff;font-size:26rpx;margin-top:10rpx}.primary.secondary{background:#536a60}
.record{display:flex;align-items:center;gap:16rpx;padding:22rpx 0;border-top:1px solid #e8e5dd}.record-dot{width:14rpx;height:14rpx;border-radius:50%;background:#668b79;box-shadow:0 0 0 7rpx #e5ede8}.record-main{flex:1;margin-left:8rpx}.record-device,.record-time{display:block}.record-device{font-size:24rpx;font-weight:600}.record-time{font-size:20rpx;color:#999;margin-top:5rpx}.record-ip{font-size:20rpx;color:#777}.empty{text-align:center;color:#999;padding:50rpx 0;font-size:23rpx}
.logout-btn{height:86rpx;line-height:86rpx;margin-top:28rpx;background:#fff;color:#315c4c;border:1px solid #d8ddd9;border-radius:17rpx;font-size:25rpx}.danger-card{padding:34rpx 30rpx;margin-top:28rpx;border:1px solid #e7cbc5;border-radius:24rpx;background:#f8efeb}.danger-title{font-size:28rpx;font-weight:650;color:#9d493f}.danger-text{font-size:22rpx;line-height:1.7;color:#906e68;margin:12rpx 0 24rpx}.danger-input{background:#fff;margin-top:14rpx;border-color:#ead7d2}.cancel-btn{height:82rpx;line-height:82rpx;margin-top:22rpx;background:#a84f44;color:#fff;border-radius:15rpx;font-size:24rpx}
.inspiration-menu{display:grid;grid-template-columns:1fr 1fr;gap:18rpx;margin:26rpx 0}.inspiration-item{display:flex;align-items:center;gap:15rpx;padding:25rpx 22rpx;border:1px solid #dce3de;border-radius:21rpx;background:rgba(255,255,255,.66)}.inspiration-item.warm{border-color:#e5d8ca}.menu-mark{flex:none;width:58rpx;height:58rpx;border-radius:17rpx;background:#315c4c;color:#fff;display:flex;align-items:center;justify-content:center;font:600 26rpx serif}.warm .menu-mark{background:#a16f48}.inspiration-item>view:nth-child(2){flex:1;min-width:0}.inspiration-item text{display:block}.inspiration-item>view:nth-child(2)>text:first-child{font-size:25rpx;font-weight:650}.inspiration-item>view:nth-child(2)>text:last-child{margin-top:5rpx;color:#92958f;font-size:18rpx}.menu-arrow{color:#9a9d97;font-size:35rpx}
@media(min-width:700px){.content{padding-top:30px}.stats{padding:22px 10px}.card{padding:28px;margin-top:22px}}
.content{width:100%;max-width:880px}.identity-main{min-width:0}.identity .email{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.record-main{min-width:0}.record-ip{overflow-wrap:anywhere;text-align:right}
@media(max-width:480px){.topbar{height:112rpx;padding:0 20rpx}.back,.spacer{width:58rpx}.back{font-size:52rpx}.top-title{font-size:30rpx}.content{padding:26rpx 18rpx 60rpx}.identity{gap:16rpx;padding:8rpx 4rpx 26rpx}.avatar{width:82rpx;height:82rpx;border-radius:24rpx;font-size:34rpx}.username{font-size:30rpx}.identity .email{max-width:430rpx}.role{padding:7rpx 13rpx}.stats{padding:24rpx 4rpx;border-radius:22rpx}.stat-value{font-size:33rpx}.stat-value.small{font-size:21rpx}.card{padding:28rpx 22rpx;border-radius:22rpx}.card-head{align-items:flex-start;gap:12rpx}.card-note{max-width:180rpx;text-align:right}.record{align-items:flex-start;flex-wrap:wrap}.record-ip{width:100%;padding-left:38rpx;text-align:left}.danger-card{padding:28rpx 22rpx}}
@media(max-width:360px){.identity .email{max-width:330rpx}.stats{flex-wrap:wrap}.stat{min-width:30%}.stat-value.small{font-size:19rpx}.code-row{flex-direction:column}.code-row .input,.code-btn{width:100%}.code-btn{margin:0}.card-head{flex-direction:column}.card-note{max-width:none;text-align:left;margin-left:54rpx}}
@media(max-width:520px){.inspiration-menu{grid-template-columns:1fr}.inspiration-item{padding:22rpx}}
@media(min-width:768px){.content{padding:34px 28px 70px}.identity{padding-left:8px;padding-right:8px}.stats{padding:24px 12px}.card{padding:30px 34px}.field{max-width:720px}.record{padding:18px 0}}
</style>
