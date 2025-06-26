import os
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Настройка CORS
CORS(app, origins="*")

# Переменные окружения для Neon PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgres://neondb_owner:npg_2oKtBfJVQPy3@ep-orange-hat-a45q4dys-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require",
)
DATABASE_URL_UNPOOLED = os.getenv(
    "DATABASE_URL_UNPOOLED",
    "postgresql://neondb_owner:npg_2oKtBfJVQPy3@ep-orange-hat-a45q4dys.us-east-1.aws.neon.tech/neondb?sslmode=require",
)

# Параметры подключения
PGHOST = os.getenv("PGHOST", "ep-orange-hat-a45q4dys-pooler.us-east-1.aws.neon.tech")
PGUSER = os.getenv("PGUSER", "neondb_owner")
PGDATABASE = os.getenv("PGDATABASE", "neondb")
PGPASSWORD = os.getenv("PGPASSWORD", "npg_2oKtBfJVQPy3")


def get_conn():
    """Получение подключения к базе данных"""
    try:
        # Используем pooled connection для лучшей производительности
        conn = psycopg2.connect(DATABASE_URL)
        logger.info("✅ Подключение к Neon PostgreSQL успешно")
        return conn
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        raise


def init_database():
    """Инициализация базы данных"""
    try:
        with get_conn() as conn, conn.cursor() as cur:
            # Создание таблицы
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS region_capacity (
                    id SERIAL PRIMARY KEY,
                    region_name VARCHAR(100) UNIQUE NOT NULL,
                    occupied INTEGER DEFAULT 0 CHECK (occupied >= 0),
                    total_capacity INTEGER DEFAULT 50 CHECK (total_capacity > 0),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
            )

            # Создание индексов для производительности
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_region_name ON region_capacity(region_name);
                CREATE INDEX IF NOT EXISTS idx_updated_at ON region_capacity(updated_at);
            """
            )

            # Функция для обновления updated_at
            cur.execute(
                """
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """
            )

            # Триггер для автоматического обновления updated_at
            cur.execute(
                """
                DROP TRIGGER IF EXISTS update_region_capacity_updated_at ON region_capacity;
                CREATE TRIGGER update_region_capacity_updated_at 
                    BEFORE UPDATE ON region_capacity 
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """
            )

            # Вставка начальных данных
            cur.execute(
                """
                INSERT INTO region_capacity (region_name, occupied, total_capacity) 
                VALUES 
                    ('Северный регион', 25, 50),
                    ('Южный регион', 42, 50),
                    ('Восточный регион', 18, 50),
                    ('Западный регион', 35, 50)
                ON CONFLICT (region_name) DO NOTHING;
            """
            )

            conn.commit()
            logger.info("✅ База данных инициализирована")

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise


@app.route("/", methods=["GET"])
def home():
    """Главная страница API"""
    return {
        "message": "Regions Database API",
        "version": "2.0",
        "database": "Neon PostgreSQL",
        "features": [
            "CRUD операции с регионами",
            "Автоматическое обновление времени",
            "Валидация данных",
            "Индексы для производительности",
        ],
        "endpoints": [
            "GET /regions - получить все регионы",
            "POST /regions - создать новый регион",
            "POST /regions/<region>/add - добавить места",
            "POST /regions/<region>/remove - убрать места",
            "PUT /regions/<region>/capacity - изменить вместимость",
            "DELETE /regions/<region> - удалить регион",
            "GET /stats - получить статистику",
            "GET /test - проверка работы сервера",
        ],
    }


@app.route("/regions", methods=["GET"])
def get_regions():
    """Получить все регионы"""
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT region_name, occupied, total_capacity, updated_at
                FROM region_capacity
                ORDER BY region_name;
            """
            )
            rows = cur.fetchall()

        regions = [
            {
                "region": r[0],
                "occupied": r[1],
                "total": r[2],
                "updated_at": r[3].isoformat() if r[3] else None,
            }
            for r in rows
        ]

        logger.info(f"Получено {len(regions)} регионов")
        return jsonify(regions)

    except Exception as e:
        logger.error(f"❌ Ошибка в get_regions: {e}")
        return {"error": str(e)}, 500


@app.route("/regions", methods=["POST"])
def create_region():
    """Создать новый регион"""
    data = request.json
    region_name = data.get("region_name", "").strip()
    total_capacity = data.get("total_capacity", 50)

    if not region_name:
        return {"error": "region_name is required"}, 400

    if total_capacity <= 0:
        return {"error": "total_capacity must be positive"}, 400

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO region_capacity (region_name, occupied, total_capacity)
                VALUES (%s, 0, %s)
                RETURNING region_name, occupied, total_capacity, updated_at;
            """,
                (region_name, total_capacity),
            )

            new_region = cur.fetchone()
            conn.commit()

        logger.info(f"Создан новый регион: {region_name}")
        return {
            "region": new_region[0],
            "occupied": new_region[1],
            "total": new_region[2],
            "updated_at": new_region[3].isoformat() if new_region[3] else None,
        }

    except psycopg2.IntegrityError:
        return {"error": "Region already exists"}, 400
    except Exception as e:
        logger.error(f"❌ Ошибка в create_region: {e}")
        return {"error": str(e)}, 500


@app.route("/regions/<region>/add", methods=["POST"])
def add_spaces(region):
    """Добавить места в регионе"""
    delta = int(request.json.get("delta", 0))
    if delta <= 0:
        return {"error": "delta must be positive"}, 400

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE region_capacity
                SET occupied = occupied + %s
                WHERE region_name = %s
                  AND occupied + %s <= total_capacity
                RETURNING region_name, occupied, total_capacity, updated_at;
            """,
                (delta, region, delta),
            )

            updated = cur.fetchone()
            if not updated:
                return {"error": "Not enough free places or region not found"}, 400
            conn.commit()

        logger.info(f"Добавлено {delta} мест в регион {region}")
        return {
            "region": updated[0],
            "occupied": updated[1],
            "total": updated[2],
            "updated_at": updated[3].isoformat() if updated[3] else None,
        }

    except Exception as e:
        logger.error(f"❌ Ошибка в add_spaces: {e}")
        return {"error": str(e)}, 500


