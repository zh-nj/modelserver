/**
 * WebSocket功能测试脚本
 * 用于验证实时数据更新功能是否正常工作
 */

// 模拟浏览器环境
global.WebSocket = class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = 0 // CONNECTING
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.onerror = null
    
    // 模拟连接成功
    setTimeout(() => {
      this.readyState = 1 // OPEN
      if (this.onopen) {
        this.onopen({ type: 'open' })
      }
      
      // 模拟接收连接确认消息
      setTimeout(() => {
        if (this.onmessage) {
          this.onmessage({
            data: JSON.stringify({
              type: 'connection_established',
              data: { client_id: 'test-client-123' },
              timestamp: Date.now()
            })
          })
        }
      }, 100)
      
      // 模拟接收GPU指标更新
      setInterval(() => {
        if (this.onmessage && this.readyState === 1) {
          this.onmessage({
            data: JSON.stringify({
              type: 'gpu_metrics_update',
              data: [
                {
                  device_id: 0,
                  name: 'NVIDIA RTX 4090',
                  memory_total: 24576,
                  memory_used: 18432 + Math.random() * 2000,
                  memory_free: 6144 - Math.random() * 2000,
                  utilization: 75 + Math.random() * 20,
                  temperature: 68 + Math.random() * 15,
                  power_usage: 320 + Math.random() * 50
                },
                {
                  device_id: 1,
                  name: 'NVIDIA RTX 4090',
                  memory_total: 24576,
                  memory_used: 12288 + Math.random() * 3000,
                  memory_free: 12288 - Math.random() * 3000,
                  utilization: 45 + Math.random() * 30,
                  temperature: 62 + Math.random() * 18,
                  power_usage: 280 + Math.random() * 60
                }
              ],
              timestamp: Date.now()
            })
          })
        }
      }, 3000)
      
    }, 500)
  }
  
  send(data) {
    console.log('WebSocket发送消息:', data)
    
    // 模拟心跳响应
    const message = JSON.parse(data)
    if (message.type === 'ping') {
      setTimeout(() => {
        if (this.onmessage) {
          this.onmessage({
            data: JSON.stringify({
              type: 'pong',
              timestamp: Date.now()
            })
          })
        }
      }, 50)
    }
  }
  
  close(code, reason) {
    this.readyState = 3 // CLOSED
    if (this.onclose) {
      this.onclose({ code, reason })
    }
  }
}

// 模拟window对象
global.window = {
  location: {
    protocol: 'http:',
    host: 'localhost:8080'
  }
}

// 导入WebSocket客户端
const { WebSocketClient, ConnectionStatus, SubscriptionType } = require('./src/services/websocket.ts')

async function testWebSocketClient() {
  console.log('开始测试WebSocket客户端...')
  
  try {
    // 创建WebSocket客户端实例
    const client = new WebSocketClient()
    
    // 添加状态监听器
    client.onStatusChange((status) => {
      console.log(`连接状态变化: ${status}`)
    })
    
    // 添加事件监听器
    client.on('gpuMetricsUpdate', (data) => {
      console.log('收到GPU指标更新:', data.length, '个GPU')
      data.forEach(gpu => {
        console.log(`  GPU ${gpu.device_id}: ${gpu.utilization.toFixed(1)}% 利用率, ${gpu.temperature.toFixed(1)}°C`)
      })
    })
    
    client.on('modelStatusUpdate', (data) => {
      console.log('收到模型状态更新:', data)
    })
    
    // 连接WebSocket
    console.log('正在连接WebSocket...')
    await client.connect()
    console.log('WebSocket连接成功!')
    
    // 订阅GPU指标更新
    console.log('订阅GPU指标更新...')
    client.subscribe(SubscriptionType.GPU_METRICS)
    
    // 订阅模型状态更新
    console.log('订阅模型状态更新...')
    client.subscribe(SubscriptionType.MODEL_UPDATES)
    
    // 等待一段时间接收数据
    console.log('等待接收实时数据...')
    await new Promise(resolve => setTimeout(resolve, 10000))
    
    // 断开连接
    console.log('断开WebSocket连接...')
    client.disconnect()
    
    console.log('WebSocket客户端测试完成!')
    
  } catch (error) {
    console.error('WebSocket客户端测试失败:', error)
  }
}

// 运行测试
if (require.main === module) {
  testWebSocketClient()
}

module.exports = { testWebSocketClient }