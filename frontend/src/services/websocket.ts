/**
 * WebSocket客户端服务
 * 提供实时数据更新和双向通信功能
 */
import type { WebSocketMessage, GPUInfo, SystemOverview, ModelInfo, ModelStatus } from '@/types'

// WebSocket消息类型
export enum MessageType {
  // 连接管理
  CONNECTION_ESTABLISHED = 'connection_established',
  PING = 'ping',
  PONG = 'pong',
  
  // 订阅管理
  SUBSCRIBE = 'subscribe',
  UNSUBSCRIBE = 'unsubscribe',
  SUBSCRIPTION_CONFIRMED = 'subscription_confirmed',
  UNSUBSCRIPTION_CONFIRMED = 'unsubscription_confirmed',
  
  // 数据更新
  MODEL_STATUS_UPDATE = 'model_status_update',
  GPU_METRICS_UPDATE = 'gpu_metrics_update',
  SYSTEM_OVERVIEW_UPDATE = 'system_overview_update',
  SYSTEM_ALERT = 'system_alert',
  CONFIG_CHANGE = 'config_change',
  
  // 错误处理
  ERROR = 'error',
  BROADCAST = 'broadcast'
}

// 订阅类型
export enum SubscriptionType {
  MODEL_UPDATES = 'model_updates',
  GPU_METRICS = 'gpu_metrics',
  SYSTEM_ALERTS = 'system_alerts',
  CONFIG_CHANGES = 'config_changes'
}

// WebSocket连接状态
export enum ConnectionStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error'
}

// 事件监听器类型
type EventListener = (data: any) => void
type StatusListener = (status: ConnectionStatus) => void

