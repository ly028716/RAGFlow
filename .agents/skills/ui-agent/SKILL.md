---
name: ui-agent
description: UI/UX设计师。界面视觉设计、交互设计、设计规范、组件库设计、响应式布局时使用。
allowed-tools: Read, Grep, Glob
---

# UI/UX 设计 Skill

为 RAGAgentLangChain 项目提供完整的 UI/UX 设计支持，包括界面设计、交互设计、设计规范、组件库设计等。

## 核心职责

- 界面视觉设计和布局规划
- 交互设计和用户体验优化
- 设计规范和设计系统制定
- 组件库设计和使用规范
- 响应式设计和适配方案
- 可访问性设计（A11y）
- 用户研究和可用性测试
- 设计原型和交互演示
- 设计文档和规范输出

## 技术栈

### 前端框架
- **UI框架**: Vue 3.5+
- **组件库**: Element Plus 2.9+
- **图标库**: @element-plus/icons-vue
- **样式**: SCSS/Sass
- **响应式**: CSS Grid + Flexbox

### 设计工具
- **原型设计**: Figma, Sketch, Adobe XD
- **图标设计**: Figma, Illustrator
- **配色工具**: Coolors, Adobe Color
- **字体工具**: Google Fonts, Font Awesome
- **设计系统**: Storybook（可选）

### 设计规范
- **设计语言**: Material Design 3, Fluent Design
- **组件规范**: Element Plus Design System
- **可访问性**: WCAG 2.1 AA级标准
- **响应式**: Mobile First 设计原则

## 项目设计架构

```
RAGAgentLangChain/
├── frontend/
│   ├── src/
│   │   ├── assets/              # 静态资源
│   │   │   ├── images/          # 图片资源
│   │   │   ├── icons/           # 图标资源
│   │   │   └── styles/          # 全局样式
│   │   │       ├── variables.scss    # 设计变量
│   │   │       ├── mixins.scss       # 样式混入
│   │   │       └── global.scss       # 全局样式
│   │   ├── components/          # 组件
│   │   │   ├── common/          # 通用组件
│   │   │   ├── chat/            # 聊天组件
│   │   │   ├── knowledge/       # 知识库组件
│   │   │   └── agent/           # Agent组件
│   │   └── views/               # 页面视图
│   └── design/                  # 设计文档（可选）
│       ├── design-system.md     # 设计系统文档
│       ├── components.md        # 组件设计规范
│       └── prototypes/          # 原型文件
└── docs/
    └── design/                  # 设计文档
        ├── ui-guidelines.md     # UI设计指南
        └── ux-guidelines.md     # UX设计指南
```

## 设计原则

### 1. 一致性原则

**视觉一致性**：
- 统一的配色方案
- 统一的字体系统
- 统一的图标风格
- 统一的间距规范

**交互一致性**：
- 统一的操作反馈
- 统一的导航模式
- 统一的表单交互
- 统一的错误提示

**代码示例**：

```scss
// frontend/src/assets/styles/variables.scss
// 设计变量定义

// 主题色
$primary-color: #409EFF;        // Element Plus 主色
$success-color: #67C23A;
$warning-color: #E6A23C;
$danger-color: #F56C6C;
$info-color: #909399;

// 中性色
$text-primary: #303133;
$text-regular: #606266;
$text-secondary: #909399;
$text-placeholder: #C0C4CC;

$border-base: #DCDFE6;
$border-light: #E4E7ED;
$border-lighter: #EBEEF5;
$border-extra-light: #F2F6FC;

$background-base: #F5F7FA;
$background-light: #FAFAFA;

// 字体
$font-family-base: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                   "Helvetica Neue", Arial, sans-serif;
$font-size-base: 14px;
$font-size-small: 12px;
$font-size-large: 16px;
$font-size-extra-large: 18px;

// 间距
$spacing-xs: 4px;
$spacing-sm: 8px;
$spacing-md: 16px;
$spacing-lg: 24px;
$spacing-xl: 32px;

// 圆角
$border-radius-base: 4px;
$border-radius-small: 2px;
$border-radius-large: 8px;
$border-radius-round: 20px;

// 阴影
$box-shadow-base: 0 2px 4px rgba(0, 0, 0, 0.12), 0 0 6px rgba(0, 0, 0, 0.04);
$box-shadow-light: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
$box-shadow-dark: 0 2px 8px 0 rgba(0, 0, 0, 0.15);

// 动画
$transition-base: all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
$transition-fade: opacity 0.3s cubic-bezier(0.23, 1, 0.32, 1);
```

