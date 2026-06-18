import { API_BASE_URL } from '../config.js'

export function request({ url, method = 'GET', data, auth = false }) {
  const token = uni.getStorageSync('token')
  const header = { 'Content-Type': 'application/json' }
  if (auth && token) header.Authorization = `Bearer ${token}`

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE_URL}${url}`,
      method,
      data,
      header,
      success: ({ statusCode, data: body }) => {
        if (statusCode >= 200 && statusCode < 300) return resolve(body)
        if (statusCode === 401 || statusCode === 403) {
          uni.removeStorageSync('token')
          uni.removeStorageSync('user')
          uni.reLaunch({ url: '/pages/login/login' })
        }
        reject(new Error(body?.detail || body?.message || '请求失败，请稍后再试'))
      },
      fail: () => reject(new Error('无法连接服务器，请检查后端地址和网络'))
    })
  })
}

export const api = {
  sendCode: (email) => request({ url: `/auth/code?email=${encodeURIComponent(email)}` }),
  register: (data) => request({ url: '/auth/register', method: 'POST', data }),
  login: (data) => request({ url: '/auth/login', method: 'POST', data }),
  generate: (data) => request({ url: '/name/generate', method: 'POST', data, auth: true }),
  feedback: (data) => request({ url: '/name/feedback', method: 'POST', data, auth: true })
}
