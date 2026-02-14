/**
 * OSS上传服务
 * 实现基于STS的临时授权、分片上传、断点续传等功能
 */

import OSS from "ali-oss";
import apiClient from "./api";
import { OSS_CONFIG, OSS_UPLOAD_CONFIG, STS_CONFIG } from "./ossConfig";
import {
  validateFile,
  compressImage,
  calculateMD5,
  generateUniqueFileName,
  formatFileSize,
  blobToFile,
} from "./ossUtils";

class OSSUploadService {
  constructor() {
    this.client = null;
    this.currentUpload = null;
    this.abortController = null;
  }

  /**
   * 获取STS临时凭证
   * @returns {Promise<Object>} STS凭证信息
   */
  async getSTSToken() {
    try {
      const response = await apiClient.get(STS_CONFIG.endpoint, {
        timeout: 10000,
      });
      return response.data;
    } catch (error) {
      throw new Error(
        "获取STS临时凭证失败: " +
          (error.response?.data?.detail || error.message || "网络错误"),
      );
    }
  }

  /**
   * 初始化OSS客户端
   * @param {Object} stsToken - STS凭证
   */
  async initOSSClient(stsToken) {
    try {
      this.client = new OSS({
        region: OSS_CONFIG.region,
        accessKeyId: stsToken.accessKeyId,
        accessKeySecret: stsToken.accessKeySecret,
        stsToken: stsToken.securityToken,
        bucket: OSS_CONFIG.bucket,
        endpoint: OSS_CONFIG.endpoint,
        secure: OSS_CONFIG.secure,
        timeout: OSS_CONFIG.timeout,
      });
    } catch (error) {
      throw new Error("OSS客户端初始化失败: " + error.message);
    }
  }

  /**
   * 上传头像到OSS
   * @param {File} file - 头像文件
   * @param {string} userId - 用户ID
   * @param {Function} onProgress - 进度回调函数
   * @returns {Promise<Object>} 上传结果
   */
  async uploadAvatar(file, userId, onProgress) {
    try {
      console.log(
        "开始上传头像:",
        file.name,
        "大小:",
        formatFileSize(file.size),
      );

      const validation = validateFile(file);
      if (!validation.valid) {
        console.error("文件验证失败:", validation.error);
        throw new Error(validation.error);
      }

      const stsToken = await this.getSTSToken();
      await this.initOSSClient(stsToken);

      const compressedFile = await this.compressIfNeeded(file);
      const md5 = await calculateMD5(compressedFile);
      const fileName = generateUniqueFileName(userId, file.name);
      const objectKey = `${OSS_UPLOAD_CONFIG.folder}${fileName}`;

      console.log("准备上传到OSS:", objectKey);

      this.abortController = new AbortController();

      const result = await this.client.multipartUpload(
        objectKey,
        compressedFile,
        {
          parallel: OSS_UPLOAD_CONFIG.parallel,
          partSize: OSS_UPLOAD_CONFIG.partSize,
          progress: (p, checkpoint, res) => {
            if (onProgress) {
              const percentage = Math.floor(p * 100);
              onProgress({
                percentage,
                loaded: Math.floor(p * compressedFile.size),
                total: compressedFile.size,
                checkpoint,
              });
            }
          },
          headers: {
            "Content-MD5": md5,
            "x-oss-object-acl": "public-read",
          },
          timeout: OSS_CONFIG.timeout,
        },
      );

      const url = this.client.signatureUrl(objectKey, {
        expires: 3600 * 24 * 365,
      });

      console.log("头像上传成功:", url.split("?")[0]);

      return {
        success: true,
        data: {
          url: url.split("?")[0],
          objectKey,
          fileName,
          fileSize: compressedFile.size,
          md5,
          uploadTime: new Date().toISOString(),
          etag: result.etag,
        },
      };
    } catch (error) {
      console.error("头像上传失败:", error);

      if (
        error.name === "RequestError" ||
        error.name === "ConnectionTimeoutError"
      ) {
        throw new Error("网络连接失败，请检查网络设置");
      } else if (error.name === "SecurityTokenExpiredError") {
        throw new Error("STS临时凭证已过期，请重新上传");
      } else if (error.name === "SignatureDoesNotMatchError") {
        throw new Error("签名验证失败，请检查凭证配置");
      } else if (error.name === "AccessDeniedError") {
        throw new Error("访问被拒绝，请检查权限配置");
      } else if (error.name === "RequestTimeoutError") {
        throw new Error("请求超时，请稍后重试");
      } else if (error.code === "AccessDenied") {
        throw new Error("访问被拒绝，请检查OSS权限配置");
      } else if (error.code === "NoSuchBucket") {
        throw new Error("OSS Bucket不存在，请检查配置");
      } else {
        throw new Error(error.message || "上传失败");
      }
    }
  }

