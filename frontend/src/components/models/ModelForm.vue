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
          
          <f7-list-input
            v-model:value="form.model_path"
            label="模型路径"
            type="text"
            placeholder="输入模型文件路径"
            :error-message="errors.model_path"
            :error-message-force="!!errors.model_path"
            required
          />
          
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

// 表单数据
const form = ref<ModelConfig>({
  id: '',
  name: '',
  framework: FrameworkType.LLAMA_CPP,
  model_path: '',
  priority: 5,
  gpu_devices: [],
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

// 重置表单
const resetForm = () => {
  form.value = {
    id: '',
    name: '',
    framework: FrameworkType.LLAMA_CPP,
    model_path: '',
    priority: 5,
    gpu_devices: [],
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
  
  return Object.keys(errors.value).length === 0
}

// 提交表单
const handleSubmit = () => {
  if (validateForm()) {
    emit('submit', { ...form.value })
  }
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
</style>