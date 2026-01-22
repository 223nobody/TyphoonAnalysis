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
      // 阿里云OSS视频代理（解决CORS跨域问题）
      "/oss-video": {
        target: "https://typhoonanalysis.oss-cn-wuhan-lr.aliyuncs.com",
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/oss-video/, ""),
        configure: (proxy, options) => {
          proxy.on("proxyReq", (proxyReq, req, res) => {
            // 设置Referer头，某些OSS配置需要
            proxyReq.setHeader(
              "Referer",
              "https://typhoonanalysis.oss-cn-wuhan-lr.aliyuncs.com/"
            );
            // 避免gzip编码影响视频流
            proxyReq.setHeader("Accept-Encoding", "identity");
          });
          proxy.on("proxyRes", (proxyRes, req, res) => {
            // 添加CORS响应头
            proxyRes.headers["access-control-allow-origin"] = "*";
            proxyRes.headers["access-control-allow-methods"] =
              "GET,HEAD,OPTIONS";
            proxyRes.headers["access-control-allow-headers"] = "*";
            // 确保Content-Type正确
            if (req.url.endsWith(".mp4") && !proxyRes.headers["content-type"]) {
              proxyRes.headers["content-type"] = "video/mp4";
            }
          });
          proxy.on("error", (err, req, res) => {
            console.error("OSS视频代理错误:", err);
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
