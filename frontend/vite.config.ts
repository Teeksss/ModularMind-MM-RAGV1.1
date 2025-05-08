import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import svgr from 'vite-plugin-svgr';
import { splitVendorChunkPlugin } from 'vite';
import { visualizer } from 'rollup-plugin-visualizer';
import path from 'path';
import pkg from './package.json';

export default defineConfig(({ mode }) => {
  // Ortam değişkenlerini yükle
  const env = loadEnv(mode, process.cwd(), '');
  
  return {
    // Proje ayarları
    define: {
      'process.env.APP_VERSION': JSON.stringify(pkg.version),
      'process.env.BUILD_DATE': JSON.stringify(new Date().toISOString()),
    },
    
    // Eklentiler
    plugins: [
      react(),
      svgr(),
      splitVendorChunkPlugin(),
      
      // Progressive Web App
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.ico', 'robots.txt', 'apple-touch-icon.png'],
        manifest: {
          name: 'ModularMind',
          short_name: 'ModularMind',
          description: 'Modern RAG Platform',
          theme_color: '#0369a1',
          background_color: '#f8fafc',
          icons: [
            {
              src: 'pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png',
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any maskable',
            },
          ],
        },
      }),
      
      // Bundle analizi (sadece analiz modunda)
      mode === 'analyze' &&
        visualizer({
          open: true,
          filename: 'dist/stats.html',
          gzipSize: true,
          brotliSize: true,
        }),
    ],
    
    // Path alias'ları
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@components': path.resolve(__dirname, './src/components'),
        '@services': path.resolve(__dirname, './src/services'),
        '@hooks': path.resolve(__dirname, './src/hooks'),
        '@pages': path.resolve(__dirname, './src/pages'),
        '@utils': path.resolve(__dirname, './src/utils'),
        '@assets': path.resolve(__dirname, './src/assets'),
        '@styles': path.resolve(__dirname, './src/styles'),
      },
    },
    
    // Sunucu yapılandırması
    server: {
      port: 3000,
      proxy: {
        // API isteklerini backend'e yönlendir
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
    
    // Derleme optimizasyonları
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: mode !== 'production', // Sadece prod olmayan environment'larda sourcemap oluştur
      
      // Chunk'ları optimize et
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        output: {
          manualChunks: {
            // Framework chunk'ı
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            
            // UI komponentleri
            'ui-components': [
              'react-icons',
              'framer-motion',
              '@headlessui/react',
              'react-toastify',
            ],
            
            // Data yönetimi
            'data-libs': ['axios', 'swr', 'lodash', 'date-fns'],
            
            // Multimodal komponentler (büyük paketler)
            'multimodal': ['react-dropzone', 'react-player'],
          },
        },
      },
      
      // CSS minimizasyonu
      cssCodeSplit: true,
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: mode === 'production', // Prod'da console log'ları kaldır
          drop_debugger: mode === 'production',
        },
      },
    },
    
    // CSS önişleme
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
        },
      },
      
      // PostCSS yapılandırması
      postcss: {
        plugins: [
          require('tailwindcss'),
          require('autoprefixer'),
          mode === 'production' && require('cssnano')({
            preset: ['default', { discardComments: { removeAll: true } }],
          }),
        ],
      },
    },
    
    // Önbellek stratejisi
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        'axios',
        '@headlessui/react',
        'framer-motion',
      ],
      exclude: [
        // Çok büyük paketler
        'monaco-editor',
      ],
    },
    
    // Test yapılandırması
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/setupTests.ts',
      coverage: {
        reporter: ['text', 'json', 'html'],
        exclude: ['**/*.d.ts', '**/*.test.tsx', '**/*.test.ts', '**/node_modules/**'],
      },
    },
  };
});