<template>
  <view class="page"><view class="safe" /><view class="wrap">
    <view class="brand"><view class="seal">名</view><text class="brand-name">知名</text></view>
    <text class="eyebrow">CREATE ACCOUNT</text><view class="title">注册账号</view><view class="subtitle">留下你的邮箱，收藏每一次好灵感</view>
    <view class="form">
      <view class="field"><text class="label">邮箱</text><input v-model.trim="form.email" class="input" placeholder="请输入邮箱地址" /></view>
      <view class="field"><text class="label">验证码</text><view class="code-row"><input v-model.trim="form.code" class="input" type="number" maxlength="4" placeholder="4 位验证码" /><button class="code-btn" :disabled="countdown > 0 || sending" @tap="sendCode">{{ countdown ? `${countdown}s 后重发` : sending ? '发送中...' : '获取验证码' }}</button></view></view>
      <view class="field"><text class="label">用户名</text><input v-model.trim="form.username" class="input" maxlength="20" placeholder="2-20 个字符" /></view>
      <view class="field"><text class="label">密码</text><input v-model="form.password" class="input" password maxlength="20" placeholder="6-20 个字符" /></view>
      <view class="field"><text class="label">确认密码</text><input v-model="form.confirm_password" class="input" password maxlength="20" placeholder="请再次输入密码" /></view>
      <button class="primary" :disabled="loading" @tap="submit">{{ loading ? '注册中...' : '创建账号' }}</button>
    </view>
    <view class="switch">已有账号？<text class="link" @tap="back">返回登录</text></view>
  </view></view>
</template>
<script setup>
import { onUnmounted, reactive, ref } from 'vue'
import { api } from '../../utils/request.js'
const form = reactive({ email: '', code: '', username: '', password: '', confirm_password: '' })
const loading = ref(false), sending = ref(false), countdown = ref(0)
let timer
const emailOk = () => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)
async function sendCode() {
  if (!emailOk()) return uni.showToast({ title: '请输入正确的邮箱', icon: 'none' })
  sending.value = true
  try { await api.sendCode(form.email); uni.showToast({ title: '验证码已发送' }); countdown.value = 60; timer = setInterval(() => { if (--countdown.value <= 0) clearInterval(timer) }, 1000) }
  catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
  finally { sending.value = false }
}
async function submit() {
  if (!emailOk()) return uni.showToast({ title: '请输入正确的邮箱', icon: 'none' })
  if (form.code.length !== 4) return uni.showToast({ title: '请输入 4 位验证码', icon: 'none' })
  if (form.username.length < 2) return uni.showToast({ title: '用户名至少 2 个字符', icon: 'none' })
  if (form.password.length < 6) return uni.showToast({ title: '密码至少 6 位', icon: 'none' })
  if (form.password !== form.confirm_password) return uni.showToast({ title: '两次密码输入不一致', icon: 'none' })
  loading.value = true
  try { await api.register(form); uni.showToast({ title: '注册成功' }); setTimeout(() => uni.navigateBack(), 700) }
  catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
  finally { loading.value = false }
}
function back() { uni.navigateBack() }
onUnmounted(() => clearInterval(timer))
</script>
<style src="../../styles/auth.css"></style>
