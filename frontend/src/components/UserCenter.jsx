/**
 * 用户中心组件
 */
import { useState, useEffect, useRef, useCallback } from "react";
import {
  Form,
  Input,
  Button,
  Upload,
  message,
  Avatar,
  Card,
  Spin,
  Divider,
  Row,
  Col,
  Modal,
  Progress,
  Alert,
} from "antd";
import {
  UserOutlined,
  EditOutlined,
  MailOutlined,
  PhoneOutlined,
  ArrowLeftOutlined,
  LogoutOutlined,
  SafetyOutlined,
  HistoryOutlined,
  StarOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  SettingOutlined,
  UploadOutlined,
  CloudUploadOutlined,
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import {
  getCurrentUser,
  updateUser,
  getUserStats,
  getCollectTyphoons,
  getUserReports,
  getQueryHistoryByCount,
} from "../services/api";
import ossUploadService from "../services/ossUploadService";
import {
  validateFile,
  readFileAsDataURL,
  formatFileSize,
} from "../services/ossUtils";
import "../styles/UserCenter.css";

const PHONE_REGEX = /^1[3-9]\d{9}$/;
const STORAGE_TOKEN_KEY = "token";
const STORAGE_USER_KEY = "user";

const UserCenter = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const token = localStorage.getItem(STORAGE_TOKEN_KEY);

  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewImage, setPreviewImage] = useState("");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [fileInfo, setFileInfo] = useState(null);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  // 用户统计数据
  const [stats, setStats] = useState({
    query_count: 0,
    collect_count: 0,
    report_count: 0,
  });
  const [collectTyphoons, setCollectTyphoons] = useState([]);
  const [userReports, setUserReports] = useState([]);
  const [queryHistory, setQueryHistory] = useState([]);

  useEffect(() => {
    if (!token) {
      message.error("请先登录");
      navigate("/login");
      return;
    }

    fetchUserInfo();
    fetchUserStats();
    fetchCollectTyphoons();
    fetchUserReports();
    fetchQueryHistory();
  }, []);

  const fetchUserInfo = async () => {
    try {
      const data = await getCurrentUser();
      setUser(data);
      localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(data));
      form.setFieldsValue({
        email: data.email,
        phone: data.phone,
      });
    } catch (error) {
      message.error(error.message || "获取用户信息失败");
      navigate("/login");
    } finally {
      setLoading(false);
    }
  };

  const fetchUserStats = async () => {
    try {
      const data = await getUserStats();
      setStats(data);
    } catch (error) {
      console.error("获取统计信息失败:", error);
      message.error(error.message || "获取统计信息失败");
    }
  };

  const fetchCollectTyphoons = async () => {
    try {
      const data = await getCollectTyphoons();
      setCollectTyphoons(data);
    } catch (error) {
      console.error("获取收藏列表失败:", error);
      message.error(error.message || "获取收藏列表失败");
    }
  };

  const fetchUserReports = async () => {
    try {
      const data = await getUserReports();
      setUserReports(data.items || []);
    } catch (error) {
      console.error("获取报告列表失败:", error);
    }
  };

  const fetchQueryHistory = async () => {
    try {
      const data = await getQueryHistoryByCount(10);
      setQueryHistory(data || []);
    } catch (error) {
      console.error("获取查询历史失败:", error);
    }
  };

  const handleUpdate = async (values) => {
    setUpdating(true);
    try {
      const data = await updateUser(values);
      setUser(data);
      localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(data));
      message.success("更新成功");
    } catch (error) {
      message.error(error.message || "更新失败");
    } finally {
      setUpdating(false);
    }
  };

  const handleAvatarChange = async (avatarUrl) => {
    if (avatarUrl) {
      const updatedUser = { ...user, avatar_url: avatarUrl };
      setUser(updatedUser);
      localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(updatedUser));
      try {
        await updateUser({ avatar_url: avatarUrl });
        message.success("头像更新成功");
      } catch (error) {
        message.error(error.message || "头像更新失败");
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_TOKEN_KEY);
    localStorage.removeItem(STORAGE_USER_KEY);
    message.success("已退出登录");
    navigate("/login");
  };

  const handleBack = () => {
    navigate("/");
  };

  const handleStatClick = (statType) => {
    navigate(`/history?type=${statType}`);
  };

  const handlePreview = useCallback(async () => {
    if (!user?.avatar_url) return;
    setPreviewImage(user.avatar_url);
    setPreviewVisible(true);
  }, [user?.avatar_url]);

  const handleRemove = useCallback(() => {
    handleAvatarChange(null);
    setFileInfo(null);
    setProgress(0);
    setError(null);
    message.success("头像已删除");
  }, []);

  const handleFileSelect = useCallback(
    async (file) => {
      setError(null);

      const validation = validateFile(file);
      if (!validation.valid) {
        setError(validation.error);
        message.error(validation.error);
        return false;
      }

      try {
        setUploading(true);
        setProgress(0);
        setFileInfo({
          name: file.name,
          size: file.size,
          type: file.type,
        });

        const result = await ossUploadService.uploadAvatarViaBackend(
          file,
          user?.id || user?.username,
          (progressData) => {
            setProgress(progressData);
          },
        );

        if (result.success) {
          handleAvatarChange(result.url);
          setFileInfo({
            name: file.name,
            size: file.size,
          });
          message.success("头像上传成功");
        } else {
          throw new Error("上传失败");
        }
      } catch (err) {
        const errorMessage = err.message || "上传失败，请重试";
        setError(errorMessage);
        message.error(errorMessage);
      } finally {
        setUploading(false);
      }

      return false;
    },
    [user?.id, user?.username],
  );

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (uploading) return;

      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleFileSelect(files[0]);
      }
    },
    [uploading, handleFileSelect],
  );

  const handleButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  if (loading) {
    return (
      <div className="loading-wrapper">
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="user-center-wrapper">
      <div className="user-center-container">
        <div className="user-center-back-button">
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
            className="back-button"
            style={{ cursor: "pointer", transition: "all 0.2s ease" }}
          >
            返回主页
          </Button>
        </div>

        <Card className="user-center-card">
          <div className="user-center-card-content">
            <div className="user-center-header-section">
              <div className="user-avatar-section">
                <Avatar
                  size={100}
                  src={user?.avatar_url}
                  icon={<UserOutlined />}
                  className="user-avatar"
                  alt={`${user?.username}的头像`}
                />
                <div className="user-avatar-upload">
                  <div className="avatar-upload-wrapper">
                    {error && (
                      <Alert
                        message="上传失败"
                        description={error}
                        type="error"
                        showIcon
                        closable
                        onClose={() => setError(null)}
                        className="avatar-upload-error"
                      />
                    )}

                    {!user?.avatar_url ? (
                      <div
                        className={`avatar-upload-area ${
                          dragActive ? "drag-active" : ""
                        }`}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                        onClick={!uploading ? handleButtonClick : undefined}
                      >
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept="image/jpeg,image/jpg,image/png,image/webp"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                              handleFileSelect(file);
                            }
                            e.target.value = "";
                          }}
                          style={{ display: "none" }}
                          disabled={uploading}
                        />
                        <div className="avatar-upload-content">
                          {uploading ? (
                            <>
                              <CloudUploadOutlined className="upload-icon" />
                              <div className="upload-text">上传中...</div>
                              <Progress
                                percent={progress}
                                size="small"
                                status="active"
                                className="upload-progress"
                              />
                              {fileInfo && (
                                <div className="upload-file-info">
                                  <div className="file-name">
                                    {fileInfo.name}
                                  </div>
                                  <div className="file-size">
                                    {formatFileSize(fileInfo.size)}
                                  </div>
                                </div>
                              )}
                            </>
                          ) : (
                            <>
                              <UploadOutlined className="upload-icon" />
                              <div className="upload-text">
                                点击或拖拽上传头像
                              </div>
                              <div className="upload-hint">
                                支持 JPG、PNG、WEBP 格式，最大 10MB
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="avatar-preview-area">
                        <div className="avatar-preview-content">
                          <img
                            src={user.avatar_url}
                            alt="头像预览"
                            className="avatar-preview-image"
                            onClick={handlePreview}
                          />
                          <div className="avatar-preview-actions">
                            <Button
                              icon={<UploadOutlined />}
                              onClick={handleButtonClick}
                              disabled={uploading}
                              size="small"
                              style={{ color: "#4070FF" }}
                            >
                              更换
                            </Button>
                            <Button
                              icon={<EyeOutlined />}
                              onClick={handlePreview}
                              size="small"
                            >
                              预览
                            </Button>
                            <Button
                              danger
                              icon={<DeleteOutlined />}
                              onClick={handleRemove}
                              size="small"
                            >
                              删除
                            </Button>
                          </div>
                          <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/jpeg,image/jpg,image/png,image/webp"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) {
                                handleFileSelect(file);
                              }
                              e.target.value = "";
                            }}
                            style={{ display: "none" }}
                            disabled={uploading}
                          />
                        </div>
                        {fileInfo && (
                          <div className="avatar-file-info">
                            <div className="file-name">{fileInfo.name}</div>
                            <div className="file-size">
                              {formatFileSize(fileInfo.size)}
                            </div>
                            {fileInfo.uploadTime && (
                              <div className="upload-time">
                                上传时间:{" "}
                                {new Date(fileInfo.uploadTime).toLocaleString()}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    <Modal
                      open={previewVisible}
                      title="头像预览"
                      footer={null}
                      onCancel={() => setPreviewVisible(false)}
                      centered
                      width={600}
                    >
                      <img
                        alt="头像预览"
                        style={{ width: "100%" }}
                        src={previewImage}
                      />
                    </Modal>
                  </div>
                </div>
              </div>

              <div className="user-info-section">
                <div className="user-name-section">
                  <h2>{user?.username}</h2>
                  <span className="user-role-badge">
                    <SafetyOutlined /> 普通用户
                  </span>
                </div>
                <p className="user-email">{user?.email}</p>
                <div className="user-stats">
                  <div
                    className="user-stat clickable-stat"
                    onClick={() => handleStatClick("query_count")}
                  >
                    <div className="user-stat-icon">
                      <HistoryOutlined />
                    </div>
                    <div className="user-stat-info">
                      <div className="user-stat-value">{stats.query_count}</div>
                      <div className="user-stat-label">查询次数</div>
                    </div>
                  </div>
                  <div
                    className="user-stat clickable-stat"
                    onClick={() => handleStatClick("collect_count")}
                  >
                    <div className="user-stat-icon">
                      <StarOutlined />
                    </div>
                    <div className="user-stat-info">
                      <div className="user-stat-value">
                        {stats.collect_count}
                      </div>
                      <div className="user-stat-label">收藏台风</div>
                    </div>
                  </div>
                  <div
                    className="user-stat clickable-stat"
                    onClick={() => handleStatClick("report_count")}
                  >
                    <div className="user-stat-icon">
                      <FileTextOutlined />
                    </div>
                    <div className="user-stat-info">
                      <div className="user-stat-value">
                        {stats.report_count}
                      </div>
                      <div className="user-stat-label">生成报告</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <Divider className="user-center-divider" />

            <div className="user-center-content-section">
              <h3 className="user-center-content-title">
                <SettingOutlined /> 编辑资料
              </h3>
              <Form form={form} layout="vertical" onFinish={handleUpdate}>
                <Form.Item
                  label="邮箱"
                  name="email"
                  rules={[
                    { required: true, message: "请输入邮箱" },
                    { type: "email", message: "请输入有效的邮箱地址" },
                  ]}
                >
                  <Input
                    prefix={<MailOutlined />}
                    placeholder="请输入邮箱地址"
                    size="large"
                    aria-label="邮箱输入框"
                  />
                </Form.Item>

                <Form.Item
                  label="手机号"
                  name="phone"
                  rules={[
                    { pattern: PHONE_REGEX, message: "请输入有效的手机号" },
                  ]}
                >
                  <Input
                    prefix={<PhoneOutlined />}
                    placeholder="请输入手机号码"
                    size="large"
                    aria-label="手机号输入框"
                  />
                </Form.Item>

                <Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<EditOutlined />}
                    className="user-center-save-button"
                    loading={updating}
                    size="large"
                    style={{ cursor: "pointer", transition: "all 0.2s ease" }}
                  >
                    保存修改
                  </Button>
                </Form.Item>
              </Form>

              <Form.Item>
                <Button
                  danger
                  icon={<LogoutOutlined />}
                  onClick={handleLogout}
                  className="user-center-logout-button"
                  size="large"
                  style={{ cursor: "pointer", transition: "all 0.2s ease" }}
                >
                  退出登录
                </Button>
              </Form.Item>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default UserCenter;