### 2. 简洁性原则

**视觉简洁**：
- 避免过度装饰
- 突出核心内容
- 合理使用留白
- 清晰的视觉层次

**交互简洁**：
- 减少操作步骤
- 提供快捷操作
- 智能默认值
- 渐进式展示

### 3. 反馈原则

**即时反馈**：
- 按钮点击反馈
- 表单验证反馈
- 加载状态提示
- 操作结果通知

**代码示例**：

```vue
<!-- 按钮加载状态 -->
<template>
  <el-button
    type="primary"
    :loading="isLoading"
    @click="handleSubmit"
  >
    {{ isLoading ? '提交中...' : '提交' }}
  </el-button>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const isLoading = ref(false)

const handleSubmit = async () => {
  isLoading.value = true
  try {
    await submitData()
    ElMessage.success('提交成功')
  } catch (error) {
    ElMessage.error('提交失败，请重试')
  } finally {
    isLoading.value = false
  }
}
</script>
```

### 4. 容错性原则

**错误预防**：
- 输入验证
- 操作确认
- 危险操作警告
- 智能提示

**错误恢复**：
- 清晰的错误信息
- 提供解决方案
- 支持撤销操作
- 保存用户输入

**代码示例**：

```vue
<!-- 危险操作确认 -->
<template>
  <el-popconfirm
    title="确定要删除这条对话吗？此操作不可恢复。"
    confirm-button-text="确定删除"
    cancel-button-text="取消"
    confirm-button-type="danger"
    @confirm="handleDelete"
  >
    <template #reference>
      <el-button type="danger" size="small">删除</el-button>
    </template>
  </el-popconfirm>
</template>
```

### 5. 可访问性原则

**键盘导航**：
- 支持Tab键导航
- 支持快捷键操作
- 焦点状态明显
- 逻辑导航顺序

**屏幕阅读器**：
- 语义化HTML
- ARIA标签
- 替代文本
- 状态通知

**代码示例**：

```vue
<!-- 可访问性优化 -->
<template>
  <button
    class="icon-button"
    aria-label="发送消息"
    :aria-disabled="disabled"
    @click="handleSend"
  >
    <el-icon><Send /></el-icon>
  </button>

  <img
    src="/avatar.png"
    alt="用户头像"
    role="img"
  />

  <div
    role="alert"
    aria-live="polite"
    v-if="errorMessage"
  >
    {{ errorMessage }}
  </div>
</template>
```

## 设计系统

### 1. 色彩系统

**主色调**：
- Primary: #409EFF（品牌色，主要操作）
- Success: #67C23A（成功状态）
- Warning: #E6A23C（警告状态）
- Danger: #F56C6C（危险操作）
- Info: #909399（信息提示）

**中性色**：
- 文本色：#303133（主要文本）
- 次要文本：#606266（次要文本）
- 占位文本：#C0C4CC（占位符）
- 边框色：#DCDFE6（边框）
- 背景色：#F5F7FA（背景）

**使用规范**：
```scss
// 正确使用
.primary-button {
  background-color: $primary-color;
  color: #FFFFFF;
}

// 错误使用 - 不要硬编码颜色
.primary-button {
  background-color: #409EFF;  // ❌ 应使用变量
}
```

### 2. 字体系统

**字体家族**：
```scss
$font-family-base: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                   "Helvetica Neue", Arial, "Noto Sans", sans-serif,
                   "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol",
                   "Noto Color Emoji";

$font-family-code: "SFMono-Regular", Consolas, "Liberation Mono", Menlo,
                   Courier, monospace;
```

**字体大小**：
- Extra Large: 18px（页面标题）
- Large: 16px（区块标题）
- Base: 14px（正文）
- Small: 12px（辅助信息）

**字重**：
- Regular: 400（正文）
- Medium: 500（强调）
- Bold: 600（标题）

**行高**：
- 标题：1.2
- 正文：1.5
- 密集：1.3

### 3. 间距系统

