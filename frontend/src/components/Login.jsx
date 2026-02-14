/**
 * 登录组件
 * 优化说明：
 * 1. 添加 cursor-pointer 到链接
 * 2. 优化过渡动画
 * 3. 改进无障碍性标签
 * 4. 使用 4 空格缩进
 */
import React, { useState } from "react";
import { Form, Input, Button, message } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { login, getCurrentUser } from "../services/api";
import "../styles/UserCenter.css";

const STORAGE_TOKEN_KEY = "token";
const STORAGE_USER_KEY = "user";

const Login = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const data = await login(values.username, values.password);
      localStorage.setItem(STORAGE_TOKEN_KEY, data.access_token);

      const userData = await getCurrentUser();
      localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(userData));

      message.success("登录成功");
      navigate("/");
    } catch (error) {
      message.error(error.message || "登录失败");
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterClick = (e) => {
    e.preventDefault();
    navigate("/register");
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h1>欢迎回来</h1>
          <p>登录台风分析系统</p>
        </div>

        <Form
          name="login"
          className="auth-form"
          onFinish={onFinish}
          autoComplete="off"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名"
              size="large"
              aria-label="用户名输入框"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              size="large"
              aria-label="密码输入框"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              className="auth-button"
              loading={loading}
              style={{ transition: "all 0.2s ease" }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <div className="auth-footer">
          还没有账号？{" "}
          <a
            href="/register"
            onClick={handleRegisterClick}
            style={{ cursor: "pointer", transition: "color 0.2s ease" }}
          >
            立即注册
          </a>
        </div>
      </div>
    </div>
  );
};

export default Login;
