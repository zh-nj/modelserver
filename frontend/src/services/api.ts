/**
 * API客户端服务
 */
import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import type { ApiResponse } from '@/types'

// 创建axios实例
export const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 添加认证token（如果需要）
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 添加请求时间戳
    config.metadata = { startTime: new Date() }
    
    console.log(`[API请求] ${config.method?.toUpperCase()} ${config.url}`, config.data)
    return config
  },
  (error) => {
    console.error('[API请求错误]', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const duration = new Date().getTime() - response.config.metadata?.startTime?.getTime()
    console.log(`[API响应] ${response.config.method?.toUpperCase()} ${response.config.url} (${duration}ms)`, response.data)
    
    // 检查业务状态码
    if (response.data && !response.data.success) {
      const error = new Error(response.data.message || response.data.error || '请求失败')
      error.name = 'BusinessError'
      return Promise.reject(error)
    }
    
    return response
  },
  (error) => {
    console.error('[API响应错误]', error)
    
    // 处理网络错误
    if (!error.response) {
      error.message = '网络连接失败，请检查网络设置'
      return Promise.reject(error)
    }
    
    // 处理HTTP状态码错误
    const { status, data } = error.response
    switch (status) {
      case 400:
        error.message = data?.message || '请求参数错误'
        break
      case 401:
        error.message = '认证失败，请重新登录'
        // 清除认证信息
        localStorage.removeItem('auth_token')
        // 可以在这里触发重新登录逻辑
        break
      case 403:
        error.message = '权限不足，无法访问该资源'
        break
      case 404:
        error.message = '请求的资源不存在'
        break
      case 429:
        error.message = '请求过于频繁，请稍后再试'
        break
      case 500:
        error.message = '服务器内部错误'
        break
      case 502:
        error.message = '网关错误'
        break
      case 503:
        error.message = '服务暂时不可用'
        break
      default:
        error.message = data?.message || `请求失败 (${status})`
    }
    
    return Promise.reject(error)
  }
)

// API方法封装
export class ApiService {
  static async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> {
    return apiClient.get(url, config)
  }

  static async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> {
    return apiClient.post(url, data, config)
  }

  static async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> {
    return apiClient.put(url, data, config)
  }

  static async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> {
    return apiClient.patch(url, data, config)
  }

  static async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<ApiResponse<T>>> {
    return apiClient.delete(url, config)
  }
}

// 扩展axios配置类型以支持metadata
declare module 'axios' {
  interface AxiosRequestConfig {
    metadata?: {
      startTime: Date
    }
  }
}