**8px 基准间距系统**：
```scss
$spacing-xs: 4px;   // 0.5x
$spacing-sm: 8px;   // 1x
$spacing-md: 16px;  // 2x
$spacing-lg: 24px;  // 3x
$spacing-xl: 32px;  // 4x
$spacing-xxl: 48px; // 6x
```

**使用场景**：
- 组件内间距：4px, 8px
- 组件间间距：16px, 24px
- 区块间距：32px, 48px
- 页面边距：24px, 32px

### 4. 圆角系统

```scss
$border-radius-small: 2px;   // 小元素（标签）
$border-radius-base: 4px;    // 基础元素（按钮、输入框）
$border-radius-large: 8px;   // 大元素（卡片）
$border-radius-round: 20px;  // 圆形元素（头像）
$border-radius-circle: 50%;  // 完全圆形
```

### 5. 阴影系统

```scss
// 基础阴影 - 悬浮元素
$box-shadow-base: 0 2px 4px rgba(0, 0, 0, 0.12),
                  0 0 6px rgba(0, 0, 0, 0.04);

// 轻阴影 - 卡片
$box-shadow-light: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

// 深阴影 - 弹窗
$box-shadow-dark: 0 2px 8px 0 rgba(0, 0, 0, 0.15);
```

## 组件设计规范

### 1. 按钮设计

**类型**：
- Primary：主要操作（提交、确认）
- Default：次要操作（取消、返回）
- Text：文本按钮（链接操作）
- Danger：危险操作（删除）

**尺寸**：
- Large：高40px（重要操作）
- Default：高32px（常规操作）
- Small：高24px（紧凑场景）

**状态**：
- Normal：正常状态
- Hover：悬停状态
- Active：激活状态
- Disabled：禁用状态
- Loading：加载状态

**代码示例**：

```vue
<template>
  <!-- 主要按钮 -->
  <el-button type="primary" size="default">
    提交
  </el-button>

  <!-- 次要按钮 -->
  <el-button size="default">
    取消
  </el-button>

  <!-- 危险按钮 -->
  <el-button type="danger" size="small">
    删除
  </el-button>

  <!-- 文本按钮 -->
  <el-button type="text">
    查看详情
  </el-button>

  <!-- 加载状态 -->
  <el-button type="primary" :loading="true">
    提交中...
  </el-button>

  <!-- 图标按钮 -->
  <el-button type="primary" :icon="Search">
    搜索
  </el-button>
</template>
```

### 2. 表单设计

**输入框**：
- 单行输入：文本、数字、邮箱等
- 多行输入：文本域
- 选择器：下拉选择、日期选择
- 开关：Switch、Checkbox、Radio

**表单布局**：
- 标签位置：左对齐、顶部对齐
- 标签宽度：固定宽度（100px-120px）
- 输入框宽度：根据内容调整
- 表单间距：16px-24px

**代码示例**：

```vue
<template>
  <el-form
    :model="form"
    :rules="rules"
    label-width="120px"
    label-position="right"
  >
    <!-- 文本输入 -->
    <el-form-item label="用户名" prop="username">
      <el-input
        v-model="form.username"
        placeholder="请输入用户名"
        clearable
      />
    </el-form-item>

    <!-- 密码输入 -->
    <el-form-item label="密码" prop="password">
      <el-input
        v-model="form.password"
        type="password"
        placeholder="请输入密码"
        show-password
      />
    </el-form-item>

    <!-- 下拉选择 -->
    <el-form-item label="角色" prop="role">
      <el-select v-model="form.role" placeholder="请选择角色">
        <el-option label="管理员" value="admin" />
        <el-option label="普通用户" value="user" />
      </el-select>
    </el-form-item>

    <!-- 开关 -->
    <el-form-item label="启用状态">
      <el-switch v-model="form.enabled" />
    </el-form-item>

    <!-- 按钮组 -->
    <el-form-item>
      <el-button type="primary" @click="handleSubmit">
        提交
      </el-button>
      <el-button @click="handleReset">
        重置
      </el-button>
    </el-form-item>
  </el-form>
</template>
```

### 3. 卡片设计

**卡片类型**：
- 基础卡片：标题 + 内容
- 带阴影卡片：悬浮效果
- 可折叠卡片：展开/收起
- 操作卡片：带操作按钮

**卡片规范**：
- 内边距：16px-24px
- 圆角：4px-8px
- 阴影：轻阴影
- 间距：16px

**代码示例**：

