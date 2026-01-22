/**
 * AI客服聊天界面组件
 */
import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "../styles/AIAgent.css";

function AIAgent() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [inputText, setInputText] = useState("");
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedModel, setSelectedModel] = useState("deepseek"); // 模型选择状态
  const messagesEndRef = useRef(null);

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 初始化：创建新会话并加载热门问题
  useEffect(() => {
    initializeChat();
    loadSessions();
  }, []);

  // 初始化聊天
  const initializeChat = async () => {
    try {
      setLoading(true);
      // 创建新会话
      const sessionResponse = await axios.post(
        "http://localhost:8000/api/ai-agent/sessions"
      );
      setCurrentSessionId(sessionResponse.data.session_id);

      // 加载热门问题
      const questionsResponse = await axios.get(
        "http://localhost:8000/api/ai-agent/questions"
      );
      setQuestions(questionsResponse.data);

      // 添加初始欢迎消息，包含问题列表
      const welcomeMessage = {
        type: "bot",
        content: "您可能关心以下内容：",
        timestamp: new Date(),
        questionList: questionsResponse.data,
      };
      setMessages([welcomeMessage]);
    } catch (error) {
      console.error("初始化失败:", error);
      const errorMessage = {
        type: "bot",
        content: "抱歉，初始化失败，请刷新页面重试。",
        timestamp: new Date(),
      };
      setMessages([errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  // 加载会话列表
  const loadSessions = async () => {
    try {
      const response = await axios.get(
        "http://localhost:8000/api/ai-agent/sessions"
      );
      setSessions(response.data);
    } catch (error) {
      console.error("加载会话列表失败:", error);
    }
  };

  // 处理问题点击
  const handleQuestionClick = async (questionId, questionText) => {
    // 添加用户消息
    const userMessage = {
      type: "user",
      content: questionText,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // 查询答案并保存到历史
    try {
      const response = await axios.post(
        "http://localhost:8000/api/ai-agent/ask",
        {
          session_id: currentSessionId,
          question: questionText,
          model: selectedModel, // 传递选择的模型
        }
      );
      const botMessage = {
        type: "bot",
        content: response.data.answer,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);

      // 刷新会话列表
      loadSessions();
    } catch (error) {
      console.error("获取答案失败:", error);
      const errorMessage = {
        type: "bot",
        content: "抱歉，获取答案失败，请稍后重试。",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  // 处理发送消息
  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage = {
      type: "user",
      content: inputText,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputText("");

    try {
      const response = await axios.post(
        "http://localhost:8000/api/ai-agent/ask",
        {
          session_id: currentSessionId,
          question: inputText,
          model: selectedModel, // 传递选择的模型
        }
      );
      const botMessage = {
        type: "bot",
        content: response.data.answer,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);

      // 刷新会话列表
      loadSessions();
    } catch (error) {
      console.error("发送消息失败:", error);
      const errorMessage = {
        type: "bot",
        content: "抱歉，发送消息失败，请稍后重试。",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  // 处理回车键发送
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 创建新对话
  const handleNewChat = async () => {
    try {
      const response = await axios.post(
        "http://localhost:8000/api/ai-agent/sessions"
      );
      setCurrentSessionId(response.data.session_id);

      // 重新加载欢迎消息
      const questionsResponse = await axios.get(
        "http://localhost:8000/api/ai-agent/questions"
      );
      const welcomeMessage = {
        type: "bot",
        content: "您可能关心以下内容：",
        timestamp: new Date(),
        questionList: questionsResponse.data,
      };
      setMessages([welcomeMessage]);

      // 刷新会话列表
      loadSessions();
    } catch (error) {
      console.error("创建新对话失败:", error);
    }
  };

  // 切换到历史会话
  const handleSessionClick = async (sessionId) => {
    try {
      setLoading(true);
      setCurrentSessionId(sessionId);

      // 加载该会话的历史记录
      const response = await axios.get(
        `http://localhost:8000/api/ai-agent/sessions/${sessionId}`
      );

      // 转换为消息格式
      const historyMessages = [];
      response.data.forEach((item) => {
        historyMessages.push({
          type: "user",
          content: item.question,
          timestamp: new Date(item.created_at),
        });
        historyMessages.push({
          type: "bot",
          content: item.answer,
          timestamp: new Date(item.created_at),
        });
      });

      setMessages(historyMessages);
    } catch (error) {
      console.error("加载会话历史失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 切换侧栏折叠状态
  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  // 返回首页
  const handleBack = () => {
    navigate("/");
  };

  return (
    <div className="ai-agent-container">
      {/* 左侧侧栏 */}
      <div
        className={`ai-agent-sidebar ${sidebarCollapsed ? "collapsed" : ""}`}
      >
        <div className="sidebar-header">
          <button className="new-chat-button" onClick={handleNewChat}>
            ➕ 新建对话
          </button>
          <button className="toggle-sidebar-button" onClick={toggleSidebar}>
            {sidebarCollapsed ? "→" : "←"}
          </button>
        </div>

        {!sidebarCollapsed && (
          <div className="sidebar-content">
            {/* 搜索框 */}
            <div className="sidebar-search">
              <input
                type="text"
                placeholder="搜索对话..."
                className="search-input"
              />
            </div>

            <h3>历史对话</h3>
            <div className="session-list">
              {sessions.map((session) => (
                <div
                  key={session.session_id}
                  className={`session-item ${
                    session.session_id === currentSessionId ? "active" : ""
                  }`}
                  onClick={() => handleSessionClick(session.session_id)}
                >
                  <div className="session-title">
                    {session.first_question.length > 30
                      ? session.first_question.substring(0, 30) + "..."
                      : session.first_question}
                  </div>
                  <div className="session-info">
                    <span className="session-count">
                      {session.message_count} 条消息
                    </span>
                    <span className="session-time">
                      {new Date(session.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 主聊天区域 */}
      <div className="ai-agent-main">
        <div className="ai-agent-header">
          <button className="back-button" onClick={handleBack}>
            ← 返回
          </button>
          <h2>🤖 AI助手</h2>
          <div className="header-placeholder"></div>
        </div>

        <div className="ai-agent-chat">
          {loading ? (
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p>正在加载...</p>
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <div key={index} className={`message ${message.type}`}>
                  <div className="message-avatar">
                    {message.type === "bot" ? "🤖" : "👤"}
                  </div>
                  <div className="message-content">
                    <div className="message-text">
                      {message.content}
                      {message.questionList && (
                        <div className="question-list">
                          {message.questionList.map((q, idx) => (
                            <div
                              key={q.id}
                              className="question-item"
                              onClick={() =>
                                handleQuestionClick(q.id, q.question)
                              }
                            >
                              <span className="question-number">
                                {idx + 1}.
                              </span>
                              <span className="question-text">
                                {q.question}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="message-time">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* 输入框区域 */}
        <div className="ai-agent-input">
          <div className="input-controls">
            <select
              className="model-selector"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              <option value="deepseek">DeepSeek</option>
              <option value="glm">GLM (智谱清言)</option>
              <option value="qwen">Qwen (通义千问)</option>
            </select>
            <textarea
              className="input-textarea"
              placeholder="输入您的问题..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button
              className="send-button"
              onClick={handleSendMessage}
              disabled={!inputText.trim()}
            >
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AIAgent;
