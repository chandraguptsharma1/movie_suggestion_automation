import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keep the dev server cache separate from static-export production builds.
  distDir: process.env.NODE_ENV === 'development' ? '.next-dev' : '.next',
  output: "export",
  reactStrictMode: true,
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: "https",
        hostname: "image.tmdb.org",
      },
      {
        protocol: "http",
        hostname: "localhost",
      },
    ],
  },
};

export default nextConfig;