```vue
<template>
  <!-- 基础卡片 -->
  <el-card class="conversation-card">
    <template #header>
      <div class="card-header">
        <span>对话标题</span>
        <el-button type="text" :icon="More" />
      </div>
    </template>
    <div class="card-content">
      对话内容...
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.conversation-card {
  margin-bottom: $spacing-md;
  border-radius: $border-radius-large;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .card-content {
    color: $text-regular;
    line-height: 1.5;
  }
}
</style>
```

### 4. 对话框设计

**对话框类型**：
- 信息对话框：展示信息
- 确认对话框：确认操作
- 表单对话框：输入信息
- 全屏对话框：复杂内容

**对话框规范**：
- 宽度：小（400px）、中（600px）、大（800px）
- 标题：清晰明确
- 按钮：主要操作在右侧
- 遮罩：半透明黑色

**代码示例**：

```vue
<template>
  <!-- 确认对话框 -->
  <el-dialog
    v-model="dialogVisible"
    title="删除确认"
    width="400px"
  >
    <p>确定要删除这条对话吗？此操作不可恢复。</p>
    <template #footer>
      <el-button @click="dialogVisible = false">
        取消
      </el-button>
      <el-button type="danger" @click="handleDelete">
        确定删除
      </el-button>
    </template>
  </el-dialog>

  <!-- 表单对话框 -->
  <el-dialog
    v-model="formDialogVisible"
    title="创建知识库"
    width="600px"
  >
    <el-form :model="form" label-width="100px">
      <el-form-item label="知识库名称">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="formDialogVisible = false">
        取消
      </el-button>
      <el-button type="primary" @click="handleCreate">
        创建
      </el-button>
    </template>
  </el-dialog>
</template>
```

## 交互设计规范

### 1. 导航设计

**导航类型**：
- 顶部导航：全局导航
- 侧边导航：功能导航
- 面包屑：层级导航
- 标签页：内容切换

**导航规范**：
- 当前页高亮
- 悬停效果
- 图标 + 文字
- 响应式折叠

**代码示例**：

```vue
<template>
  <!-- 侧边导航 -->
  <el-menu
    :default-active="activeMenu"
    class="sidebar-menu"
    @select="handleMenuSelect"
  >
    <el-menu-item index="/chat">
      <el-icon><ChatDotRound /></el-icon>
      <span>对话</span>
    </el-menu-item>

    <el-menu-item index="/knowledge">
      <el-icon><Document /></el-icon>
      <span>知识库</span>
    </el-menu-item>

    <el-menu-item index="/agent">
      <el-icon><Robot /></el-icon>
      <span>Agent</span>
    </el-menu-item>

    <el-menu-item index="/settings">
      <el-icon><Setting /></el-icon>
      <span>设置</span>
    </el-menu-item>
  </el-menu>
</template>

<style scoped lang="scss">
.sidebar-menu {
  height: 100%;
  border-right: 1px solid $border-base;

  .el-menu-item {
    &.is-active {
      background-color: $primary-color;
      color: #FFFFFF;
    }

    &:hover {
      background-color: $background-base;
    }
  }
}
</style>
```

### 2. 加载状态

**加载类型**：
- 全局加载：页面加载
- 局部加载：组件加载
- 按钮加载：操作加载
- 骨架屏：内容占位

**代码示例**：

```vue
<template>
  <!-- 骨架屏 -->
  <el-skeleton :loading="loading" :rows="5" animated>
    <template #default>
      <div class="content">
        实际内容...
      </div>
    </template>
  </el-skeleton>

  <!-- 局部加载 -->
  <div v-loading="loading" class="loading-container">
    内容区域
  </div>
</template>
```

### 3. 空状态

**空状态设计**：
- 图标：表意清晰
- 文案：简洁明了
- 操作：引导用户
- 样式：居中显示

**代码示例**：

```vue
<template>
  <el-empty
    v-if="conversations.length === 0"
    description="暂无对话记录"
  >
    <el-button type="primary" @click="handleCreate">
      创建新对话
    </el-button>
  </el-empty>
</template>

<style scoped lang="scss">
.el-empty {
  padding: $spacing-xl 0;
}
</style>
```

## 响应式设计

### 1. 断点系统

