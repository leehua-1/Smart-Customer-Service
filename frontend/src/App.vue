<template>
  <div class="chat-wrapper">
    <div class="chat-container">
      <header class="chat-header">
        <div class="header-left">
          <div class="logo-icon">AI</div>
          <div class="header-title">
            <h1>智能客服系统</h1>
            <span class="subtitle">专业、高效、贴心</span>
          </div>
        </div>
        <div class="header-right">
          <span class="session-tag">会话：{{ shortSessionId }}</span>
          
          <!-- 修改：点击按钮结束人工 -->
          <transition name="fade">
            <span v-if="isHumanMode" class="human-badge cancel-btn" @click="cancelHuman">
              ✖ 结束人工
            </span>
          </transition>
        </div>
      </header>

      <main class="chat-body" ref="messageListRef">
        <div v-for="(msg, index) in messages" :key="index" class="message-wrapper">
          <div v-if="msg.role === 'system'" class="system-msg">
            <span class="system-text">{{ msg.content }}</span>
          </div>

          <div v-else :class="['message-row', msg.role === 'user' ? 'row-right' : 'row-left']">
            <div :class="['avatar', msg.role === 'user' ? 'user-avatar' : (msg.isHuman ? 'human-avatar' : 'bot-avatar')]">
              {{ msg.role === 'user' ? '我' : (msg.isHuman ? '客服' : 'AI') }}
            </div>
            <div class="message-content">
              <div :class="['bubble', msg.role === 'user' ? 'user-bubble' : (msg.isHuman ? 'human-bubble' : 'bot-bubble')]">
                {{ msg.content }}
              </div>
              <div class="msg-time">{{ msg.time }}</div>
            </div>
          </div>
        </div>

        <transition name="fade">
          <div v-if="loading" class="message-row row-left">
            <div class="avatar bot-avatar">AI</div>
            <div class="bubble bot-bubble typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </transition>
      </main>

      <footer class="chat-footer">
        <div class="input-wrapper">
          <el-input
            v-model="userInput"
            placeholder="请描述您遇到的问题，按 Enter 发送..."
            size="large"
            class="custom-input"
            @keydown.enter.prevent="handleEnter"
            :disabled="loading"
          />
          <el-button 
            type="primary" 
            size="large" 
            class="send-btn"
            @click="sendMessage" 
            :loading="loading"
          >
            发送
          </el-button>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000/api'

const userInput = ref('')
const messages = ref([])
const loading = ref(false)
const sessionId = ref('')
const messageListRef = ref(null)
const isHumanMode = ref(false)

let pollTimer = null
let lastPolledHumanMsg = '' 

