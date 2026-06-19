import { API_BASE_URL } from '../config.js'

export function request({ url, method = 'GET', data, auth = false, timeout = 30000, failureMessage = '' }) {
  const token = uni.getStorageSync('token')
  const header = { 'Content-Type': 'application/json' }
  if (auth && token) header.Authorization = `Bearer ${token}`

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE_URL}${url}`,
      method,
      data,
      header,
      timeout,
      success: ({ statusCode, data: body }) => {
        if (statusCode >= 200 && statusCode < 300) return resolve(body)
        const detail = body?.detail || body?.message || ''
        const authExpired = statusCode === 401 || (
          statusCode === 403 && /Token|Access Token|账号已被禁用/.test(detail)
        )
        if (authExpired) {
          uni.removeStorageSync('token')
          uni.removeStorageSync('user')
          uni.reLaunch({ url: '/pages/login/login' })
        }
        reject(new Error(detail || '请求失败，请稍后再试'))
      },
      fail: ({ errMsg = '' }) => {
        const message = failureMessage || (
          /timeout/i.test(errMsg)
            ? '请求超时，请稍后重试'
            : '无法连接服务器，请检查后端地址和网络'
        )
        reject(new Error(message))
      }
    })
  })
}

export const api = {
  sendCode: (email) => request({ url: `/auth/code?email=${encodeURIComponent(email)}` }),
  register: (data) => request({ url: '/auth/register', method: 'POST', data }),
  login: (data) => request({ url: '/auth/login', method: 'POST', data }),
  generate: (data) => request({
    url: '/name/generate',
    method: 'POST',
    data,
    auth: true,
    timeout: 90000,
    failureMessage: '当前访问人数较多，生成服务暂时繁忙，请稍后重新尝试。'
  }),
  feedback: (data) => request({
    url: '/name/feedback',
    method: 'POST',
    data,
    auth: true,
    timeout: 90000,
    failureMessage: '当前访问人数较多，生成服务暂时繁忙，请稍后重新尝试。'
  }),
  userCenter: () => request({ url: '/users/me', auth: true }),
  loginRecords: () => request({ url: '/users/me/login-records', auth: true }),
  updateProfile: (data) => request({ url: '/users/me/profile', method: 'PATCH', data, auth: true }),
  updatePassword: (data) => request({ url: '/users/me/password', method: 'PATCH', data, auth: true }),
  cancelAccount: (data) => request({ url: '/users/me', method: 'DELETE', data, auth: true }),
  adminUsers: ({ search = '', page = 1, pageSize = 20 }) => request({
    url: `/admin/users?search=${encodeURIComponent(search)}&page=${page}&page_size=${pageSize}`,
    auth: true
  }),
  setUserActive: (userId, isActive) => request({
    url: `/admin/users/${userId}/status`,
    method: 'PATCH',
    data: { is_active: isActive },
    auth: true
  })
}
