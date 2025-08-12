<template>
  <f7-popup :opened="opened" @popup:closed="$emit('close')">
    <f7-page>
      <f7-navbar :title="isEdit ? '编辑模型' : '添加模型'">
        <f7-nav-left>
          <f7-link @click="$emit('close')">取消</f7-link>
        </f7-nav-left>
        <f7-nav-right>
          <f7-link @click="handleSubmit" :class="{ disabled: !isFormValid }">
            {{ isEdit ? '更新' : '创建' }}
          </f7-link>
        </f7-nav-right>
      </f7-navbar>
      
      <f7-page-content>
        <f7-block-title>基本信息</f7-block-title>
        <f7-list>
          <f7-list-input
            v-model:value="form.name"
            label="模型名称"
            type="text"
            placeholder="输入模型名称"
            :error-message="errors.name"
            :error-message-force="!!errors.name"
            required
          />
          
          <f7-list-item>
            <f7-input
              v-model:value="form.model_path"
              label="模型路径"
              type="text"
              placeholder="输入模型文件路径或点击浏览选择"
              :error-message="errors.model_path"
              :error-message-force="!!errors.model_path"
              required
            />
            <div slot="after" class="file-selector-container">
              <f7-button
                small
                outline
                @click="openFileSelector"
                class="file-selector-btn"
              >
                文件
              </f7-button>
              <f7-button
                small
                outline
                @click="openFolderSelector"
                class="file-selector-btn"
                style="margin-left: 4px;"
              >
                文件夹
              </f7-button>
              <input
                ref="fileInput"
                type="file"
                accept=".gguf,.bin,.safetensors,.pth,.onnx"
                @change="handleFileSelect"
                style="display: none"
              />
              <input
                ref="folderInput"
                type="file"
                webkitdirectory
                @change="handleFolderSelect"
                style="display: none"
              />
            </div>
          </f7-list-item>
          
          <f7-list-input
            v-model:value="form.priority"
            label="优先级"
            type="number"
            min="1"
            max="10"
            placeholder="1-10，数字越大优先级越高"
            :error-message="errors.priority"
            :error-message-force="!!errors.priority"
            required
          />
          
          <f7-list-item>
            <f7-input
              v-model:value="form.additional_parameters"
              label="附加参数"
              type="textarea"
              placeholder="例如: --ctx-size 4096 --n-gpu-layers 32"
              :error-message="errors.additional_parameters"
              :error-message-force="!!errors.additional_parameters"
              resizable
            />
            <div slot="footer" class="parameter-help">
              <small>
                支持格式：--参数名 值 或 --标志<br>
                多个参数用空格分隔，例如：--ctx-size 4096 --temperature 0.7
              </small>
            </div>
          </f7-list-item>
        </f7-list>
        
        <f7-block-title>框架配置</f7-block-title>
        <f7-list>
          <f7-list-item
            title="推理框架"
            smart-select
            :smart-select-params="{ openIn: 'popup', closeOnSelect: true }"
          >
            <select v-model="form.framework" name="framework">
              <option value="llama_cpp">llama.cpp</option>
              <option value="vllm">vLLM</option>
              <option value="docker">Docker</option>
            </select>
          </f7-list-item>
        </f7-list>
        
        <f7-block-title>GPU配置</f7-block-title>
        <f7-list>
          <f7-list-item title="GPU设备">
            <div class="gpu-selection">
              <f7-checkbox
                v-for="gpu in availableGPUs"
                :key="gpu.device_id"
                :value="gpu.device_id"
                :checked="form.gpu_devices.includes(gpu.device_id)"
                @change="toggleGPU(gpu.device_id, $event.target.checked)"
              >
                GPU {{ gpu.device_id }} ({{ gpu.name }})
                <div class="gpu-info">
                  {{ Math.round(gpu.memory_free / 1024) }}GB 可用 / {{ Math.round(gpu.memory_total / 1024) }}GB 总计
                </div>
              </f7-checkbox>
            </div>
          </f7-list-item>
        </f7-list>
        
        <f7-block-title>资源需求</f7-block-title>
        <f7-list>
          <f7-list-input
            v-model:value="form.resource_requirements.gpu_memory"
            label="GPU内存需求 (MB)"
            type="number"
            min="0"
            placeholder="预估GPU内存需求"
          />
          
          <f7-list-input
            v-model:value="form.resource_requirements.gpu_count"
            label="GPU数量"
            type="number"
            min="1"
            placeholder="需要的GPU数量"
          />
        </f7-list>
        
        <f7-block-title>高级配置</f7-block-title>
        <f7-list>
          <f7-list-item
            title="启用健康检查"
            :after="form.health_check.enabled ? '开启' : '关闭'"
          >
            <f7-toggle
              slot="after"
              :checked="form.health_check.enabled"
              @toggle:change="form.health_check.enabled = $event"
            />
          </f7-list-item>
          
          <template v-if="form.health_check.enabled">
            <f7-list-input
              v-model:value="form.health_check.interval"
              label="检查间隔 (秒)"
              type="number"
              min="10"
            />
            
            <f7-list-input
              v-model:value="form.health_check.timeout"
              label="超时时间 (秒)"
              type="number"
              min="1"
            />
            
            <f7-list-input
              v-model:value="form.health_check.retries"
              label="重试次数"
              type="number"
              min="0"
            />
          </template>
        </f7-list>
        
        <f7-block-title>重试策略</f7-block-title>
        <f7-list>
          <f7-list-input
            v-model:value="form.retry_policy.max_retries"
            label="最大重试次数"
            type="number"
            min="0"
          />
          
          <f7-list-input
            v-model:value="form.retry_policy.retry_interval"
            label="重试间隔 (秒)"
            type="number"
            min="1"
          />
          
          <f7-list-input
            v-model:value="form.retry_policy.backoff_factor"
            label="退避因子"
            type="number"
            min="1"
            step="0.1"
          />
        </f7-list>
        
        <!-- 框架特定参数 -->
        <template v-if="form.framework === 'llama_cpp'">
          <f7-block-title>llama.cpp 参数</f7-block-title>
          <f7-list>
            <f7-list-input
              v-model:value="form.parameters.port"
              label="端口"
              type="number"
              min="1024"
              max="65535"
              placeholder="8080"
            />
            
            <f7-list-input
              v-model:value="form.parameters.host"
              label="主机地址"
              type="text"
              placeholder="0.0.0.0"
            />
            
            <f7-list-input
              v-model:value="form.parameters.ctx_size"
              label="上下文长度"
              type="number"
              min="512"
              placeholder="2048"
            />
            
            <f7-list-input
              v-model:value="form.parameters.n_gpu_layers"
              label="GPU层数"
              type="number"
              min="0"
              placeholder="32"
            />
          </f7-list>
        </template>
        
        <template v-if="form.framework === 'vllm'">
          <f7-block-title>vLLM 参数</f7-block-title>
          <f7-list>
            <f7-list-input
              v-model:value="form.parameters.port"
              label="端口"
              type="number"
              min="1024"
              max="65535"
              placeholder="8000"
            />
            
            <f7-list-input
              v-model:value="form.parameters.host"
              label="主机地址"
              type="text"
              placeholder="0.0.0.0"
            />
            
            <f7-list-input
              v-model:value="form.parameters.max_model_len"
              label="最大模型长度"
              type="number"
              min="512"
              placeholder="4096"
            />
            
            <f7-list-input
              v-model:value="form.parameters.tensor_parallel_size"
              label="张量并行大小"
              type="number"
              min="1"
              placeholder="1"
            />
          </f7-list>
        </template>
        
        <template v-if="form.framework === 'docker'">
          <f7-block-title>Docker 参数</f7-block-title>
          <f7-list>
            <f7-list-input
              v-model:value="form.parameters.image"
              label="Docker镜像"
              type="text"
              placeholder="vllm/vllm-openai:latest"
            />
            
            <f7-list-input
              v-model:value="form.parameters.container_name"
              label="容器名称"
              type="text"
              placeholder="自动生成"
            />
            
            <f7-list-input
              v-model:value="form.parameters.port_mapping"
              label="端口映射"
              type="text"
              placeholder="8000:8000"
            />
          </f7-list>
        </template>
      </f7-page-content>
    </f7-page>
  </f7-popup>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import type { ModelConfig, ModelInfo, GPUInfo } from '@/types'
