/** @type {import('next').NextConfig} */
const nextConfig = {
  // 禁用默认字体优化以避免 Google Fonts 问题
  optimizeFonts: false,
  
  // 允许从任意域名加载图片
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },

  // 配置 webpack
  webpack: (config, { isServer }) => {
    // 在所有构建中禁用 undici
    config.resolve.fallback = {
      ...config.resolve.fallback,
      undici: false,
      'node-fetch': require.resolve('node-fetch'),
      https: require.resolve('https-browserify'),
      http: require.resolve('stream-http'),
      stream: require.resolve('stream-browserify'),
      url: require.resolve('url/'),
      buffer: require.resolve('buffer/'),
    };

    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      };
    }
    
    return config;
  },
  
  // 添加环境变量和对文件系统的权限
  experimental: {
    serverComponentsExternalPackages: ['fs', 'path'],
    outputFileTracingRoot: process.cwd(),
    outputFileTracingIncludes: {
      '/api/**/*': ['./src/lib/novel/sources/rules/**/*'],
    },
  },
  
  // 禁用静态生成，改用动态生成
  output: 'standalone',
  
  // 显式标记动态路由
  rewrites: async () => {
    return [
      {
        source: '/api/:path*',
        destination: '/api/:path*',
      },
    ];
  },
  
  // 配置API路由为动态服务器端渲染
  onDemandEntries: {
    // period (in ms) where the server will keep pages in the buffer
    maxInactiveAge: 25 * 1000,
    // number of pages that should be kept simultaneously without being disposed
    pagesBufferLength: 4,
  },
}

module.exports = nextConfig 