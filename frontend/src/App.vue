<template>
    <div class="chat-container">
        <header class="chat-header">
            <h1>智能客服系统</h1>
            <span class="session-tag">会话：{{ shortSessionId }}</span>
        </header>

        <main class="chat-body" ref="messageListRef">
            <div v-for="(msg, index) in messages"
                 :key="index"
                 :class="['message-row', msg.role === 'user' ? 'row-user' : 'row-bot']">
                <div class="avatar">{{ msg.role === 'user' ? '我' : 'AI' }}</div>
                <div class="bubble">{{ msg.content }}</div>
            </div>

            <div v-if="loading" class="message-row row-bot">
                <div class="avatar">AI</div>
                <div class="bubble typing">正在输入…</div>
            </div>
        </main>

        <footer class="chat-footer">
            <el-input v-model="userInput"
                      placeholder="请输入您的问题，按回车发送"
                      size="large"
                      @keyup.enter="sendMessage"
                      :disabled="loading" />
            <el-button type="primary"
                       size="large"
                       @click="sendMessage"
                       :loading="loading">
                发送
            </el-button>
        </footer>
    </div>
</template>

<script setup>
    import { ref, computed, nextTick, onMounted } from 'vue'
    import axios from 'axios'

    const API_BASE = 'http://127.0.0.1:8000/api'

    const userInput = ref('')
    const messages = ref([])
    const loading = ref(false)
    const sessionId = ref('')
    const messageListRef = ref(null)

    // 从 localStorage 恢复会话
    onMounted(() => {
    const saved = localStorage.getItem('chat_session_id')
    if (saved) {
    sessionId.value = saved
    } else {
    sessionId.value = ''
    }

    messages.value.push({
    role: 'bot',
    content: '您好，我是智能客服助手，请问有什么可以帮您？'
    })
    })

    // 会话 ID 显示前 8 位
    const shortSessionId = computed(() => {
    if (!sessionId.value) return '新会话'
    return sessionId.value.slice(0, 8)
    })

    // 滚动到底部
    async function scrollToBottom() {
    await nextTick()
    if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
    }

    // 发送消息
    async function sendMessage() {
    const text = userInput.value.trim()
    if (!text || loading.value) return

    messages.value.push({ role: 'user', content: text })
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

    messages.value.push({
    role: 'bot',
    content: res.data.reply
    })
    } catch (err) {
    messages.value.push({
    role: 'bot',
    content: '抱歉，服务暂时不可用，请稍后再试。'
    })
    console.error(err)
    } finally {
    loading.value = false
    scrollToBottom()
    }
    }
</script>

<style scoped>
    .chat-container {
        display: flex;
        flex-direction: column;
        height: 100vh;
        max-width: 900px;
        margin: 0 auto;
        background: #f5f7fa;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    .chat-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 24px;
        background: #409eff;
        color: #fff;
    }

        .chat-header h1 {
            font-size: 18px;
            margin: 0;
        }

    .session-tag {
        font-size: 12px;
        opacity: 0.85;
    }

    .chat-body {
        flex: 1;
        overflow-y: auto;
        padding: 24px;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .message-row {
        display: flex;
        align-items: flex-start;
        gap: 10px;
    }

    .row-user {
        flex-direction: row-reverse;
    }

    .avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: #409eff;
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        flex-shrink: 0;
    }

    .row-bot .avatar {
        background: #67c23a;
    }

    .bubble {
        max-width: 70%;
        padding: 10px 14px;
        border-radius: 8px;
        background: #fff;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        line-height: 1.5;
        word-break: break-word;
        white-space: pre-wrap;
    }

    .row-user .bubble {
        background: #409eff;
        color: #fff;
    }

    .typing {
        color: #909399;
        font-style: italic;
    }

    .chat-footer {
        display: flex;
        gap: 12px;
        padding: 16px 24px;
        background: #fff;
        border-top: 1px solid #ebeef5;
    }
</style>