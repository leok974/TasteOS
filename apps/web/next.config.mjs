/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Add rewrite to proxy /api calls to the backend service
  // Service name 'api' is defined in docker-compose
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://api:8000/api/:path*",
      },
    ];
  },
};
export default nextConfig;