```scss
// 断点定义
$breakpoint-xs: 480px;   // 手机
$breakpoint-sm: 768px;   // 平板
$breakpoint-md: 1024px;  // 小屏电脑
$breakpoint-lg: 1280px;  // 大屏电脑
$breakpoint-xl: 1920px;  // 超大屏

// 媒体查询混入
@mixin respond-to($breakpoint) {
  @if $breakpoint == xs {
    @media (max-width: $breakpoint-xs) { @content; }
  }
  @else if $breakpoint == sm {
    @media (max-width: $breakpoint-sm) { @content; }
  }
  @else if $breakpoint == md {
    @media (max-width: $breakpoint-md) { @content; }
  }
  @else if $breakpoint == lg {
    @media (max-width: $breakpoint-lg) { @content; }
  }
}
```

### 2. 响应式布局

**布局策略**：
- Mobile First：从小屏开始设计
- 流式布局：使用百分比
- 弹性布局：Flexbox
- 网格布局：CSS Grid

**代码示例**：

```vue
<template>
  <div class="responsive-layout">
    <aside class="sidebar">侧边栏</aside>
    <main class="main-content">主内容</main>
  </div>
</template>

<style scoped lang="scss">
.responsive-layout {
  display: flex;
  height: 100vh;

  .sidebar {
    width: 240px;
    background-color: $background-base;

    @include respond-to(md) {
      width: 200px;
    }

    @include respond-to(sm) {
      position: fixed;
      left: -240px;
      transition: left 0.3s;

      &.open {
        left: 0;
      }
    }
  }

  .main-content {
    flex: 1;
    padding: $spacing-lg;

    @include respond-to(sm) {
      padding: $spacing-md;
    }
  }
}
</style>
```

### 3. 响应式组件

**组件适配**：
- 表格：横向滚动或卡片展示
- 表单：单列布局
- 导航：汉堡菜单
- 对话框：全屏显示

**代码示例**：

```vue
<template>
  <div class="responsive-table">
    <!-- 桌面端：表格 -->
    <el-table
      v-if="!isMobile"
      :data="tableData"
    >
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="date" label="日期" />
      <el-table-column prop="status" label="状态" />
    </el-table>

    <!-- 移动端：卡片 -->
    <div v-else class="mobile-cards">
      <el-card
        v-for="item in tableData"
        :key="item.id"
        class="mobile-card"
      >
        <div class="card-row">
          <span class="label">名称：</span>
          <span>{{ item.name }}</span>
        </div>
        <div class="card-row">
          <span class="label">日期：</span>
          <span>{{ item.date }}</span>
        </div>
        <div class="card-row">
          <span class="label">状态：</span>
          <el-tag>{{ item.status }}</el-tag>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const isMobile = ref(false)

const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>
```

## 页面布局设计

### 1. 聊天页面布局

```vue
<template>
  <div class="chat-layout">
    <!-- 侧边栏：对话列表 -->
    <aside class="conversation-sidebar">
      <div class="sidebar-header">
        <h3>对话列表</h3>
        <el-button type="primary" :icon="Plus" @click="createConversation">
          新建对话
        </el-button>
      </div>
      <div class="conversation-list">
        <!-- 对话列表项 -->
      </div>
    </aside>

    <!-- 主内容区：聊天界面 -->
    <main class="chat-main">
      <div class="chat-header">
        <h2>{{ currentConversation?.title }}</h2>
      </div>
      <div class="message-list">
        <!-- 消息列表 -->
      </div>
      <div class="chat-input">
        <!-- 输入框 -->
      </div>
    </main>
  </div>
</template>

<style scoped lang="scss">
.chat-layout {
  display: flex;
  height: 100vh;

  .conversation-sidebar {
    width: 280px;
    border-right: 1px solid $border-base;
    display: flex;
    flex-direction: column;

    .sidebar-header {
      padding: $spacing-md;
      border-bottom: 1px solid $border-base;
    }

    .conversation-list {
      flex: 1;
      overflow-y: auto;
    }
  }

  .chat-main {
    flex: 1;
    display: flex;
    flex-direction: column;

    .chat-header {
      padding: $spacing-md;
      border-bottom: 1px solid $border-base;
    }

    .message-list {
      flex: 1;
      overflow-y: auto;
      padding: $spacing-md;
    }

    .chat-input {
      padding: $spacing-md;
      border-top: 1px solid $border-base;
    }
  }
}
</style>
```

## 设计工具和流程

