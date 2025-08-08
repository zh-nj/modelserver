/**
 * 简单的监控组件测试
 */

// 模拟测试监控数据结构
const testGpuData = [
  {
    device_id: 0,
    name: 'NVIDIA RTX 4090',
    memory_total: 24576,
    memory_used: 18432,
    memory_free: 6144,
    utilization: 75,
    temperature: 68,
    power_usage: 320
  },
  {
    device_id: 1,
    name: 'NVIDIA RTX 4090',
    memory_total: 24576,
    memory_used: 12288,
    memory_free: 12288,
    utilization: 45,
    temperature: 62,
    power_usage: 280
  }
]

const testSystemOverview = {
  total_models: 8,
  running_models: 5,
  total_gpus: 4,
  available_gpus: 2,
  total_memory: 98304,
  used_memory: 59392,
  free_memory: 38912,
  uptime: 172800
}

// 测试数据格式化函数
function formatMemorySize(sizeInMB) {
  if (sizeInMB >= 1024) {
    return `${(sizeInMB / 1024).toFixed(1)}GB`
  }
  return `${sizeInMB}MB`
}

function formatUptime(seconds) {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) {
    return `${days}天${hours}小时${minutes}分钟`
  } else if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else {
    return `${minutes}分钟`
  }
}

function getGpuStatusColor(utilization, temperature) {
  if (temperature > 80 || utilization > 90) return 'red'
  if (temperature > 70 || utilization > 70) return 'orange'
  return 'green'
}

// 运行测试
console.log('=== 监控组件测试 ===')

console.log('\n1. GPU数据测试:')
testGpuData.forEach(gpu => {
  console.log(`GPU ${gpu.device_id}: ${gpu.name}`)
  console.log(`  利用率: ${gpu.utilization}%`)
  console.log(`  内存: ${formatMemorySize(gpu.memory_used)} / ${formatMemorySize(gpu.memory_total)}`)
  console.log(`  温度: ${gpu.temperature}°C`)
  console.log(`  状态: ${getGpuStatusColor(gpu.utilization, gpu.temperature)}`)
  console.log('')
})

console.log('2. 系统概览测试:')
console.log(`运行模型: ${testSystemOverview.running_models}/${testSystemOverview.total_models}`)
console.log(`可用GPU: ${testSystemOverview.available_gpus}/${testSystemOverview.total_gpus}`)
console.log(`内存使用: ${formatMemorySize(testSystemOverview.used_memory)} / ${formatMemorySize(testSystemOverview.total_memory)}`)
console.log(`运行时间: ${formatUptime(testSystemOverview.uptime)}`)

console.log('\n3. 计算属性测试:')
const totalGpuMemory = testGpuData.reduce((total, gpu) => total + gpu.memory_total, 0)
const usedGpuMemory = testGpuData.reduce((total, gpu) => total + gpu.memory_used, 0)
const averageUtilization = Math.round(testGpuData.reduce((sum, gpu) => sum + gpu.utilization, 0) / testGpuData.length)
const averageTemperature = Math.round(testGpuData.reduce((sum, gpu) => sum + gpu.temperature, 0) / testGpuData.length)

console.log(`总GPU内存: ${formatMemorySize(totalGpuMemory)}`)
console.log(`已用GPU内存: ${formatMemorySize(usedGpuMemory)}`)
console.log(`平均利用率: ${averageUtilization}%`)
console.log(`平均温度: ${averageTemperature}°C`)

console.log('\n✅ 监控组件测试完成')