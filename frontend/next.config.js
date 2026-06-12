/** @type {import('next').NextConfig} */
const isGitHubPages = process.env.NEXT_PUBLIC_BASE_PATH === "/gorilla";
const basePath = isGitHubPages ? "/gorilla" : "";

const nextConfig = {
  reactStrictMode: true,
  output: "export",
  trailingSlash: true,
  basePath,
  assetPrefix: basePath ? `${basePath}/` : "",
  images: { unoptimized: true },

  // Allow webpack to leave CDN dynamic imports as-is
  webpack(config) {
    // Suppress "Critical dependency" warnings for dynamic CDN imports
    config.module = config.module || {};
    config.module.exprContextCritical = false;
    return config;
  },
};

module.exports = nextConfig;
