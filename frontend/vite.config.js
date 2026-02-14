import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: "0.0.0.0",
    proxy: {
      // 后端API代理
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
      // Swagger文档代理
      "/docs": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
      // OpenAPI JSON代理
      "/openapi.json": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
      // 健康检查代理
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
      // 阿里云OSS视频代理（解决CORS跨域问题）
      "/oss-video": {
        target: "https://typhoonanalysis.oss-cn-wuhan-lr.aliyuncs.com",
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/oss-video/, ""),
        configure: (proxy, options) => {
          proxy.on("proxyReq", (proxyReq, req, res) => {
            proxyReq.setHeader(
              "Referer",
              "https://typhoonanalysis.oss-cn-wuhan-lr.aliyuncs.com/"
            );
            proxyReq.setHeader("Accept-Encoding", "identity");
          });
          proxy.on("proxyRes", (proxyRes, req, res) => {
            proxyRes.headers["access-control-allow-origin"] = "*";
            proxyRes.headers["access-control-allow-methods"] =
              "GET,HEAD,OPTIONS";
            proxyRes.headers["access-control-allow-headers"] = "*";
            if (req.url.endsWith(".mp4") && !proxyRes.headers["content-type"]) {
              proxyRes.headers["content-type"] = "video/mp4";
            }
          });
          proxy.on("error", (err, req, res) => {
            console.error("OSS视频代理错误:", err);
          });
        },
      },
      // 阿里云OSS图片代理（解决CORS跨域问题）
      "/oss-image": {
        target: "https://typhoonanalysis.oss-cn-wuhan-lr.aliyuncs.com",
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/oss-image/, ""),
        configure: (proxy, options) => {
          proxy.on("proxyReq", (proxyReq, req, res) => {
            proxyReq.setHeader(
              "Referer",
              "https://typhoonanalysis.oss-cn-wuhan-lr.aliyuncs.com/"
            );
          });
          proxy.on("proxyRes", (proxyRes, req, res) => {
            proxyRes.headers["access-control-allow-origin"] = "*";
            proxyRes.headers["access-control-allow-methods"] =
              "GET,HEAD,OPTIONS";
            proxyRes.headers["access-control-allow-headers"] = "*";
            if (
              (req.url.match(/\.(jpg|jpeg|png|gif|webp)$/i) ||
                req.url.includes("user_image")) &&
              !proxyRes.headers["content-type"]
            ) {
              proxyRes.headers["content-type"] = "image/jpeg";
            }
          });
          proxy.on("error", (err, req, res) => {
            console.error("OSS图片代理错误:", err);
          });
        },
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
