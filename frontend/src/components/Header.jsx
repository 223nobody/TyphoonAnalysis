/**
 * 头部组件
 * 优化说明：
 * 1. 移除 emoji 图标 🌀，使用 SVG 图标（CloudOutlined）
 * 2. 添加 cursor-pointer 到可点击元素
 * 3. 优化交互反馈和过渡动画

 */
import React, { useState, useEffect, useRef, useCallback } from "react";
import { headerRoutes, getCurrentUser } from "../services/api";
import {
  UserOutlined,
  LogoutOutlined,
  CloudOutlined,
  BookOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import { Avatar, Dropdown, message, Button } from "antd";
import { useNavigate } from "react-router-dom";
import "../styles/Header.css";

function Header() {
  const [user, setUser] = useState(null);
  const [avatarLoading, setAvatarLoading] = useState(false);
  const [avatarError, setAvatarError] = useState(false);
  const imageRef = useRef(null);
  const navigate = useNavigate();

  const getAvatarUrlWithProcessing = (url) => {
    if (!url) return null;
    if (url.includes("typhoonanalysis.oss-cn-wuhan-lr.aliyuncs.com")) {
      return `${url}?x-oss-process=image/resize,w_128,h_128/quality,q_80`;
    }
    return url;
  };

  const loadAvatarImage = (avatarUrl) => {
    if (!avatarUrl) {
      setAvatarLoading(false);
      setAvatarError(false);
      return;
    }

    const processedUrl = getAvatarUrlWithProcessing(avatarUrl);
    console.log("Header - 开始加载头像:", avatarUrl);
    console.log("Header - 处理后的URL:", processedUrl);
    setAvatarLoading(true);
    setAvatarError(false);

    const img = new Image();
    imageRef.current = img;

    img.onload = () => {
      console.log("Header - 头像加载成功");
      setAvatarLoading(false);
      setAvatarError(false);
    };

    img.onerror = (error) => {
      console.error("Header - 头像加载失败:", error);
      setAvatarLoading(false);
      setAvatarError(true);
    };

    img.src = processedUrl;
  };

  const refreshUserInfo = useCallback(async () => {
    try {
      const userData = await getCurrentUser();
      console.log("Header - 从数据库获取用户信息:", userData);
      setUser(userData);
      localStorage.setItem("user", JSON.stringify(userData));
      loadAvatarImage(userData?.avatar_url);
    } catch (error) {
      console.error("Header - 从数据库获取用户信息失败:", error);
      setAvatarLoading(false);
      setAvatarError(true);
    }
  }, []);

  useEffect(() => {
    const userStr = localStorage.getItem("user");
    if (userStr) {
      try {
        const userData = JSON.parse(userStr);
        console.log("Header - 从localStorage解析用户数据:", userData);
        setUser(userData);

        if (userData?.avatar_url) {
          loadAvatarImage(userData.avatar_url);
        } else {
          console.log("Header - 用户没有头像URL，从数据库刷新");
          refreshUserInfo();
        }
      } catch (error) {
        console.error("Header - 解析用户数据失败:", error);
        setAvatarLoading(false);
        setAvatarError(false);
      }
    }

    return () => {
      if (imageRef.current) {
        imageRef.current.onload = null;
        imageRef.current.onerror = null;
        imageRef.current.src = "";
        imageRef.current = null;
      }
    };
  }, [refreshUserInfo]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
    setAvatarLoading(false);
    setAvatarError(false);
    message.success("已退出登录");
    navigate("/login");
  };

  const handleLoginClick = (e) => {
    e.preventDefault();
    navigate("/login");
  };

  const handleAvatarClick = () => {
    navigate("/user-center");
  };

  // 键盘导航支持 - 增强可访问性
  const handleUserInfoKeyDown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleAvatarClick();
    }
  };

  const userMenuItems = [
    {
      key: "user-center",
      label: "用户中心",
      onClick: handleAvatarClick,
    },
    {
      type: "divider",
    },
    {
      key: "logout",
      label: "退出登录",
      icon: <LogoutOutlined />,
      onClick: handleLogout,
    },
  ];

  return (
    <header className="header" role="banner">
      <h1 className="header-title">
        <CloudOutlined className="header-icon" aria-hidden="true" />
        <span>台风路径可视化系统</span>
      </h1>

      <Button
        type="primary"
        icon={<BookOutlined />}
        onClick={() =>
          window.open(headerRoutes.apiDocs, "_blank", "noopener,noreferrer")
        }
        className="header-button-api-docs"
      >
        API文档
      </Button>
      <Button
        type="primary"
        icon={<BookOutlined />}
        onClick={() =>
          window.open(headerRoutes.apiHealth, "_blank", "noopener,noreferrer")
        }
        className="header-button-api-health"
      >
        系统状态
      </Button>
      <div className="header-user">
        {user ? (
          <Dropdown
            menu={{ items: userMenuItems }}
            placement="bottomRight"
            trigger={["hover"]}
          >
            <Avatar
              src={
                user?.avatar_url && !avatarError && !avatarLoading
                  ? getAvatarUrlWithProcessing(user.avatar_url)
                  : undefined
              }
              icon={<UserOutlined />}
              size={64}
              onClick={(e) => {
                e.stopPropagation();
                handleAvatarClick();
              }}
              style={{ cursor: "pointer" }}
            />
          </Dropdown>
        ) : (
          <a
            href="/login"
            className="login-link"
            onClick={handleLoginClick}
            aria-label="登录"
            style={{ cursor: "pointer" }}
          >
            登录
          </a>
        )}
      </div>
    </header>
  );
}

export default Header;
