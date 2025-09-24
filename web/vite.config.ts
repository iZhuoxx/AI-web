import { defineConfig } from 'vite'
import path from 'path'
import UnoCSS from 'unocss/vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { AntDesignVueResolver } from 'unplugin-vue-components/resolvers'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    UnoCSS({}),
    AutoImport({
      imports: ['vue'],
      dts: 'auto-imports.d.ts',
    }),
    Components({
      resolvers: [AntDesignVueResolver()],
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    host: '0.0.0.0',           // 允许局域网/WSL 访问（Windows 浏览器访问 WSL 很有用）
    port: 5173,
    strictPort: true,
    proxy: {
      // 把前端发到 /api 的请求代理到 FastAPI 后端 :8000
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // 如果你的后端在 WSL 而浏览器在 Windows，这里保持 localhost 即可
        // 若你后端跑在别的机器，改成对应的地址
      },
    },
  },
  // 生产打包在后端挂载到根路径时，用默认 base 即可（'/'）
  // 如果你需要把 dist 部署在子路径下，可以设置 base: '/subpath/'
})
