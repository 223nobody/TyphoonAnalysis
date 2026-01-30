/**
 * OSS配置文件
 * 根据README.md中的说明配置阿里云OSS连接参数
 */

export const OSS_CONFIG = {
  bucket: "typhoonanalysis",
  region: "oss-cn-wuhan",
  endpoint: "oss-cn-wuhan-lr.aliyuncs.com",
  secure: true,
  timeout: 120000,
};

export const OSS_UPLOAD_CONFIG = {
  folder: "user_image/",
  maxFileSize: 10 * 1024 * 1024,
  allowedTypes: ["image/jpeg", "image/jpg", "image/png", "image/webp"],
  partSize: 1024 * 1024,
  parallel: 3,
};

export const STS_CONFIG = {
  endpoint: "/api/auth/sts-token",
  expiresIn: 3600,
};
