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
};

module.exports = nextConfig;
