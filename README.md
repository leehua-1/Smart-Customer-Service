本项目是一个基于 Vue 3 和 Django 以及本地大模型 Qwen2.5 构建的商业级智能客服系统

核心特性
双层意图识别：本地 BGE 极速响应结合 Qwen2.5 大模型兜底，兼顾速度与准确率
多轮对话管理：基于状态机的槽位填充，支持多轮追问与上下文记忆
情感感知：识别用户情绪，在用户愤怒时自动追加安抚话术
人机无缝协同：AI 无法处理时自动转人工排队，后台提供大屏看板与客服工作台，支持极速连续回复

技术栈
前端：Vue 3 Vite Element Plus Axios
后端：Django 5 Django REST Framework MySQL
算法与模型：Sentence Transformers (BGE) FAISS Ollama (Qwen2.5)

快速启动
1 大模型：ollama run qwen2.5:1.5b
2 后端：cd backend 然后 python manage.py runserver
3 前端：cd frontend 然后 npm install 和 npm run dev
