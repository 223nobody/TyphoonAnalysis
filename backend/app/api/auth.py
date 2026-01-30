from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import logging
import json

from app.core.database import get_db
from app.core.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_active_user
)
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    Token
)
from app.services.oss.oss_service import oss_service

router = APIRouter(prefix="/auth", tags=["用户认证"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(User).where(User.username == user_data.username)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        stmt = select(User).where(User.email == user_data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )
        
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password=get_password_hash(user_data.password),
            phone=user_data.phone,
            status=1
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(f"新用户注册成功: {user_data.username}")
        
        user_response = UserResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            phone=new_user.phone,
            avatar_url=new_user.avatar_url,
            status=new_user.status,
            created_at=new_user.created_at,
            updated_at=new_user.updated_at,
            last_login_at=new_user.last_login_at
        )
        
        return user_response
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"用户注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(User).where(User.username == form_data.username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not verify_password(form_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if user.status != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号已被禁用"
            )
        
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
        
        access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
        
        logger.info(f"用户登录成功: {user.username}")
        
        await db.refresh(user)
        
        user_response = UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            avatar_url=user.avatar_url,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at
        )
        
        return Token(
            access_token=access_token,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    user_response = UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        avatar_url=current_user.avatar_url,
        status=current_user.status,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login_at=current_user.last_login_at
    )
    return user_response


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        if user_update.email is not None:
            stmt = select(User).where(
                User.email == user_update.email,
                User.id != current_user.id
            )
            result = await db.execute(stmt)
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被其他用户使用"
                )
            current_user.email = user_update.email
        
        if user_update.phone is not None:
            current_user.phone = user_update.phone
        
        if user_update.avatar_url is not None:
            current_user.avatar_url = user_update.avatar_url
        
        await db.commit()
        await db.refresh(current_user)
        
        logger.info(f"用户信息更新成功: {current_user.username}")
        
        user_response = UserResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            phone=current_user.phone,
            avatar_url=current_user.avatar_url,
            status=current_user.status,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at,
            last_login_at=current_user.last_login_at
        )
        
        return user_response
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新用户信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新失败: {str(e)}"
        )


@router.post("/upload-avatar", response_model=dict)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    上传用户头像

    Args:
        file: 上传的头像文件
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        dict: 包含头像 URL 的响应
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="请上传图片文件"
            )

        # 验证文件大小（10MB 限制）
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制，最大允许 {max_size // (1024 * 1024)}MB"
            )

        # 重置文件指针
        await file.seek(0)

        # 上传到 OSS
        avatar_url = await oss_service.upload_avatar(file, current_user.id)

        # 更新用户头像 URL
        current_user.avatar_url = avatar_url
        await db.commit()
        await db.refresh(current_user)

        logger.info(f"用户头像上传成功: {current_user.username} -> {avatar_url}")

        return {
            "url": avatar_url,
            "success": True,
            "message": "头像上传成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"头像上传失败: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"头像上传失败: {str(e)}"
        )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    logger.info(f"用户登出: {current_user.username}")
    return {"message": "登出成功"}


@router.get("/sts-token")
async def get_sts_token():
    """
    获取STS临时凭证

    前端使用此凭证可以直接上传文件到OSS，无需经过后端服务器，
    减轻服务器压力并提高上传速度。

    Returns:
        dict: 包含accessKeyId、accessKeySecret、securityToken和expiration

    Raises:
        HTTPException: 当获取STS凭证失败时抛出500错误
    """
    try:
        from app.core.config import settings
        from app.services.oss_service import oss_service

        # 检查OSS服务是否可用
        if oss_service.client is None:
            logger.error("OSS服务未配置，请检查环境变量配置")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OSS服务未配置，请检查环境变量中的OSS_ACCESS_KEY_ID、OSS_ACCESS_KEY_SECRET等配置"
            )

        # 尝试使用阿里云STS服务获取临时凭证
        try:
            from alibabacloud_tea_openapi import models as open_api_models
            from alibabacloud_sts20150401.client import Client as StsClient

            # 创建STS客户端配置
            config = open_api_models.Config(
                access_key_id=settings.OSS_ACCESS_KEY_ID,
                access_key_secret=settings.OSS_ACCESS_KEY_SECRET,
                region_id=settings.OSS_REGION.replace('oss-', '')
            )

            # 创建STS客户端
            client = StsClient(config)

            # 创建请求
            assume_role_request = models.AssumeRoleRequest(
                role_arn=os.getenv("ALIYUN_ROLE_ARN", ""),
                role_session_name="typhoon-analysis-upload",
                duration_seconds=3600
            )

            # 发送请求
            response = client.assume_role(assume_role_request)
            credentials = response.body.credentials

            logger.info(f"STS临时凭证获取成功，过期时间: {credentials.expiration}")

            return {
                "accessKeyId": credentials.access_key_id,
                "accessKeySecret": credentials.access_key_secret,
                "securityToken": credentials.security_token,
                "expiration": credentials.expiration
            }

        except ImportError:
            # 如果没有安装aliyun-python-sdk-sts，直接使用OSS配置
            logger.warning("未安装aliyun-python-sdk-sts，直接使用OSS配置")
            from datetime import timedelta
            expiration = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            return {
                "accessKeyId": settings.OSS_ACCESS_KEY_ID,
                "accessKeySecret": settings.OSS_ACCESS_KEY_SECRET,
                "securityToken": "",
                "expiration": expiration
            }
        except Exception as e:
            logger.error(f"STS服务调用失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取STS临时凭证失败: {str(e)}"
            )

    except Exception as e:
        logger.error(f"获取STS临时凭证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取STS临时凭证失败: {str(e)}"
        )



