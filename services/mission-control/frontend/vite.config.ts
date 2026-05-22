import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  const BACKEND_URL = env.VITE_BACKEND_URL || 'http://localhost:9998'
  const FRONTEND_PORT = Number(env.VITE_PORT || 9999)
  const isHmrEnabled = env.VITE_ENABLE_HMR === 'true'

  return {
    plugins: [
      react({
        fastRefresh: true,
      }),
    ],

    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },

    server: {
      host: '0.0.0.0',
      port: FRONTEND_PORT,
      strictPort: true,

      /**
       * HMR
       * Vô hiệu hóa HMR mặc định (hmr: false) để tránh reload/nháy trang khi CPU/RAM bị nghẽn (chạy model).
       * Bật lại bằng cách thêm VITE_ENABLE_HMR=true vào file .env.
       */
      hmr: isHmrEnabled
        ? {
            protocol: 'ws',
            host: 'localhost',
            port: FRONTEND_PORT,
            timeout: 30000,
          }
        : false,

      /**
       * File watching
       * Polling mặc định bật (true) vì dự án chạy trong Docker bind mount trên Windows.
       * Có thể tắt bằng cách cấu hình VITE_USE_POLLING=false trong .env.
       */
      watch: {
        usePolling: env.VITE_USE_POLLING !== 'false',
        interval: 1000,

        ignored: [
          '**/.git/**',
          '**/node_modules/**',

          // AI / backend heavy folders
          '**/backend/**',
          '**/core/**',
          '**/models/**',
          '**/skills/**',
          '**/storage/**',
          '**/intelligence/**',

          // hidden system folders
          '**/.gemini/**',
          '**/.claude/**',
          '**/.cursor/**',
          '**/.vscode/**',

          // logs/temp
          '**/*.log',
          '**/tmp/**',
          '**/cache/**',

          // binary/model files
          '**/*.gguf',
          '**/*.bin',
          '**/*.safetensors',
          '**/*.pt',
          '**/*.onnx',
        ],
      },

      proxy: {
        '/api': {
          target: BACKEND_URL,
          changeOrigin: true,
          secure: false,
          ws: true,
        },
        '/socket.io': {
          target: BACKEND_URL,
          ws: true,
          changeOrigin: true,
          secure: false,
        },
      },
    },

    /**
     * Giảm noisy log
     */
    clearScreen: false,

    /**
     * Tăng tốc optimize deps
     */
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
      ],
    },

    /**
     * Build optimization
     */
    build: {
      target: 'esnext',
      chunkSizeWarningLimit: 1500,
      sourcemap: mode === 'development',
      rollupOptions: {
        output: {
          manualChunks: {
            react: ['react', 'react-dom'],
          },
        },
      },
    },

    /**
     * Environment define
     */
    define: {
      __APP_ENV__: JSON.stringify(mode),
    },
  }
})
