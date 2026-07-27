import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('SettingsView model contract', () => {
  it('shows only the DashScope defaults used by the constrained RAG runtime', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/views/settings/SettingsView.vue'),
      'utf-8'
    )

    expect(source).toContain("defaultModel: 'qwen-plus'")
    expect(source).toContain('label="qwen-plus" value="qwen-plus"')
    expect(source).toContain("embeddingModel: 'text-embedding-v3'")
    expect(source).toContain('label="text-embedding-v3" value="text-embedding-v3"')
    expect(source).not.toContain('qwen-turbo')
    expect(source).not.toContain('text-embedding-v1')
  })
})
