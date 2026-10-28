/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 前端构建产物输出到 gui/web/dist，由后端 launch.py 直接静态托管。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 650,
    rollupOptions: {
      output: {
        // 按依赖/功能分 chunk：首屏只拉 vendor+index，echarts/tiptap/markdown 按需，
        // writing 主体与 writing-extras（图表+重度面板）分离避免 monolithic 600KB+。
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('echarts')) return 'echarts'
            if (id.includes('@tiptap') || id.includes('prosemirror')) return 'tiptap'
            if (id.includes('react-markdown') || id.includes('remark-')) return 'markdown'
            if (id.includes('@tanstack')) return 'virtual'
            if (id.includes('react') || id.includes('@mui') || id.includes('@emotion')) return 'vendor'
          }
          // writing-extras 仅在 WritingWorkbench「创作」tab 才加载，与核心分离
          if (id.includes('/components/WritingExtras') || id.includes('/components/writingExtras.samples')) return 'writing-extras'
          // writingExt 板内 4 张专用图表：仅 extras 引用，外置避免 WritingWorkbench 垄断 600KB
          if (id.includes('/components/charts/CreationRateChart') || id.includes('/components/charts/EmotionWaveChart') || id.includes('/components/charts/RhythmRadarChart') || id.includes('/components/charts/ReaderRetentionChart')) return 'writing-extras'
        },
      },
    },
  },
  test: {
    testTimeout: 15000,
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    maxWorkers: 2,
  },
})
