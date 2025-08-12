# 设计文档

## 概述

改进模型添加表单的用户体验，通过添加文件选择器和附加参数字段，使用户能够更方便地配置模型路径和自定义启动参数。

## 架构

### 组件架构
- **ModelForm.vue**: 主要的模型配置表单组件
- **FileSelector**: 新增的文件选择器组件（可选，或使用HTML5 file input）
- **ParameterInput**: 附加参数输入组件

### 数据流
1. 用户点击文件选择器 → 打开文件对话框
2. 用户选择模型文件 → 文件路径自动填入表单
3. 用户输入附加参数 → 参数保存到模型配置
4. 表单提交 → 包含文件路径和附加参数的完整配置

## 组件和接口

### 文件选择器功能
```typescript
interface FileSelector {
  // 支持的文件类型
  acceptedTypes: string[]
  // 当前选择的文件路径
  selectedPath: string
  // 文件选择事件
  onFileSelect: (path: string) => void
}
```

### 附加参数配置
```typescript
interface AdditionalParameters {
  // 参数字符串
  parameters: string
  // 参数验证
  validate: () => boolean
  // 参数解析
  parse: () => Record<string, any>
}
```

### 表单数据模型扩展
```typescript
interface ModelConfig {
  // 现有字段...
  model_path: string
  additional_parameters?: string  // 新增：附加参数
  // 其他字段...
}
```

## 数据模型

### 文件类型过滤
支持的模型文件格式：
- `.gguf` - GGUF格式模型文件
- `.bin` - 二进制模型文件
- `.safetensors` - SafeTensors格式
- `.pth` - PyTorch模型文件
- `.onnx` - ONNX模型文件

### 参数格式
附加参数支持以下格式：
- 键值对：`--key value`
- 布尔标志：`--flag`
- 多个参数：`--key1 value1 --key2 value2`

## 错误处理

### 文件选择错误
- 文件不存在
- 文件格式不支持
- 文件权限问题
- 路径过长

### 参数验证错误
- 参数格式错误
- 冲突的参数
- 无效的参数值

### 用户反馈
- 清晰的错误消息
- 输入提示和示例
- 实时验证反馈

## 测试策略

### 单元测试
- 文件选择器组件测试
- 参数解析和验证测试
- 表单验证逻辑测试

### 集成测试
- 文件选择到路径填入的完整流程
- 参数输入到模型配置保存的流程
- 表单提交和数据传递测试

### 用户体验测试
- 文件选择器的易用性
- 参数输入的直观性
- 错误处理的友好性