### 1. 设计工具推荐

**原型设计**：
- Figma：协作设计、原型制作
- Sketch：界面设计（macOS）
- Adobe XD：原型和交互设计

**图标资源**：
- Element Plus Icons：项目使用的图标库
- Iconify：海量图标库
- Font Awesome：经典图标库

**配色工具**：
- Coolors：配色方案生成
- Adobe Color：色轮和配色
- Material Design Color Tool：Material配色

**字体资源**：
- Google Fonts：免费字体
- Font Squirrel：免费商用字体

### 2. 设计流程

**需求分析** → **信息架构** → **线框图** → **视觉设计** → **交互原型** → **开发交付** → **测试优化**

1. **需求分析**：理解用户需求和业务目标
2. **信息架构**：规划页面结构和导航
3. **线框图**：绘制低保真原型
4. **视觉设计**：完成高保真设计稿
5. **交互原型**：制作可交互原型
6. **开发交付**：输出设计规范和切图
7. **测试优化**：收集反馈并优化

### 3. 设计交付物

**必需交付物**：
- 设计稿（Figma/Sketch文件）
- 设计规范文档
- 组件库文档
- 切图资源

**可选交付物**：
- 交互原型
- 用户流程图
- 设计系统文档

## 协作接口

### 输入来源

- **产品 Skill**: 产品需求、用户故事、功能规格
- **用户研究**: 用户画像、使用场景、痛点分析

### 输出交付

- **给前端开发 Skill**: 设计稿、设计规范、组件规范、切图资源
- **给产品 Skill**: 设计方案、交互原型、可用性测试报告
- **给测试 Skill**: 视觉验收标准、交互验收标准

## 注意事项

### 1. 设计一致性

- 严格遵守设计系统
- 使用统一的组件库
- 保持视觉风格一致
- 维护设计规范文档

### 2. 性能考虑

- 优化图片资源（WebP格式）
- 使用SVG图标
- 避免过度动画
- 懒加载图片

### 3. 可访问性

- 颜色对比度符合WCAG标准
- 提供键盘导航支持
- 添加ARIA标签
- 支持屏幕阅读器

### 4. 响应式设计

- Mobile First设计原则
- 测试多种设备和屏幕尺寸
- 考虑触摸操作
- 优化移动端性能

### 5. 用户体验

- 减少用户认知负担
- 提供清晰的操作反馈
- 优化加载体验
- 处理边界情况

## 设计最佳实践

### 1. 视觉层次

- 使用大小、颜色、间距建立层次
- 重要信息突出显示
- 次要信息弱化处理
- 保持视觉平衡

### 2. 留白使用

- 适当的留白提升可读性
- 组件间保持合理间距
- 避免过度拥挤
- 利用留白引导视线

### 3. 色彩运用

- 主色用于主要操作
- 辅助色用于次要信息
- 中性色用于背景和文本
- 保持色彩和谐

### 4. 字体排版

- 标题和正文层次分明
- 行高保持舒适阅读
- 字号大小合理
- 对齐方式统一

### 5. 图标使用

- 图标风格统一
- 图标含义清晰
- 配合文字说明
- 尺寸大小一致

## 常用资源

### 设计灵感

- Dribbble：设计作品展示
- Behance：创意作品平台
- Awwwards：优秀网站设计
- UI Movement：UI动效灵感

### 组件库参考

- Element Plus：本项目使用
- Ant Design：企业级UI设计
- Material-UI：Material Design实现
- Chakra UI：可访问性优先

### 设计系统

- Material Design：Google设计语言
- Fluent Design：Microsoft设计语言
- Human Interface Guidelines：Apple设计指南
- Carbon Design System：IBM设计系统

### 学习资源

- Refactoring UI：UI设计实践
- Laws of UX：用户体验法则
- Nielsen Norman Group：UX研究
- Smashing Magazine：设计开发资源

## 总结

UI/UX设计是产品成功的关键因素。好的设计应该：

1. **以用户为中心**：理解用户需求，解决用户问题
2. **保持一致性**：遵循设计系统，维护品牌形象
3. **注重细节**：精雕细琢，追求完美
4. **持续优化**：收集反馈，不断改进
5. **协作沟通**：与团队紧密配合，确保落地

记住：设计不仅是让产品看起来好看，更重要的是让产品易用、好用。
```