const getTime = () => {
  const d = new Date()
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

const handleEnter = (e) => {
  if (e.isComposing) return;
  sendMessage()
}

onMounted(async () => {
  const saved = localStorage.getItem('chat_session_id')
  if (saved) sessionId.value = saved

  messages.value.push({
    role: 'bot',
    content: '您好，我是智能客服助手，请问有什么可以帮您？',
    time: getTime()
  })

  if (sessionId.value) {
    try {
      const res = await axios.get(`${API_BASE}/chat/poll/`, {
        params: { session_id: sessionId.value }
      })
      if (res.data.replies && res.data.replies.length > 0) {
        lastPolledHumanMsg = res.data.replies[res.data.replies.length - 1]
        isHumanMode.value = true 
      }
    } catch (e) {}
  }

  pollTimer = setInterval(async () => {
    if (!isHumanMode.value || !sessionId.value) return
    try {
      const res = await axios.get(`${API_BASE}/chat/poll/`, {
        params: { session_id: sessionId.value }
      })
      
      if (res.data.replies && res.data.replies.length > 0) {
        const latestReply = res.data.replies[res.data.replies.length - 1]
        if (latestReply !== lastPolledHumanMsg) {
          messages.value.push({ 
            role: 'bot', 
            content: latestReply,
            isHuman: true,
            time: getTime()
          })
          lastPolledHumanMsg = latestReply
          scrollToBottom()
        }
      }
    } catch (e) {}
  }, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const shortSessionId = computed(() => {
  return sessionId.value ? sessionId.value.slice(0, 8) : '新会话'
})

async function scrollToBottom() {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

// 点击按钮取消人工排队
async function cancelHuman() {
  if (!sessionId.value) return
  try {
    await axios.post(`${API_BASE}/chat/cancel_human/`, {
      session_id: sessionId.value
    })
    isHumanMode.value = false
    messages.value.push({ 
      role: 'system', 
      content: '您已结束人工服务，AI 助手继续为您服务。' 
    })
    scrollToBottom()
  } catch (err) {
    console.error('取消失败', err)
  }
}

async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text, time: getTime() })
  userInput.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await axios.post(`${API_BASE}/chat/`, {
      message: text,
      session_id: sessionId.value || null
    })

    sessionId.value = res.data.session_id
    localStorage.setItem('chat_session_id', sessionId.value)

    if (res.data.is_human_mode && !isHumanMode.value) {
      isHumanMode.value = true
      messages.value.push({ 
        role: 'system', 
        content: '系统已为您转接人工客服，请稍候...' 
      })
    } else if (!res.data.is_human_mode && isHumanMode.value) {
      isHumanMode.value = false
      messages.value.push({ 
        role: 'system', 
        content: '人工客服已断开，已交还给 AI 助手。' 
      })
    }

    setTimeout(() => {
        messages.value.push({ 
            role: 'bot', 
            content: res.data.reply,
            time: getTime()
        })
        loading.value = false
        scrollToBottom()
    }, 600)
    
  } catch (err) {
    messages.value.push({ role: 'bot', content: '网络异常，请稍后再试。', time: getTime() })
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.chat-wrapper { height: 100vh; display: flex; justify-content: center; align-items: center; background: #e9ecef; background-image: radial-gradient(#d1d5db 1px, transparent 1px); background-size: 20px 20px; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; }
.chat-container { width: 100%; max-width: 900px; height: 95vh; background: #ffffff; border-radius: 16px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1); display: flex; flex-direction: column; overflow: hidden; }
.chat-header { background: linear-gradient(135deg, #4f8cff, #3a7bd5); color: white; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 12px; }
.logo-icon { width: 40px; height: 40px; background: rgba(255,255,255,0.2); border-radius: 10px; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 18px; }
.header-title h1 { margin: 0; font-size: 18px; font-weight: 600; }
.subtitle { font-size: 12px; opacity: 0.8; }
.header-right { display: flex; align-items: center; gap: 16px; }
.session-tag { font-size: 13px; opacity: 0.9; background: rgba(0,0,0,0.15); padding: 4px 10px; border-radius: 20px; }

/* 取消按钮样式 */
.human-badge { 
  background: #ff9f43; color: white; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: bold; 
  box-shadow: 0 0 10px rgba(255,159,67,0.5); animation: pulse 2s infinite; 
  cursor: pointer; transition: 0.3s; user-select: none;
}
.human-badge:hover { background: #ff7b00; transform: scale(1.05); }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(255,159,67, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(255,159,67, 0); } 100% { box-shadow: 0 0 0 0 rgba(255,159,67, 0); } }

.chat-body { flex: 1; padding: 24px; overflow-y: auto; background: #f8f9fa; display: flex; flex-direction: column; gap: 20px; }
.message-row { display: flex; gap: 12px; align-items: flex-start; max-width: 80%; }
.row-left { align-self: flex-start; }
.row-right { align-self: flex-end; flex-direction: row-reverse; }
.message-content { display: flex; flex-direction: column; }
.msg-time { font-size: 11px; color: #b0b0b0; margin-top: 4px; text-align: right; }
.row-left .msg-time { text-align: left; }
.avatar { width: 40px; height: 40px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 14px; font-weight: bold; color: white; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.bot-avatar { background: #4f8cff; }
.user-avatar { background: #6c757d; }
.human-avatar { background: #ff9f43; }
.bubble { padding: 12px 16px; border-radius: 12px; font-size: 15px; line-height: 1.6; word-break: break-word; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
.bot-bubble { background: white; color: #333; border-top-left-radius: 2px; }
.user-bubble { background: #4f8cff; color: white; border-top-right-radius: 2px; }
.human-bubble { background: #fff8f0; color: #d35400; border: 1px solid #ffccaa; border-top-left-radius: 2px; }
.system-msg { display: flex; justify-content: center; width: 100%; margin: 10px 0; }
.system-text { background: rgba(0, 0, 0, 0.05); color: #666; font-size: 12px; padding: 6px 12px; border-radius: 16px; }
.typing-indicator { display: flex; gap: 4px; padding: 14px 18px; }
.typing-indicator span { width: 6px; height: 6px; background: #909399; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out both; }
.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }
.chat-footer { padding: 20px 24px; background: white; border-top: 1px solid #f0f0f0; }
.input-wrapper { display: flex; gap: 12px; }
.custom-input :deep(.el-input__wrapper) { border-radius: 24px; padding: 4px 20px; background: #f4f6f8; box-shadow: none; }
.custom-input :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px #4f8cff inset; background: white; }
.send-btn { border-radius: 24px; padding: 0 24px; background: #4f8cff; border: none; font-weight: 600; }
.send-btn:hover { background: #3a7bd5; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>