import { FrameworkType } from '@/types'
import { useSystemStore } from '@/stores/system'

interface Props {
  opened: boolean
  model?: ModelInfo
}

interface Emits {
  (e: 'close'): void
  (e: 'submit', config: ModelConfig): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const systemStore = useSystemStore()

// 是否为编辑模式
const isEdit = computed(() => !!props.model)

// 可用GPU列表
const availableGPUs = ref<GPUInfo[]>([])

// 文件输入引用
const fileInput = ref<HTMLInputElement>()
const folderInput = ref<HTMLInputElement>()

// 表单数据
const form = ref<ModelConfig>({
  id: '',
  name: '',
  framework: FrameworkType.LLAMA_CPP,
  model_path: '',
  priority: 5,
  gpu_devices: [],
  additional_parameters: '',
  parameters: {
    port: 8080,
    host: '0.0.0.0'
  },
  resource_requirements: {
    gpu_memory: 4096,
    gpu_count: 1
  },
  health_check: {
    enabled: true,
    interval: 30,
    timeout: 10,
    retries: 3
  },
  retry_policy: {
    max_retries: 3,
    retry_interval: 60,
    backoff_factor: 2.0
  }
})

// 表单验证错误
const errors = ref<Record<string, string>>({})

// 表单是否有效
const isFormValid = computed(() => {
  return form.value.name.trim() !== '' &&
         form.value.model_path.trim() !== '' &&
         form.value.priority >= 1 && form.value.priority <= 10 &&
         form.value.gpu_devices.length > 0 &&
         Object.keys(errors.value).length === 0
})

// 监听模型变化，初始化表单
watch(() => props.model, (newModel) => {
  if (newModel) {
    form.value = { ...newModel }
  } else {
    resetForm()
  }
}, { immediate: true })

// 监听框架变化，更新默认参数
watch(() => form.value.framework, (newFramework) => {
  switch (newFramework) {
    case FrameworkType.LLAMA_CPP:
      form.value.parameters = {
        port: 8080,
        host: '0.0.0.0',
        ctx_size: 2048,
        n_gpu_layers: 32
      }
      break
    case FrameworkType.VLLM:
      form.value.parameters = {
        port: 8000,
        host: '0.0.0.0',
        max_model_len: 4096,
        tensor_parallel_size: 1
      }
      break
    case FrameworkType.DOCKER:
      form.value.parameters = {
        image: 'vllm/vllm-openai:latest',
        container_name: '',
        port_mapping: '8000:8000'
      }
      break
  }
})

// 监听附加参数变化，实时验证
watch(() => form.value.additional_parameters, (newParams) => {
  if (newParams && newParams.trim()) {
    validateAdditionalParameters(newParams)
  } else {
    // 清除参数错误
    if (errors.value.additional_parameters) {
      delete errors.value.additional_parameters
    }
  }
})

// 监听模型路径变化，智能填写模型名称
watch(() => form.value.model_path, (newPath, oldPath) => {
  // 只有在非编辑模式下才自动填写
  if (!isEdit.value && newPath.trim()) {
    // 如果模型名称为空，或者名称是从旧路径自动生成的，则更新名称
    const oldGeneratedName = oldPath ? generateModelNameFromPath(oldPath) : ''
    const currentName = form.value.name.trim()
    
    if (!currentName || currentName === oldGeneratedName) {
      form.value.name = generateModelNameFromPath(newPath)
    }
  }
})

// 重置表单
const resetForm = () => {
  form.value = {
    id: '',
    name: '',
    framework: FrameworkType.LLAMA_CPP,
    model_path: '',
    priority: 5,
    gpu_devices: [],
    additional_parameters: '',
    parameters: {
      port: 8080,
      host: '0.0.0.0'
    },
    resource_requirements: {
      gpu_memory: 4096,
      gpu_count: 1
    },
    health_check: {
      enabled: true,
      interval: 30,
      timeout: 10,
      retries: 3
    },
    retry_policy: {
      max_retries: 3,
      retry_interval: 60,
      backoff_factor: 2.0
    }
  }
  errors.value = {}
}

// 切换GPU选择
const toggleGPU = (deviceId: number, checked: boolean) => {
  if (checked) {
    if (!form.value.gpu_devices.includes(deviceId)) {
      form.value.gpu_devices.push(deviceId)
    }
  } else {
    form.value.gpu_devices = form.value.gpu_devices.filter(id => id !== deviceId)
  }
}

// 验证附加参数格式
const validateAdditionalParameters = (params: string): boolean => {
  if (!params.trim()) {
    return true // 空参数是有效的
  }
  
  // 基本的参数格式验证：检查是否包含 -- 开头的参数
  const paramPattern = /--[\w-]+(\s+[\w.-]+)?/g
  const matches = params.match(paramPattern)
  
  if (!matches) {
    errors.value.additional_parameters = '参数格式错误。请使用 --参数名 值 的格式'
    return false
  }
  
  // 检查是否有未匹配的内容（可能的格式错误）
  const matchedLength = matches.join(' ').length
  const cleanParams = params.replace(/\s+/g, ' ').trim()
  
  if (matchedLength < cleanParams.length * 0.8) {
    errors.value.additional_parameters = '参数格式可能有误。请检查参数格式'
    return false
  }
  
  return true
}

// 验证表单
const validateForm = () => {
  errors.value = {}
  
  if (!form.value.name.trim()) {
    errors.value.name = '模型名称不能为空'
  }
  
  if (!form.value.model_path.trim()) {
    errors.value.model_path = '模型路径不能为空'
  }
  
  if (form.value.priority < 1 || form.value.priority > 10) {
    errors.value.priority = '优先级必须在1-10之间'
  }
  
  if (form.value.gpu_devices.length === 0) {
    errors.value.gpu_devices = '至少选择一个GPU设备'
  }
  
  // 验证附加参数
  if (form.value.additional_parameters) {
    validateAdditionalParameters(form.value.additional_parameters)
  }
  
  return Object.keys(errors.value).length === 0
}

// 提交表单
const handleSubmit = () => {
  if (validateForm()) {
    emit('submit', { ...form.value })
  }
}

// 打开文件选择器
const openFileSelector = () => {
  if (fileInput.value) {
    fileInput.value.click()
  }
}

// 打开文件夹选择器
const openFolderSelector = () => {
  if (folderInput.value) {
    folderInput.value.click()
  }
}

// 处理文件选择
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  
  if (file) {
    // 在浏览器环境中，我们只能获取文件名，不能获取完整路径
    // 但我们可以显示文件名，让用户知道选择了什么文件
    form.value.model_path = file.name
    
    // 清除可能的路径错误
    if (errors.value.model_path) {
      delete errors.value.model_path
    }
    
    // 可以在这里添加文件验证逻辑
    validateSelectedFile(file)
  }
}

