/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Add rewrite to proxy /api calls to the backend service
  // Service name 'api' is defined in docker-compose
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: process.env.API_URL 
          ? `${process.env.API_URL}/api/:path*` 
          : "http://api:8000/api/:path*",
      },
      {
        source: "/media/:path*",
        destination: process.env.API_URL
          ? `${process.env.API_URL}/media/:path*`
          : "http://api:8000/media/:path*",
      },
    ];
  },
};
export default nextConfig;