  /**
   * 通过后端代理上传头像
   * @param {File} file - 头像文件
   * @param {string} userId - 用户ID
   * @param {Function} onProgress - 进度回调函数
   * @returns {Promise<Object>} 上传结果
   */
  async uploadAvatarViaBackend(file, userId, onProgress) {
    try {
      const validation = validateFile(file);
      if (!validation.valid) {
        throw new Error(validation.error);
      }

      const formData = new FormData();
      formData.append("file", file);

      const response = await apiClient.post("/auth/upload-avatar", formData, {
        onUploadProgress: (progressEvent) => {
          if (onProgress) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total,
            );
            onProgress(percentCompleted);
          }
        },
      });

      return {
        url: response.url,
        success: true,
      };
    } catch (error) {
      throw new Error(error.message || "网络连接失败，请检查网络设置");
    }
  }

  /**
   * 压缩图片（如果需要）
   * @param {File} file - 原始文件
   * @returns {Promise<File>} 处理后的文件
   */
  async compressIfNeeded(file) {
    const maxSize = 2 * 1024 * 1024;
    if (file.size <= maxSize) {
      return file;
    }

    try {
      const blob = await compressImage(file, 0.8, 1920, 1920);
      const compressedFile = blobToFile(blob, file.name);
      return compressedFile;
    } catch (error) {
      return file;
    }
  }

  /**
   * 取消上传
   */
  cancelUpload() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    if (this.client) {
      this.client.cancel();
    }
  }

  /**
   * 断点续传
   * @param {File} file - 文件对象
   * @param {string} userId - 用户ID
   * @param {Object} checkpoint - 断点信息
   * @param {Function} onProgress - 进度回调
   * @returns {Promise<Object>} 上传结果
   */
  async resumeUpload(file, userId, checkpoint, onProgress) {
    try {
      console.log("开始断点续传:", checkpoint.name);

      const stsToken = await this.getSTSToken();
      await this.initOSSClient(stsToken);

      this.abortController = new AbortController();

      const result = await this.client.multipartUpload(checkpoint.name, file, {
        parallel: OSS_UPLOAD_CONFIG.parallel,
        partSize: OSS_UPLOAD_CONFIG.partSize,
        checkpoint: checkpoint,
        progress: (p, cpt, res) => {
          if (onProgress) {
            const percentage = Math.floor(p * 100);
            onProgress({
              percentage,
              loaded: Math.floor(p * file.size),
              total: file.size,
              checkpoint: cpt,
            });
          }
        },
        timeout: OSS_CONFIG.timeout,
      });

      const url = this.client.signatureUrl(checkpoint.name, {
        expires: 3600 * 24 * 365,
      });

      console.log("断点续传成功:", url.split("?")[0]);

      return {
        success: true,
        data: {
          url: url.split("?")[0],
          objectKey: checkpoint.name,
          fileName: checkpoint.name.split("/").pop(),
          fileSize: file.size,
          uploadTime: new Date().toISOString(),
          etag: result.etag,
        },
      };
    } catch (error) {
      console.error("断点续传失败:", error);
      throw new Error("断点续传失败: " + error.message);
    }
  }

  /**
   * 删除OSS文件
   * @param {string} objectKey - 对象键
   * @returns {Promise<boolean>} 是否删除成功
   */
  async deleteFile(objectKey) {
    try {
      console.log("开始删除文件:", objectKey);

      const stsToken = await this.getSTSToken();
      await this.initOSSClient(stsToken);

      await this.client.delete(objectKey);
      console.log("文件删除成功:", objectKey);
      return true;
    } catch (error) {
      console.error("删除文件失败:", error);
      return false;
    }
  }

  /**
   * 获取文件签名URL
   * @param {string} objectKey - 对象键
   * @param {number} expires - 过期时间（秒）
   * @returns {Promise<string>} 签名URL
   */
  async getSignatureUrl(objectKey, expires = 3600) {
    try {
      const stsToken = await this.getSTSToken();
      await this.initOSSClient(stsToken);

      return this.client.signatureUrl(objectKey, { expires });
    } catch (error) {
      throw new Error("获取签名URL失败: " + error.message);
    }
  }

  /**
   * 检查文件是否存在
   * @param {string} objectKey - 对象键
   * @returns {Promise<boolean>} 是否存在
   */
  async checkFileExists(objectKey) {
    try {
      const stsToken = await this.getSTSToken();
      await this.initOSSClient(stsToken);

      await this.client.head(objectKey);
      return true;
    } catch (error) {
      if (error.name === "NoSuchKeyError") {
        return false;
      }
      throw error;
    }
  }
}

export default new OSSUploadService();
