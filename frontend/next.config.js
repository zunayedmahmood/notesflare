/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for Electron — disables image optimization that needs a server
  output: "export",
  // Electron loads the app from the filesystem, not a web server
  trailingSlash: true,
  assetPrefix: "./",
  // Disable telemetry or additional server features
  experimental: {},
};

module.exports = nextConfig;
