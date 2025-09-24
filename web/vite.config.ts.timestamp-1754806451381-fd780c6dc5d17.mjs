// vite.config.ts
import { defineConfig } from "file:///mnt/c/Users/xiaoh/Web_Dev/AI-web/web/node_modules/.pnpm/vite@4.5.14_@types+node@18.19.121/node_modules/vite/dist/node/index.js";
import path from "path";
import UnoCSS from "file:///mnt/c/Users/xiaoh/Web_Dev/AI-web/web/node_modules/.pnpm/unocss@0.49.8_rollup@3.29.5_vite@4.5.14_@types+node@18.19.121_/node_modules/unocss/dist/vite.mjs";
import vue from "file:///mnt/c/Users/xiaoh/Web_Dev/AI-web/web/node_modules/.pnpm/@vitejs+plugin-vue@4.6.2_vite@4.5.14_@types+node@18.19.121__vue@3.5.18_typescript@4.9.5_/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import AutoImport from "file:///mnt/c/Users/xiaoh/Web_Dev/AI-web/web/node_modules/.pnpm/unplugin-auto-import@0.14.4_@vueuse+core@9.13.0_vue@3.5.18_typescript@4.9.5___rollup@3.29.5/node_modules/unplugin-auto-import/dist/vite.js";
import Components from "file:///mnt/c/Users/xiaoh/Web_Dev/AI-web/web/node_modules/.pnpm/unplugin-vue-components@0.23.0_@babel+parser@7.28.0_rollup@3.29.5_vue@3.5.18_typescript@4.9.5_/node_modules/unplugin-vue-components/dist/vite.mjs";
import { AntDesignVueResolver } from "file:///mnt/c/Users/xiaoh/Web_Dev/AI-web/web/node_modules/.pnpm/unplugin-vue-components@0.23.0_@babel+parser@7.28.0_rollup@3.29.5_vue@3.5.18_typescript@4.9.5_/node_modules/unplugin-vue-components/dist/resolvers.mjs";
var __vite_injected_original_dirname = "/mnt/c/Users/xiaoh/Web_Dev/AI-web/web";
var vite_config_default = defineConfig({
  plugins: [
    vue(),
    UnoCSS({}),
    AutoImport({
      imports: ["vue"],
      dts: "auto-imports.d.ts"
    }),
    Components({
      resolvers: [AntDesignVueResolver()]
    })
  ],
  resolve: {
    alias: {
      "@": path.resolve(__vite_injected_original_dirname, "src")
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCIvbW50L2MvVXNlcnMveGlhb2gvV2ViX0Rldi9BSS13ZWIvd2ViXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCIvbW50L2MvVXNlcnMveGlhb2gvV2ViX0Rldi9BSS13ZWIvd2ViL3ZpdGUuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9tbnQvYy9Vc2Vycy94aWFvaC9XZWJfRGV2L0FJLXdlYi93ZWIvdml0ZS5jb25maWcudHNcIjtpbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlJ1xuaW1wb3J0IHBhdGggZnJvbSAncGF0aCdcbmltcG9ydCBVbm9DU1MgZnJvbSAndW5vY3NzL3ZpdGUnXG5pbXBvcnQgdnVlIGZyb20gJ0B2aXRlanMvcGx1Z2luLXZ1ZSdcbmltcG9ydCBBdXRvSW1wb3J0IGZyb20gJ3VucGx1Z2luLWF1dG8taW1wb3J0L3ZpdGUnXG5pbXBvcnQgQ29tcG9uZW50cyBmcm9tICd1bnBsdWdpbi12dWUtY29tcG9uZW50cy92aXRlJztcbmltcG9ydCB7IEFudERlc2lnblZ1ZVJlc29sdmVyIH0gZnJvbSAndW5wbHVnaW4tdnVlLWNvbXBvbmVudHMvcmVzb2x2ZXJzJztcblxuLy8gaHR0cHM6Ly92aXRlanMuZGV2L2NvbmZpZy9cbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZyh7XG4gIHBsdWdpbnM6IFtcbiAgICB2dWUoKSxcbiAgICBVbm9DU1MoeyB9KSxcbiAgICBBdXRvSW1wb3J0KHtcbiAgICAgIGltcG9ydHM6IFsndnVlJ10sXG4gICAgICBkdHM6ICdhdXRvLWltcG9ydHMuZC50cycsXG4gICAgfSksXG4gICAgQ29tcG9uZW50cyh7XG4gICAgICByZXNvbHZlcnM6IFtBbnREZXNpZ25WdWVSZXNvbHZlcigpXSxcbiAgICB9KSxcbiAgXSxcbiAgcmVzb2x2ZToge1xuICAgIGFsaWFzOiB7XG4gICAgICAnQCc6IHBhdGgucmVzb2x2ZShfX2Rpcm5hbWUsICdzcmMnKVxuICAgIH1cbiAgfVxufSlcblxuXG4vLyBleHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuLy8gICBwbHVnaW5zOiBbdnVlKCldLFxuXG4vLyB9KSJdLAogICJtYXBwaW5ncyI6ICI7QUFBaVMsU0FBUyxvQkFBb0I7QUFDOVQsT0FBTyxVQUFVO0FBQ2pCLE9BQU8sWUFBWTtBQUNuQixPQUFPLFNBQVM7QUFDaEIsT0FBTyxnQkFBZ0I7QUFDdkIsT0FBTyxnQkFBZ0I7QUFDdkIsU0FBUyw0QkFBNEI7QUFOckMsSUFBTSxtQ0FBbUM7QUFTekMsSUFBTyxzQkFBUSxhQUFhO0FBQUEsRUFDMUIsU0FBUztBQUFBLElBQ1AsSUFBSTtBQUFBLElBQ0osT0FBTyxDQUFFLENBQUM7QUFBQSxJQUNWLFdBQVc7QUFBQSxNQUNULFNBQVMsQ0FBQyxLQUFLO0FBQUEsTUFDZixLQUFLO0FBQUEsSUFDUCxDQUFDO0FBQUEsSUFDRCxXQUFXO0FBQUEsTUFDVCxXQUFXLENBQUMscUJBQXFCLENBQUM7QUFBQSxJQUNwQyxDQUFDO0FBQUEsRUFDSDtBQUFBLEVBQ0EsU0FBUztBQUFBLElBQ1AsT0FBTztBQUFBLE1BQ0wsS0FBSyxLQUFLLFFBQVEsa0NBQVcsS0FBSztBQUFBLElBQ3BDO0FBQUEsRUFDRjtBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
