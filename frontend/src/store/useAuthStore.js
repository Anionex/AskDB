import { create } from 'zustand'
import axios from 'axios'

const API_BASE = 'http://localhost:8000/api'

export const useAuthStore = create((set, get) => ({
  user: null,
  isLoggedIn: false,
  isLoading: false,
  error: null,

  checkAuth: async () => {
    const token = localStorage.getItem('askdb_token')
    if (!token) return false

    set({ isLoading: true })
    try {
      const response = await axios.post(`${API_BASE}/auth/verify`, { token })
      if (response.data.success && response.data.valid) {
        set({ user: response.data.user, isLoggedIn: true, isLoading: false })
        return true
      } else {
        localStorage.removeItem('askdb_token')
        set({ user: null, isLoggedIn: false, isLoading: false })
        return false
      }
    } catch (error) {
      localStorage.removeItem('askdb_token')
      set({ user: null, isLoggedIn: false, isLoading: false, error: error.message })
      return false
    }
  },

  login: async (username, password) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(`${API_BASE}/auth/login`, { username, password })
      if (response.data.success) {
        localStorage.setItem('askdb_token', response.data.token)
        set({ user: response.data.user, isLoggedIn: true, isLoading: false })
        return { success: true }
      } else {
        set({ isLoading: false, error: response.data.message })
        return { success: false, message: response.data.message }
      }
    } catch (error) {
      const message = error.response?.data?.message || '登录失败'
      set({ isLoading: false, error: message })
      return { success: false, message }
    }
  },

  logout: () => {
    localStorage.removeItem('askdb_token')
    set({ user: null, isLoggedIn: false })
  }
}))










