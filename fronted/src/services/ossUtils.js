/**
 * OSS工具函数集合
 * 包含文件验证、压缩、MD5校验等功能
 */

import { OSS_UPLOAD_CONFIG } from './ossConfig';

/**
 * 验证文件类型
 * @param {File} file - 文件对象
 * @returns {Object} { valid: boolean, error: string }
 */
export const validateFileType = (file) => {
  if (!OSS_UPLOAD_CONFIG.allowedTypes.includes(file.type)) {
    return {
      valid: false,
      error: `不支持的文件格式。仅支持 JPG、PNG、WEBP 格式的图片`,
    };
  }
  return { valid: true };
};

/**
 * 验证文件大小
 * @param {File} file - 文件对象
 * @returns {Object} { valid: boolean, error: string }
 */
export const validateFileSize = (file) => {
  if (file.size > OSS_UPLOAD_CONFIG.maxFileSize) {
    return {
      valid: false,
      error: `文件大小超过限制。最大允许 ${OSS_UPLOAD_CONFIG.maxFileSize / 1024 / 1024}MB`,
    };
  }
  return { valid: true };
};

/**
 * 综合文件验证
 * @param {File} file - 文件对象
 * @returns {Object} { valid: boolean, error: string }
 */
export const validateFile = (file) => {
  const typeValidation = validateFileType(file);
  if (!typeValidation.valid) {
    return typeValidation;
  }

  const sizeValidation = validateFileSize(file);
  if (!sizeValidation.valid) {
    return sizeValidation;
  }

  return { valid: true };
};

/**
 * 压缩图片
 * @param {File} file - 原始文件
 * @param {number} quality - 压缩质量 (0-1)
 * @param {number} maxWidth - 最大宽度
 * @param {number} maxHeight - 最大高度
 * @returns {Promise<Blob>} 压缩后的图片Blob
 */
export const compressImage = (file, quality = 0.85, maxWidth = 1920, maxHeight = 1920) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;

        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width = width * ratio;
          height = height * ratio;
        }

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob);
            } else {
              reject(new Error('图片压缩失败'));
            }
          },
          file.type,
          quality
        );
      };
      img.onerror = () => reject(new Error('图片加载失败'));
      img.src = e.target.result;
    };
    reader.onerror = () => reject(new Error('文件读取失败'));
    reader.readAsDataURL(file);
  });
};

/**
 * 计算文件MD5
 * @param {File} file - 文件对象
 * @returns {Promise<string>} MD5哈希值
 */
export const calculateMD5 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const buffer = e.target.result;
        const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        resolve(hashHex);
      } catch (error) {
        reject(new Error('MD5计算失败'));
      }
    };
    reader.onerror = () => reject(new Error('文件读取失败'));
    reader.readAsArrayBuffer(file);
  });
};

/**
 * 生成唯一文件名
 * @param {string} userId - 用户ID
 * @param {string} originalName - 原始文件名
 * @returns {string} 唯一文件名
 */
export const generateUniqueFileName = (userId, originalName) => {
  const timestamp = Date.now();
  const randomStr = Math.random().toString(36).substring(2, 15);
  const ext = originalName.split('.').pop().toLowerCase();
  return `${userId}_${timestamp}_${randomStr}.${ext}`;
};

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的大小字符串
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

/**
 * 获取文件扩展名
 * @param {string} filename - 文件名
 * @returns {string} 扩展名
 */
export const getFileExtension = (filename) => {
  return filename.split('.').pop().toLowerCase();
};

/**
 * 将Blob转换为File
 * @param {Blob} blob - Blob对象
 * @param {string} filename - 文件名
 * @returns {File} File对象
 */
export const blobToFile = (blob, filename) => {
  return new File([blob], filename, { type: blob.type });
};

/**
 * 读取文件为DataURL
 * @param {File} file - 文件对象
 * @returns {Promise<string>} DataURL字符串
 */
export const readFileAsDataURL = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = () => reject(new Error('文件读取失败'));
    reader.readAsDataURL(file);
  });
};

/**
 * 获取图片尺寸
 * @param {File} file - 图片文件
 * @returns {Promise<Object>} { width, height }
 */
export const getImageDimensions = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        resolve({ width: img.width, height: img.height });
      };
      img.onerror = () => reject(new Error('图片加载失败'));
      img.src = e.target.result;
    };
    reader.onerror = () => reject(new Error('文件读取失败'));
    reader.readAsDataURL(file);
  });
};
