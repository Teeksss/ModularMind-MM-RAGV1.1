const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const TerserPlugin = require('terser-webpack-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const CopyPlugin = require('copy-webpack-plugin');
const { WebpackManifestPlugin } = require('webpack-manifest-plugin');
const dotenv = require('dotenv');
const webpack = require('webpack');

// .env dosyasını yükle
const env = dotenv.config().parsed || {};

// Environment değişkenlerini webpack DefinePlugin için uygun formata çevir
const envKeys = Object.keys(env).reduce((prev, next) => {
  prev[`process.env.${next}`] = JSON.stringify(env[next]);
  return prev;
}, {});

// Üretim modu kontrolü
const isProduction = process.env.NODE_ENV === 'production';

// Tarih oluştur
const buildDate = new Date().toISOString();

module.exports = {
  // Giriş noktası
  entry: {
    main: './src/index.tsx',
    // Dinamik import edilecek büyük modüller için ayrı chunk'lar
    multimodal: './src/features/multimodal/index.ts',
    fineTuning: './src/features/fine-tuning/index.ts'
  },
  
  // Çıkış yapılandırması
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: isProduction 
      ? 'static/js/[name].[contenthash:8].js' 
      : 'static/js/[name].js',
    chunkFilename: isProduction 
      ? 'static/js/[name].[contenthash:8].chunk.js' 
      : 'static/js/[name].chunk.js',
    assetModuleFilename: 'static/media/[name].[hash][ext]',
    publicPath: '/',
    clean: true
  },
  
  // Devserver yapılandırması
  devServer: {
    historyApiFallback: true,
    port: 3000,
    hot: true,
    open: true,
    static: {
      directory: path.join(__dirname, 'public'),
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        pathRewrite: { '^/api': '/api' },
        changeOrigin: true,
      },
    },
  },
  
  // Mode
  mode: isProduction ? 'production' : 'development',
  
  // Devtool
  devtool: isProduction ? 'source-map' : 'eval-source-map',
  
  // Modül çözümleyiciler
  resolve: {
    extensions: ['.tsx', '.ts', '.js', '.jsx', '.json'],
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@components': path.resolve(__dirname, 'src/components'),
      '@services': path.resolve(__dirname, 'src/services'),
      '@hooks': path.resolve(__dirname, 'src/hooks'),
      '@pages': path.resolve(__dirname, 'src/pages'),
      '@utils': path.resolve(__dirname, 'src/utils'),
      '@assets': path.resolve(__dirname, 'src/assets'),
      '@styles': path.resolve(__dirname, 'src/styles'),
    },
  },
  
  // Modül kuralları
  module: {
    rules: [
      // TypeScript ve JavaScript
      {
        test: /\.(ts|tsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: [
              '@babel/preset-env',
              '@babel/preset-react',
              '@babel/preset-typescript',
            ],
            plugins: [
              ['@babel/plugin-transform-runtime', { regenerator: true }],
            ],
          },
        },
      },
      // CSS ve SCSS
      {
        test: /\.(css|scss)$/,
        use: [
          isProduction ? MiniCssExtractPlugin.loader : 'style-loader',
          {
            loader: 'css-loader',
            options: {
              importLoaders: 1,
              sourceMap: !isProduction,
            },
          },
          'postcss-loader',
          'sass-loader',
        ],
      },
      // Görüntüler
      {
        test: /\.(png|jpe?g|gif|svg|webp)$/i,
        type: 'asset',
        parser: {
          dataUrlCondition: {
            maxSize: 8 * 1024, // 8kb
          },
        },
      },
      // Fontlar
      {
        test: /\.(woff|woff2|eot|ttf|otf)$/i,
        type: 'asset/resource',
      },
    ],
  },
  
  // Eklentiler
  plugins: [
    // HTML oluşturma
    new HtmlWebpackPlugin({
      template: './public/index.html',
      favicon: './public/favicon.ico',
      inject: true,
      meta: {
        viewport: 'width=device-width, initial-scale=1, shrink-to-fit=no',
        description: 'ModularMind - Modern Retrieval Augmented Generation Platform',
        'theme-color': '#0369a1',
      },
      minify: isProduction ? {
        removeComments: true,
        collapseWhitespace: true,
        removeRedundantAttributes: true,
        useShortDoctype: true,
        removeEmptyAttributes: true,
        removeStyleLinkTypeAttributes: true,
        keepClosingSlash: true,
        minifyJS: true,
        minifyCSS: true,
        minifyURLs: true,
      } : false,
    }),
    
    // CSS çıkarma
    new MiniCssExtractPlugin({
      filename: 'static/css/[name].[contenthash:8].css',
      chunkFilename: 'static/css/[name].[contenthash:8].chunk.css',
    }),
    
    // Temizleme
    new CleanWebpackPlugin(),
    
    // Statik dosyaları kopyalama
    new CopyPlugin({
      patterns: [
        {
          from: 'public',
          globOptions: {
            ignore: ['**/index.html', '**/favicon.ico'],
          },
          to: '[path][name][ext]',
        },
      ],
    }),
    
    // Manifest oluşturma
    new WebpackManifestPlugin({
      fileName: 'asset-manifest.json',
      publicPath: '/',
      generate: (seed, files, entrypoints) => {
        const manifestFiles = files.reduce((manifest, file) => {
          manifest[file.name] = file.path;
          return manifest;
        }, seed);
        
        const entrypointFiles = entrypoints.main.filter(
          fileName => !fileName.endsWith('.map')
        );

        return {
          files: manifestFiles,
          entrypoints: entrypointFiles,
        };
      },
    }),
    
    // Env değişkenleri
    new webpack.DefinePlugin({
      ...envKeys,
      'process.env.NODE_ENV': JSON.stringify(isProduction ? 'production' : 'development'),
      'process.env.APP_VERSION': JSON.stringify(require('./package.json').version),
      'process.env.BUILD_DATE': JSON.stringify(buildDate),
    }),
  ],
  
  // Optimizasyon
  optimization: {
    minimize: isProduction,
    minimizer: [
      new TerserPlugin({
        terserOptions: {
          parse: {
            ecma: 8,
          },
          compress: {
            ecma: 5,
            warnings: false,
            comparisons: false,
            inline: 2,
            drop_console: isProduction,
          },
          mangle: {
            safari10: true,
          },
          output: {
            ecma: 5,
            comments: false,
            ascii_only: true,
          },
        },
        extractComments: false,
      }),
      new CssMinimizerPlugin(),
    ],
    // Chunk bölme stratejisi
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        // Vendor
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
          priority: 20,
        },
        // Framework modülleri
        framework: {
          test: /[\\/]node_modules[\\/](react|react-dom|react-router-dom)[\\/]/,
          name: 'framework',
          chunks: 'all',
          priority: 30,
        },
        // UI komponentleri
        ui: {
          test: /[\\/]node_modules[\\/](framer-motion|@headlessui|react-icons)[\\/]/,
          name: 'ui',
          chunks: 'all',
          priority: 25
        },
        // Ortak kod
        common: {
          name: 'common',
          minChunks: 2,
          chunks: 'async',
          priority: 10,
          reuseExistingChunk: true,
          enforce: true,
        },
      },
    },
    // Runtime chunk
    runtimeChunk: {
      name: entrypoint => `runtime-${entrypoint.name}`,
    },
  },
  
  // Performance bütçeleri
  performance: {
    hints: isProduction ? 'warning' : false,
    maxEntrypointSize: 512000,
    maxAssetSize: 512000,
  },
};