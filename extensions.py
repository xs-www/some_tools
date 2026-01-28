from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

# 数据库、迁移、跨域实例化（延迟初始化）
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