// 处理文件夹选择
const handleFolderSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = target.files
  
  if (files && files.length > 0) {
    // 获取第一个文件的路径，提取文件夹路径
    const firstFile = files[0]
    const folderPath = firstFile.webkitRelativePath.split('/')[0]
    
    // 设置文件夹路径
    form.value.model_path = folderPath
    
    // 清除可能的路径错误
    if (errors.value.model_path) {
      delete errors.value.model_path
    }
  }
}

// 验证选择的文件
const validateSelectedFile = (file: File) => {
  const allowedExtensions = ['.gguf', '.bin', '.safetensors', '.pth', '.onnx']
  const fileName = file.name.toLowerCase()
  
  const isValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext))
  
  if (!isValidExtension) {
    errors.value.model_path = `不支持的文件格式。支持的格式：${allowedExtensions.join(', ')}`
  } else {
    // 清除错误信息
    if (errors.value.model_path) {
      delete errors.value.model_path
    }
  }
}

// 从路径生成模型名称
const generateModelNameFromPath = (path: string): string => {
  if (!path.trim()) return ''
  
  // 移除路径分隔符，获取最后一部分
  const pathParts = path.replace(/\\/g, '/').split('/')
  let fileName = pathParts[pathParts.length - 1]
  
  // 如果是文件，移除扩展名
  const fileExtensions = ['.gguf', '.bin', '.safetensors', '.pth', '.onnx']
  for (const ext of fileExtensions) {
    if (fileName.toLowerCase().endsWith(ext)) {
      fileName = fileName.slice(0, -ext.length)
      break
    }
  }
  
  // 清理文件名，移除特殊字符，用空格替换下划线和连字符
  let modelName = fileName
    .replace(/[_-]/g, ' ')
    .replace(/[^\w\s\u4e00-\u9fff]/g, '')
    .trim()
  
  // 首字母大写
  modelName = modelName.replace(/\b\w/g, char => char.toUpperCase())
  
  // 如果处理后为空，使用原始文件名
  if (!modelName) {
    modelName = fileName || 'New Model'
  }
  
  return modelName
}

// 加载GPU信息
const loadGPUInfo = async () => {
  try {
    await systemStore.fetchGPUInfo()
    availableGPUs.value = systemStore.gpuInfo
  } catch (error) {
    console.error('加载GPU信息失败:', error)
  }
}

onMounted(() => {
  loadGPUInfo()
})
</script>

<style scoped>
.gpu-selection {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0;
}

.gpu-info {
  font-size: 12px;
  color: var(--f7-text-color-secondary);
  margin-top: 4px;
}

.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.file-selector-container {
  display: flex;
  align-items: center;
  margin-left: 8px;
}

.file-selector-btn {
  min-width: 60px;
  height: 32px;
}

.parameter-help {
  margin-top: 8px;
  padding: 8px 0;
}

.parameter-help small {
  color: var(--f7-text-color-secondary);
  line-height: 1.4;
}
</style>