Flask 后端框架骨架

说明:
- 应用工厂：`create_app` 位于 `app.py`
- 配置：`config.py`
- 扩展：`extensions.py`（数据库、迁移、CORS）
- 控制器：`controller.py` 中提供 `api_bp` 蓝图

如何使用：

1. 创建虚拟环境并安装依赖：

   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

2. 运行：

   python app.py

依赖示例请参见 `requirements.txt`。
