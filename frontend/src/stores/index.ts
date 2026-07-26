import { createPinia } from 'pinia'

const pinia = createPinia()

export default pinia

export * from './auth'
export * from './conversation'
export * from './knowledge'
export * from './agent'
export * from './prompts'
