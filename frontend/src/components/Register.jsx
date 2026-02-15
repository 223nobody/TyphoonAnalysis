/**
 * 注册组件
 * 优化说明：
 * 1. 添加 cursor-pointer 到链接
 * 2. 优化过渡动画
 * 3. 改进无障碍性标签
 * 4. 使用 4 空格缩进
 */
import React, { useState } from "react";
import { Form, Input, Button, message } from "antd";
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  PhoneOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { register } from "../services/api";
import "../styles/UserCenter.css";

const Register = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      await register(values);
      message.success("注册成功，请登录");
      navigate("/login");
    } catch (error) {
      message.error(error.message || "注册失败");
    } finally {
      setLoading(false);
    }
  };

  const handleLoginClick = (e) => {
    e.preventDefault();
    navigate("/login");
  };

  return (
    <div className="auth-container">
      <div className="floating-orbs" />
      <div className="auth-card">
        <div className="auth-header">
          <h1>创建账号</h1>
          <p>注册台风分析系统</p>
        </div>

        <Form
          name="register"
          className="auth-form"
          onFinish={onFinish}
          autoComplete="off"
        >
          <Form.Item
            name="username"
            rules={[
              { required: true, message: "请输入用户名" },
              { min: 3, message: "用户名至少3个字符" },
              { max: 50, message: "用户名最多50个字符" },
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名"
              size="large"
              aria-label="用户名输入框"
            />
          </Form.Item>

          <Form.Item
            name="email"
            rules={[
              { required: true, message: "请输入邮箱" },
              { type: "email", message: "请输入有效的邮箱地址" },
            ]}
          >
            <Input
              prefix={<MailOutlined />}
              placeholder="邮箱"
              size="large"
              aria-label="邮箱输入框"
            />
          </Form.Item>

          <Form.Item name="phone">
            <Input
              prefix={<PhoneOutlined />}
              placeholder="手机号（可选）"
              size="large"
              aria-label="手机号输入框"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: "请输入密码" },
              { min: 6, message: "密码至少6个字符" },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              size="large"
              aria-label="密码输入框"
            />
          </Form.Item>

          <Form.Item
            name="confirm"
            dependencies={["password"]}
            rules={[
              { required: true, message: "请确认密码" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("password") === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error("两次输入的密码不一致"));
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="确认密码"
              size="large"
              aria-label="确认密码输入框"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              className="auth-button"
              loading={loading}
            >
              注册
            </Button>
          </Form.Item>
        </Form>

        <div className="auth-footer">
          <span>已有账号？</span>{" "}
          <a href="/login" onClick={handleLoginClick}>
            立即登录
          </a>
        </div>
      </div>
    </div>
  );
};

export default Register;
