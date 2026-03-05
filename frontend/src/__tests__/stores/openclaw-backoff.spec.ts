/**
 * OpenClaw Store 指数退避测试
 *
 * 测试指数退避和抖动机制
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useOpenClawStore } from '@/stores/openclaw'

describe('OpenClaw Store - 指数退避机制', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('calculateBackoffDelay', () => {
    it('第1次重试应该返回约5秒（带抖动）', () => {
      const store = useOpenClawStore()
      const delay = (store as any).calculateBackoffDelay(1)

      // 基础延迟 5000ms，抖动因子 0.3
      // 期望范围：5000 * (1 - 0.3) 到 5000 * (1 + 0.3)
      // 即：3500ms 到 6500ms
      expect(delay).toBeGreaterThanOrEqual(3500)
      expect(delay).toBeLessThanOrEqual(6500)
    })

    it('第2次重试应该返回约10秒（带抖动）', () => {
      const store = useOpenClawStore()
      const delay = (store as any).calculateBackoffDelay(2)

      // 指数退避：5000 * 2^(2-1) = 10000ms
      // 抖动范围：7000ms 到 13000ms
      expect(delay).toBeGreaterThanOrEqual(7000)
      expect(delay).toBeLessThanOrEqual(13000)
    })

    it('第3次重试应该返回约20秒（带抖动）', () => {
      const store = useOpenClawStore()
      const delay = (store as any).calculateBackoffDelay(3)

      // 指数退避：5000 * 2^(3-1) = 20000ms
      // 抖动范围：14000ms 到 26000ms
      expect(delay).toBeGreaterThanOrEqual(14000)
      expect(delay).toBeLessThanOrEqual(26000)
    })

    it('应该限制最大延迟为60秒', () => {
      const store = useOpenClawStore()

      // 第5次重试：5000 * 2^4 = 80000ms，应该被限制为60000ms
      const delay = (store as any).calculateBackoffDelay(5)

      // 最大延迟 60000ms，抖动范围：42000ms 到 78000ms
      expect(delay).toBeGreaterThanOrEqual(42000)
      expect(delay).toBeLessThanOrEqual(78000)
    })

    it('多次调用应该返回不同的值（验证抖动）', () => {
      const store = useOpenClawStore()
      const delays = []

      // 调用10次，收集延迟值
      for (let i = 0; i < 10; i++) {
        delays.push((store as any).calculateBackoffDelay(1))
      }

      // 由于抖动，至少应该有2个不同的值
      const uniqueDelays = new Set(delays)
      expect(uniqueDelays.size).toBeGreaterThanOrEqual(2)
    })

    it('应该支持自定义配置', () => {
      const store = useOpenClawStore()

      // 修改配置
      store.updateConfig({
        retryBaseDelay: 1000, // 1秒基础延迟
        retryMaxDelay: 10000, // 10秒最大延迟
        retryJitterFactor: 0.5 // 50%抖动
      })

      const delay = (store as any).calculateBackoffDelay(1)

      // 基础延迟 1000ms，抖动因子 0.5
      // 期望范围：500ms 到 1500ms
      expect(delay).toBeGreaterThanOrEqual(500)
      expect(delay).toBeLessThanOrEqual(1500)
    })
  })

  describe('指数退避行为验证', () => {
    it('延迟应该随重试次数指数增长', () => {
      const store = useOpenClawStore()

      const delay1 = (store as any).calculateBackoffDelay(1)
      const delay2 = (store as any).calculateBackoffDelay(2)
      const delay3 = (store as any).calculateBackoffDelay(3)

      // 由于抖动，我们只能验证大致的增长趋势
      // delay2 应该大约是 delay1 的 2 倍（考虑抖动）
      // delay3 应该大约是 delay2 的 2 倍（考虑抖动）

      // 使用平均值来减少抖动的影响
      const avgDelay1 = Array.from({ length: 10 }, () =>
        (store as any).calculateBackoffDelay(1)
      ).reduce((a, b) => a + b, 0) / 10

      const avgDelay2 = Array.from({ length: 10 }, () =>
        (store as any).calculateBackoffDelay(2)
      ).reduce((a, b) => a + b, 0) / 10

      const avgDelay3 = Array.from({ length: 10 }, () =>
        (store as any).calculateBackoffDelay(3)
      ).reduce((a, b) => a + b, 0) / 10

      // 验证指数增长（允许20%误差）
      expect(avgDelay2).toBeGreaterThan(avgDelay1 * 1.6) // 2 * 0.8
      expect(avgDelay2).toBeLessThan(avgDelay1 * 2.4) // 2 * 1.2

      expect(avgDelay3).toBeGreaterThan(avgDelay2 * 1.6)
      expect(avgDelay3).toBeLessThan(avgDelay2 * 2.4)
    })

    it('抖动应该在配置的范围内', () => {
      const store = useOpenClawStore()
      const delays = []

      // 收集100个样本
      for (let i = 0; i < 100; i++) {
        delays.push((store as any).calculateBackoffDelay(1))
      }

      // 计算统计信息
      const min = Math.min(...delays)
      const max = Math.max(...delays)
      const avg = delays.reduce((a, b) => a + b, 0) / delays.length

      // 基础延迟 5000ms，抖动因子 0.3
      // 理论范围：3500ms 到 6500ms
      // 平均值应该接近 5000ms（允许10%误差）
      expect(avg).toBeGreaterThan(4500)
      expect(avg).toBeLessThan(5500)

      // 最小值和最大值应该在理论范围内
      expect(min).toBeGreaterThanOrEqual(3500)
      expect(max).toBeLessThanOrEqual(6500)
    })
  })
})