export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private clientId: string | null = null
  private status: ConnectionStatus = ConnectionStatus.DISCONNECTED
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectInterval = 3000
  private heartbeatInterval: number | null = null
  private heartbeatTimer: number | null = null
  
  // 事件监听器
  private eventListeners: Map<string, EventListener[]> = new Map()
  private statusListeners: StatusListener[] = []
  
  // 订阅状态
  private subscriptions: Set<SubscriptionType> = new Set()
  private pendingSubscriptions: Set<SubscriptionType> = new Set()

  constructor(baseUrl: string = '') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = baseUrl || window.location.host
    this.url = `${protocol}//${host}/ws/system-status`
    this.heartbeatInterval = 30000 // 30秒心跳间隔
  }

  /**
   * 连接WebSocket
   */
  async connect(): Promise<void> {
    if (this.status === ConnectionStatus.CONNECTED || this.status === ConnectionStatus.CONNECTING) {
      return
    }

    this.setStatus(ConnectionStatus.CONNECTING)

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('WebSocket连接已建立')
          this.setStatus(ConnectionStatus.CONNECTED)
          this.reconnectAttempts = 0
          this.startHeartbeat()
          this.resubscribeAll()
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('解析WebSocket消息失败:', error)
          }
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket连接已关闭:', event.code, event.reason)
          this.cleanup()
          
          if (event.code !== 1000) { // 非正常关闭
            this.attemptReconnect()
          } else {
            this.setStatus(ConnectionStatus.DISCONNECTED)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket连接错误:', error)
          this.setStatus(ConnectionStatus.ERROR)
          reject(error)
        }

        // 连接超时处理
        setTimeout(() => {
          if (this.status === ConnectionStatus.CONNECTING) {
            this.ws?.close()
            reject(new Error('WebSocket连接超时'))
          }
        }, 10000)

      } catch (error) {
        this.setStatus(ConnectionStatus.ERROR)
        reject(error)
      }
    })
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, '客户端主动断开')
    }
    this.cleanup()
    this.setStatus(ConnectionStatus.DISCONNECTED)
  }

  /**
   * 发送消息
   */
  private send(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket未连接，无法发送消息:', message)
    }
  }

  /**
   * 订阅消息类型
   */
  subscribe(type: SubscriptionType): void {
    this.subscriptions.add(type)
    
    if (this.status === ConnectionStatus.CONNECTED) {
      this.send({
        type: MessageType.SUBSCRIBE,
        subscription_type: type,
        timestamp: Date.now()
      })
    } else {
      this.pendingSubscriptions.add(type)
    }
  }

  /**
   * 取消订阅
   */
  unsubscribe(type: SubscriptionType): void {
    this.subscriptions.delete(type)
    this.pendingSubscriptions.delete(type)
    
    if (this.status === ConnectionStatus.CONNECTED) {
      this.send({
        type: MessageType.UNSUBSCRIBE,
        subscription_type: type,
        timestamp: Date.now()
      })
    }
  }

  /**
   * 添加事件监听器
   */
  on(event: string, listener: EventListener): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, [])
    }
    this.eventListeners.get(event)!.push(listener)
  }

  /**
   * 移除事件监听器
   */
  off(event: string, listener?: EventListener): void {
    if (!this.eventListeners.has(event)) return
    
    if (listener) {
      const listeners = this.eventListeners.get(event)!
      const index = listeners.indexOf(listener)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    } else {
      this.eventListeners.delete(event)
    }
  }

  /**
   * 添加状态监听器
   */
  onStatusChange(listener: StatusListener): void {
    this.statusListeners.push(listener)
  }

  /**
   * 移除状态监听器
   */
  offStatusChange(listener: StatusListener): void {
    const index = this.statusListeners.indexOf(listener)
    if (index > -1) {
      this.statusListeners.splice(index, 1)
    }
  }

  /**
   * 获取连接状态
   */
  getStatus(): ConnectionStatus {
    return this.status
  }

  /**
   * 获取客户端ID
   */
  getClientId(): string | null {
    return this.clientId
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(message: WebSocketMessage): void {
    const { type, data } = message

    switch (type) {
      case MessageType.CONNECTION_ESTABLISHED:
        this.clientId = data.client_id
        console.log('WebSocket客户端ID:', this.clientId)
        break

      case MessageType.PONG:
        // 心跳响应，无需处理
        break

      case MessageType.SUBSCRIPTION_CONFIRMED:
        console.log('订阅确认:', data.subscription_type)
        this.pendingSubscriptions.delete(data.subscription_type)
        break

      case MessageType.UNSUBSCRIPTION_CONFIRMED:
        console.log('取消订阅确认:', data.subscription_type)
        break

      case MessageType.MODEL_STATUS_UPDATE:
        this.emit('modelStatusUpdate', data)
        break

      case MessageType.GPU_METRICS_UPDATE:
        this.emit('gpuMetricsUpdate', data)
        break

      case MessageType.SYSTEM_OVERVIEW_UPDATE:
        this.emit('systemOverviewUpdate', data)
        break

      case MessageType.SYSTEM_ALERT:
        this.emit('systemAlert', data)
        break

      case MessageType.CONFIG_CHANGE:
        this.emit('configChange', data)
        break

      case MessageType.BROADCAST:
        this.emit('broadcast', data)
        break

      case MessageType.ERROR:
        console.error('WebSocket服务器错误:', data.message)
        this.emit('error', data)
        break

      default:
        console.warn('未知的WebSocket消息类型:', type)
    }
  }

  /**
   * 触发事件
   */
  private emit(event: string, data: any): void {
    const listeners = this.eventListeners.get(event)
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(data)
        } catch (error) {
          console.error('事件监听器执行失败:', error)
        }
      })
    }
  }

  /**
   * 设置连接状态
   */
  private setStatus(status: ConnectionStatus): void {
    if (this.status !== status) {
      this.status = status
      this.statusListeners.forEach(listener => {
        try {
          listener(status)
        } catch (error) {
          console.error('状态监听器执行失败:', error)
        }
      })
    }
  }

  /**
   * 尝试重连
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('WebSocket重连次数已达上限')
      this.setStatus(ConnectionStatus.ERROR)
      return
    }

    this.reconnectAttempts++
    this.setStatus(ConnectionStatus.RECONNECTING)
    
    console.log(`尝试重连WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
    
    setTimeout(() => {
      this.connect().catch(error => {
        console.error('WebSocket重连失败:', error)
      })
    }, this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1)) // 指数退避
  }

  /**
   * 重新订阅所有类型
   */
  private resubscribeAll(): void {
    this.subscriptions.forEach(type => {
      this.pendingSubscriptions.add(type)
      this.send({
        type: MessageType.SUBSCRIBE,
        subscription_type: type,
        timestamp: Date.now()
      })
    })
  }

  /**
   * 开始心跳检测
   */
  private startHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
    }

    this.heartbeatTimer = setInterval(() => {
      if (this.status === ConnectionStatus.CONNECTED) {
        this.send({
          type: MessageType.PING,
          timestamp: Date.now()
        })
      }
    }, this.heartbeatInterval!) as unknown as number
  }

  /**
   * 清理资源
   */
  private cleanup(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
    
    this.ws = null
    this.clientId = null
  }
}

// 全局WebSocket客户端实例
let globalWebSocketClient: WebSocketClient | null = null

/**
 * 获取全局WebSocket客户端实例
 */
export function getWebSocketClient(): WebSocketClient {
  if (!globalWebSocketClient) {
    globalWebSocketClient = new WebSocketClient()
  }
  return globalWebSocketClient
}

/**
 * 初始化WebSocket连接
 */
export async function initWebSocket(): Promise<WebSocketClient> {
  const client = getWebSocketClient()
  
  if (client.getStatus() === ConnectionStatus.DISCONNECTED) {
    await client.connect()
  }
  
  return client
}

/**
 * 销毁WebSocket连接
 */
export function destroyWebSocket(): void {
  if (globalWebSocketClient) {
    globalWebSocketClient.disconnect()
    globalWebSocketClient = null
  }
}