@app.route("/regions/<region>/remove", methods=["POST"])
def remove_spaces(region):
    """Убрать места из региона"""
    delta = int(request.json.get("delta", 0))
    if delta <= 0:
        return {"error": "delta must be positive"}, 400

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE region_capacity
                SET occupied = occupied - %s
                WHERE region_name = %s
                  AND occupied - %s >= 0
                RETURNING region_name, occupied, total_capacity, updated_at;
            """,
                (delta, region, delta),
            )

            updated = cur.fetchone()
            if not updated:
                return {"error": "Not enough occupied spaces or region not found"}, 400
            conn.commit()

        logger.info(f"Убрано {delta} мест из региона {region}")
        return {
            "region": updated[0],
            "occupied": updated[1],
            "total": updated[2],
            "updated_at": updated[3].isoformat() if updated[3] else None,
        }

    except Exception as e:
        logger.error(f"❌ Ошибка в remove_spaces: {e}")
        return {"error": str(e)}, 500


@app.route("/regions/<region>/capacity", methods=["PUT"])
def update_capacity(region):
    """Изменить вместимость региона"""
    new_capacity = int(request.json.get("capacity", 0))
    if new_capacity <= 0:
        return {"error": "capacity must be positive"}, 400

    try:
        with get_conn() as conn, conn.cursor() as cur:
            # Проверяем текущее состояние
            cur.execute(
                "SELECT occupied FROM region_capacity WHERE region_name = %s;",
                (region,),
            )
            result = cur.fetchone()
            if not result:
                return {"error": "Region not found"}, 404

            occupied = result[0]
            if new_capacity < occupied:
                return {
                    "error": f"New capacity ({new_capacity}) cannot be less than occupied spaces ({occupied})"
                }, 400

            cur.execute(
                """
                UPDATE region_capacity
                SET total_capacity = %s
                WHERE region_name = %s
                RETURNING region_name, occupied, total_capacity, updated_at;
            """,
                (new_capacity, region),
            )

            updated = cur.fetchone()
            conn.commit()

        logger.info(f"Изменена вместимость региона {region} на {new_capacity}")
        return {
            "region": updated[0],
            "occupied": updated[1],
            "total": updated[2],
            "updated_at": updated[3].isoformat() if updated[3] else None,
        }

    except Exception as e:
        logger.error(f"❌ Ошибка в update_capacity: {e}")
        return {"error": str(e)}, 500


@app.route("/regions/<region>", methods=["DELETE"])
def delete_region(region):
    """Удалить регион"""
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM region_capacity
                WHERE region_name = %s
                RETURNING region_name;
            """,
                (region,),
            )

            deleted = cur.fetchone()
            if not deleted:
                return {"error": "Region not found"}, 404
            conn.commit()

        logger.info(f"Удален регион: {region}")
        return {"message": f"Region '{region}' deleted successfully"}

    except Exception as e:
        logger.error(f"❌ Ошибка в delete_region: {e}")
        return {"error": str(e)}, 500


@app.route("/stats", methods=["GET"])
def get_stats():
    """Получить общую статистику"""
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    COUNT(*) as total_regions,
                    SUM(occupied) as total_occupied,
                    SUM(total_capacity) as total_capacity,
                    AVG(CAST(occupied AS FLOAT) / CAST(total_capacity AS FLOAT) * 100) as avg_occupancy,
                    MAX(updated_at) as last_update
                FROM region_capacity;
            """
            )
            stats = cur.fetchone()

        return {
            "total_regions": stats[0] or 0,
            "total_occupied": stats[1] or 0,
            "total_capacity": stats[2] or 0,
            "average_occupancy": round(stats[3] or 0, 2),
            "last_update": stats[4].isoformat() if stats[4] else None,
        }

    except Exception as e:
        logger.error(f"❌ Ошибка в get_stats: {e}")
        return {"error": str(e)}, 500


@app.route("/test", methods=["GET"])
def test():
    """Проверка работы сервера"""
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM region_capacity;")
            count = cur.fetchone()[0]

        return {
            "status": "Server is running",
            "message": "Neon PostgreSQL connection works!",
            "database": "Neon PostgreSQL",
            "host": PGHOST,
            "database_name": PGDATABASE,
            "regions_count": count,
            "server_url": "https://sternly-prophetic-taipan.cloudpub.ru:443",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Ошибка в test: {e}")
        return {"status": "Database error", "error": str(e)}, 500


# Обработка ошибок
@app.errorhandler(404)
def not_found(error):
    return {"error": "Endpoint not found"}, 404


@app.errorhandler(500)
def internal_error(error):
    return {"error": "Internal server error"}, 500


if __name__ == "__main__":
    print("🚀 Запуск сервера с Neon PostgreSQL...")
    print(f"🗄️ База данных: {PGDATABASE}@{PGHOST}")
    print("🌐 Сервер: https://sternly-prophetic-taipan.cloudpub.ru:443")

    # Инициализация базы данных
    try:
        init_database()
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")
        exit(1)

    # Запуск сервера
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
