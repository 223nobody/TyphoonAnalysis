"""
阿里云OSS服务模块
提供文件上传、下载、删除等功能
"""

import os
import uuid
from datetime import datetime
from typing import Optional
from loguru import logger
from fastapi import UploadFile, HTTPException

from app.core.config import settings


class OSSService:
    """阿里云OSS服务类"""

    def __init__(self):
        """初始化OSS客户端"""
        self.bucket_name = settings.OSS_BUCKET_NAME
        self.access_key_id = settings.OSS_ACCESS_KEY_ID
        self.access_key_secret = settings.OSS_ACCESS_KEY_SECRET
        self.endpoint = settings.OSS_ENDPOINT

        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化OSS客户端"""
        try:
            # 检查必需配置
            if not self.access_key_id:
                logger.warning("OSS_ACCESS_KEY_ID未配置")
                self.client = None
                return

            if not self.access_key_secret:
                logger.warning("OSS_ACCESS_KEY_SECRET未配置")
                self.client = None
                return

            if not self.bucket_name:
                logger.warning("OSS_BUCKET_NAME未配置")
                self.client = None
                return

            if not self.endpoint:
                logger.warning("OSS_ENDPOINT未配置")
                self.client = None
                return

            # 使用aliyun-oss-sdk-oss2
            import oss2

            # 创建认证对象
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)

            # 创建Bucket对象
            self.client = oss2.Bucket(auth, self.endpoint, self.bucket_name)

            # 测试连接
            try:
                self.client.get_bucket_info()
                logger.info(f"OSS客户端初始化成功: {self.bucket_name}@{self.endpoint}")
            except oss2.exceptions.NoSuchBucket:
                logger.error(f"OSS Bucket不存在: {self.bucket_name}")
                self.client = None
            except oss2.exceptions.AccessDenied:
                logger.error("OSS访问被拒绝，请检查AccessKey权限")
                self.client = None
            except Exception as e:
                logger.error(f"OSS连接测试失败: {str(e)}")
                self.client = None

        except ImportError:
            logger.error("oss2库未安装，请运行: pip install oss2")
            self.client = None
        except Exception as e:
            logger.error(f"OSS客户端初始化失败: {str(e)}")
            self.client = None

    def _check_client(self):
        """检查OSS客户端是否可用"""
        if self.client is None:
            error_msg = "OSS服务未配置或初始化失败"
            logger.error(error_msg)

            # 提供详细的错误提示
            if not settings.OSS_ACCESS_KEY_ID:
                error_msg += "：OSS_ACCESS_KEY_ID未配置"
            elif not settings.OSS_ACCESS_KEY_SECRET:
                error_msg += "：OSS_ACCESS_KEY_SECRET未配置"
            elif not settings.OSS_BUCKET_NAME:
                error_msg += "：OSS_BUCKET_NAME未配置"
            elif not settings.OSS_ENDPOINT:
                error_msg += "：OSS_ENDPOINT未配置"

            raise HTTPException(
                status_code=500,
                detail=error_msg
            )

    async def upload_avatar(
        self,
        file: UploadFile,
        user_id: int,
        max_size: int = 10 * 1024 * 1024
    ) -> str:
        """
        上传用户头像

        Args:
            file: 上传的文件对象
            user_id: 用户ID
            max_size: 最大文件大小（字节），默认10MB

        Returns:
            str: 头像的访问URL

        Raises:
            HTTPException: 上传失败时抛出异常
        """
        try:
            self._check_client()

            # 验证文件类型
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail="请上传图片文件"
                )

            # 读取文件内容
            file_content = await file.read()
            file_size = len(file_content)

            # 验证文件大小
            if file_size > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"文件大小超过限制，最大允许 {max_size // (1024 * 1024)}MB"
                )

            # 生成唯一文件名
            file_ext = self._get_file_extension(file.filename or "jpg")
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            random_str = str(uuid.uuid4())[:8]
            object_name = f"user_image/avatar_{user_id}_{timestamp}_{random_str}.{file_ext}"

            logger.info(f"开始上传头像: user_id={user_id}, object_name={object_name}, size={file_size}")

            # 上传文件到OSS
            self.client.put_object(
                object_name,
                file_content,
                headers={
                    'Content-Type': file.content_type,
                    'x-oss-object-acl': 'public-read'
                }
            )

            # 生成访问URL
            avatar_url = self._generate_url(object_name)

            logger.info(f"头像上传成功: user_id={user_id}, object_name={object_name}, url={avatar_url}")

            return avatar_url

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"头像上传失败: user_id={user_id}, error={str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"头像上传失败: {str(e)}"
            )

    async def upload_image(
        self,
        file: UploadFile,
        folder: str = "images",
        max_size: int = 10 * 1024 * 1024
    ) -> str:
        """
        上传通用图片

        Args:
            file: 上传的文件对象
            folder: 存储文件夹
            max_size: 最大文件大小（字节），默认10MB

        Returns:
            str: 图片的访问URL
        """
        try:
            self._check_client()

            # 验证文件类型
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=400,
                    detail="请上传图片文件"
                )

            # 读取文件内容
            file_content = await file.read()
            file_size = len(file_content)

            # 验证文件大小
            if file_size > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"文件大小超过限制，最大允许 {max_size // (1024 * 1024)}MB"
                )

            # 生成唯一文件名
            file_ext = self._get_file_extension(file.filename or "jpg")
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            random_str = str(uuid.uuid4())[:8]
            object_name = f"{folder}/{timestamp}_{random_str}.{file_ext}"

            # 上传文件到OSS
            self.client.put_object(
                object_name,
                file_content,
                headers={
                    'Content-Type': file.content_type,
                    'x-oss-object-acl': 'public-read'
                }
            )

            # 生成访问URL
            image_url = self._generate_url(object_name)

            logger.info(f"图片上传成功: object_name={object_name}, size={file_size}")

            return image_url

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"图片上传失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"图片上传失败: {str(e)}"
            )

    def delete_file(self, object_name: str) -> bool:
        """
        删除OSS文件

        Args:
            object_name: 对象名称

        Returns:
            bool: 是否删除成功
        """
        try:
            self._check_client()

            logger.info(f"开始删除文件: {object_name}")

            self.client.delete_object(object_name)

            logger.info(f"文件删除成功: {object_name}")
            return True

        except Exception as e:
            logger.error(f"文件删除失败: object_name={object_name}, error={str(e)}")
            return False

    def file_exists(self, object_name: str) -> bool:
        """
        检查文件是否存在

        Args:
            object_name: 对象名称

        Returns:
            bool: 文件是否存在
        """
        try:
            self._check_client()

            self.client.head_object(object_name)
            return True

        except Exception:
            return False

    def _get_file_extension(self, filename: str) -> str:
        """
        获取文件扩展名

        Args:
            filename: 文件名

        Returns:
            str: 文件扩展名（小写）
        """
        if '.' in filename:
            return filename.rsplit('.', 1)[1].lower()
        return 'jpg'

    def _generate_url(self, object_name: str) -> str:
        """
        生成文件访问URL

        Args:
            object_name: 对象名称

        Returns:
            str: 访问URL
        """
        # 使用默认OSS域名
        return f"https://{self.bucket_name}.{self.endpoint}/{object_name}"

    def get_file_url(self, object_name: str, expires: int = 3600) -> str:
        """
        获取文件的签名URL（用于私有文件）

        Args:
            object_name: 对象名称
            expires: 过期时间（秒），默认1小时

        Returns:
            str: 签名URL
        """
        try:
            self._check_client()

            # 生成签名URL
            url = self.client.sign_url(
                'GET',
                object_name,
                expires
            )

            return url

        except Exception as e:
            logger.error(f"生成签名URL失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"生成签名URL失败: {str(e)}"
            )


# 创建全局OSS服务实例
oss_service = OSSService()
