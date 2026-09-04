var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers';
import { resolve } from 'path';
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000';
export default defineConfig({
    plugins: __spreadArray([
        vue()
    ], (process.env.VITEST
        ? []
        : [
            Components({
                dts: false,
                resolvers: [ElementPlusResolver({ importStyle: 'css' })]
            })
        ]), true),
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src')
        }
    },
    server: {
        host: '0.0.0.0',
        port: 5173,
        proxy: {
            '/api': {
                target: apiProxyTarget,
                changeOrigin: true
            }
        }
    },
    css: {
        preprocessorOptions: {
            scss: {
                additionalData: "@use \"@/styles/variables.scss\" as *;"
            }
        }
    },
    test: {
        globals: true,
        environment: 'happy-dom',
        setupFiles: ['./src/__tests__/setup.ts'],
        include: ['src/**/*.{test,spec}.{js,ts}'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            include: ['src/**/*.{ts,vue}'],
            exclude: ['src/__tests__/**', 'src/types/**', 'src/env.d.ts']
        }
    }
});
